import boto3
from red.utility import print, log_output
import time
import json


@log_output
def create_ecr(repository_name):
    ecr_client = boto3.client("ecr")
    try:
        existing_repos = ecr_client.describe_repositories(
            repositoryNames=[repository_name],
        )
        return existing_repos.get("repositories", [])[0].get("repositoryUri", None)
    except ecr_client.exceptions.RepositoryNotFoundException:
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
        print(f"Repository created")
        return response["repository"]["repositoryUri"]
