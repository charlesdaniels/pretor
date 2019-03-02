# Copyright 2019 Charles A Daniels
# Distributed under the GNU AGPLv3 License (https://www.gnu.org/licenses/agpl.txt)

import argparse
import logging
import pathlib
import sys
import tabulate
import tomlkit as toml
from tomlkit.toml_document import TOMLDocument

from . import constants
from . import exceptions
from . import util


def course_cli():
    """course_cli"""

    parser = argparse.ArgumentParser(
        """CLI tool for displaying information
about a pretor course. This tool is primarily of use to those creating or
modifying pretor course definitions."""
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
        "--course",
        "-c",
        required=True,
        type=pathlib.Path,
        help="Specify the course definition file to load.",
    )

    action = parser.add_mutually_exclusive_group(required=True)

    action.add_argument(
        "--summary",
        "-s",
        default=False,
        action="store_true",
        help="Display a summary of the generated course object.",
    )

    action.add_argument(
        "--rubric",
        "-r",
        default=None,
        help="Display the rubric for the specified assignment.",
    )

    args = parser.parse_args()

    if args.debug:
        util.setup_logging(logging.DEBUG)
    else:
        util.setup_logging()

    try:
        course = load_course_definition(args.course)

        if args.summary:
            sys.stdout.write(course.generate_tree())

        elif args.rubric is not None:
            if args.rubric not in course.assignments:
                raise KeyError("no such assignment '{}'".format(args.rubric))

            sys.stdout.write(course.assignments[args.rubric].generate_rubric())

    except Exception as e:
        util.log_exception(e)
        sys.exit(1)


def load_courses(pathlist, glob="**/*.toml"):
    """load_courses

    Load course definitions from a list of files or directories

    :param pathlist:
    """

    # load all courses in the coursepath
    courses = {}
    for p in pathlist:
        p = pathlib.Path(p)
        if p.is_file():
            logging.debug("loading course from file {}".format(p))
            try:
                c = load_course_definition(p)
                courses[c.name] = c
                logging.debug("loaded course successfully")
            except Exception as e:
                util.log_exception(e)
                logging.warning("failed to load course from '{}'".format(p))
        else:
            for fp in p.glob(glob):
                logging.debug("loading course from file {}".format(fp))
                try:
                    c = load_course_definition(fp)
                    courses[c.name] = c
                    logging.debug("loaded course successfully")
                except Exception as e:
                    util.log_exception(e)
                    logging.warning("failed to load course from '{}'".format(fp))

    return courses


def load_assignment(as_key, course_data, course):

    as_data = dict(course_data[as_key])

    for key in ["name", "weight"]:
        if key not in as_data:
            raise exceptions.InvalidFile(
                (
                    "course file '{}' malformed"
                    + "'{}' malformed assignment with key '{}'"
                ).format(path, as_key)
            )

    # weights are percentages
    weight = float(as_data["weight"])
    if weight < 0 or weight > 1:
        raise exceptions.InvalidFile(
            (
                "course file '{}' malformed" + "assignment '{}': invalid weight {}"
            ).format(path, as_data["name"], as_data["weight"])
        )

    # pop out name and weight, leaving us just the categories
    name = as_data["name"]
    description = ""
    if "description" in as_data:
        description = as_data["description"]
        as_data.pop("description")
    as_data.pop("name")
    as_data.pop("weight")

    for key in ["name", "weight", "description"]:
        if key in as_data:
            logging.error(
                "You should never see this, if you do, you have found a bug in Pretor. Please send a bug report, and be sure to include the message 'course:205'"
            )

    # validate that all the category marks are valid
    for cat_name in as_data:
        try:
            as_data[cat_name] = int(as_data[cat_name])
            assert as_data[cat_name] >= 0
        except Exception as e:

            raise exceptions.InvalidFile(
                (
                    "course file '{}' malformed"
                    + "assignment '{}' category '{}' invalid marks: {}"
                ).format(path, as_data["name"], cat_name, as_Dta[cat_name])
            )

    # XXX: this double linking might confuse the garbage collector, should
    # investigate if there are any negative implications
    assignment = Assignment(
        course=course,
        name=name,
        weight=weight,
        categories=as_data,
        description=description,
    )

    return assignment


