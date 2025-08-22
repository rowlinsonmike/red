import boto3
import time
import traceback
from botocore.exceptions import ClientError
import json
import boto3
import time
from red.utility import print, log_output


def submit_batch_job(job_name, job_queue, job_definition, environment=None):
    try:
        # Create batch client
        batch_client = boto3.client("batch")

        # Prepare submission parameters
        submit_job_params = {
            "jobName": job_name,
            "jobQueue": job_queue,
            "jobDefinition": job_definition,
        }

        # Add container overrides if specified
        container_overrides = {}

        if environment:
            container_overrides["environment"] = environment

        if container_overrides:
            submit_job_params["containerOverrides"] = container_overrides

        # Submit the job
        response = batch_client.submit_job(**submit_job_params)

        return {"jobId": response["jobId"], "jobName": response["jobName"]}

    except Exception as e:
        print(f"Error submitting batch job: {str(e)}")
        raise


def get_job_definition_environment_variables(job_definition_name=None):
    batch_client = boto3.client("batch")

    # Parameters for the API call
    params = {"status": "ACTIVE"}  # Only get active job definitions

    # If a specific job definition name is provided
    if job_definition_name:
        params["jobDefinitionName"] = job_definition_name

    job_definitions = []
    paginator = batch_client.get_paginator("describe_job_definitions")

    # Iterate through all pages
    for page in paginator.paginate(**params):
        job_definitions.extend(page["jobDefinitions"])
    # Extract environment variables for each job definition
    results = []
    for job_def in job_definitions:
        job_def_name = job_def["jobDefinitionName"]
        revision = job_def["revision"]

        # Check if containerProperties exists and has environment variables
        env_vars = {}
        if (
            "containerProperties" in job_def
            and "environment" in job_def["containerProperties"]
        ):
            for env in job_def["containerProperties"]["environment"]:
                results.append({"Name": env["name"], "Value": env["value"]})
    return results


