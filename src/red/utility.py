import re
from rich.console import Console
import os
import json
import sys
from datetime import datetime, timezone
import sys
import functools
from contextlib import redirect_stdout, redirect_stderr


console = Console()
print = console.print


def milliseconds_to_date(milliseconds):
    seconds = milliseconds / 1000
    date = datetime.fromtimestamp(seconds, tz=timezone.utc)
    return date.strftime("%Y-%m-%d %H:%M:%S UTC")


def load_config():
    try:
        with open(".red", "r") as f:
            config = json.load(f)
        if not config.get("Name"):
            print("Name must be defined in .red file")
            sys.exit()
        return config
    except:
        print("Error with .red file")
        sys.exit(0)


def slugify(text):
    # Convert the text to lowercase
    text = text.lower()

    # Replace spaces and special characters with underscores
    text = re.sub(r"[^a-z0-9]+", "_", text)

    # Remove leading and trailing underscores
    text = text.strip("_")

    return text


def file_exists(file_name):
    cwd = os.getcwd()
    # Construct the full file path
    file_path = os.path.join(cwd, file_name)
    return os.path.exists(file_path)


def create_folder(folder_path):
    if os.path.exists(folder_path):
        print("The folder specified already exists")
        sys.exit()
    else:
        os.makedirs(folder_path)


def create_file(file_name, content):
    try:
        # Get the current working directory
        cwd = os.getcwd()

        # Construct the full file path
        file_path = os.path.join(cwd, file_name)
        # create it and write the content
        with open(file_path, "w") as file:
            file.write(content)

        return True
    except IOError as e:
        print(f"Error creating file: {str(e)}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        return False


def log_output(func):
    LOG_FILE = "red.log"

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with open(LOG_FILE, "a") as f:
            with redirect_stdout(f), redirect_stderr(f):
                return func(*args, **kwargs)

    return wrapper
