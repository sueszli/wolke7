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


def get_account_id():
    return boto3.client("sts").get_caller_identity()["Account"]


if __name__ == "__main__":
    print(f"account id: {get_account_id()}")

    # create temporary zip to upload function
    lambdapath = Path.cwd() / "src" / "aws" / "lambda_function.py"
    lambdazip = lambdapath.with_suffix(".zip")
    if lambdazip.exists():
        lambdazip.unlink()
    with zipfile.ZipFile(lambdazip, "w") as z:
        z.write(lambdapath, lambdapath.name)
    print(f"{Fore.GREEN}created zip {lambdazip}{Style.RESET_ALL}")

    # delete zip file
    if lambdazip.exists():
        lambdazip.unlink()
