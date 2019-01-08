import sys
import argparse
import logging
import os
import toml
import pathlib
import getpass
import datetime
import hashlib
import socket

import pretor.util

descr = """
Tool for generate Pretor Submission Files (PSF).
"""

def load_toml(project : pathlib.Path):
    """load_toml

    Load the pretor.toml file from the specified project path.

    :param project:
    :type project: pathlib.Path
    """

    logging.info("loading pretor.toml for project {}".format(project))

    project = pathlib.Path(project)

    toml_file = project / "pretor.toml"
    if not toml_file.exists():
        logging.error("'{}' does not exist (are you sure '{}' is your project folder?)"
                .format(toml_file, project))
        raise pretor.exceptions.MissingFile(toml_file)

    toml_data = toml.load(str(toml_file))

    require_keys = ["assignment", "course"]
    for key in require_keys:
        if key not in toml_data:
            raise pretor.exceptions.InvalidFile(
                "File '{}' missing key '{}'".format(toml_file, key))

    if "name_format" not in toml_data:
        toml_data["name_format"] = "{course}.{assignment}.{student}"

    with open(str(toml_file), 'rb') as f:
        toml_data["checksum"] = hashlib.sha256(f.read()).hexdigest()

    logging.info("loaded pretor.toml successfully.")

    return toml_data

def pack(directory, destination, name=None, student=None):
    """pack

    Pack an assignment submission.

    :param directory: Top level project directory.
    :param destination: Destination folder for generated PSF.
    :param name: Name of output file (inferred from TOML data if not specified)
    :param student: Student's user ID (inferred from getpass if not specified)
    """

    toml_data = load_toml(directory)

    format_data = {}
    if student is None:
        format_data["student"] = getpass.getuser()
    else:
        format_data["student"] = student
    format_data["course"] = toml_data["course"]
    format_data["assignment"] = toml_data["assignment"]
    logging.debug("generated format_data: {}".format(format_data))

    # infer name from TOML data
    if name is None:
        name = toml_data["name_format"].format(**format_data)
    if name[:4] != ".psf":
        name = "{}.psf".format(name)

    destination_file = os.path.join(destination, name)
    logging.info("writing PSF file to '{}'".format(destination_file))

    metadata = {}
    metadata["timestamp"] = datetime.datetime.now()
    metadata["toml_checksum"] = toml_data["checksum"]
    metadata["user"] = getpass.getuser()
    metadata["host"] = socket.gethostname()

    pretor.util.zip_folder(directory,
        destination_file,
        comment=toml.dumps(metadata))

def main():

    parser = argparse.ArgumentParser(description=descr)

    parser.add_argument("--directory", "-d", default="./", type=pathlib.Path,
            help="Directory to pack for submission. This directory " +
            "should contain your project's pretor.toml file. (default: ./)")

    parser.add_argument("--destination", "-e", default="../",
            help="Directory in which to place packed file (default: ../)")

    parser.add_argument("--name", "-n", default=None,
            help="Override output file name (not recommended, this is " +
            "usually generated from pretor.toml, which your instructor " +
            "should provide. If you specify this option, it may make " +
            "it more difficult for your instructor to grade your " +
            "assignment).")

    parser.add_argument("--debug", "-b", default=False, action="store_true",
            help="Output pretor debugging messages.")

    parser.add_argument("--student", "-s", default=None,
            help="Override user ID associated with the generated file. " +
            "If this option is not specified, the username of the logged " +
            "in user will be used. Unless your instructor tells you " +
            "otherwise, you should not specify this option unless you " +
            "are generating a submission file for a user other than " +
            "whoever is logged into the computer.")

    args = parser.parse_args()

    if args.debug:
        pretor.util.setup_logging(logging.DEBUG)
    else:
        pretor.util.setup_logging()


    try:
        pack(directory      = args.directory,
                destination = args.destination,
                name        = args.name,
                student     = args.student)


    except Exception as e:
        pretor.util.log_exception(e)
        exit(1)
