import boto3
from botocore.exceptions import ClientError
from colorama import Fore, Style


def assert_user_authenticated():
    sts = boto3.client("sts")
    assert sts.get_caller_identity(), "unable to authenticate"

    accid = sts.get_caller_identity()["Account"]
    secret = boto3.session.Session().get_credentials().secret_key
    access = boto3.session.Session().get_credentials().access_key
    session = boto3.session.Session().get_credentials().token
    region = boto3.session.Session().region_name
    assert region == "us-east-1", "region must be set to us-east-1"
    # print(f"credentials:\n\tacc id: {accid}\n\tsecret: {secret}\n\taccess: {access}\n\tsession: {session}\n\tnregion: {region}\n")

    try:
        ec2 = boto3.client("ec2")
        _ = ec2.describe_instances()
    except ClientError as e:
        print(f"{Fore.RED}ec2 instance not accessible - start lab, update credentials{Style.RESET_ALL}")
        exit(1)
