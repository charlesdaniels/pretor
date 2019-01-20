import copy
import logging
import os
import pathlib
import sys
import toml
import argparse
import tabulate

from . import exceptions
from . import constants
from . import course
from . import util

def grade_dbg_cli():

    parser = argparse.ArgumentParser("""CLI tool for displaying information
stored in Pretor grade definition files. This tool is primarily for debugging
issues relating to the pretor.grade module, and is not recommended for
production use.
""")

    parser.add_argument("--version", action="version",
            version=constants.version)

    parser.add_argument("--debug", "-d", action="store_true", default=False,
            help="Log debugging output to the console.")

    parser.add_argument("--course", "-c", required=True, type=pathlib.Path,
            help="Specify the course definition file to load.")

    parser.add_argument("--assignment", "-a", required=True,
            help="Specify the assignment to associate with the grade")

    parser.add_argument("--file", "-f", required=True, type=pathlib.Path,
            help="Specify the Pretor grade definition file to load")

    action = parser.add_mutually_exclusive_group(required=True)

    action.add_argument("--scorecard", "-s", default=False,
            action="store_true", help="Display the scorecard.")

    args = parser.parse_args()

    if args.debug:
        util.setup_logging(logging.DEBUG)
    else:
        util.setup_logging()

    try:
        the_course = course.load_course_definition(args.course)
        assignment = the_course.assignments[args.assignment]
        grade = Grade(assignment)
        grade.load_file(args.file)

        if args.scorecard:
            sys.stdout.write(grade.generate_scorecard())

    except Exception as e:
        util.log_exception(e)
        sys.exit(1)

