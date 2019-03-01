# Copyright 2019 Charles A Daniels
# Distributed under the GNU AGPLv3 License (https://www.gnu.org/licenses/agpl.txt)

from . import constants
from . import course
from . import grade
from . import psf
from . import util

import argparse
import csv
import logging
import pathlib
import sys


def xsvimport_cli(argv=None):
    parser = argparse.ArgumentParser(
        """Import existing grade records to an existing library of PSFs."""
    )

    parser.add_argument(
        "--coursepath",
        "-P",
        default="./",
        type=str,
        help="Specify colon-delimited course definition search path.",
    )

    parser.add_argument(
        "PSFs",
        nargs="+",
        type=pathlib.Path,
        help="Specify PSFs to import grades into, or path(s) to "
        + "recursively search for PSFs in.",
    )

    parser.add_argument(
        "--input",
        "-i",
        default=None,
        help="Specify where to read grade records from. If unspecified "
        + "and standard in is not a TTY, standard input will be used.",
    )

    parser.add_argument(
        "--schema",
        "-s",
        default=None,
        help="Specify the schema to use. If none is specified, then the "
        + "first line of the input will be used. The schema is a "
        + "comma-delimited list, which may contain any of the fields "
        + "course, section, semester, assignment, group, feedback, "
        + "bonus_multiplier, bonus_marks, bonus_score, penalty_multiplier, "
        + "penalty_marks, penalty_score.",
    )

    parser.add_argument(
        "--force",
        "-f",
        default=False,
        action="store_true",
        help="Force records to be applied even if the schema is " + "ambiguous.",
    )

    parser.add_argument(
        "--tsv",
        "-t",
        default=False,
        help="By default, the input is assumed to be CSV. By asserting "
        + "this flag, it may be parsed as TSV instead.",
    )

    parser.add_argument(
        "--baserev",
        "-b",
        default="submission",
        help="Override the base revision (default: submission)",
    )

    args = util.handle_args(parser, argv)

    fp = None
    if args.input is not None:
        fp = open(str(args.input), "r")
    elif not sys.stdin.isatty():
        fp = sys.stdin
    else:
        logging.error("No input source, specify --input")
        sys.exit(1)

    xsv_reader = None
    if args.tsv:
        xsv_reader = csv.reader(fp, delimiter="\t")
    else:
        xsv_reader = csv.reader(fp)

    xsv_data, schema = read_xsv(fp, xsv_reader, args.schema)

    logging.info("loaded {} records from input".format(len(xsv_data)))

    logging.debug("loading PSFs... ")
    psf_collection = psf.load_collection(args.PSFs)
    logging.info("loaded {} PSFs".format(len(psf_collection)))

    metadata_keys = ["semester", "course", "section", "group", "assignment"]
    schema_keys = [k for k in metadata_keys if k in schema]
    if len(schema_keys) < 1:
        logging.error(
            "schema must specify at least one of: semester, course, section, group, assignment"
        )
        sys.exit(1)

    courses = course.load_courses(args.coursepath.split(":"))

    logging.debug("loaded courses: {}".format(courses))

    for rec in xsv_data:
        logging.debug("attempting to apply record {}".format(rec))

        # select every PSF which matches this query
        candidates = [p for p in psf_collection if match(p, rec, schema_keys)]

        if len(candidates) < 1:
            logging.warning("Record '{}' matches no PSF, skipping".format(rec))
            continue

        elif len(candidates) > 1 and not args.force:
            logging.warning(
                "Record '{}' matches multiple PSFs, refusing to import ambiguous record without --force"
            ).format(rec)
            continue

        # apply the record
        for psf_obj in candidates:
            logging.debug("applying record '{}' to PSF '{}'".format(rec, psf_obj))

            grade_obj, rev = create_grade(psf_obj, courses, args.baserev)

            if grade_obj is None:
                continue

            grade_data = {"categories": {}}
            score_keys = [
                "feedback",
                "override",
                "bonus_multiplier",
                "bonus_marks",
                "bonus_score",
                "penalty_multiplier",
                "penalty_marks",
                "penalty_score",
            ]

            # generate data to load into the grade
            for key in rec:
                if key in score_keys:
                    grade_data[key] = rec[key]
                elif key in metadata_keys:
                    pass
                else:
                    grade_data["categories"][key] = rec[key]
            grade_obj.load_data(grade_data)

            # populate the revision with the grade
            rev.grade = grade_obj

            # note that we get loaded_from from load_collection
            psf_obj.save_to_archive(psf_obj.loaded_from)


def match(psf_obj, record, keys):
    """match

    Check if a given PSF object matches the specified record, given a list of
    metadata keys to compare along.

    :param psf_obj:
    :param record:
    :param keys:
    """

    # we will match this PSF unless invalidate is tripped
    invalidate = False
    for key in keys:

        # check that it has the key
        if key not in psf_obj.metadata:
            logging.warning("PSF {} missing key {}, ignoring".format(key))
            invalidate = True

        #  check if they key matches
        elif psf_obj.metadata[key] != record[key]:
            invalidate = True

    return not invalidate


def create_grade(psf_obj, courses, baserev="submission"):
    """create_grade

    Instantiate a Grade object for the PSF in a new canonical grade revision.

    Return the object, or None if there is insufficient data to create it, 
    as well as the revision in which it was created, as a tuple in that order.

    :param psf_obj:
    :param courses:
    :param baserev:
    """

    course_obj = None
    rev = None

    # setup the revision
    if psf_obj.is_graded():
        rev = psf_obj.create_grade_revision()
    else:
        rev = psf_obj.create_revision("graded_0", baserev)

    # setup the course so we can instantiate the grade
    if "course" not in psf_obj.metadata:
        logging.warning("PSF {} missing course, skipping it".format(psf_obj))
        return None

    elif psf_obj.metadata["course"] not in courses:
        logging.warning(
            "PSF {} specifies unknown course {}, skipping it".format(
                psf_obj, psf_obj.metadata["course"]
            )
        )
        return None

    else:
        course_obj = courses[psf_obj.metadata["course"]]

    # setup the assignment so we can instantiate the grade
    if "assignment" not in psf_obj.metadata:
        logging.warning("PSF {} missing assignment, skipping it".format(psf_obj))
        return None

    elif psf_obj.metadata["assignment"] not in course_obj.assignments:
        logging.warning(
            "PSF {} specifies unknown assignment '{}' for course '{}', skipping it".format(
                psf_obj, psf_obj.metadata["assignment"], course_obj
            )
        )
        return None

    # create the grade object
    grade_obj = grade.Grade(course_obj.assignments[psf_obj.metadata["assignment"]])

    return grade_obj, rev


def read_xsv(fp, reader, schema=None):
    """read_xsv

    Read an XSV file using the given reader. If the schema is None, then it is
    loaded from the first line of the file. Return (records, schema).

    :param fp: file to read from
    :param reader:
    :param schema:
    """
    xsv_data = []
    schema = None
    if schema is not None:
        schema = schema.split(",")

    for row in reader:
        if schema is None:
            schema = row
            continue

        if len(row) != len(schema):
            logging.error(
                "Malformed file, row '{}' does not match schema '{}'".format(
                    row, schema
                )
            )
            sys.exit(1)

        rec = {}
        for tup in zip(row, schema):
            rec[tup[1]] = tup[0]

        xsv_data.append(rec)

    fp.close()

    return xsv_data, schema
