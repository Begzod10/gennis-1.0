import pprint
from datetime import datetime
from app import app, api, desc, jsonify, db
from backend.models.models import TeacherSalary, Teachers, CalendarYear, Locations, TeacherSalaries, TeacherBlackSalary, \
    CalendarDay
from sqlalchemy import func


@app.route(f'{api}/bot_teacher_salary_years/<int:teacher_id>', methods=["POST", "GET"])
def bot_teacher_salary_years(teacher_id):
    teacher = Teachers.query.filter(Teachers.id == teacher_id).first()
    teacher_salary = TeacherSalary.query.filter(Teachers.id == teacher_id).all()

    years = CalendarYear.query.filter(CalendarYear.id.in_([year.calendar_year for year in teacher_salary])).order_by(
        desc(CalendarYear.date)).all()
    return jsonify({'years': [year.date.strftime("%Y") for year in years]})


@app.route(f'{api}/bot_teacher_salary/<int:teacher_id>/<int:year>', methods=["POST", "GET"])
def bot_teacher_salary(teacher_id, year):
    teacher = Teachers.query.filter(Teachers.id == teacher_id).first()
    get_year = CalendarYear.query.filter(CalendarYear.date == datetime(year, 1, 1)).first()

    salary_list = []
    for location in teacher.locations:
        get_location = Locations.query.filter(Locations.id == location.id).first()
        teacher_salary = TeacherSalary.query.filter(TeacherSalary.teacher_id == teacher_id,
                                                    TeacherSalary.location_id == location.id,
                                                    TeacherSalary.calendar_year == get_year.id).order_by(
            desc(TeacherSalary.id)).all()
        info = {
            "teacher_id": teacher.id,
            "name": teacher.user.name,
            "surname": teacher.user.surname,
            "year": year,
            "location": get_location.name,
            "salary_list": [salary.convert_json() for salary in teacher_salary]
        }
        salary_list.append(info)
    return jsonify(salary_list)


@app.route(f'{api}/bot_teacher_salary_details/<teacher_id>/<salary_id>')
def bot_teacher_salary_details(teacher_id, salary_id):
    teacher = Teachers.query.filter(Teachers.id == teacher_id).first()
    teacher_salary = TeacherSalary.query.filter(TeacherSalary.teacher_id == teacher_id,
                                                TeacherSalary.id == salary_id).first()
    daily_salaries = TeacherSalaries.query.filter(TeacherSalaries.teacher_id == teacher.id,
                                                  TeacherSalaries.salary_location_id == teacher_salary.id).join(
        TeacherSalaries.day).order_by(
        desc(CalendarDay.date)).all()

    total = db.session.query(
        func.sum(TeacherBlackSalary.total_salary)
    ).filter(
        TeacherBlackSalary.calendar_month == teacher_salary.calendar_month,
        TeacherBlackSalary.teacher_id == teacher_id,
        TeacherBlackSalary.location_id == teacher_salary.location_id,
        TeacherBlackSalary.status == False
    ).scalar()

    info = {
        "teacher_id": teacher.id,
        "total_salary": teacher_salary.total_salary + teacher_salary.extra if teacher_salary.extra else teacher_salary.total_salary,
        "taken_money": teacher_salary.taken_money,
        "debt": teacher_salary.debt,
        "remaining_salary": teacher_salary.remaining_salary,
        "name": teacher.user.name,
        "surname": teacher.user.surname,
        "month": teacher_salary.month.date.strftime("%Y-%m"),
        "location": teacher_salary.location.name,
        "salary_list": [salary.convert_json() for salary in daily_salaries],
        "black_salary": total if total else 0
    }
    return info