@log_output
def create_minimal_batch_role(role_name):
    iam = boto3.client("iam")

    # Trust policy allowing both Lambda and Batch
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": [
                        "ecs.amazonaws.com",
                        "ecs-tasks.amazonaws.com",
                        "batch.amazonaws.com",
                    ]
                },
                "Action": "sts:AssumeRole",
            }
        ],
    }

    # Basic permission policy
    permission_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AWSBatchPolicyStatement1",
                "Effect": "Allow",
                "Action": [
                    "ec2:DescribeAccountAttributes",
                    "ec2:DescribeInstances",
                    "ec2:DescribeInstanceStatus",
                    "ec2:DescribeInstanceAttribute",
                    "ec2:DescribeSubnets",
                    "ec2:DescribeSecurityGroups",
                    "ec2:DescribeKeyPairs",
                    "ec2:DescribeImages",
                    "ec2:DescribeImageAttribute",
                    "ec2:DescribeSpotInstanceRequests",
                    "ec2:DescribeSpotFleetInstances",
                    "ec2:DescribeSpotFleetRequests",
                    "ec2:DescribeSpotPriceHistory",
                    "ec2:DescribeSpotFleetRequestHistory",
                    "ec2:DescribeVpcClassicLink",
                    "ec2:DescribeLaunchTemplateVersions",
                    "ec2:CreateLaunchTemplate",
                    "ec2:DeleteLaunchTemplate",
                    "ec2:RequestSpotFleet",
                    "ec2:CancelSpotFleetRequests",
                    "ec2:ModifySpotFleetRequest",
                    "ec2:TerminateInstances",
                    "ec2:RunInstances",
                    "autoscaling:DescribeAccountLimits",
                    "autoscaling:DescribeAutoScalingGroups",
                    "autoscaling:DescribeLaunchConfigurations",
                    "autoscaling:DescribeAutoScalingInstances",
                    "autoscaling:DescribeScalingActivities",
                    "autoscaling:CreateLaunchConfiguration",
                    "autoscaling:CreateAutoScalingGroup",
                    "autoscaling:UpdateAutoScalingGroup",
                    "autoscaling:SetDesiredCapacity",
                    "autoscaling:DeleteLaunchConfiguration",
                    "autoscaling:DeleteAutoScalingGroup",
                    "autoscaling:CreateOrUpdateTags",
                    "autoscaling:SuspendProcesses",
                    "autoscaling:PutNotificationConfiguration",
                    "autoscaling:TerminateInstanceInAutoScalingGroup",
                    "ecs:DescribeClusters",
                    "ecs:DescribeContainerInstances",
                    "ecs:DescribeTaskDefinition",
                    "ecs:DescribeTasks",
                    "ecs:ListAccountSettings",
                    "ecs:ListClusters",
                    "ecs:ListContainerInstances",
                    "ecs:ListTaskDefinitionFamilies",
                    "ecs:ListTaskDefinitions",
                    "ecs:ListTasks",
                    "ecs:CreateCluster",
                    "ecs:DeleteCluster",
                    "ecs:RegisterTaskDefinition",
                    "ecs:DeregisterTaskDefinition",
                    "ecs:RunTask",
                    "ecs:StartTask",
                    "ecs:StopTask",
                    "ecs:UpdateContainerAgent",
                    "ecs:DeregisterContainerInstance",
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:DescribeLogGroups",
                    "iam:GetInstanceProfile",
                    "iam:GetRole",
                ],
                "Resource": "*",
            },
            {
                "Sid": "AWSBatchPolicyStatement2",
                "Effect": "Allow",
                "Action": "ecs:TagResource",
                "Resource": ["arn:aws:ecs:*:*:task/*_Batch_*"],
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
            {
                "Sid": "AWSBatchPolicyStatement3",
                "Effect": "Allow",
                "Action": "iam:PassRole",
                "Resource": ["*"],
                "Condition": {
                    "StringEquals": {
                        "iam:PassedToService": [
                            "ec2.amazonaws.com",
                            "ec2.amazonaws.com.cn",
                            "ecs-tasks.amazonaws.com",
                        ]
                    }
                },
            },
            {
                "Sid": "AWSBatchPolicyStatement4",
                "Effect": "Allow",
                "Action": "iam:CreateServiceLinkedRole",
                "Resource": "*",
                "Condition": {
                    "StringEquals": {
                        "iam:AWSServiceName": [
                            "spot.amazonaws.com",
                            "spotfleet.amazonaws.com",
                            "autoscaling.amazonaws.com",
                            "ecs.amazonaws.com",
                        ]
                    }
                },
            },
            {
                "Sid": "AWSBatchPolicyStatement5",
                "Effect": "Allow",
                "Action": ["ec2:CreateTags"],
                "Resource": ["*"],
                "Condition": {"StringEquals": {"ec2:CreateAction": "RunInstances"}},
            },
        ],
    }

    try:
        # Check if role already exists
        try:
            existing_role = iam.get_role(RoleName=role_name)
            print(f"Role {role_name} already exists")
            return existing_role["Role"]["Arn"]
        except iam.exceptions.NoSuchEntityException:
            # Role doesn't exist, create it
            print(f"Creating role: {role_name}")
            role = iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="Minimal viable role for Lambda and Batch execution",
            )

            # Create the policy
            print("Creating policy")
            policy = iam.create_policy(
                PolicyName=f"{role_name}",
                PolicyDocument=json.dumps(permission_policy),
            )

            # Wait briefly for AWS to propagate the role
            time.sleep(10)

            # Attach the policy to the role
            print("Attaching policy to role")
            iam.attach_role_policy(
                RoleName=role_name, PolicyArn=policy["Policy"]["Arn"]
            )

            return role["Role"]["Arn"]

    except ClientError as e:
        print(f"Error handling role: {str(e)}")
        raise


