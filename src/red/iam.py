import boto3
import json
from botocore.exceptions import ClientError
from red.utility import print, log_output

import boto3
import json
from botocore.exceptions import ClientError


@log_output
def create_role(
    role_name,
    trust_policy,
    basic_policy_arn,
    custom_policy_name,
    custom_policy_document,
):
    """
    Create an IAM role for a Lambda function with a custom policy.
    If resources already exist, it will use them instead of creating new ones.

    :param role_name: The name of the IAM role to create or use
    :param custom_policy_name: The name of the custom policy to create or use
    :param custom_policy_document: The policy document as a dictionary
    :return: The ARN of the role, or None if the operation failed
    """
    iam = boto3.client("iam")

    # Define the trust policy for Lambda

    role_arn = None

    try:
        # Try to create the IAM role, if it doesn't exist
        try:
            response = iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description=f"IAM role for Lambda function {role_name}",
            )
            role_arn = response["Role"]["Arn"]
            print(f"Created IAM role: {role_arn}")
        except iam.exceptions.EntityAlreadyExistsException:
            print(f"IAM role {role_name} already exists. Using existing role.")
            role_arn = iam.get_role(RoleName=role_name)["Role"]["Arn"]

        # Attach the AWSLambdaBasicExecutionRole policy if not already attached
        attached_policies = iam.list_attached_role_policies(RoleName=role_name)[
            "AttachedPolicies"
        ]
        if basic_policy_arn and not any(
            p["PolicyArn"] == basic_policy_arn for p in attached_policies
        ):
            iam.attach_role_policy(RoleName=role_name, PolicyArn=basic_policy_arn)
            # print(f"Attached AWSLambdaBasicExecutionRole policy to {role_name}")
        # Create or update the custom policy
        if not custom_policy_document:
            return role_arn
        custom_policy_arn = None
        try:
            # Try to create the policy
            custom_policy_response = iam.create_policy(
                PolicyName=custom_policy_name,
                PolicyDocument=json.dumps(custom_policy_document),
            )
            custom_policy_arn = custom_policy_response["Policy"]["Arn"]
            print(f"Created custom policy: {custom_policy_arn}")
        except iam.exceptions.EntityAlreadyExistsException:
            # Policy exists, let's update it
            print(
                f"Custom policy {custom_policy_name} already exists. Updating policy."
            )
            policies = iam.list_policies(Scope="Local", PathPrefix="/")["Policies"]
            custom_policy = next(
                (p for p in policies if p["PolicyName"] == custom_policy_name), None
            )
            if custom_policy:
                custom_policy_arn = custom_policy["Arn"]
                # Delete old versions of the policy
                versions = iam.list_policy_versions(PolicyArn=custom_policy_arn)[
                    "Versions"
                ]
                newest_version = sorted(
                    versions, key=lambda x: x["CreateDate"], reverse=True
                )[0]
                for version in versions:
                    if (
                        version["VersionId"] != newest_version["VersionId"]
                        and not version["IsDefaultVersion"]
                    ):
                        iam.delete_policy_version(
                            PolicyArn=custom_policy_arn,
                            VersionId=version["VersionId"],
                        )
                        print(
                            f"Deleted version of custom policy: {version['VersionId']}"
                        )
                # Create a new version of the policy
                iam.create_policy_version(
                    PolicyArn=custom_policy_arn,
                    PolicyDocument=json.dumps(custom_policy_document),
                    SetAsDefault=True,
                )
                print(f"Updated custom policy: {custom_policy_arn}")
        # Attach the custom policy to the role if not already attached
        if custom_policy_arn:
            if not any(p["PolicyArn"] == custom_policy_arn for p in attached_policies):
                iam.attach_role_policy(RoleName=role_name, PolicyArn=custom_policy_arn)
                print(f"Attached custom policy to {role_name}")
            else:
                print(f"Custom policy already attached to {role_name}")
        else:
            print("Failed to create or find custom policy")

        return role_arn

    except ClientError as e:
        print(f"Error in IAM operations: {e}")
        return None


@log_output
def create_lambda_role(role_name, custom_policy_name, custom_policy_document):
    """
    Create an IAM role for a Lambda function with a custom policy.
    If resources already exist, it will use them instead of creating new ones.

    :param role_name: The name of the IAM role to create or use
    :param custom_policy_name: The name of the custom policy to create or use
    :param custom_policy_document: The policy document as a dictionary
    :return: The ARN of the role, or None if the operation failed
    """
    # Define the trust policy for Lambda
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }

    basic_policy_arn = (
        "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    )
    role = create_role(
        role_name,
        trust_policy,
        basic_policy_arn,
        custom_policy_name,
        custom_policy_document,
    )
    return role
