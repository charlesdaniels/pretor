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

    db = sqlite3.connect(":memory:")

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

            # keep in mind that this is all order sensitive
            vals = [thepsf.ID, str(path.name), str(path)]

            for key in ["course", "semester", "section", "group", "assignment"]:
                if key in thepsf.metadata:
                    vals.append(thepsf.metadata[key])
                else:
                    vals.append(None)

            vals.append(thepsf.is_graded())

            if thepsf.is_graded():
                vals.append(thepsf.get_grade_rev().grade.get_score())
            else:
                vals.append(None)

            for key in ["no_meta_check", "allow_no_toml", "disable_version_check"]:
                if key in thepsf.metadata:
                    vals.append(thepsf.metadata[key])
                else:
                    vals.append(None)

            for key in [
                "no_meta_check",
                "allow_no_toml",
                "disable_version_check",
                "hostname",
                "timestamp",
                "user",
                "source_dir",
                "pretor_version",
            ]:
                if key in thepsf.forensic:
                    vals.append(thepsf.forensic[key])
                else:
                    vals.append(None)

            cursor.execute(
                "INSERT INTO psf VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                vals,
            )

        return db
