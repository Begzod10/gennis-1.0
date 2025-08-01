from sqlalchemy.orm import joinedload

from app import app, db, request, jsonify, or_, contains_eager, classroom_server
from backend.account.models import StudentPayments, BookPayments
from backend.group.models import AttendanceHistoryStudent, GroupTest
from backend.models.models import Users, Roles, CalendarMonth, CalendarDay, CalendarYear, Attendance, AttendanceDays, \
    Students, Groups, Teachers, StudentCharity, Subjects, SubjectLevels, TeacherBlackSalary, StaffSalary, \
    DeletedTeachers, Locations, LessonPlan, Group_Room_Week, Parent
from werkzeug.security import check_password_hash
from backend.functions.utils import api, refresh_age, update_salary, iterate_models, get_json_field, check_exist_id, \
    find_calendar_date, update_school_salary
from backend.time_table.models import Week
from datetime import datetime
from sqlalchemy import and_
from datetime import timedelta
from sqlalchemy import extract


@app.route(f"{api}/mobile/student_group_list/<username>", methods=['GET'])
def get_student_group_list(username):
    user = Users.query.filter_by(username=username).first()
    student = Students.query.get(user.student.id)

    today_eng_name = datetime.today().strftime('%A')
    today_week = Week.query.filter_by(eng_name=today_eng_name).first()

    group_list = []
    for gr in student.group:
        lesson = None
        if today_week:
            lesson = Group_Room_Week.query.filter_by(week_id=today_week.id, group_id=gr.id).first()
            if not lesson:
                lesson = (Group_Room_Week.query
                          .join(Week)
                          .filter(and_(
                    Week.order > today_week.order,
                    Group_Room_Week.group_id == gr.id))
                          .order_by(Week.order.asc())
                          .first())
        info = {
            "id": gr.id,
            "name": gr.name.title(),
            "subject": gr.subject.name,
            "level": gr.level.name if gr.level else None,
            "teacher": f"{gr.teacher[0].user.name} {gr.teacher[0].user.surname}",
            "time": {
                "day": lesson.week.name if lesson else None,
                "time": f"{lesson.start_time}:{lesson.end_time}" if lesson else None
            }
        }
        group_list.append(info)

    return jsonify({"group_list": group_list})


@app.route(f"{api}/mobile/get_student_attendance_days_list/<username>/<group_id>/<year>/<month>", methods=['GET'])
def get_student_attendance_days_list(username, group_id, year, month):
    user = Users.query.filter_by(username=username).first()
    student = Students.query.filter_by(user_id=user.id).first()
    today = datetime.today().date()

    calendar_days = CalendarDay.query.filter(
        db.extract('year', CalendarDay.date) == int(year),
        db.extract('month', CalendarDay.date) == int(month)
    ).order_by(CalendarDay.date).all()

    group = Groups.query.filter(Groups.id == int(group_id)).first
    info = {
        "group": group.subject.name,
        "attendances": [],
    }
    for day in calendar_days:
        if not day: continue

        attendance_info = {
            "date": day.date.strftime("%Y-%m-%d"),
            "day_status": bool(day.id),
            "is_today": day.date == today,
            "status": ""
        }

        if day.id:
            attendance_day = AttendanceDays.query.filter_by(
                student_id=student.id,
                calendar_day=day.id,
                group_id=group.id
            ).first()
            if attendance_day:
                attendance_info['status'] = True if attendance_day.status in [1, 2] else False
                attendance_info["average_ball"] = attendance_day.average_ball
                attendance_info["homework"] = attendance_day.homework

            info['attendances'].append(attendance_info)

    return jsonify({"msg": info})


@app.route(f"{api}/mobile/get_student_ranking/<username>/<group_id>/<year>/<month>", methods=['GET'])
def get_student_ranking(username: str, group_id: int, year: int, month: int):
    calendar_year = db.session.query(CalendarYear).filter(
        db.extract('year', CalendarYear.date) == year
    ).first()

    calendar_month = db.session.query(CalendarMonth).filter(
        CalendarMonth.year_id == calendar_year.id,
        db.extract('month', CalendarMonth.date) == month
    ).first()
    if not calendar_month:
        return {"error": "Oy topilmadi"}

    attendance_list = (
        db.session.query(Attendance)
        .join(Students)
        .join(Users, Students.user_id == Users.id)
        .options(joinedload(Attendance.student).joinedload(Students.attendance))
        .filter(
            Attendance.group_id == group_id,
            Attendance.calendar_month == calendar_month.id,
            Attendance.calendar_year == calendar_year.id
        )
        .order_by(Attendance.ball_percentage.desc())
        .all()
    )

    result = []
    for idx, att in enumerate(attendance_list, start=1):
        student = att.student
        user = student.user
        is_highlight = (user.username == username)
        result.append({
            "rank": idx,
            "student_id": student.id,
            "username": user.username,
            "full_name": f"{student.representative_name or ''} {student.representative_surname or ''}".strip(),
            "ball_percentage": att.ball_percentage,
            "highlight": is_highlight
        })

    return result


@app.route(f"{api}/mobile/get_lesson_plan_list/<group_id>/<year>/<month>", methods=['GET'])
def get_lesson_plan_list(group_id, year, month):
    lesson_plans = (
        db.session.query(LessonPlan)
        .filter(
            LessonPlan.group_id == group_id,
            extract('year', LessonPlan.date) == int(year),
            extract('month', LessonPlan.date) == int(month)
        )
        .order_by(LessonPlan.date.asc())
        .all()
    )

    return [{
        "id": lp.id,
        "date": lp.date.strftime('%Y-%m-%d'),
        "objective": lp.objective,
        "main_lesson": lp.main_lesson,
        "homework": lp.homework,
        "assessment": lp.assessment,
        "activities": lp.activities,
        "resources": lp.resources
    } for lp in lesson_plans]


@app.route(f"{api}/mobile/lesson_plan_profile/<int:id>", methods=['GET'])
def lesson_plan_profile(id):
    lesson_plan = LessonPlan.query.filter(LessonPlan.id == id).first()

    return {
        "id": lesson_plan.id,
        "date": lesson_plan.date.strftime('%Y-%m-%d'),
        "objective": lesson_plan.objective,
        "main_lesson": lesson_plan.main_lesson,
        "homework": lesson_plan.homework,
        "assessment": lesson_plan.assessment,
        "activities": lesson_plan.activities,
        "resources": lesson_plan.resources
    }


@app.route(f"{api}/mobile/student_profile_edit/<username>", methods=['PUT'])
def lesson_plan_profile(username):
    user = Users.query.filter_by(username=username).first()

    if request.method == "PUT":
        data = request.get_json()

        user.name = data.get('name', user.name)
        user.surname = data.get('surname', user.surname)
        user.father_name = data.get('father_name', user.father_name)
        user.phone = data.get('phone', user.phone)

        born_date = data.get('born_date')
        if born_date:
            try:
                day, month, year = map(int, born_date.split('-'))
                user.born_day = day
                user.born_month = month
                user.born_year = year
            except:
                return jsonify({"error": "Tug‘ilgan sana noto‘g‘ri formatda. To‘g‘ri format: DD-MM-YYYY"}), 400

        db.session.commit()

    return {
        "msg": "yangilandi",
    }
