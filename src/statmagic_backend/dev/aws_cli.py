from io import StringIO

import boto3
from botocore.exceptions import ClientError
from pathlib import Path
import re

import logging
logger = logging.getLogger("statmagic_backend")

def ls(profile, endpoint, bucket, path, pattern, recursive=False):
    """
        Search for files in S3 Bucket

        Parameters
        ----------
        profile: str
            Name of profile in AWS credentials file where access keys are saved
        endpoint : str
            Endpoint URL of s3 bucket
        bucket : str
            Bucket to search
        path : str, optional
            Path within AWS bucket to limit search to
        pattern : str, optional
            Search pattern
        recursive : bool, optional
            Whether to recursively search subfolders

        Returns
        -------
        files: list
            List of object names
        """
    s3_session = boto3.Session(profile_name=profile)
    credentials = s3_session.get_credentials()
    # if credentials are not configured for the specified profile, switch to the default profile
    if credentials is None:
        s3_session = boto3.Session()
    if endpoint:
        s3_client = s3_session.client("s3", endpoint_url=endpoint)
    else:
        s3_client = s3_session.client("s3")
    if path:
        contents = s3_client.list_objects_v2(Bucket=bucket, Prefix=path)['Contents']
    else:
        contents = s3_client.list_objects_v2(Bucket=bucket)['Contents']

    if pattern:
        matches = []
        for item in contents:
            key = item['Key']
            if re.search(pattern, key):
                matches.append(item)
    else:
        matches = contents

    files = []

    for match in matches:
        files.append(match['Key'])

    return files


def upload(profile, endpoint, filename, bucket, object_name=None, extra_args=None, callback=None):
    """
    Upload a file to an S3 Bucket

    Parameters
    ----------
    profile: str
        Name of profile in AWS credentials file where access keys are saved
    endpoint : str
        Endpoint URL of s3 bucket
    filename : str
        File to upload
    bucket : str
        Bucket to upload to
    object_name : str, optional
        S3 object name. If not specified, ``filename`` is used.
    extra_args : dict, optional
        Additional keyword arguments to :meth:`boto3.Client.upload_file`
    callback : callable, optional
        Instance of a class whose ``__call__`` method displays upload progress

    Returns
    -------
    success : bool
        ``True`` if upload succeeded, ``False`` otherwise.
    """
    # default values
    if extra_args is None:
        extra_args = {}
    if callback is None:
        class NullCallback(object):
            def __init__(self):
                pass
            def __call__(self):
                pass
        callback = NullCallback()

    # If S3 object_name was not specified, use filename
    if object_name is None:
        object_name = Path(filename).stem

    # Upload the file
    s3_session = boto3.Session(profile_name=profile)
    if s3_session.get_credentials() is None:
        s3_session = boto3.Session()
    if endpoint:
        s3_client = s3_session.client("s3", endpoint_url=endpoint)
    else:
        s3_client = s3_session.client("s3")
    try:
        response = s3_client.upload_file(filename, bucket, object_name)
    except ClientError as e:
        # logging.error(e)
        return False
    return True


def download(profile, endpoint, bucket, object_name, filename, extra_args=None, callback=None):
    """
    Download a file from an S3 Bucket

    Parameters
    ----------
    profile: str
        Name of profile in AWS credentials file where access keys are saved
    endpoint : str
        Endpoint URL of s3 bucket
    bucket : str
        Bucket to download from
    object_name : str
        S3 object name.
    filename : str
        File to save to.
    extra_args : dict, optional
        Additional keyword arguments to :meth:`boto3.Client.download_file`
    callback : callable, optional
        Instance of a class whose ``__call__`` method displays upload progress

    Returns
    -------
    success : bool
        ``True`` if upload succeeded, ``False`` otherwise.
    """
    # default values
    if extra_args is None:
        extra_args = {}
    if callback is None:
        class NullCallback(object):
            def __init__(self):
                pass
            def __call__(self):
                pass
        callback = NullCallback()

    # Download the file
    s3_session = boto3.Session(profile_name=profile)
    if s3_session.get_credentials() is None:
        s3_session = boto3.Session()
    if endpoint == '':
        s3_client = s3_session.client("s3")
    else:
        s3_client = s3_session.client("s3", endpoint_url=endpoint)
    try:
        response = s3_client.download_file(bucket, object_name, filename)
    except ClientError as e:
        # logging.error(e)
        return False
    return True


if __name__ == "__main__":
    s3_session = boto3.Session(profile_name="default")
    s3_client = s3_session.client("s3", endpoint_url="https://s3.macrostrat.chtc.io")
    logger.debug(s3_client.list_buckets())
    pass
