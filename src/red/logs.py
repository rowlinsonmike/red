import sys

import boto3
import questionary
from rich import box
from rich.markdown import Markdown
from rich.panel import Panel

from red.utility import milliseconds_to_date, print


def list_logs(name):
    logs_client = boto3.client("logs")
    log_group_name = f"{name}"
    response = logs_client.describe_log_streams(
        logGroupName=log_group_name, orderBy="LastEventTime", descending=True, limit=10
    )
    if not len(response["logStreams"]):
        print("No logs")
        sys.exit()
    selection = questionary.select(
        "Select Log",
        choices=[
            f"{index + 1}. {milliseconds_to_date(x.get('creationTime'))} {x.get('logStreamName')}"
            for index, x in enumerate(response["logStreams"])
        ],
    ).ask()
    return response["logStreams"][int(selection.split(".")[0]) - 1]


def get_log(name, log_stream_name):
    logs_client = boto3.client("logs")
    log_group_name = f"{name}"
    if log_stream_name == "_latest":
        stream_response = logs_client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy="LastEventTime",
            descending=True,
            limit=1,
        )
        if not stream_response.get("logStreams"):
            panel = Panel(
                Markdown("no logs"),
                title="🦊 RED project logs",
                border_style="#ff4444",
                box=box.ROUNDED,
            )
            return print(panel)
        log_stream_name = stream_response["logStreams"][0]["logStreamName"]

    response = logs_client.get_log_events(
        logGroupName=log_group_name, logStreamName=log_stream_name, startFromHead=True
    )
    for event in response["events"]:
        print(event["timestamp"], event["message"])
