import boto3
from botocore.exceptions import ClientError
import zipfile
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

    client = boto3.client("lambda", region_name="us-west-1")
    accountid = boto3.client("sts").get_caller_identity()["Account"]
    print(f"accountid: {accountid}")
    role = "LabRole"

    with open(zip_file, "rb") as f:
        response = client.create_function(
            FunctionName=function_name,
            Runtime="python3.8",
            Role=f"arn:aws:iam::{accountid}:role/{role}",
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": f.read()},
        )
    print(response)

    print(f"created lambda function {function_name}")


def invoke_lambda_function(function_name):
    print(f"{Fore.GREEN}invoking lambda function {function_name}{Style.RESET_ALL}")

    client = boto3.client("lambda", region_name="us-west-1")
    response = client.invoke(FunctionName=function_name)
    print(response)


def list_lambda_functions():
    print(f"{Fore.GREEN}listing lambda functions{Style.RESET_ALL}")

    client = boto3.client("lambda")
    response = client.list_functions()
    print("functions:")
    if "Functions" in response:
        for function in response["Functions"]:
            print(f"\t{function['FunctionName']}")


def delete_lambda_function(function_name):
    print(f"{Fore.GREEN}deleting lambda function {function_name}{Style.RESET_ALL}")

    client = boto3.client("lambda", region_name="us-west-1")
    response = client.delete_function(FunctionName=function_name)
    print(response)


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

    # ----

    function_name = "wolke-sieben-lambda"
    # create_lambda_function(function_name, lambdazip)

    # invoke_lambda_function(function_name)

    list_lambda_functions()

    # delete_lambda_function(function_name)

    # ----

    # create lambda zip file
    if lambdazip.exists():
        lambdazip.unlink()
    print(f"deleted lambda zip")
