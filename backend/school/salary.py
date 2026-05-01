from .models import SchoolInfo, SchoolUserSalary, SchoolUserSalaryDay
from backend.models.models import CalendarDay, CalendarMonth, CalendarYear
from app import app, api, jsonify, request, db
from datetime import datetime
from backend.functions.utils import api, find_calendar_date, iterate_models


@app.route(f'{api}/school_user_salary/<school_user_id>')
def school_user_salary(school_user_id):
    school_user_salaries = SchoolUserSalary.query.filter(SchoolUserSalary.school_user_id == school_user_id).join(
        SchoolUserSalary.month).order_by(SchoolUserSalary.month.desc()).all()
    return jsonify({"salaries": school_user_salaries}), 200


@app.route(f'{api}/school_user_salary_day/<salary_id>', methods=['GET', 'POST', 'DELETE', 'PUT'])
def school_user_salary(salary_id):
    if request.method == "POST":
        date = request.get_json()['date']
        salary = request.get_json()['salary']
        payment_type_id = request.get_json()['payment_type_id']
        day = date[8:10]
        month = date[5:7]
        current_year = datetime.now().year
        old_year = datetime.now().year - 1
        month_date = str(datetime.now().month)

        if len(month) == 1:
            month = "0" + str(month)

        if month_date == "12" and month == "01":
            current_year = old_year
        if not month_date:
            month_date = month

        date_day = str(current_year) + "-" + str(month_date) + "-" + str(day)
        date_month = str(current_year) + "-" + str(month_date)
        date_year = str(current_year)
        date_day = datetime.strptime(date_day, "%Y-%m-%d")
        date_month = datetime.strptime(date_month, "%Y-%m")
        date_year = datetime.strptime(date_year, "%Y")
        school_user_salary_get = SchoolUserSalary.query.filter(SchoolUserSalary.id == salary_id).first()
        calendar_year, calendar_month, calendar_day = find_calendar_date(date_day, date_month, date_year)
        add_salary = SchoolUserSalaryDay(calendar_day=calendar_day.id, salary=salary,
                                         school_user_id=school_user_salary_get.school_user_id,
                                         payment_type_id=payment_type_id, salary_id=salary_id)
        add_salary.add()
        return {"message": "Salary created", "id": add_salary.id}, 200
    elif request.method == "PUT":
        get_salary = SchoolUserSalaryDay.query.filter(SchoolUserSalaryDay.id == salary_id).first()
        get_salary.payment_type_id = request.get_json()['payment_type_id']
        db.session.commit()
        return {"message": "Salary updated", "id": get_salary.id}, 200
    elif request.method == "DELETE":
        get_salary = SchoolUserSalaryDay.query.filter(SchoolUserSalaryDay.id == salary_id).first()
        get_salary.deleted = True
        db.session.commit()
        return {"message": "Salary deleted", "id": get_salary.id}, 200
    school_user_salaries = SchoolUserSalaryDay.query.filter(SchoolUserSalaryDay.school_user_id == salary_id,
                                                            SchoolUserSalaryDay.deleted == False).join(
        SchoolUserSalaryDay.month).order_by(SchoolUserSalaryDay.day.desc()).all()
    return jsonify({"salaries": school_user_salaries}), 200



