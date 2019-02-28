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

    parser.add_argument("--version", action="version", version=constants.version)

    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        default=False,
        help="Log debugging output to the console.",
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

    args = None
    if argv is not None:
        args = parser.parse_args(argv)
    else:
        args = parser.parse_args()

    if args.debug:
        util.setup_logging(logging.DEBUG)
    else:
        util.setup_logging()

    fp = None
    if args.input is not None:
        fp = open(str(args.input), "r")
    elif not sys.stdin.isatty():
        fp = sys.stdin
    else:
        logging.error("No input source, specify --input")
        sys.exit(1)

    xsv_data = []
    xsv_reader = None
    schema = None
    if args.schema is not None:
        schema = args.schema.split(",")

    if args.tsv:
        xsv_reader = csv.reader(fp, delimiter="\t")
    else:
        xsv_reader = csv.reader(fp)

    for row in xsv_reader:
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
        candidates = []
        for psf_obj in psf_collection:

            # we will match this PSF unless invalidate is tripped
            invalidate = False
            for key in schema_keys:

                # check that it has the key
                if key not in psf_obj.metadata:
                    logging.warning("PSF {} missing key {}, ignoring".format(key))
                    invalidate = True

                #  check if they key matches
                elif psf_obj.metadata[key] != rec[key]:
                    invalidate = True

            if not invalidate:
                candidates.append(psf_obj)

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

            course_obj = None
            rev = None

            # setup the revision
            if psf_obj.is_graded():
                rev = psf_obj.create_grade_revision()
            else:
                rev = psf_obj.create_revision("graded_0", args.baserev)

            # setup the course so we can instantiate the grade
            if "course" not in psf_obj.metadata:
                logging.warning("PSF {} missing course, skipping it".format(psf_obj))
                continue

            elif psf_obj.metadata["course"] not in courses:
                logging.warning(
                    "PSF {} specifies unknown course {}, skipping it".format(
                        psf_obj, psf_obj.metadata["course"]
                    )
                )
                continue

            else:
                course_obj = courses[psf_obj.metadata["course"]]

            # setup the assignment so we can instantiate the grade
            if "assignment" not in psf_obj.metadata:
                logging.warning(
                    "PSF {} missing assignment, skipping it".format(psf_obj)
                )
                continue

            elif psf_obj.metadata["assignment"] not in course_obj.assignments:
                logging.warning(
                    "PSF {} specifies unknown assignment '{}' for course '{}', skipping it".format(
                        psf_obj, psf_obj.metadata["assignment"], course_obj
                    )
                )
                continue

            # create the grade object
            grade_obj = grade.Grade(
                course_obj.assignments[psf_obj.metadata["assignment"]]
            )
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
