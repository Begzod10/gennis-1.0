from flask import Blueprint, jsonify, request
from sqlalchemy import desc
from backend.functions.utils import iterate_models
from backend.models.models import StudentTest, Groups, GroupTest, Students

classroom_student_tests_bp = Blueprint('classroom', __name__)


@classroom_student_tests_bp.route(f'test/dates/<student_id>')
def classroom_student_test_dates(student_id):
    student = Students.query.filter(Students.id == student_id).first()
    groups = student.groups
    group_tests = GroupTest.query.filter(GroupTest.group_id.in_(groups)).order_by(desc(GroupTest.calendar_day)).all()
    dates = []
    for group_test in group_tests:
        info = {
            "year": {"id": group_test.calendar_year, "value": group_test.year.date.strftime("%Y")},
            "month": {"id": group_test.calendar_month, "value": group_test.month.date.strftime("%m")},
        }
        dates.append(info)
    return jsonify({"test_dates": dates})


@classroom_student_tests_bp.route(f'test/results/<student_id>', methods=['POST'])
def classroom_student_test_results(student_id):
    tests = []
    student_tests = StudentTest.query.filter(StudentTest.student_id == student_id).order_by(desc(StudentTest.id)).all()
    group_ids = [gr.group_id for gr in student_tests]
    group_ids = list(dict.fromkeys(group_ids))
    year_id = request.get_json()['year_id', None]
    month_id = request.get_json()['month_id', None]
    if year_id is not None:
        groups = Groups.query.filter(Groups.id.in_(group_ids)).join(Groups.test).filter(
            GroupTest.calendar_year == year_id,
            GroupTest.calendar_month == month_id).order_by(
            desc(GroupTest.calendar_day)).all()
    elif month_id is not None:
        groups = Groups.query.filter(Groups.id.in_(group_ids)).join(Groups.test).filter(
            GroupTest.calendar_month == month_id).order_by(
            desc(GroupTest.calendar_day)).all()
    else:
        groups = Groups.query.filter(Groups.id.in_(group_ids)).join(Groups.test).order_by(
            desc(GroupTest.calendar_day)).all()
    for gr in groups:
        student_tests = StudentTest.query.filter(StudentTest.group_id == gr.id,
                                                 StudentTest.student_id == student_id).order_by(
            desc(StudentTest.id)).all()
        info = {
            "id": gr.id,
            "name": gr.name,
            "teacher": f"{gr.teacher[0].user.name} {gr.teacher[0].user.surname}",
            "subject": gr.subject.name,
            "tests": iterate_models(student_tests)
        }
        tests.append(info)
    return jsonify({"test_results": tests})
