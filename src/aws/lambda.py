import boto3
from botocore.exceptions import ClientError
from botocore import exceptions as botocore
from botocore.response import StreamingBody
import zipfile
import json
from pathlib import Path
from colorama import Fore, Style
from util import *


"""
# create a lambda function
# notice how we're using the existing `LabRole` role
aws lambda create-function --function-name my-function --runtime python3.8 --role arn:aws:iam::<YOUR ACCOUNT ID HERE>:role/LabRole --handler lambda_function.lambda_handler --zip-file fileb://lambda_function.zip

# invoke the lambda function and print the output
aws lambda invoke --function-name my-function response.json && rm -rf response.json
"""


def create_lambda_function(function_name, zip_file):
    print(f"{Fore.GREEN}creating lambda function {function_name}{Style.RESET_ALL}")

    client = boto3.client("lambda")
    accountid = boto3.client("sts").get_caller_identity()["Account"]
    role = "LabRole"

    assert zip_file.exists(), f"zip file {zip_file} does not exist"
    assert zip_file.suffix == ".zip", f"zip file {zip_file} must have .zip extension"
    assert zip_file.stat().st_size > 0, f"zip file {zip_file} must not be empty"
    existing_functions = client.list_functions()["Functions"]
    for function in existing_functions:
        if function_name == function["FunctionName"]:
            print(f"lambda function {function_name} already exists")
            return

    with open(zip_file, "rb") as f:
        response = client.create_function(
            FunctionName=function_name,
            Runtime="python3.8",
            Role=f"arn:aws:iam::{accountid}:role/{role}",
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": f.read()},
        )
    print(json.dumps(response, indent=2))

    print(f"created lambda function {function_name}")


def invoke_lambda_function(function_name):
    print(f"{Fore.GREEN}invoking lambda function {function_name}{Style.RESET_ALL}")

    client = boto3.client("lambda")

    # invoke the lambda function with an empty event
    response = client.invoke(FunctionName=function_name)

    # check if response is serializable
    if "Payload" in response and isinstance(response["Payload"], StreamingBody):
        payload_content = response["Payload"].read().decode("utf-8")

        print(json.dumps(payload_content, indent=2))

        if "StatusCode" in response:
            print(f"status code: {response['StatusCode']}")

        if "FunctionError" in response:
            print(f"function error: {response['FunctionError']}")
    else:
        print(json.dumps(response, indent=2))


def list_lambda_functions():
    print(f"{Fore.GREEN}listing lambda functions{Style.RESET_ALL}")

    client = boto3.client("lambda")
    response = client.list_functions()
    for function in response["Functions"]:
        print(f"\t{function['FunctionName']}")


def delete_lambda_function(function_name):
    print(f"{Fore.GREEN}deleting lambda function {function_name}{Style.RESET_ALL}")

    client = boto3.client("lambda")
    response = client.delete_function(FunctionName=function_name)
    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    assert_user_authenticated()

    # create lambda zip file
    lambdapath = Path.cwd() / "src" / "aws" / "lambda_function.py"
    lambdazip = lambdapath.with_suffix(".zip")
    if lambdazip.exists():
        lambdazip.unlink()
        print(f"deleted lambda zip")
    with zipfile.ZipFile(lambdazip, "w") as z:
        z.write(lambdapath, lambdapath.name)
    print(f"created lambda zip")

    function_name = "wolke-sieben-lambda"
    create_lambda_function(function_name, lambdazip)
    list_lambda_functions()

    invoke_lambda_function(function_name)

    delete_lambda_function(function_name)
    list_lambda_functions()

    # create lambda zip file
    if lambdazip.exists():
        lambdazip.unlink()
    print(f"deleted lambda zip")
