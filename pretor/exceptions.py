# Copyright 2019 Charles A Daniels
# Distributed under the GNU GPLv3 License (https://www.gnu.org/licenses/gpl.txt)


class MissingFile(Exception):
    """MissingTomlFile

    Indicates that a file was expected but not found, usually in the context
    of something the user was supposed to supply.
    """
    def __init__(this, path="unspecified"):
        path = str(path)
        message = "Missing file: {}".format(path)

        super().__init__(message)

class InvalidFile(Exception):
    """InvalidFile

    Indicates that a (user-supplied) file exists, but contains invalid data.
    """

    def __init__(this, msg="unspecified"):
        msg= str(msg)
        message = "Invalid file: {}".format(msg)

        super().__init__(message)

class StateError(Exception):
    """
    Indicates that the system state is in some way inconsistent with what it
    should be.
    """

    def __init__(this, msg="unspecified"):
        msg= str(msg)
        message = "State error: {}".format(msg)

        super().__init__(message)
