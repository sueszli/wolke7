import boto3
import zipfile
from pathlib import Path
from colorama import Fore, Style


"""
# create demo lambda function
echo 'def lambda_handler(event, context): print(event)' > lambda_function.py
zip lambda_function.zip lambda_function.py

# note your own account id
aws sts get-caller-identity

# create a lambda function
# change `<YOUR ACCOUNT ID HERE>` with your own account id
# notice how we're using the existing `LabRole` role
aws lambda create-function --function-name my-function --runtime python3.8 --role arn:aws:iam::<YOUR ACCOUNT ID HERE>:role/LabRole --handler lambda_function.lambda_handler --zip-file fileb://lambda_function.zip

# invoke the lambda function and print the output
aws lambda invoke --function-name my-function response.json && rm -rf response.json

# show existing lambda functions
aws lambda list-functions

# delete the lambda function
aws lambda delete-function --function-name my-function
"""

client = boto3.client("lambda", region_name="us-west-1")


def create_lambda_function(function_name, zip_file):
    print(f"{Fore.GREEN}creating lambda function {function_name}{Style.RESET_ALL}")

    accountid = boto3.client("sts").get_caller_identity()["Account"]
    role = "LabRole"

    with open(zip_file, "rb") as f:
        response = client.create_function(
            FunctionName=function_name,
            Runtime="python3.8",
            Role=f"arn:aws:iam::{accountid}:role/{role}",
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": f.read()},
        )

    print(f"created lambda function {function_name}")
    return response["FunctionArn"]


def invoke_lambda_function(function_name):
    print(f"{Fore.GREEN}invoking lambda function {function_name}{Style.RESET_ALL}")

    response = client.invoke(FunctionName=function_name)

    print(f"invoked lambda function {function_name}")
    return response


def list_lambda_functions():
    print(f"{Fore.GREEN}listing lambda functions{Style.RESET_ALL}")

    response = client.list_functions()

    print(f"listed lambda functions")
    return response


def delete_lambda_function(function_name):
    print(f"{Fore.GREEN}deleting lambda function {function_name}{Style.RESET_ALL}")

    response = client.delete_function(FunctionName=function_name)

    print(f"deleted lambda function {function_name}")
    return response


if __name__ == "__main__":
    # create temporary zip to upload function
    lambdapath = Path.cwd() / "src" / "aws" / "lambda_function.py"
    lambdazip = lambdapath.with_suffix(".zip")
    if lambdazip.exists():
        lambdazip.unlink()
    with zipfile.ZipFile(lambdazip, "w") as z:
        z.write(lambdapath, lambdapath.name)
    print(f"{Fore.GREEN}created zip {lambdazip}{Style.RESET_ALL}")

    function_name = "my-function"
    create_lambda_function(function_name, lambdazip)

    invoke_lambda_function(function_name)

    list_lambda_functions()

    delete_lambda_function(function_name)

    # delete zip file
    if lambdazip.exists():
        lambdazip.unlink()
