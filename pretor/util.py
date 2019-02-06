# Copyright 2019 Charles A Daniels
# Distributed under the GNU GPLv3 License (https://www.gnu.org/licenses/gpl.txt)

import logging
import os
import pprint
import pretor.exceptions
import sys
import traceback
import zipfile

def setup_logging(level=logging.INFO):
    logging.basicConfig(level=level,
            format='%(levelname)s: %(message)s',
            datefmt='%H:%M:%S')


def log_exception(e):
    logging.error("Exception: {}".format(e))
    logging.debug("".join(traceback.format_tb(e.__traceback__)))

def log_pretty(logfunc, obj):
    logfunc(pprint.pformat(obj))
