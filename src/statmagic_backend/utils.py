import inspect
import os
import sys
from pathlib import Path


def prettyPrintDict(d):
    """
    Returns string representation of ``d`` with ``name=value`` for each item,
    on separate lines.

    Parameters
    ----------
    d : dict
        Dictionary to parse

    Returns
    -------
    parsedString : str
        String representation of ``d``
    """
    parsedString = ""
    for key, value in d.items():
        parsedString += f"\n{key}={value}"
    return parsedString


def loggingDecorator(func):
    """
    Logs what arguments ``func`` got called with and what it returned.

    Parameters
    ----------
    func : function
        Function to log arguments for

    Returns
    -------
    loggedFunc : function
        ``func`` modified to log its inputs and outputs
    """
    def decoratedFunc(*args, **kwargs):
        numPosArgs = len(args)
        posArgNames = func.__code__.co_varnames[:numPosArgs]
        posArgsDict = {posArgNames[i]: args[i] for i in range(numPosArgs)}
        argsDict = {**posArgsDict, **kwargs}
        logEntry = f"{func.__name__} called with arguments {prettyPrintDict(argsDict)}"
        result = func(*args, **kwargs)
        logEntry += f", returned {result}"
        print(logEntry)
    return decoratedFunc


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


@loggingDecorator
def polytextreplace(poly_text):
    ptype = poly_text.split(" ")[0]

    if ptype == 'Polygon':
        poly_text = poly_text.replace('Polygon', 'POLYGON', 1)
    elif ptype == 'MultiPolygonZ':
        for r in (('MultiPolygonZ', 'POLYGON', 1), ("(", "", 1), (")", "", 1)):
            poly_text = poly_text.replace(*r)
    return poly_text



if __name__ == "__main__":
    polytextreplace("Polygon")