@log_output
def create_batch_environment(
    function_name,
    repo_uri,
    config,
    # role_arn, subnet_a, subnet_b, security_group_id, ecr_image, data_bucket
):
    batch_client = boto3.client("batch")
    logs_client = boto3.client("logs")
    # Create MVP role if not one provided
    role = config.get("Role")
    if not role:
        role = create_minimal_batch_role(function_name)
    # Create Log Group if it doesn't exist
    log_group_name = function_name

    # Check if Log Group exists
    describe_response = logs_client.describe_log_groups(
        logGroupNamePrefix=log_group_name
    )
    existing_log_groups = [
        group["logGroupName"] for group in describe_response.get("logGroups", [])
    ]

    if log_group_name not in existing_log_groups:
        print(f"Creating Log Group: {log_group_name}")
        logs_client.create_log_group(
            logGroupName=log_group_name, tags={"Name": log_group_name}
        )

    # Create Compute Environment if it doesn't exist
    compute_env_name = function_name

    # Check if Compute Environment exists
    describe_response = batch_client.describe_compute_environments(
        computeEnvironments=[compute_env_name]
    )
    existing_compute_envs = [
        env["computeEnvironmentName"]
        for env in describe_response.get("computeEnvironments", [])
    ]

    if compute_env_name not in existing_compute_envs:
        print(f"Creating Compute Environment: {compute_env_name}")
        batch_client.create_compute_environment(
            computeEnvironmentName=compute_env_name,
            type="MANAGED",
            state="ENABLED",
            serviceRole=role,
            computeResources={
                "type": "FARGATE",
                "maxvCpus": 100,
                "subnets": config.get("VPC", {}).get("SubnetIds", []),
                "securityGroupIds": config.get("VPC", {}).get("SecurityGroupIds", []),
            },
        )

        # Wait for compute environment to be ready
        while True:
            response = batch_client.describe_compute_environments(
                computeEnvironments=[compute_env_name]
            )
            status = response["computeEnvironments"][0]["status"]
            if status == "VALID":
                break
            time.sleep(10)
    else:
        print(f"Compute Environment already exists: {compute_env_name}")

    # Create Job Queue if it doesn't exist
    job_queue_name = function_name

    # Check if Job Queue exists
    describe_response = batch_client.describe_job_queues(jobQueues=[job_queue_name])
    existing_job_queues = [
        queue["jobQueueName"] for queue in describe_response.get("jobQueues", [])
    ]

    if job_queue_name not in existing_job_queues:
        print(f"Creating Job Queue: {job_queue_name}")
        batch_client.create_job_queue(
            jobQueueName=job_queue_name,
            state="ENABLED",
            priority=1,
            computeEnvironmentOrder=[
                {"order": 1, "computeEnvironment": compute_env_name}
            ],
        )

        # Wait for job queue to be ready
        while True:
            response = batch_client.describe_job_queues(jobQueues=[job_queue_name])
            status = response["jobQueues"][0]["status"]
            if status == "VALID":
                break
            time.sleep(10)

    else:
        print(f"Job Queue already exists: {job_queue_name}")

    # Create Job Definition if it doesn't exist
    job_def_name = function_name

    # Check if Job Definition exists
    describe_response = batch_client.describe_job_definitions(
        jobDefinitionName=job_def_name
    )
    # deregister old job def
    for job in describe_response.get("jobDefinitions", []):
        if job.get("status") != "INACTIVE":
            response = batch_client.deregister_job_definition(
                jobDefinition=job.get("jobDefinitionArn")
            )
    existing_job_defs = [
        def_.get("jobDefinitionArn")
        for def_ in describe_response.get("jobDefinitions", [])
    ]

    if job_def_name not in existing_job_defs:
        print(f"Creating Job Definition: {job_def_name}")
        runtime = {}
        if config.get("Arch") == "arm64":
            runtime = {
                "runtimePlatform": {
                    "cpuArchitecture": "ARM64",
                    "operatingSystemFamily": "LINUX",
                },
            }
        job_arn = batch_client.register_job_definition(
            jobDefinitionName=job_def_name,
            type="container",
            platformCapabilities=["FARGATE"],
            timeout={"attemptDurationSeconds": config.get("Timeout", 10000)},
            retryStrategy={"attempts": 1},
            propagateTags=True,
            containerProperties={
                # "enableExecuteCommand": True,
                "image": repo_uri,
                "jobRoleArn": role,
                "executionRoleArn": role,
                "fargatePlatformConfiguration": {"platformVersion": "LATEST"},
                "networkConfiguration": {
                    "assignPublicIp": config.get("assignPublicIp", "DISABLED")
                },
                "resourceRequirements": [
                    {"type": "VCPU", "value": str(config.get("Cpu"))},
                    {"type": "MEMORY", "value": str(config.get("MemorySize"))},
                ],
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": log_group_name,
                        "awslogs-region": batch_client.meta.region_name,
                        "awslogs-stream-prefix": job_def_name,
                    },
                },
                "environment": [
                    {"name": k, "value": v} for k, v in config.get("Env", {}).items()
                ],
                **runtime,
            },
        )["jobDefinitionArn"]

        # Wait for job definition to be registered
        while True:
            response = batch_client.describe_job_definitions(jobDefinitions=[job_arn])
            status = response["jobDefinitions"][0].get("status", "")
            if status == "ACTIVE":
                break
            time.sleep(10)

    else:
        print(f"Job Definition already exists: {job_def_name}")

    return {
        "compute_environment": compute_env_name,
        "job_queue": job_queue_name,
        "job_definition": job_def_name,
    }


