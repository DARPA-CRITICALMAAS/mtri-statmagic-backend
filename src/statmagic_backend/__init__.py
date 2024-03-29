import logging
# from io import StringIO
# log_stream = StringIO()

log_format = "%(asctime)s %(levelname)s: %(message)s"
formatter = logging.Formatter(log_format)

class LogStream:
    def __init__(self):
        self.logs = []
    def write(self, log):
        self.logs.append(log)
        print(log)
    def flush(self):
        # TODO: figure out why flush gets called when something is logged
        pass
    def __str__(self):
        return "\n".join(self.logs)

stream = LogStream()
stream_handler = logging.StreamHandler(stream=stream)
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.DEBUG)
logger = logging.getLogger("statmagic_backend")
logger.setLevel(logging.DEBUG)
logger.addHandler(stream_handler)

from . import *

# import os
# from pathlib import Path
# 
# 
# from utils import recursive_hardlink
# 
# 
# qgis_path = Path.home() / ".local/share/QGIS/QGIS3/profiles/default/python/plugins"
# 
# # create hardlinks to plugin_reloader
# local_path = Path(__file__).parent / "plugins" / "plugin_reloader"
# recursive_hardlink(local_path, qgis_path)
