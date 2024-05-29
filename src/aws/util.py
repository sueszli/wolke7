import boto3
from botocore.exceptions import ClientError
from colorama import Fore, Style


def assert_user_authenticated():
    # check if user is authenticated
    sts = boto3.client("sts")
    assert sts.get_caller_identity(), "unable to authenticate"

    # check if user has access to aws resources
    try:
        ec2 = boto3.client("ec2")
        instances = ec2.describe_instances()
    except ClientError as e:
        print(f"{Fore.RED}ec2 instance not accessible{Style.RESET_ALL}")
        exit(1)
