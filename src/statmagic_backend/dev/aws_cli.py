from io import StringIO

import boto3
from botocore.exceptions import ClientError
from pathlib import Path
import re
import subprocess

from statmagic_backend.utils import logger

def ls(endpoint, bucket, path, pattern, recursive=False):
    if path:
        s3path = f"s3://{bucket}/{path}"
    else:
        s3path = f"s3://{bucket}"

    command = ["aws", "s3", "ls", s3path, "--endpoint-url", endpoint]

    if recursive:
        command += ["--recursive"]

    result = subprocess.run(command, stdout=subprocess.PIPE)
    result_clean = result.stdout.decode("utf-8").split("\n")

    if pattern:
        matches = []
        for line in result_clean:
            if re.search(pattern, line):
                matches.append(line)
    else:
        matches = result_clean

    files = []

    for match in matches:
        files.append(match.split(" ")[-1])

    return files


def upload(endpoint, filename, bucket, object_name=None, extra_args=None, callback=None):
    """
    Upload a file to an S3 Bucket

    Parameters
    ----------
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
    s3_session = boto3.Session(profile_name="default")
    s3_client = s3_session.client("s3", endpoint_url=endpoint)
    try:
        response = s3_client.upload_file(filename, bucket, object_name)
    except ClientError as e:
        # logging.error(e)
        return False
    return True


if __name__ == "__main__":
    s3_session = boto3.Session(profile_name="default")
    s3_client = s3_session.client("s3", endpoint_url="https://s3.macrostrat.chtc.io")
    print(s3_client.list_buckets())
    pass
