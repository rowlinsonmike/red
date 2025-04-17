import sh
import sys
from red.utility import print, log_output


@log_output
def login_to_ecr(account_ecr):
    try:
        # Get ECR login password
        ecr_password = sh.aws("ecr", "get-login-password").strip()
        # Perform Docker login
        docker_login = sh.docker.login(
            "--username", "AWS", "--password-stdin", account_ecr, _in=ecr_password
        )
        print("Docker login successful")

    except:
        print("An error occurred while executing the command")
        sys.exit()


@log_output
def build_image(uri):
    try:
        sh.docker.build("-t", f"{uri}:latest", ".", _out=sys.stdout, _err=sys.stderr)
        print("Successfully built container locally")
    except:
        print("An error occurred while trying to build image")
        sys.exit()


@log_output
def push_image(uri):
    try:
        sh.docker.push(f"{uri}:latest", _out=sys.stdout, _err=sys.stderr)
        print(f"Successfully pushed docker image to ECR ({uri})!\n")
    except:
        print("An error occurred while trying to push docker image to ECR")
        sys.exit()


def push_to_ecr(uri, account_ecr, skip_push):
    login_to_ecr(account_ecr)
    build_image(uri)
    if skip_push:
        return
    push_image(uri)