class Grade:
    """Grade

    Top-level abstraction for the concept of a specific grade on a specific
    assignment.

    Scores are stored in .categories, which is a hashtable containing the
    category names as keys, and the category scores as integers. This is
    analagous to course.Assignment.categories.

    Each Grade object also contains a pointer to the assignment it is a grade
    for. This is required because the assignments categories are used to
    compute the overall score on the assignment, and also for formatting
    scorecards

    Note that the category scores are initialized to 100%, this is as a
    shortcut for graders - a score file absent of any information implies a
    100% score.

    A grade also stores four additional parameters:

    feedback: instructor feedback as a string if any

    bonus_multiplier: bonus multiplier (>= 0.0)

    penalty_multiplier: penalty multiplier (>= 0.0)

    bonus_marks: bonus marks amount (positive integer)

    bonus_score: bonus score amount (0..1)

    penalty_marks: penalty marks amount (positive integer)

    penalty_score: penalty score amount (0..1)

    override: override final score (0..1)

    See the documentation for get_score() for information on how scores are
    calculated.

    """

    def __init__(this, assignment: course.Assignment):
        """__init__

        :param this:
        :param assignment:
        :type assignment: course.Assignment
        """

        this.assignment = assignment

        this.feedback = ""
        this.override = None

        this.bonus_multiplier = 0.0
        this.bonus_marks = 0
        this.bonus_score = 0.0

        this.penalty_multiplier = 0.0
        this.penalty_marks = 0
        this.penalty_score = 0.0

        this.categories = copy.deepcopy(this.assignment.categories)

    def __str__(this):
        return "<Grade for Assignment {}, score={}>".format(
                this.assignment, this.get_score())

    def get_score(this):
        """get_score

        Compute the score and return it as a float in 0..1.

        If the override field is specified (not ``None``), then it will be used
        as the final percent score in 0..1. This is in place to allow graders
        the freedom to handle special circumstances without having to hack
        category scores or bonus amount.

        NOTE: where '0..1' is used, this implies that the given field is a
        floating point percentage such that a value of '0' indicates a 0%
        score, and a value of '1.0' indicates a 100% score. However, such
        values are not actually bounds checked, so a bonus or penalty of less
        than 0 or greater than 1 is allowed.

        If the override field is ``None``, then the assignment grade is
        calculated as g = ((m + b_m - p_m)/ M) * (1.0 + b - p) + B - P, where:

        g is the final percent score in 0..1 (scores of higher than 1 may be
        possible with bonus)

        m is the number of earned marks on the assignment (sum of category
        scores)

        b_m is the number of bonus marks on the assignment

        p_m is the number of penalty marks on the assignment

        M is the maximum number of marks on the assignment (sum of category
        maxes)

        b is the bonus multiplier

        p is the penalty multiplier

        B is the score bonus

        P is the score penalty

        :param this:
        """

        if this.override is not None:
            return this.override

        marks = (this.get_marks() +
                    this.bonus_marks -
                    this.penalty_marks) / this.assignment.max_marks()

        marks *= (1.0 + this.bonus_multiplier - this.penalty_multiplier)

        marks += (this.bonus_score - this.penalty_score)

        return marks


    def get_marks(this):
        """get_marks

        Return the total number of earned marks on this assignment.

        :param this:
        """

        return sum(this.categories.values())

    def dump_string(this, path: pathlib.Path):
        """dump_string

        Dump the current category scores and any optional fields that are
        nonzero to a TOML file. This is generally used for the purpose of
        generating a template for the grader to fill in.

        This function should not be used (alone) for serializing Grade objects,
        as the relationship between the Grade and the Assignment will not be
        preserved.

        Note that this function will add a "assignment_name" field which is
        used by the PSF archive loader. This field is not used by load_file().

        :param this:
        :param path:
        :type path: pathlib.Path
        """

        logging.debug("dumping grade {} to '{}'".format(this, path))

        data = {}

        # dump any optional fields, if they exist
        if this.feedback is not "":
            data["feedback"] = this.feedback

        if this.bonus_multiplier != 0:
            data["bonus_multiplier"] = this.bonus_multiplier

        if this.bonus_marks != 0:
            data["bonus_marks"] = this.bonus_marks

        if this.bonus_score != 0:
            data["bonus_score"] = this.bonus_score

        if this.penalty_multiplier != 0:
            data["penalty_multiplier"] = this.penalty_multiplier

        if this.penalty_marks != 0:
            data["penalty_marks"] = this.penalty_marks

        if this.penalty_score != 0:
            data["penalty_score"] = this.penalty_score

        # this is required because the PSF archive loader stores the entire
        # course definition, and we need to know which specific assignment
        # to load
        data["assignment_name"] this.assignment.name

        # dump categories
        data["categories"] = this.categories

        return toml.dumps(data)


    def generate_scorecard(this):
        """generate_scorecard

        Generate a scorecard for this Grade. This is a human-readable string
        which contains the student's marks on each each category, their
        calculated score, any feedback, and any bonuses, penalties, or override
        if present.

        :param this:
        """

        s = "SCORECARD FOR {}: {}\n\n".format(
                this.assignment.course.name, this.assignment.name)

        if this.feedback != "":
            s += this.feedback + "\n\n"

        table_data = [["CATEGORY", "MARKS", "MAX MARKS", "PERCENT SCORE"]]

        for category in this.categories:
            table_data.append([
               category,
               this.categories[category],
               this.assignment.categories[category],
               "{:3.2f}%".format(this.get_category_percent(category) * 100)
               ])

        if this.bonus_marks != 0:
           table_data.append(["BONUS MARKS", this.bonus_marks, "--", "--"])

        if this.penalty_marks != 0:
            table_data.append(
                ["PENALTY MARKS", this.penalty_marks, "--", "--"])

        s += tabulate.tabulate(table_data, tablefmt = "plain")

        s += "\n\n"

        raw_score = (this.get_marks() / this.assignment.max_marks())
        raw_score_net = ((this.get_marks() + this.bonus_marks + 
            this.penalty_marks) / this.assignment.max_marks())

        s += "OVERALL MARKS: {}\n".format(this.get_marks())
        s += "MAXIMUM OVERALL MARKS: {}\n".format(this.assignment.max_marks())
        s += "RAW SCORE: {:3.2f}%\n".format(raw_score * 100)

        if (this.bonus_marks != 0 or this.penalty_marks != 0):
            s += "RAW SCORE NET OF BONUS/PENALTY MARKS: {:3.2f}%\n".format(
                     raw_score_net * 100)

        s += "\n"

        score_multiplier = raw_score_net * (1.0 + this.bonus_multiplier - 
                this.penalty_multiplier)

        if this.bonus_multiplier != 0:
            s += "BONUS MULTIPLIER: {:3.2f}\n".format(this.bonus_multiplier)

        if this.penalty_multiplier != 0:
            s += "PENALTY MULTIPLIER: {:3.2f}\n".format(this.penalty_multiplier)

        if (this.penalty_multiplier != 0 or this.bonus_multiplier != 0):
            s += "SCORE NET OF BONUS/PENALTY MULTIPLIER: {:3.2f}%\n\n".format(
                    score_multiplier * 100)

        score_bonus = score_multiplier + this.bonus_score - this.penalty_score
        if this.bonus_score != 0:
            s += "BONUS SCORE: {:3.2f}%\n".format(this.bonus_score * 100)

        if this.penalty_score != 0:
            s += "PENALTY SCORE: {:3.2f}%\n".format(this.penalty_score * 100)

        if (this.penalty_score !=0 or this.bonus_score !=0):
            s += "SCORE NET OF BONUS/PENALTY SCORE: {:3.2f}%\n\n".format(
                    score_bonus * 100)

        s += "OVERALL SCORE: {:3.2f}%\n".format(this.get_score() * 100)

        return s


    def get_category_percent(this, category):
        """get_category_percent

        Get the percent score in 0..1 for a single specific category. The
        caller is expected to do error handling.

        :param this:
        :param category:
        """

        return this.categories[category] / this.assignment.categories[category]


    def load_file(this, path: pathlib.Path):
        """load_file

        Load a grade file from disk. A grade file is a TOML file with one
        optional top level key: "feedback" which is a string containing one
        required section, "categories", which contains category names as keys
        and category scores as integer values. Omitted categories are taken to
        be their maximum value (full credit by default).

        Additionally, a grade file may contain the following optional keys, as
        specified in the description of this object: feedback,
        bonus_multiplier, bonus_marks, bonus_score, penalty_multiplier,
        penalty_marks, penalty_score.

        :param this:
        :param path:
        :type path: pathlib.Path
        """

        logging.debug("loading grade data from file '{}' to {}"
                .format(path, this))

        path = pathlib.Path(path)

        grade_data = toml.load(path)

        # try to load optional fields
        try:
            if "feedback" in grade_data:
                this.feedback = grade_data["feedback"]

            if "override" in grade_data:
                this.override = float(grade_data["override"])

            if "bonus_multiplier" in grade_data:
                this.bonus_multiplier = float(grade_data["bonus_multiplier"])

            if "bonus_marks" in grade_data:
                this.bonus_marks = int(grade_data["bonus_marks"])

            if "bonus_score" in grade_data:
                this.bonus_score = float(grade_data["bonus_score"])

            if "penalty_multiplier" in grade_data:
                this.penalty_multiplier = float(grade_data["penalty_multiplier"])

            if "penalty_marks" in grade_data:
                this.penalty_marks = int(grade_data["penalty_marks"])

            if "penalty_score" in grade_data:
                this.penalty_score = float(grade_data["penalty_score"])

        except Exception as e:
            util.log_exception(e)
            raise exceptions.InvalidFile(
                    "Could not load grade data from file '{}', malformed field"
                    .format(path))

        if "categories" not in grade_data:
            raise exceptions.InvalidFile(
                    "Could not load grade data from file '{}', missing categories"
                    .format(path))

        for category in grade_data["categories"]:
            marks = 0
            try:
                marks = int(grade_data["categories"][category])
            except Exception as e:
                util.log_exception(e)
                raise exceptions.InvalidFile(
                        ("Could not load grade data from file '{}', category" +
                            " '{}' has an invalid valid '{}'")
                        .format(path, category, grade_data["categories"][category]))

            # don't allow categories that don't pertain to this assignment
            if category not in this.categories:
                raise exceptions.InvalidFile(
                        ("Could not load grade data from file '{}', category" +
                            " '{}' not present in assignment {}")
                        .format(path, category, this.assignment))

            this.categories[category] = marks
