# tasks/salary.py
from .celery_app import celery
from backend.functions.debt_salary_update import salary_debt
from backend.student.class_model import Student_Functions
from backend.functions.utils import update_salary
from backend.models.models import TeacherBlackSalary, Students, db


@celery.task(name='process_salary_debt')
def process_salary_debt(student_id, group_id, attendance_id, status_attendance, type_attendance, teacher_id,
                        calendar_month, calendar_year, salary_per_day):
    salary_location = salary_debt(
        student_id, group_id, attendance_id,
        status_attendance, type_attendance
    )

    update_salary(teacher_id)
    student_obj = Students.query.get(student_id)
    st_functions = Student_Functions(student_id=student_id)
    st_functions.update_debt()
    st_functions.update_balance()
    if type_attendance == "add":
        if student_obj.debtor == 2:
            black_salary = TeacherBlackSalary.query.filter_by(
                teacher_id=teacher_id,
                student_id=student_id,
                calendar_month=calendar_month.id,
                calendar_year=calendar_year.id,
                location_id=student_obj.user.location_id,
                salary_id=salary_location.id,
                status=False
            ).first()
            if not black_salary:
                black_salary = TeacherBlackSalary(
                    teacher_id=teacher_id,
                    total_salary=salary_per_day,
                    student_id=student_obj.id,
                    salary_id=salary_location.id,
                    calendar_month=calendar_month.id,
                    calendar_year=calendar_year.id,
                    location_id=student_obj.user.location_id
                )
                black_salary.add()
            else:
                black_salary.total_salary += salary_per_day
                db.session.commit()
    return {"salary_location_id": salary_location.id}


@celery.task(name='send_student_info')
def send_student_info(user_id, attendance_id):
    from backend.models.models import Users, Students, Parent, AttendanceDays
    attendance = AttendanceDays.query.get(attendance_id)
    user = Users.query.get(user_id)
    parent = Parent.query.filter_by(user_id=user.id).first()

    return {
        "user": user.convert_json(),
        "parent": bool(parent),
        "attendance": attendance.convert_json()
    }
