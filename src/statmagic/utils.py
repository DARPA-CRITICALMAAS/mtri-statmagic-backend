import os
from pathlib import Path


def recursive_hardlink(local_path, qgis_path):
    """
    "recursively" create hardlinks for all files within ``local_path``
    that quantum entangle them with the analogous path under ``plugin_path``.

    Parameters
    ----------
    local_path : pathlib.Path
        Path to a subdirectory of the current Pycharm project in which you
        want to be able to edit plugin source code conveniently
    qgis_path : pathlib.Path
        Path to where the plugin code needs to reside for QGIS to see it

    Notes
    -----
    The algorithm isn't actually recursive, but it's easier to imagine it is.
    """

    # create local_path if it doesn't exist
    os.makedirs(local_path, exist_ok=True)

    # hardlink all files in plugin_path to local_path
    for entry in qgis_path.glob("**/*"):
        relative_path = entry.relative_to(qgis_path)
        if entry.is_dir():
            os.makedirs(local_path / relative_path, exist_ok=True)
        else:
            (local_path / relative_path).hardlink_to(entry)
