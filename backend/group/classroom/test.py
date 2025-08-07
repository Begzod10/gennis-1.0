from datetime import datetime

from app import app

from backend.group.test import api
from sqlalchemy.orm import contains_eager
from backend.models.models import GroupTest, CalendarYear, CalendarMonth, StudentTest, Groups, Students, db

from backend.functions.small_info import user_photo_folder, checkFile

from backend.functions.utils import get_or_creat_datetime, find_calendar_date, iterate_models, get_json_field, \
    filter_month_day

from flask import request, jsonify
from flask_jwt_extended import jwt_required
import os
import json
from werkzeug.utils import secure_filename
import pprint
from flask import Blueprint

group_classroom_test_bp = Blueprint('group_classroom_test', __name__)


@group_classroom_test_bp.route(f'/create_test_classroom/<int:group_id>', methods=["POST", "PUT", "DELETE"])
def create_test_classroom(group_id):
    # File upload
    url = ""
    if 'file' in request.files:
        app.config['UPLOAD_FOLDER'] = user_photo_folder()
        photo = request.files['file']
        if photo and checkFile(photo.filename):
            filename = secure_filename(photo.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(filepath)
            url = f"static/img_folder/{filename}"
        else:
            return jsonify({"success": False, "msg": "Invalid file format"}), 400

    # Read and parse info field
    if request.method == "POST" or request.method == "PUT":
        info = request.form.get("info")
        if not info:
            return jsonify({"success": False, "msg": "Missing 'info'"}), 400

        try:
            data = json.loads(info)
        except json.JSONDecodeError:
            return jsonify({"success": False, "msg": "Invalid JSON in 'info'"}), 400

        try:
            year, month, day = data['date'][:4], data['date'][5:7], data['date'][8:]
            year, month, day = get_or_creat_datetime(year, month, day)
        except:
            return jsonify({"success": False, "msg": "Invalid date format"}), 400

        if request.method == "POST":
            group = Groups.query.filter(Groups.id == group_id).first()
            if not group:
                return jsonify({"success": False, "msg": "Group not found"}), 404

            test = GroupTest(
                name=data['name'],
                group_id=group_id,
                subject_id=group.subject_id,
                level=data['level'],
                calendar_year=year.id,
                calendar_month=month.id,
                calendar_day=day.id,
                number_tests=data['number'],
                file=url
            )
            test.add()
            return jsonify({
                "success": True,
                "msg": "Test created",
                "test": test.convert_json()
            })

        elif request.method == "PUT":
            test = GroupTest.query.get(data.get("test_id"))
            if not test:
                return jsonify({"success": False, "msg": "Test not found"}), 404

            test.name = data.get("name", test.name)
            test.level = data.get("level", test.level)
            test.number_tests = data.get("number", test.number_tests)
            test.calendar_year = year.id
            test.calendar_month = month.id
            test.calendar_day = day.id
            if url:
                test.file = url
            db.session.commit()
            return jsonify({
                "success": True,
                "msg": "Test updated",
                "test": test.convert_json()
            })

    elif request.method == "DELETE":
        test = GroupTest.query.get(request.get_json().get("test_id"))
        if not test:
            return jsonify({"success": False, "msg": "Test not found"}), 404

        db.session.delete(test)
        db.session.commit()
        return jsonify({"success": True, "msg": "Test deleted"})


@group_classroom_test_bp.route(f'/filter_datas_in_group_classroom/<int:group_id>', methods=["POST", "GET"])
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


@group_classroom_test_bp.route(f'/filter_test_group_classroom/<int:group_id>', methods=['POST'])
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


@group_classroom_test_bp.route(f'/submit_test_group_classroom/<int:group_id>', methods=["POST"])
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
