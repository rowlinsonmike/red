import typer
from typing_extensions import Annotated
from dataclasses import dataclass
import boto3
import json
import sh
import sys
import time
import json
from red.utility import print, load_config
from red.content import INIT_FINISH
from red import ecr, docker, utility, content, iam, compute, schedule, batch
import shlex
import os
from rich.progress import Progress, SpinnerColumn, TextColumn
from datetime import datetime

selected_date = None

app = typer.Typer()


@app.command("init")
def run_init(
    name: str = typer.Argument(..., help="name of project"),
    batch: bool = typer.Option(False, "--batch", "-b", help="init a batch environment"),
    code: bool = typer.Option(
        False, "--code", "-c", help="init a serverless environment"
    ),
):
    if not name:
        print("Must use the --name option")
    name = utility.slugify(name)
    utility.create_folder(name)
    os.chdir(name)
    envs = (
        content.BATCH_ENV_FILE
        if batch
        else content.CODE_ENV_FILE if code else content.ENV_FILE
    )
    env_content = {"Name": name, **envs}
    env_content = json.dumps(env_content, indent=2)
    utility.create_file(".red", env_content)
    if not code:
        utility.create_file(
            "Dockerfile",
            content.BATCH_DOCKERFILE if batch else content.PYTHON_LAMBDA_DOCKERFILE,
        )
        if not batch:
            utility.create_file("lambda_function.py", content.PYTHON_LAMBDA_FUNCTION)
        else:
            utility.create_file("main.py", content.BATCH_PYTHON)
    else:
        # serverless
        utility.create_file("main.py", content.PYTHON_LAMBDA_FUNCTION)
        utility.create_file("requirements.txt", "")
    print(INIT_FINISH(name))


@app.command("deploy")
def run_deploy(
    skip_build: bool = typer.Option(
        False,
        "--skip-build",
        "-sb",
        help="skip build phase (only for container workloads)",
    ),
    skip_push: bool = typer.Option(
        False,
        "--skip-push",
        "-sp",
        help="skip push phase (only for container workloads)",
    ),
    no_infra: bool = typer.Option(
        False,
        "--no-infra",
        "-ni",
        help="only build and deploy image to ECR, will not deploy compute infra (only for container workloads)",
    ),
):
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task("[#ff4444]Deploying RED project...", total=None)
        config = load_config()
        name = config.get("Name")
        # create ecr container if it doesn't exist and collect ecr arn
        if config.get("Type") == "LambdaCode":
            progress.update(
                task, description=f"[#ff4444]Creating Serverless Lambda Environment"
            )
            role_arn = iam.create_lambda_role(name, name, config.get("IamPolicy"))
            time.sleep(10)
            config["RoleArn"] = role_arn
            compute.create_serverless_function(name, config)
        else:
            repo_uri = ecr.create_ecr(name)
            account_ecr = repo_uri.split("/")[0]
            # build and ship image to ecr
            if not skip_build:
                progress.update(task, description=f"[#ff4444]Pushing to ECR")
                docker.push_to_ecr(repo_uri, account_ecr, skip_push)
            if no_infra:
                return
            if skip_push:
                return
            if config.get("Type") == "Batch":
                progress.update(
                    task, description=f"[#ff4444]Creating Batch Environment"
                )
                batch.create_batch_environment(name, repo_uri, config)
            else:
                progress.update(
                    task, description=f"[#ff4444]Creating Lambda Environment"
                )
                # create  / update iam role
                role_arn = iam.create_lambda_role(name, name, config.get("IamPolicy"))
                time.sleep(10)
                config["RoleArn"] = role_arn
                compute.create_function(name, repo_uri, config)
    print("RED project deployed")


@app.command("run")
def run_execute(
    payload: str = typer.Option("{}", "--payload", "-p", help="optional payload"),
    cron: str = typer.Option("", "--cron", "-c", help="optional schedule cron job"),
    cron_name: str = typer.Option("", "--schedule_name", "-sn", help="schedule name"),
    once: str = typer.Option(
        "", "--once", "-o", help="one time one, yyyy-mm-ddThh:mm:ss"
    ),
    detached: bool = typer.Option(
        False, "--detached", "-d", help="execute in async mode"
    ),
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
    compute_type = config.get("Type")
    if cron or once:
        if not cron_name:
            print("Must specify --schedule_name")
            return
        cron_name = utility.slugify(cron_name)
        schedule.schedule_lambda_compute(
            name, cron_name, payload, cron, once, compute_type, config
        )
        print("RED project schedule created")
    else:
        if compute_type == "Batch":
            envs = batch.get_job_definition_environment_variables(name)
            envs = [{"name": x.get("Name"), "value": x.get("Value")} for x in envs]
            envs.extend([{"name": k, "value": v} for k, v in payload.items()])
            batch.submit_batch_job(f"{name}_execution", name, name, environment=envs)
            print("RED project batch job submitted")
            return
        compute.execute_and_tail_lambda(name, payload, detached)


@app.command()
def sched(log: str = typer.Option("", "--log", "-l", help="log stream to view")):
    config = load_config()
    name = config.get("Name")
    schedule.list_schedules(name)


@app.command("kill")
def run_kill(
    schedule_name: str = typer.Option("", "--schedule", "-s", help="schedule name")
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
        if config.get("Type") == "Batch":
            batch.delete_batch_environment(name)
            return
        compute.delete_resources(name, config.get("type"))
        print("Deleted RED project")


def select_option(text, options):
    while True:
        choice = typer.prompt(
            text,
            type=int,
            show_default=False,
        )
        if 1 <= choice <= len(options):
            return options[choice - 1]
        print("Invalid option. Please try again.")


@app.command()
def log(latest: bool = typer.Option(False, "--latest", "-l", help="get latest log")):
    config = load_config()
    name = config.get("Name")
    if latest:
        return compute.get_log(name, "_latest", config.get("Type"))
    logs = compute.list_logs(name, config.get("Type"))
    log = select_option("Select a log number", logs)
    compute.get_log(name, log.get("logStreamName"), config.get("Type"))


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """🦊 RED (Really Easy Deployments)"""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


if __name__ == "__main__":
    app()
