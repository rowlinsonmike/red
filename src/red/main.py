import json
import os
import platform
import shlex
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import boto3
import questionary
import rich
import sh
import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing_extensions import Annotated

from red import batch, constants, docker, ecr, logs, schedule, utility
from red.infra import select_network_resources
from red.utility import load_config, print

selected_date = None

app = typer.Typer()


@app.command("init")
def run_init():
    cwd = Path.cwd()
    if (Path(cwd) / ".red").exists():
        return print("RED already in project")
    name = cwd.name.replace(" ", "-")
    env_content = {
        "Name": name,
        "VPC": {"SubnetIds": [], "SecurityGroupIds": []},
    }
    env_content["Arch"] = platform.machine()
    cpu = questionary.select(
        "Select CPU Count",
        choices=constants.SPECS.keys(),
    ).ask()
    memory = questionary.select(
        "Memory Size (MB)",
        choices=[str(x) for x in constants.SPECS.get(str(cpu))],
    ).ask()
    env_content["Cpu"] = cpu
    env_content["MemorySize"] = memory

    # timeout
    def validate_timeout(entry):
        try:
            entry = int(entry)
            if entry < 1:
                return "Minimum value is 1"
            if entry > 10000:
                return "Maximum value is 20160"  # 1,209,600 secs,  max 14 days for fargate job
        except:
            return "Not a valid number"
        return True

    timeout = questionary.text(
        "Maximum time in minutes your job can run?", validate=validate_timeout
    ).ask()
    env_content["Timeout"] = int(timeout) * 60
    is_public = questionary.confirm(
        "Is the environment public? If private, you must have a NAT Gateway for your private Batch environment to interact with the internet"
    ).ask()
    env_content["assignPublicIp"] = "ENABLED" if is_public else "DISABLED"
    resources = select_network_resources()
    env_content["VPC"]["SubnetIds"] = resources["subnets"]
    env_content["VPC"]["SecurityGroupIds"] = resources["security_groups"]
    env_content["IamPolicy"] = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ssmmessages:CreateControlChannel",
                    "ssmmessages:CreateDataChannel",
                    "ssmmessages:OpenControlChannel",
                    "ssmmessages:OpenDataChannel",
                ],
                "Resource": "*",
            },
            {
                "Effect": "Allow",
                "Action": [
                    "ecr:GetAuthorizationToken",
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                ],
                "Resource": "*",
            },
        ],
    }
    env_content = json.dumps(env_content, indent=2)
    if utility.file_exists("Dockerfile"):
        utility.create_file(".red", env_content)
        print("Dockerfile already exists.")
    else:
        utility.create_file(".red", env_content)
        utility.create_file("Dockerfile", constants.BATCH_DOCKERFILE)
        utility.create_file("main.py", constants.BATCH_PYTHON)
    print("🦊 RED project setup!")


@app.command("deploy")
def run_deploy():
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task("[#ff4444]Deploying RED project...", total=None)
        config = load_config()
        name = config.get("Name")
        progress.update(task, description="[#ff4444]Confirming ECR")
        repo_uri = ecr.create_ecr(name)
        account_ecr = repo_uri.split("/")[0]
        progress.update(task, description="[#ff4444]Pushing to ECR")
        docker.push_to_ecr(repo_uri, account_ecr, config, quiet=True)
        progress.update(task, description=f"[#ff4444]Creating Batch Environment")
        batch.create_batch_environment(name, repo_uri, config)
    print("RED project deployed")


