import os
import sys
import traceback

import sh

from red.utility import catch_error, print


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
        catch_error("An error ocurred during Docker login")


def build_image(uri, config, quiet=False):
    try:
        if quiet:
            sh.docker.build(
                "-t",
                f"{uri}:latest",
                "-f",
                config.get("DockerfilePath", "Dockerfile"),
                config.get("BuildContext", "."),
                _out=None,
                _err=None,
            )
        else:
            sh.docker.build(
                "-t",
                f"{uri}:latest",
                "-f",
                config.get("DockerfilePath", "Dockerfile"),
                ".",
                _out=sys.stdout,
                _err=sys.stderr,
            )
        print("Created Docker image")
    except:
        catch_error("An error ocurred while building image")


def push_image(uri, quiet=False):
    try:
        if quiet:
            sh.docker.push(f"{uri}:latest", _out=None, _err=None)
        else:
            sh.docker.push(f"{uri}:latest", _out=sys.stdout, _err=sys.stderr)
        print(f"Pushed docker image to ECR ({uri})!\\n")
    except:
        catch_error("An error ocurred pushing image to ECR")


def pull_image(uri):
    try:
        sh.docker.pull(f"{uri}", _out=sys.stdout, _err=sys.stderr)
        print(f"Successfully pulled docker image from ECR ({uri})!\n")
    except:
        print("An error occurred while trying to pull docker image from ECR")
        sys.exit()


def push_to_ecr(uri, account_ecr, config, quiet=False):
    login_to_ecr(account_ecr)
    build_image(uri, config, quiet=quiet)
    push_image(uri, quiet=quiet)


def pull_from_ecr(uri, account_ecr):
    login_to_ecr(account_ecr)
    pull_image(uri)


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