def load_course_definition(origin):
    """load_course_definition

    Load a course definition from disk.

    A course definition a toml containing several sections.

    The section "course" is special - it is required, and stores top-level
    metadata about the course. This section must contain the key "name",
    and may optionally contain a "description" key.

    All other sections are assumed to be assignment definitions. Each must
    contain at a minimum the keys:

    * "name" - the assignment name
    * "weight" - floating point weight out of the overall course in 0..1.0

    The "description" key may optionally be defined.

    All other keys are assumed to be rubric categories -- the key is the
    category name, and the value is the integer number of maximum marks.
    At least one such category must be defined.

    :param origin: Either a path to load TOML from, or a dictionary.
    """

    course_data = origin
    if (type(origin) is not dict) and (type(origin) is not TOMLDocument):
        path = pathlib.Path(origin)
        logging.debug("loading course definition from '{}'...".format(path))
        with open(str(path), "r") as f:
            course_data = dict(toml.loads(f.read()))

    # validate course definition
    if "course" not in course_data:
        raise exceptions.InvalidFile("course file '{}' missing [course]".format(path))

    if "name" not in course_data["course"]:
        raise exceptions.InvalidFile("course file '{}' specifies no name".format(path))

    if len(course_data) < 2:
        raise exceptions.InvalidFile(
            "course file '{}' specifies no assignments".format(path)
        )

    course = Course(
        course_data["course"]["name"],
        description=course_datap["course"]["description"]
        if "description" in course_data
        else "",
    )

    # load each individual assignment
    for as_key in [k for k in course_data.keys() if k != "course"]:
        assignment = load_assignment(as_key, course_data, course)
        course.assignments[assignment.name] = assignment

    return course


class Course:
    """Course

    Abstraction for a single course, corresponding to a course definition on
    disk.
    """

    def __init__(this, name, description=""):
        this.assignments = {}
        this.name = name
        this.description = description

    def __str__(this):
        return "<Course name='{}', {} assignments>".format(
            this.name, len(this.assignments)
        )

    def generate_tree(this):
        """generate_tree

        Generate a string containing a tree-style representation of this
        assignment.

        :param this:
        """

        s = str(this) + "\n"
        for assignment in this.assignments:
            s += "\t" + str(this.assignments[assignment]) + "\n"
        return s

    def dump_string(this):
        """dump_string

        Generate a serialized representation of this object that can be loaded
        via load_course_definition().

        :param this:
        """

        data = {}

        data["course"] = {"name": this.name, "description": this.description}
        for assignment_name in this.assignments:
            assignment = this.assignments[assignment_name]
            data[assignment_name] = {
                "name": assignment.name,
                "weight": assignment.weight,
                "description": assignment.description,
            }
            for key in assignment.categories:
                data[assignment_name][key] = assignment.categories[key]

        return toml.dumps(data)


class Assignment:
    """Assignment

    Abstraction for a single assignment, corresponding to a rubric file in
    a course definition.
    """

    def __init__(this, course, name, weight, categories, description=""):
        """__init__

        :param this:
        :param name: the assignment name
        :param weight: weight of the assignment out of the course in 0..1
        :param categories: table with category names as keys and maximum marks
                           per category as the values (as a positive integer).
        :param course: the parent Course object
        :param description: optional assignment description
        """

        this.course = course
        this.name = name
        this.weight = weight
        this.categories = categories
        this.description = description

    def __str__(this):
        return "<Assignment name='{}' weight={}>".format(this.name, this.weight)

    def generate_rubric(this):
        """generate_rubric

        Generate a string containing the rubric for the course.

        :param this:
        """

        s = "{}: {} ({:3.2f}%)\n\n".format(
            this.course.name, this.name, this.weight * 100
        )

        if this.description != "":
            s += this.description + "\n\n"

        s += tabulate.tabulate(
            [(cat, this.categories[cat]) for cat in this.categories.keys()],
            tablefmt="plain",
        )

        s += "\n\nSUM OF MARKS: {}\n".format(this.max_marks())

        return s

    def max_marks(this):
        """max_marks

        Return the sum of all category marks.

        :param this:
        """

        return sum(this.categories.values())
