import boto3
from colorama import Fore, Style


def get_account_id():
    return boto3.client("sts").get_caller_identity()["Account"]


if __name__ == "__main__":
    print(f"account id: {get_account_id()}")
