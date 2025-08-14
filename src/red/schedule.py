import boto3
import json
import time
from red.utility import print, log_output
from zoneinfo import ZoneInfo
from red import iam, batch
from rich.table import Table
from rich.panel import Panel
from rich.console import Console
from rich.text import Text
from rich import box
from rich.markdown import Markdown
import os


@log_output
def create_schedule_group(name):
    try:
        scheduler_client = boto3.client("scheduler")
        response = scheduler_client.create_schedule_group(Name=name)
        time.sleep(5)
        return name
    except scheduler_client.exceptions.ConflictException:
        return name


@log_output
def schedule_lambda_compute(
    function_name, cron_name, payload, cron, onetime, compute_type, config
):
    # Initialize boto3 clients
    scheduler_client = boto3.client("scheduler")
    lambda_client = boto3.client("lambda")
    # create schedule group
    create_schedule_group(function_name)
    # Create IAM role for EventBridge Scheduler
    role_name = function_name + "_schedule"
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "scheduler.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    custom_policy_name = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "batch:SubmitJob",
                    "batch:DescribeJobDefinitions",
                    "batch:DescribeJobQueues",
                    "lambda:InvokeFunction",
                ],
                "Resource": ["*"],
            }
        ],
    }
    role_arn = iam.create_role(
        role_name,
        trust_policy,
        None,
        custom_policy_name=function_name + "_schedule_policy",
        custom_policy_document=custom_policy_name,
    )
    time.sleep(10)

    # Schedule details
    schedule_expression = f"cron({cron})" if cron else f"at({onetime})"

    # Get the current terminal's time zone
    current_timezone = time.tzname[0]

    # Create the schedule
    if compute_type == "Batch":
        sts_client = boto3.client("sts")
        account_id = sts_client.get_caller_identity()["Account"]
        job = f"arn:aws:batch:{scheduler_client.meta.region_name}:{account_id}:job-definition/{function_name}"
        queue = f"arn:aws:batch:{scheduler_client.meta.region_name}:{account_id}:job-queue/{function_name}"
        compute_env = f"arn:aws:batch:{scheduler_client.meta.region_name}:{account_id}:compute-environment/{function_name}"
        envs = batch.get_job_definition_environment_variables(function_name)
        envs.extend([{"Name": k, "Value": v} for k, v in payload.items()])
        schedule_response = scheduler_client.create_schedule(
            Name=cron_name,
            ActionAfterCompletion="NONE" if not onetime else "DELETE",
            GroupName=function_name,
            ScheduleExpression=schedule_expression,
            ScheduleExpressionTimezone=current_timezone,
            FlexibleTimeWindow={"Mode": "OFF"},
            Target={
                "Arn": "arn:aws:scheduler:::aws-sdk:batch:submitJob",
                "RoleArn": role_arn,
                "Input": json.dumps(
                    {
                        "JobDefinition": job,  # ARN of your job definition
                        "JobName": f"scheduled_{function_name}",
                        "JobQueue": queue,
                        "ContainerOverrides": {"Environment": envs},
                    }
                ),
            },
            State="ENABLED",
        )
    else:
        # Lambda function details
        lambda_function_name = function_name
        lambda_function_arn = lambda_client.get_function(
            FunctionName=lambda_function_name
        )["Configuration"]["FunctionArn"]
        schedule_response = scheduler_client.create_schedule(
            Name=cron_name,
            ActionAfterCompletion="NONE" if not onetime else "DELETE",
            GroupName=function_name,
            ScheduleExpression=schedule_expression,
            ScheduleExpressionTimezone=current_timezone,
            FlexibleTimeWindow={"Mode": "OFF"},
            Target={
                "Arn": lambda_function_arn,
                "RoleArn": role_arn,
                "Input": json.dumps(payload),
            },
            State="ENABLED",
        )
    print(f"Schedule created: {cron_name}")


@log_output
def delete_schedule(schedule, name):
    scheduler_client = boto3.client("scheduler")
    response = scheduler_client.delete_schedule(GroupName=name, Name=schedule)
    print(f"Deleted schedule: {schedule}")


@log_output
def delete_schedule_group(name):
    try:
        scheduler_client = boto3.client("scheduler")
        response = scheduler_client.delete_schedule_group(Name=name)
        time.sleep(5)
        print(f"Deleted schedule group: {name}")
    except:
        ...


def list_schedules(name):
    md = ""
    try:
        scheduler_client = boto3.client("scheduler")
        response = scheduler_client.list_schedules(GroupName=name).get("Schedules", [])
        for index, x in enumerate(response):
            md += f'{index+1}. {x.get("Name")} \n\t>{ x.get("CreationDate").strftime("%Y-%m-%d %H:%M:%S")}\n'

    except:
        md += "**No Schedules**"
    panel = Panel(
        Markdown(md),
        title="🦊 RED project schedules",
        border_style="#ff4444",
        box=box.ROUNDED,
    )
    print(panel)
