import unittest
import sys
import tempfile
import shutil
import os
import pathlib
import contextlib
import io

from pretor import grade


class DummyAssignment:

    def __init__(this):

        this.categories = {
                "category1": 50,
                "category2": 50,
            }

    def max_marks(this):
        return 100


class TestGrade(unittest.TestCase):

    def setUp(this):
        this.assignment = DummyAssignment()

    def teardOwn():
        this.assignment = None

    def test_load_data(this):

        grade_obj = grade.Grade(this.assignment)

        data = {
            "feedback": "the feedback",
            "bonus_multiplier": 1,
            "bonus_marks": 2,
            "bonus_score": 3,
            "penalty_multiplier": 4,
            "penalty_marks": 5,
            "penalty_score": 6,
            "categories": {"category1": 50, "category2": 50},
        }

        grade_obj.load_data(data)

        this.assertEqual(data["feedback"], grade_obj.feedback)
        this.assertEqual(data["bonus_multiplier"], grade_obj.bonus_multiplier)
        this.assertEqual(data["bonus_marks"], grade_obj.bonus_marks)
        this.assertEqual(data["bonus_score"], grade_obj.bonus_score)
        this.assertEqual(data["penalty_multiplier"], grade_obj.penalty_multiplier)
        this.assertEqual(data["penalty_marks"], grade_obj.penalty_marks)
        this.assertEqual(data["penalty_score"], grade_obj.penalty_score)

    def test_bonus_multiplier(this):
        grade_obj = grade.Grade(this.assignment)
        grade_obj.bonus_multiplier = 0.1
        this.assertEqual(grade_obj.get_score(), 1.1)

    def test_bonus_marks(this):
        grade_obj = grade.Grade(this.assignment)
        grade_obj.bonus_marks = 20
        this.assertEqual(grade_obj.get_score(), 1.2)

    def test_bonus_score(this):
        grade_obj = grade.Grade(this.assignment)
        grade_obj.bonus_score = 0.3
        this.assertEqual(grade_obj.get_score(), 1.3)

    def test_penalty_multiplier(this):
        grade_obj = grade.Grade(this.assignment)
        grade_obj.penalty_multiplier = 0.4
        this.assertEqual(grade_obj.get_score(), 0.6)

    def test_penalty_marks(this):
        grade_obj = grade.Grade(this.assignment)
        grade_obj.penalty_marks = 50
        this.assertEqual(grade_obj.get_score(), 0.5)

    def test_penalty_score(this):
        grade_obj = grade.Grade(this.assignment)
        grade_obj.penalty_score = 0.6
        this.assertEqual(grade_obj.get_score(), 0.4)

    def test_override(this):
        grade_obj = grade.Grade(this.assignment)
        grade_obj.penalty_score = 0.6
        grade_obj.override = 123.456
        this.assertEqual(grade_obj.get_score(), 123.456)

