from backend.models.models import Students, Group_Room_Week, Week, Teachers, Groups, TeacherSalary, Parent, Users, db

from flask import Blueprint, jsonify
from sqlalchemy import desc

user_bp = Blueprint('user', __name__)


@user_bp.route(f'time_table/<pk>/<user_type>')
def bot_student_time_table(pk, user_type):
    student = Students.query.filter(Students.id == pk).first()
    teacher = Teachers.query.filter(Teachers.id == pk).first()

    table_list = []
    if user_type == "student" or user_type == "parent":
        group = student.group
    else:
        group = teacher.group

    group = Groups.query.filter(Groups.id.in_([gr.id for gr in group]), Groups.deleted == False,
                                Groups.status == True).order_by(Groups.id).all()
    for gr in group:
        info = {
            "id": gr.id,
            "name": gr.name,
            "teacher": f"{gr.teacher[0].user.name} {gr.teacher[0].user.surname}",
            "subject": gr.subject.name,
            "lessons": []
        }
        student_time_table = Group_Room_Week.query.filter(
            Group_Room_Week.group_id == gr.id).join(Week).order_by(Week.order).all()
        for time in student_time_table:
            info["lessons"].append({
                "day": time.week.name,
                "room": time.room.name,
                "from": time.start_time.strftime("%H:%M"),
                "to": time.end_time.strftime("%H:%M"),
                "order": time.week.order
            })
        table_list.append(info)
    return jsonify({"table_list": table_list})


@user_bp.route(f'balance/<platform_id>/<user_type>')
def bot_student_balance(platform_id, user_type):
    student = Students.query.filter(Students.id == platform_id).first()
    teacher = Teachers.query.filter(Teachers.id == platform_id).first()
    balance = 0
    if user_type == "student" or user_type == "parent":
        balance = student.user.balance
    else:
        last_two_salaries = (
            TeacherSalary.query
            .filter(TeacherSalary.teacher_id == teacher.id)
            .order_by(
                TeacherSalary.id.desc())  # or use .order_by(TeacherSalary.created_at.desc()) if you have a timestamp
            .limit(2)
            .all()
        )
        if last_two_salaries:
            for salary in last_two_salaries:
                balance += salary.remaining_salary

    return jsonify({"balance": balance})


@user_bp.route(f'balance/list/<platform_id>/<user_type>')
def bot_user_balance(platform_id, user_type):
    student = Students.query.filter(Students.id == platform_id).first()
    teacher = Teachers.query.filter(Teachers.id == platform_id).first()
    balance = 0
    if user_type == "student" or user_type == "teacher":
        if user_type == "student":
            balance = student.user.balance

        elif user_type == "teacher":
            last_two_salaries = (
                TeacherSalary.query
                .filter(TeacherSalary.teacher_id == teacher.id)
                .order_by(
                    TeacherSalary.id.desc())  # or use .order_by(TeacherSalary.created_at.desc()) if you have a timestamp
                .limit(2)
                .all()
            )
            if last_two_salaries:
                for salary in last_two_salaries:
                    balance += salary.remaining_salary

        return jsonify({"balance": balance})
    else:
        parent = Parent.query.filter(Parent.id == platform_id).first()
        infos = []
        for st in parent.student:
            info = {
                "id": st.id,
                "name": st.user.name,
                "surname": st.user.surname,
                "balance": st.user.balance
            }
            infos.append(info)
        return jsonify({"student_list": infos})


@user_bp.route(f'telegram_id/<platform_id>/<telegram_id>')
def bot_user_telegram_id(platform_id, telegram_id):
    user = Users.query.filter(Users.id == platform_id).first()
    if user:
        user.telegram_id = telegram_id
        db.session.commit()
    return jsonify({"telegram_id": telegram_id})
