import boto3
from red.utility import print, milliseconds_to_date, log_output
import time
import json
from botocore.exceptions import ClientError
import base64
from botocore.exceptions import WaiterError
from rich.table import Table
from rich.panel import Panel
from rich.console import Console
from rich.text import Text
from rich import box
from rich.columns import Columns
from rich.markdown import Markdown


@log_output
def wait_for_function_active(function_name, max_wait_time=300):
    print("Waiting for Lambda function to be active...")
    lambda_client = boto3.client("lambda")
    start_time = time.time()

    while time.time() - start_time < max_wait_time:
        response = lambda_client.get_function(FunctionName=function_name)

        state = response["Configuration"]["State"]
        last_update_status = response["Configuration"].get("LastUpdateStatus")

        if state == "Active" and (
            last_update_status == "Successful" or last_update_status is None
        ):
            return True

        time.sleep(10)

    return False


@log_output
def create_function(function_name, repo_uri, config):
    lambda_client = boto3.client("lambda")

    try:
        existing_function = lambda_client.get_function(FunctionName=function_name)
        try:
            print(f"Updating Lambda function")
            current_version = int(
                existing_function["Configuration"]["Environment"]["Variables"].get(
                    "version", 0
                )
            )
        except:
            current_version = 0
        new_version = current_version + 1
        function_params = {
            "Timeout": config.get("Timeout", 300),
            "MemorySize": config.get("MemorySize", 128),
            "Role": config.get("RoleArn"),
            "KMSKeyArn": "",
        }
        if config.get("Vpc"):
            function_params["VpcConfig"] = config.get("Vpc")
        config["Environment"] = config.get("Environment", {})
        config["Environment"]["Variables"] = config["Environment"].get("Variables", {})
        config["Environment"]["Variables"]["version"] = new_version
        config["Environment"]["Variables"] = {**config["Environment"]["Variables"]}
        response = lambda_client.update_function_configuration(
            FunctionName=function_name,
            **function_params,
        )
        waiter = lambda_client.get_waiter("function_updated")
        waiter.wait(FunctionName=function_name)
        response = lambda_client.update_function_code(
            FunctionName=function_name, ImageUri=f"{repo_uri}:latest"
        )
        wait_for_function_active(function_name)
        print(f"Lambda function updated")

    except lambda_client.exceptions.ResourceNotFoundException:
        print(f"Creating Lambda function")
        function_params = {
            "Timeout": config.get("Timeout", 300),
            "MemorySize": config.get("MemorySize", 128),
            "Role": config.get("RoleArn"),
            "Architectures": [config.get("Arch", "x86_64")],
            "KMSKeyArn": "",
        }
        if config.get("Vpc"):
            function_params["VpcConfig"] = config.get("Vpc")
        config["Environment"] = config.get("Environment", {})
        config["Environment"]["Variables"] = config["Environment"].get("Variables", {})
        config["Environment"]["Variables"]["version"] = "1"
        config["Environment"]["Variables"] = {**config["Environment"]["Variables"]}

        response = lambda_client.create_function(
            FunctionName=function_name,
            PackageType="Image",
            Code={"ImageUri": f"{repo_uri}:latest"},
            **function_params,
        )
        wait_for_function_active(function_name)
        print(f"Lambda function created: {response['FunctionArn']}")

    return response["FunctionArn"]


def execute_and_tail_lambda(function_name, payload, detached):
    # Initialize boto3 clients
    lambda_client = boto3.client("lambda")
    params = {"InvocationType": "Event"}
    if not detached:
        params["InvocationType"] = "RequestResponse"
        params["LogType"] = "Tail"
    try:
        # Invoke Lambda function
        response = lambda_client.invoke(
            FunctionName=function_name, Payload=json.dumps(payload), **params
        )
        if detached:
            print("Lambda function executed")
            return
        log = response.get("LogResult")
        decoded_log_b = base64.b64decode(log)
        decoded_log = decoded_log_b.decode("utf-8")
        print(decoded_log)

    except Exception as e:
        print(f"An error occurred: {e}")


