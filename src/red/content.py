from rich.panel import Panel
from rich.console import Console
from rich.text import Text
from rich.markdown import Markdown
from rich import box


def INIT_FINISH(x):
    steps_md = f"""
## Next Steps:
1. `cd {x}`
2. Develop your container
3. `red deploy`
"""
    panel = Panel(
        Markdown(steps_md),
        title="🦊 RED project setup!",
        border_style="#ff4444",
        box=box.ROUNDED,
    )
    return panel


BATCH_ENV_FILE = {
    "Type": "Batch",
    "Timeout": 10000,
    "Cpu": 1,
    "MemorySize": 2048,
    "assignPublicIp": "ENABLED",
    "Arch": "x86_64",
    "VPC": {"SubnetIds": [], "SecurityGroupIds": []},
}

BATCH_DOCKERFILE = """FROM python:3.13
COPY . .
ENTRYPOINT [ "python", "main.py" ]
"""

BATCH_PYTHON = """def handler():
    print("hello world")

if __name__ == "__main__":
    handler()
"""

ENV_FILE = {"Type": "Lambda", "Timeout": 300, "MemorySize": 128, "Arch": "x86_64"}

PYTHON_LAMBDA_DOCKERFILE = """# Define custom function directory
ARG FUNCTION_DIR="/function"

FROM python:3.12 AS build-image

# Include global arg in this stage of the build
ARG FUNCTION_DIR

# Copy function code
RUN mkdir -p ${FUNCTION_DIR}
COPY . ${FUNCTION_DIR}

# Install the function's dependencies
RUN pip install \
    --target ${FUNCTION_DIR} \
        awslambdaric

# Use a slim version of the base Python image to reduce the final image size
FROM python:3.12-slim

# Include global arg in this stage of the build
ARG FUNCTION_DIR
# Set working directory to function root directory
WORKDIR ${FUNCTION_DIR}

# Copy in the built dependencies
COPY --from=build-image ${FUNCTION_DIR} ${FUNCTION_DIR}

# Set runtime interface client as default command for the container runtime
ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]
# Pass the name of the function handler as an argument to the runtime
CMD [ "lambda_function.handler" ]
"""


PYTHON_LAMBDA_FUNCTION = """import sys

def handler(event, context):
    print('Hello from AWS Lambda using Python' + sys.version + '!')
    return 'Hello from AWS Lambda using Python' + sys.version + '!'
"""
