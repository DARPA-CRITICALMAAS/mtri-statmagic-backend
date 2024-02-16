from io import StringIO

import pandas as pd
import re
import subprocess

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
