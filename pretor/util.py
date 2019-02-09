# Copyright 2019 Charles A Daniels
# Distributed under the GNU AGPLv3 License (https://www.gnu.org/licenses/agpl.txt)

import logging
import os
import pprint
import pretor.exceptions
import sys
import traceback
import zipfile


def setup_logging(level=logging.INFO):
    logging.basicConfig(
        level=level, format="%(levelname)s: %(message)s", datefmt="%H:%M:%S"
    )


def log_exception(e):
    logging.error("Exception: {}".format(e))
    logging.debug("".join(traceback.format_tb(e.__traceback__)))


def log_pretty(logfunc, obj):
    logfunc(pprint.pformat(obj))


def compare_versions(v1, v2):
    """compare_versions

    Returns True if v1 is at least as new as or newer than v2.

    :param v1:
    :param v2:
    """

    v1 = str(v1).strip()
    v2 = str(v2).strip()

    v1 = v1.split("-")[0]
    v1 = [int(x) for x in v1.split(".")]

    v2 = v2.split("-")[0]
    v2 = [int(x) for x in v2.split(".")]

    for i in range(min([len(v1), len(v2)])):
        if v1[i] > v2[i]:
            return True
        if v1[i] < v2[i]:
            return False

    return True
