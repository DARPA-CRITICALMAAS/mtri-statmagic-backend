from io import StringIO

import boto3
from botocore.exceptions import ClientError
from pathlib import Path
import re

import logging
logger = logging.getLogger("statmagic_backend")

def session_setup(profile, endpoint):
    session = boto3.Session()
    if profile in session.available_profiles:
        session = boto3.Session(profile_name=profile)
        if session.get_credentials() is None:
            session = boto3.Session()
    if endpoint:
        client = session.client("s3", endpoint_url=endpoint)
    else:
        client = session.client("s3")
    return client, session.get_credentials()

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
    s3_client, credentials = session_setup(profile, endpoint)
    if credentials is None:
        return None

    files = []
    if path:
        kwargs = {'Bucket': bucket, 'Prefix': path}
    else:
        kwargs = {'Bucket': bucket}
    while True:
        response = s3_client.list_objects_v2(**kwargs)
        for item in response['Contents']:
            if item['Size'] > 0:
                key = item['Key']
                if pattern:
                    if re.search(pattern, key):
                        files.append(key)
                else:
                    files.append(key)
        try:
            kwargs['ContinuationToken'] = response['NextContinuationToken']
        except KeyError:
            break

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
    s3_client, credentials = session_setup(profile, endpoint)
    if credentials is None:
        return None
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
    s3_client, credentials = session_setup(profile, endpoint)
    if credentials is None:
        return None
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