@log_output
def delete_resources(function_name):
    lambda_client = boto3.client("lambda")
    iam_client = boto3.client("iam")
    ecr_client = boto3.client("ecr")

    # Delete Lambda function
    try:
        lambda_client.delete_function(FunctionName=function_name)
        print(f"Deleting Lambda function: {function_name}")
        time.sleep(5)
    except lambda_client.exceptions.ResourceNotFoundException:
        print(f"Lambda function {function_name} not found")

    # Delete lambda IAM role
    try:
        # Detach all policies from the role
        attached_policies = iam_client.list_attached_role_policies(
            RoleName=function_name
        )["AttachedPolicies"]
        for policy in attached_policies:
            iam_client.detach_role_policy(
                RoleName=function_name, PolicyArn=policy["PolicyArn"]
            )
        iam_client.delete_role(RoleName=function_name)
        print(f"Deleting IAM role: {function_name}")
        time.sleep(5)
    except iam_client.exceptions.NoSuchEntityException:
        print(f"IAM role {function_name} not found")
    # delete scheduler role
    try:
        # Detach all policies from the role
        schedule_name = function_name + "_schedule"
        attached_policies = iam_client.list_attached_role_policies(
            RoleName=schedule_name
        )["AttachedPolicies"]
        for policy in attached_policies:
            iam_client.detach_role_policy(
                RoleName=schedule_name, PolicyArn=policy["PolicyArn"]
            )
        iam_client.delete_role(RoleName=schedule_name)
        print(f"Deleting IAM role: {schedule_name}")
        time.sleep(5)
    except iam_client.exceptions.NoSuchEntityException:
        print(f"IAM role {schedule_name} not found")

    # Delete ECR repository and images
    try:
        response = ecr_client.describe_images(repositoryName=function_name)
        image_ids = [
            {"imageDigest": image["imageDigest"]} for image in response["imageDetails"]
        ]
        if image_ids:
            ecr_client.batch_delete_image(
                repositoryName=function_name, imageIds=image_ids
            )
        ecr_client.delete_repository(repositoryName=function_name)
        print(f"Deleting ECR repository: {function_name}")
    except ecr_client.exceptions.RepositoryNotFoundException:
        print(f"ECR repository {function_name} not found")

    print("All resources have been terminated")


def list_logs(name, compute_type):
    # Initialize the CloudWatch Logs client
    logs_client = boto3.client("logs")
    if compute_type == "Batch":
        log_group_name = f"{name}"
    else:
        # Specify the log group name for your Lambda function
        log_group_name = f"/aws/lambda/{name}"

    # List the log streams, sorted by last event time in descending order
    response = logs_client.describe_log_streams(
        logGroupName=log_group_name, orderBy="LastEventTime", descending=True, limit=10
    )
    logs_md = ""

    for index, x in enumerate(response["logStreams"]):
        logs_md += f"{index+1}. {x.get("logStreamName")} \n\t>{milliseconds_to_date(x.get("creationTime"))}\n"
    panel = Panel(
        Markdown(logs_md),
        title="🦊 RED project logs",
        border_style="#ff4444",
        box=box.ROUNDED,
    )
    print(panel)


def get_log(name, log_stream_name, compute_type):
    # Initialize the CloudWatch Logs client
    logs_client = boto3.client("logs")
    if compute_type == "Batch":
        log_group_name = f"{name}"
    else:
        # Specify the log group name for your Lambda function
        log_group_name = f"/aws/lambda/{name}"
    print(log_group_name)
    # Get the log events
    response = logs_client.get_log_events(
        logGroupName=log_group_name, logStreamName=log_stream_name, startFromHead=True
    )

    # Print the log events
    for event in response["events"]:
        print(event["timestamp"], event["message"])
