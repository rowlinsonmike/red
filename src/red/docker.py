import sh
import sys
from red.utility import print, log_output
import os


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
def build_image(uri, config):
    try:
        if config.get("Type").lower() == "image":
            sh.docker.build(
                "-t",
                f"{uri}:latest",
                "-f",
                config.get("DockerfilePath", "Dockerfile"),
                ".",
                _out=sys.stdout,
                _err=sys.stderr,
            )
        else:
            sh.docker.build(
                "-t", f"{uri}:latest", ".", _out=sys.stdout, _err=sys.stderr
            )
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


@log_output
def pull_image(uri):
    try:
        sh.docker.pull(f"{uri}", _out=sys.stdout, _err=sys.stderr)
        print(f"Successfully pulled docker image from ECR ({uri})!\n")
    except:
        print("An error occurred while trying to pull docker image from ECR")
        sys.exit()


def push_to_ecr(uri, account_ecr, skip_push, config):
    login_to_ecr(account_ecr)
    build_image(uri, config)
    if skip_push:
        return
    push_image(uri)


def pull_from_ecr(uri, account_ecr):
    login_to_ecr(account_ecr)
    pull_image(uri)


@log_output
def build_serverless_package(config):
    runtime = config.get("Runtime")
    platform = (
        "manylinux2014_x86_64"
        if config.get("Arch") == "x86_64"
        else "manylinux2014_aarch64"
    )
    cwd = os.getcwd()
    # Create docker command with proper argument handling
    docker = sh.docker.bake(
        "run", "-v", f"{cwd}:/working", "--rm", "amazonlinux:latest"
    )
    # Chain commands inside container
    commands = f"""
    cd /working
    ls -lat
    yum install pip zip -y &&
    pip install --platform {platform} --target=. --implementation cp --python-version {runtime} --only-binary=:all: --upgrade -r ./requirements.txt &&
    rm -f ../lambda_package.zip
    rm -f ./lambda_package.zip
    zip ../lambda_package.zip -r . &&
    mv ../lambda_package.zip ./lambda_package.zip
    """
    # Execute the command
    docker("/bin/bash", "-c", commands, _out=sys.stdout, _err=sys.stderr)