@log_output
def delete_batch_environment(name):
    batch_client = boto3.client("batch")
    logs_client = boto3.client("logs")

    # 1. Disable Job Queue
    try:
        print(f"Disabling job queue: {name}")
        batch_client.update_job_queue(jobQueue=name, state="DISABLED")

        # Wait for job queue to be disabled
        while True:
            response = batch_client.describe_job_queues(jobQueues=[name])
            if not response["jobQueues"]:
                break
            status = response["jobQueues"][0]["status"]
            state = response["jobQueues"][0]["state"]
            if status == "VALID" and state == "DISABLED":
                break
            time.sleep(10)

    except:
        ...

    # 2. Delete Job Queue
    try:
        print(f"Deleting job queue: {name}")
        batch_client.delete_job_queue(jobQueue=name)

        # Wait for job queue to be deleted
        while True:
            response = batch_client.describe_job_queues(jobQueues=[name])
            if not response["jobQueues"]:
                break
            time.sleep(10)

    except:
        print(f"Skipping Job Queue")

    # 3. Disable Compute Environment
    try:
        print(f"Disabling compute environment: {name}")
        batch_client.update_compute_environment(
            computeEnvironment=name, state="DISABLED"
        )

        # Wait for compute environment to be disabled
        while True:
            response = batch_client.describe_compute_environments(
                computeEnvironments=[name]
            )
            if not response["computeEnvironments"]:
                break
            status = response["computeEnvironments"][0]["status"]
            state = response["computeEnvironments"][0]["state"]
            if status == "VALID" and state == "DISABLED":
                break
            time.sleep(10)

    except:
        ...

    # 4. Delete Compute Environment
    try:
        print(f"Deleting compute environment: {name}")
        batch_client.delete_compute_environment(computeEnvironment=name)

        # Wait for compute environment to be deleted
        while True:
            response = batch_client.describe_compute_environments(
                computeEnvironments=[name]
            )
            if not response["computeEnvironments"]:
                break
            time.sleep(10)

    except:
        print(f"Skipping Compute Environment")

    # 5. Deregister Job Definition
    try:
        print(f"Deregistering job definition: {name}")
        response = batch_client.describe_job_definitions(
            jobDefinitionName=name, status="ACTIVE"
        )

        for job_def in response["jobDefinitions"]:
            batch_client.deregister_job_definition(
                jobDefinition=job_def["jobDefinitionArn"]
            )

    except:
        print(f"Skipping Job Definition")

    # 6. Delete Log Group
    try:
        print(f"Deleting log group: {name}")
        logs_client.delete_log_group(logGroupName=name)
    except Exception as e:
        print(f"Skipping Log Group")
    # Delete IAM role
    iam_client = boto3.client("iam")
    try:
        try:
            # Detach all policies from the role
            attached_policies = iam_client.list_attached_role_policies(RoleName=name)[
                "AttachedPolicies"
            ]
            for policy in attached_policies:
                iam_client.detach_role_policy(
                    RoleName=name, PolicyArn=policy["PolicyArn"]
                )
                time.sleep(5)
                try:
                    iam_client.delete_policy(PolicyArn=policy["PolicyArn"])
                except:
                    ...
            iam_client.delete_role(RoleName=name)
        except:
            ...
        print(f"Deleting IAM role: {name}")
        time.sleep(5)
    except:
        traceback.print_exc()
        print(f"Couldn't delete IAM role")
    print("All batch environment resources have been deleted successfully")
