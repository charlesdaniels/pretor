import toml
import os
import logging
import subprocess
import distutils.dir_util

import pretor.constants

def load_assignment_file (fpath):
    """load_assignment_file

    Load an assignment TOML file by it's path and sanity check it's contents.

    In particular, an assignment file must have the following keys:

    * test_command - the command to execute to produce the results file

    * include - boolean, assert if supporting files (e.g. test cases) need
      to be copied into the environment before execution

    * include_path - directory containing supporting files to be copied into
      the test environment. Files directly under this path are copied into the
      root directory of the test environment. If this path is relative, it is
      treated as relative to the parent directory of the assignment TOML file.
      This value is normalized to an absolute path before this function
      returns. Note that the include path is not validated to exist in this
      function.

    :param fpath:
    """

    logging.debug("loading assignment file {}".format(fpath))

    assignment = None
    with open(fpath, "r") as f:
        assignment = toml.load(f)

    # validate keys are present
    if 'test_command' not in assignment:
        logging.error("assignment file {} missing key {}"
                .format(fpath, "test_command"))
        raise InvalidFile(fpath)

    if 'include' not in assignment:
        logging.error("assignment file {} missing key {}"
                .format(fpath, "include"))
        raise InvalidFile(fpath)

    # if we assert include, we must also assert the include path
    assignment["include"] = bool(assignment["include"])
    if assignment["include"] and ('include_path' not in assignment):
        logging.error("assignment file {} asserts include but does not specify include_path"
                .format(fpath))
        raise InvalidFile(fpath)

    # normalize the include path if it is not absolute
    if not os.path.isabs(assignment["include_path"]):
        # make absolute relative to parent of fpath
        assignment["include_path"] = os.path.join(
                os.path.dirname(fpath),
                assignment["include_path"])

    return assignment

def setup_assignment(submission_file, assignment_file):
    """setup_assignment

    Setup an assignment environment and return it's path.

    :param submission_file:
    :param assignment_file:
    :param output_file:
    """

    assignment = pretor.assignment.load_assignment_file(assignment_file)

    temp_dir = tempfile.gettempdir()
    os.makedirs(temp_dir)

    # create the assignment directory
    assignment_dir = calculate_assignment_dir(temp_dir)
    os.makedirs(assignment_dir)

    # copy in the submission file
    os.copy(submission_file, assignment_dir)

    # extract the submission file
    # TODO

    # copy in the include dir
    if assignment["include"]:
        distutils.dir_util.copy(assignment["include_path"], assignment_dir)


    return temp_dir

def calculate_assignment_dir(assignment_env):
    return os.path.join(assignment_env,
            pretor.constants.assignment_dir_name)

def execute_command(assignment_env, command):
    """execute_command

    Run a command in the execution environment of a particular assignment.

    Returns a tuple of (return_code, stdout, stderr)

    :param assignment_env:
    :param command: a list to pass to Popen
    """
    assignment_dir = calculate_assignment_dir(temp_dir)
    os.chdir(assignment_dir)

    logging.debug("execute command '{}' in assignment env '{}'"
            .format(command, assignment_env))

    process = subprocess.Popen(command, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    retcode = process.returncode

    logging.debug("command exited with code '{}'".format(retcode))

    return (retcode, stdout, stderr)
