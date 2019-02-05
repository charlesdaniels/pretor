import argparse
import csv
import io
import logging
import pathlib
import sys
import tabulate

from . import constants
from . import util
from . import psf

def csv_line(data):
    """csv_line

    Generate a single line of CSV as a string.

    :param data: list of items constituting the record
    """
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerow(data)
    return output.getvalue()

def format_moodle(psf_obj):
    """format_moodle

    Format a PSF's grading information for import into Moodle as CSV.

    Note that the SCORE is shown as a floating point percentage, i.e. 100.00
    would be full credit.

    Output format:

        SEMESTER,COURSE,SECTION,GROUP,SCORE,FEEDBACK

    :param psf_obj:
    """

    record = get_record(psf_obj)
    return csv_line(record)

def get_record(psf_obj):
    """get_record

    Generate a list containing the fields

        SEMESTER,COURSE,SECTION,GROUP,SCORE,FEEDBACK

    In that order from the given PSF.

    :param psf_obj:
    """

    data = get_fields(psf_obj)
    record = [
        data["semester"],
        data["course"],
        data["section"],
        data["group"],
        data["score"],
        data["feedback"]
    ]

    return record

def get_fields(psf_obj):
    """get_fields

    Return a hashtable containing the relevant fields or sensible default
    values if they are missing for the specified PSF. Score is normalized
    to a 100% scale, so a value of 100.00 means full credit.

    :param psf_obj:
    """

    semester = "UNSPECIFIED"
    if "semester" in psf_obj.metadata:
        semester = psf_obj.metadata["semester"]

    course = "UNSPECIFIED"
    if "course" in psf_obj.metadata:
        course = psf_obj.metadata["course"]

    section = "UNSPECIFIED"
    if "section" in psf_obj.metadata:
        section = psf_obj.metadata["section"]

    group = "UNSPECIFIED"
    if "group" in psf_obj.metadata:
        group = psf_obj.metadata["group"]

    feedback = ""
    if "feedback" in psf_obj.metadata:
        feedback = psf_obj.metadata["feedback"]

    score = 0
    if psf_obj.is_graded():
        score = psf_obj.get_grade_rev().grade.get_score() * 100.0
    else:
        feedback += "\nNo grade has been recorded for this assignment."

    return {
        "semester": semester,
        "course": course,
        "section": section,
        "group": group,
        "feedback": feedback,
        "score": score
    }

def export_cli():
    parser = argparse.ArgumentParser("""
A tool for exporting Pretor grades into various formats.
""")

    parser.add_argument("--version", action="version",
            version=constants.version)

    parser.add_argument("--debug", "-d", action="store_true", default=False,
            help="Log debugging output to the console.")

    parser.add_argument("--input", "-i", default="./**/*.psf",
            help="Specify glob pattern to search for PSF files to export." +
            " (default: **/*.psf)")

    format = parser.add_mutually_exclusive_group(required=True)

    format.add_argument("--moodle", "-m", default=False,
            action="store_true", help="Export to Moodle-compatible CSV")

    format.add_argument("--table", "-t", default=False, action="store_true",
            help="Export to human-readable plain text table")

    args = parser.parse_args()

    if args.debug:
        util.setup_logging(logging.DEBUG)
    else:
        util.setup_logging()

    PSFs = []
    try:
        for path in pathlib.Path().glob(args.input):
            if path.is_file():
                PSFs.append(psf.PSF())
                PSFs[-1].load_from_archive(path)

        logging.debug("loaded {} PSFs".format(len(PSFs)))

        if args.moodle:
            for p in PSFs:
                sys.stdout.write(format_moodle(p))

        elif args.table:
            sys.stdout.write(tabulate.tabulate(
                [get_record(p) for p in PSFs], tablefmt="plain"))
            sys.stdout.write("\n")

    except Exception as e:
        util.log_exception(e)
        sys.exit(1)
