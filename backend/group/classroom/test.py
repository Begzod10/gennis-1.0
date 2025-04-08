from datetime import datetime

from app import app, request, jsonify, db, contains_eager
from backend.group.test import api
from backend.functions.utils import find_calendar_date, get_json_field, iterate_models
from backend.models.models import GroupTest, CalendarYear, CalendarMonth, StudentTest, Groups, Students
from flask_jwt_extended import jwt_required


@app.route(f'{api}/filter_datas_in_group_classroom/<int:group_id>', methods=["POST", "GET"])
def filter_datas_in_group_classroom(group_id):
    month_list = []
    if request.method == "GET":
        calendar_year, calendar_month, calendar_day = find_calendar_date()
        group_tests = GroupTest.query.filter(GroupTest.group_id == group_id).all()
        group_tests_month = GroupTest.query.filter(GroupTest.group_id == group_id,
                                                   GroupTest.calendar_year == calendar_year.id).all()
        years_list = []

        for group_test in group_tests:
            years_list.append(group_test.year.date.strftime("%Y"))
        for group_test in group_tests_month:
            month_list.append(group_test.month.date.strftime("%m"))
        years_list.sort()
        month_list.sort()
        years_list = list(dict.fromkeys(years_list))
        month_list = list(dict.fromkeys(month_list))
        return jsonify({
            "years_list": years_list,
            "month_list": month_list,
            "current_year": calendar_year.date.strftime("%Y"),
            "current_month": calendar_month.date.strftime("%m"),
        })
    else:
        year = datetime.strptime(f"{get_json_field('year')}", "%Y")

        calendar_year = CalendarYear.query.filter(CalendarYear.date == year).first()

        group_tests = GroupTest.query.filter(GroupTest.group_id == group_id,
                                             GroupTest.calendar_year == calendar_year.id).all()
        for group_test in group_tests:
            month_list.append(group_test.month.date.strftime("%m"))
        month_list = list(dict.fromkeys(month_list))
        return jsonify({
            "month_list": month_list
        })


@app.route(f'{api}/filter_test_group_classroom/<int:group_id>', methods=['POST'])
def filter_test_group_classroom(group_id):
    year = get_json_field('year')
    month = get_json_field('month')
    month = f"{year}-{month}"
    calendar_year = CalendarYear.query.filter(CalendarYear.date == datetime.strptime(year, "%Y")).first()
    calendar_month = CalendarMonth.query.filter(CalendarMonth.date == datetime.strptime(month, "%Y-%m"),
                                                CalendarMonth.year_id == calendar_year.id).first()
    tests = GroupTest.query.filter(GroupTest.calendar_year == calendar_year.id,
                                   GroupTest.calendar_month == calendar_month.id,
                                   GroupTest.group_id == group_id).order_by(GroupTest.calendar_month).all()
    students = db.session.query(Students).join(Students.group).options(contains_eager(Students.group)).filter(
        Groups.id == group_id
    ).all()
    return jsonify({"tests": iterate_models(tests),
                    "students": iterate_models(students)})


@app.route(f'{api}/submit_test_group_classroom/<int:group_id>', methods=["POST"])
def submit_test_group_classroom(group_id):
    group = Groups.query.filter(Groups.id == group_id).first()
    if request.method == "POST":
        group_test = GroupTest.query.filter(GroupTest.group_id == group.id,
                                            GroupTest.id == get_json_field('test_id')).first()
        group_percentage = 0
        len_students = 0
        for student in get_json_field('students'):
            student_get = Students.query.filter(Students.user_id == student['id']).first()
            true_answers = student['true_answers'] if "true_answers" in student else 0
            if true_answers != 0:
                len_students += 1
                true_answers = int(true_answers)
                percentage = round((true_answers / group_test.number_tests) * 100)
                group_percentage += percentage
                exist_test = StudentTest.query.filter(StudentTest.student_id == student_get.id,
                                                      StudentTest.group_id == group_id,
                                                      StudentTest.group_test_id == group_test.id,
                                                      StudentTest.calendar_day == group_test.calendar_day).first()
                if not exist_test:
                    add_test_result = StudentTest(subject_id=group.subject_id, group_test_id=group_test.id,
                                                  calendar_day=group_test.calendar_day,
                                                  student_id=student_get.id, true_answers=true_answers,
                                                  percentage=percentage, group_id=group_id)
                    add_test_result.add()
                else:
                    exist_test.true_answers = true_answers
                    exist_test.percentage = percentage
                    db.session.commit()
            else:
                exist_test = StudentTest.query.filter(StudentTest.student_id == student_get.id,
                                                      StudentTest.group_id == group_id,
                                                      StudentTest.group_test_id == group_test.id,
                                                      StudentTest.calendar_day == group_test.calendar_day).first()
                if exist_test:
                    db.session.delete(exist_test)
                    db.session.commit()
        group_test.percentage = round(group_percentage / len_students)
        db.session.commit()
        return jsonify({
            "status": True,
            "test": group_test.convert_json(),
            "msg": "Test natijasi kiritildi"
        })
