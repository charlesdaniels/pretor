import logging
import sqlite3
import argparse
import pathlib
import tabulate
import csv
import tempfile

from . import constants
from . import util
from . import psf


def query_cli(argv=None):
    parser = argparse.ArgumentParser(
        """
A tool for querying collections of PSFs using SQL.
        """
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
        "--glob",
        "-g",
        default="./**/*.psf",
        help="Specify the glob pattern used to select input files"
        + ". (default: ./**/*.psf)",
    )

    fmt = parser.add_mutually_exclusive_group()

    fmt.add_argument(
        "--pretty",
        "-p",
        default=False,
        action="store_true",
        help="Pretty-print query results.",
    )

    fmt.add_argument(
        "--tsv",
        "-t",
        default=False,
        action="store_true",
        help="Print output as tab-separated values",
    )

    fmt.add_argument(
        "--csv",
        "-c",
        default=False,
        action="store_true",
        help="Print output as comma-separated values",
    )

    action = parser.add_mutually_exclusive_group(required=True)

    action.add_argument(
        "--query",
        "-q",
        default=None,
        help="Specify an SQL query to run. Note that all data is "
        + "stored in a table named 'psf'",
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

    db = build_database(args.glob)
    rows = []
    cols = []
    with db:
        cursor = db.cursor()
        try:
            cursor.execute(args.query)
            rows = cursor.fetchall()
            cols = [x[0] for x in cursor.description]
        except Exception as e:
            util.log_exception(e)

    if args.pretty:
        print(tabulate.tabulate(rows, cols, tablefmt="fancy_grid"))

    elif args.csv:
        f = tempfile.SpooledTemporaryFile(mode="w")
        writer = csv.writer(f)
        writer.writerow(cols)
        writer.writerows(rows)
        f.seek(0)
        print(f.read())

    elif args.tsv:
        f = tempfile.SpooledTemporaryFile(mode="w")
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(cols)
        writer.writerows(rows)
        f.seek(0)
        print(f.read())

    else:
        print(tabulate.tabulate(rows, tablefmt="plain"))


def build_database(glob):
    """build_database

    Build a sqlite database from a library of PSFs specified by the given glob.

    :param glob:
    """

    db = sqlite3.connect("memory")

    schema = """
CREATE TABLE psf(
    uuid TEXT,
    filename TEXT,
    path TEXT,
    course TEXT,
    semester TEXT,
    section TEXT,
    groupid TEXT,
    assignment TEXT,
    graded BOOL,
    grade FLOAT,
    no_meta_check BOOL,
    allow_no_toml BOOL,
    disable_version_check BOOL,
    forensic_no_meta_check BOOL,
    forensic_allow_no_toml BOOL,
    forensic_disable_version_check BOOL,
    forensic_hostname TEXT,
    forensic_timestamp TEXT,
    forensic_user TEXT,
    forensic_source_dir TEXT,
    forensic_pretor_version TEXT
);
    """
    with db:
        cursor = db.cursor()
        cursor.execute("DROP TABLE IF EXISTS psf")
        cursor.execute(schema)

        for path in pathlib.Path().glob(glob):
            thepsf = psf.PSF()
            try:
                thepsf.load_from_archive(path)
            except Exception as e:
                logging.warning("could not load '{}', skipping".format(path))
                util.log_exception(e)

            course = None
            if "course" in thepsf.metadata:
                course = thepsf.metadata["course"]

            assignment = None
            if "assignment" in thepsf.metadata:
                assignment = thepsf.metadata["assignment"]

            group = None
            if "group" in thepsf.metadata:
                group = thepsf.metadata["group"]

            semester = None
            if "semester" in thepsf.metadata:
                semester = thepsf.metadata["semester"]

            section = None
            if "section" in thepsf.metadata:
                section = thepsf.metadata["section"]

            no_meta_check = None
            if "no_meta_check" in thepsf.metadata:
                no_meta_check = thepsf.metadata["no_meta_check"]

            allow_no_toml = None
            if "allow_no_toml" in thepsf.metadata:
                allow_no_toml = thepsf.metadata["allow_no_toml"]

            disable_version_check = None
            if "disable_version_check" in thepsf.metadata:
                disable_version_check = thepsf.metadata["disable_version_check"]

            forensic_no_meta_check = None
            if "forensic_no_meta_check" in thepsf.forensic:
                forensic_no_meta_check = thepsf.forensic["no_meta_check"]

            forensic_allow_no_toml = None
            if "forensic_allow_no_toml" in thepsf.forensic:
                forensic_allow_no_toml = thepsf.forensic["allow_no_toml"]

            forensic_disable_version_check = None
            if "forensic_disable_version_check" in thepsf.forensic:
                forensic_disable_version_check = thepsf.forensic[
                    "disable_version_check"
                ]

            forensic_hostname = None
            if "forensic_hostname" in thepsf.forensic:
                forensic_hostname = thepsf.forensic["hostname"]

            forensic_user = None
            if "forensic_user" in thepsf.forensic:
                forensic_user = thepsf.forensic["user"]

            forensic_timestamp = None
            if "forensic_timestamp" in thepsf.forensic:
                forensic_timestamp = thepsf.forensic["timestamp"]

            forensic_source_dir = None
            if "forensic_source_dir" in thepsf.forensic:
                forensic_source_dir = thepsf.forensic["source_dir"]

            forensic_pretor_version = None
            if "forensic_pretor_version" in thepsf.forensic:
                forensic_pretor_version = thepsf.forensic["pretor_version"]

            grade = None
            if thepsf.is_graded():
                grade = thepsf.get_grade_rev().grade.get_score()

            vals = []

            vals.append(thepsf.ID)  # uuid TEXT,
            vals.append(str(path.name))  # filename TEXT,
            vals.append(str(path))  # path TEXT,
            vals.append(course)  # course TEXT,
            vals.append(semester)  # semester TEXT,
            vals.append(section)  # section TEXT,
            vals.append(group)  # group TEXT,
            vals.append(assignment)  # assignment TEXT,
            vals.append(thepsf.is_graded())  # graded BOOL,
            vals.append(grade)  # grade FLOAT,
            vals.append(no_meta_check)  # no_meta_check BOOL,
            vals.append(allow_no_toml)  # allow_no_toml BOOL,
            vals.append(disable_version_check)  # disable_version_check BOOL,
            vals.append(forensic_no_meta_check)  # forensic_no_meta_check BOOL,
            vals.append(forensic_allow_no_toml)  # forensic_allow_no_toml BOOL,
            vals.append(
                forensic_disable_version_check
            )  # forensic_disable_version_check BOOL,
            vals.append(forensic_hostname)  # forensic_hostname TEXT,
            vals.append(forensic_timestamp)  # forensic_timestamp TEXT,
            vals.append(forensic_user)  # forensic_user TEXT,
            vals.append(forensic_source_dir)  # forensic_source_dir TEXT,
            vals.append(forensic_pretor_version)  # forensic_pretor_version TEXT

            cursor.execute(
                "INSERT INTO psf VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                vals,
            )

        return db
