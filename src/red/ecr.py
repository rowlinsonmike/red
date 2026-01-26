import json
import sys
import time
import traceback

import boto3

from red.utility import print


def create_ecr(repository_name):
    ecr_client = boto3.client("ecr")
    try:
        existing_repos = ecr_client.describe_repositories(
            repositoryNames=[repository_name],
        )
        return existing_repos.get("repositories", [])[0].get("repositoryUri", None)
    except ecr_client.exceptions.RepositoryNotFoundException:
        try:
            response = ecr_client.create_repository(repositoryName=repository_name)
            time.sleep(5)
            lifecycle_policy = {
                "rules": [
                    {
                        "rulePriority": 1,
                        "description": "Keep only the latest image",
                        "selection": {
                            "tagStatus": "any",
                            "countType": "imageCountMoreThan",
                            "countNumber": 1,
                        },
                        "action": {"type": "expire"},
                    }
                ]
            }
            ecr_client.put_lifecycle_policy(
                repositoryName=repository_name,
                lifecyclePolicyText=json.dumps(lifecycle_policy),
            )
            print(
                "ECR repo created: {}".format(response["repository"]["repositoryUri"])
            )
            return response["repository"]["repositoryUri"]
        except:
            print("Failed to create ECR repo: {}".format(traceback.format_exc()))
            sys.exit()


def delete_ecr_repo(function_name):
    ecr_client = boto3.client("ecr")
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