@app.command("run")
def run_execute(
    payload: str = typer.Option("{}", "--payload", "-p", help="optional payload"),
    cron: bool = typer.Option(False, "--cron", "-c", help="optional schedule cron job"),
):
    config = load_config()
    name = config.get("Name")
    try:
        json_data = json.loads(payload)
    except json.JSONDecodeError:
        try:
            json_data = json.loads(shlex.quote(payload))
        except json.JSONDecodeError:
            raise typer.BadParameter("Invalid JSON input")
    payload = json_data
    if cron:
        schedule_name = questionary.text("Schedule Name").ask()
        cron_exp = questionary.text("AWS cron expression.").ask()
        is_once = questionary.confirm("One time run?").ask()
        cron_name = utility.slugify(schedule_name)
        schedule.schedule_compute(name, cron_name, payload, cron_exp, is_once, config)
        print("RED project schedule created")
    else:
        envs = batch.get_job_definition_environment_variables(name)
        envs = [{"name": x.get("Name"), "value": x.get("Value")} for x in envs]
        envs.extend([{"name": k, "value": v} for k, v in payload.items()])
        batch.submit_batch_job(f"{name}_execution", name, name, environment=envs)
        print("RED project batch job submitted")
        return


# @app.command("pull")
# def run_pull(
#     repo_uri: str = typer.Argument(
#         ...,
#         help='ECR repo uri (e.g. "ECR image URI, .e.g 123456789012.dkr.ecr.us-east-1.amazonaws.com/myimage:latest")',
#     ),
# ):
#     with Progress(
#         SpinnerColumn(),
#         TextColumn("[progress.description]{task.description}"),
#         transient=True,
#     ) as progress:
#         task = progress.add_task("[#ff4444]Pulling ECR Image...", total=None)
#         account_ecr = repo_uri.split("/")[0]
#         docker.pull_from_ecr(repo_uri, account_ecr)
#         print("Pulled ECR Image!")


@app.command()
def cron(
    delete: bool = typer.Option(
        False, "--delete", "-d", help="delete selected cron jobs"
    ),
):
    config = load_config()
    name = config.get("Name")
    schedules, data = schedule.list_schedules(name)
    if not len(schedules):
        return print("No schedules")
    if delete:
        selected_schedules = questionary.checkbox(
            "Select Schedules to delete:",
            choices=schedules,
            instruction="(Select at least 1)",
        ).ask()
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task(
                "[#ff4444]Deleting selected RED schedules...", total=None
            )
            for x in selected_schedules:
                schedule_name = data[int(x.split(".")[0]) - 1].get("Name")
                progress.update(task, description=f"[#ff4444]Deleting Schedule")
                schedule.delete_schedule(schedule_name, name)

    else:
        selected = questionary.select(
            "Select Schedule to View",
            choices=schedules,
        ).ask()
        schedule_name = data[int(selected.split(".")[0]) - 1].get("Name")
        response = schedule.get_schedule(schedule_name, name)
        print(response)


@app.command("kill")
def run_kill(
    schedule_name: str = typer.Option("", "--schedule", "-s", help="schedule name"),
):
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task("[#ff4444]Deleting RED project...", total=None)
        config = load_config()
        name = config.get("Name")
        if schedule_name:
            progress.update(task, description=f"[#ff4444]Deleting Schedule")
            schedule_name = utility.slugify(schedule_name)
            schedule.delete_schedule(schedule_name, name)
            print("Deleted RED project schedule")
            return
        progress.update(task, description=f"[#ff4444]Deleting Schedule Group")
        schedule.delete_schedule_group(name)
        progress.update(task, advance=50)
        progress.update(task, description=f"[#ff4444]Deleting compute environment")
        batch.delete_batch_environment(name)
        progress.update(task, description=f"[#ff4444]Deleting ECR repo")
        ecr.delete_ecr_repo(name)

        print("Deleted RED project")


@app.command()
def log(latest: bool = typer.Option(False, "--latest", "-l", help="get latest log")):
    config = load_config()
    name = config.get("Name")
    if latest:
        return logs.get_log(name, "_latest")
    log = logs.list_logs(name)
    logs.get_log(name, log.get("logStreamName"))


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """🦊 RED (Really Easy Deployments)"""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


if __name__ == "__main__":
    app()
