import boto3
from botocore.exceptions import ClientError
from botocore import exceptions as botocore
from botocore.response import StreamingBody
import zipfile
import json
from pathlib import Path
from colorama import Fore, Style
from util import *


def create_lambda_function(function_name, file_path):
    print(f"{Fore.GREEN}creating lambda function {function_name}{Style.RESET_ALL}")

    client = boto3.client("lambda")
    accountid = boto3.client("sts").get_caller_identity()["Account"]
    role = "LabRole"

    def lambda_function_exists(function_name):
        existing_functions = client.list_functions()["Functions"]
        for function in existing_functions:
            if function_name == function["FunctionName"]:
                return True
        return False

    if lambda_function_exists(function_name):
        print(f"lambda function {function_name} already exists")
        return

    def get_lambda_zip_file(file_path):
        assert file_path.exists(), f"file {file_path} does not exist"
        assert file_path.suffix == ".py", f"file {file_path} must have .py extension"
        assert file_path.stat().st_size > 0, f"file {file_path} must not be empty"

        zip_file_path = file_path.with_suffix(".zip")
        if zip_file_path.exists():
            zip_file_path.unlink()
            print(f"deleted lambda zip")

        with zipfile.ZipFile(zip_file_path, "w") as z:
            z.write(file_path, file_path.name)
        print(f"created lambda zip")
        return zip_file_path

    zip_file_path = get_lambda_zip_file(file_path)

    with open(zip_file_path, "rb") as f:
        response = client.create_function(
            FunctionName=function_name,
            Runtime="python3.8",
            Role=f"arn:aws:iam::{accountid}:role/{role}",
            Handler="lambda_function.main",
            Code={"ZipFile": f.read()},
        )
    print(json.dumps(response, indent=2))

    print(f"created lambda function {function_name}")


def invoke_lambda_function(function_name):
    print(f"{Fore.GREEN}invoking lambda function {function_name}{Style.RESET_ALL}")

    client = boto3.client("lambda")

    def assert_exists(function_name):
        existing_functions = client.list_functions()["Functions"]
        for function in existing_functions:
            if function_name == function["FunctionName"]:
                return
        assert False, f"lambda function {function_name} does not exist"

    def wait_until_ready(function_name):
        while True:
            try:
                response = client.get_function(FunctionName=function_name)
                if response["Configuration"]["State"] == "Active":
                    break
                print(f"waiting for lambda function {function_name} to be ready")
            except botocore.ClientError:
                pass

    assert_exists(function_name)
    wait_until_ready(function_name)

    # todo: fix this
    payload = {"hello": "world"}
    response = client.invoke(FunctionName=function_name, Payload=json.dumps(payload))

    decoded_response = json.loads(response["Payload"].read().decode("utf-8"))
    print(json.dumps(decoded_response, indent=2))


def list_lambda_functions():
    print(f"{Fore.GREEN}listing lambda functions{Style.RESET_ALL}")

    client = boto3.client("lambda")
    response = client.list_functions()
    for function in response["Functions"]:
        print(f"\t{function['FunctionName']}")


def delete_lambda_function(function_name, file_path):
    print(f"{Fore.GREEN}deleting lambda function {function_name}{Style.RESET_ALL}")

    client = boto3.client("lambda")
    response = client.delete_function(FunctionName=function_name)
    print(json.dumps(response, indent=2))

    zip_file_path = file_path.with_suffix(".zip")
    assert zip_file_path.exists(), f"zip file {zip_file_path} does not exist"
    zip_file_path.unlink()
    print(f"deleted lambda zip")


if __name__ == "__main__":
    assert_user_authenticated()

    function_name = "wolke-sieben-lambda"
    file_path = Path.cwd() / "src" / "aws" / "lambda_function.py"
    create_lambda_function(function_name, file_path)
    list_lambda_functions()

    invoke_lambda_function(function_name)

    delete_lambda_function(function_name, file_path)
    list_lambda_functions()
