import inspect
import os
import sys
import datetime
from pathlib import Path

import logging
logger = logging.getLogger()
logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s", level=logging.DEBUG)


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
    funcName = f"{func.__module__}.{func.__name__}"
    def decoratedFunc(*args, **kwargs):
        # parse argument names / values into a printable format
        numPosArgs = len(args)
        posArgNames = func.__code__.co_varnames[:numPosArgs]
        posArgsDict = {posArgNames[i]: args[i] for i in range(numPosArgs)}
        argsDict = {**posArgsDict, **kwargs}
        argsString = prettyPrintDict(argsDict)

        # print the arguments
        if argsDict:
            logEntry = f"At {datetime.datetime.now()}, " \
                       f"{funcName} was called with: {argsString}\n"
        else:
            logEntry = f"At {datetime.datetime.now()}, " \
                       f"{funcName} was called with no arguments.\n"

        # actually call the function
        result = func(*args, **kwargs)

        # print what it returned
        logEntry += f"At {datetime.datetime.now()}, " \
                    f"{funcName} returned {result}."
        logger.info(logEntry)     # TODO: write to file instead

        # return what the function returned so the function can be a black box
        return result
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
