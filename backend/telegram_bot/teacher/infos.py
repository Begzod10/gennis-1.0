import pprint
from datetime import datetime
from app import app, api, desc, jsonify
from backend.models.models import TeacherSalary, Teachers, CalendarYear, Locations


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
    print(get_year.id)
    salary_list = []
    print(teacher.locations)
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
