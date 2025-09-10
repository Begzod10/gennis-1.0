from flask import jsonify
from flask_jwt_extended import jwt_required
from backend.functions.utils import find_calendar_date, get_json_field, update_salary
from backend.models.models import AttendanceHistoryStudent, Students, Groups, Roles, Week, Group_Room_Week, Rooms, \
    Users, Attendance, AttendanceDays, Teachers, TeacherBlackSalary, db, LessonPlan, CalendarMonth, Subjects, \
    CalendarDay, StudentCharity, CalendarYear
from backend.functions.utils import update_school_salary
from backend.functions.utils import iterate_models
from datetime import timedelta
from backend.teacher.utils import send_telegram_message
from sqlalchemy import desc, or_
from backend.functions.functions import get_dates_for_weekdays
from sqlalchemy.orm import contains_eager
from datetime import datetime
from backend.functions.filters import update_lesson_plan, old_current_dates
from backend.group.class_model import Group_Functions
from backend.student.class_model import Student_Functions
from backend.functions.debt_salary_update import salary_debt
from flask import Blueprint, request

group_classroom_attendance_bp = Blueprint('group_classroom_attendance', __name__)


@group_classroom_attendance_bp.route(f'/group_dates2_classroom/<int:group_id>')
def group_dates2_classroom(group_id):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    year_list = []
    month_list = []
    attendance_month = AttendanceHistoryStudent.query.filter(
        AttendanceHistoryStudent.group_id == group_id,
    ).order_by(AttendanceHistoryStudent.id).all()
    for attendance in attendance_month:
        year = AttendanceHistoryStudent.query.filter(AttendanceHistoryStudent.group_id == group_id,
                                                     AttendanceHistoryStudent.calendar_year == attendance.calendar_year).all()
        info = {
            'year': '',
            'months': []
        }
        if info['year'] != attendance.year.date.strftime("%Y"):
            info['year'] = attendance.year.date.strftime("%Y")
        for month in year:
            if attendance.year.date.strftime("%Y") not in year_list:
                year_list.append(attendance.year.date.strftime("%Y"))
            if month.month.date.strftime("%m") not in info['months']:
                info['months'].append(month.month.date.strftime("%m"))
                info['months'].sort()
        month_list.append(info)
    year_list = list(dict.fromkeys(year_list))
    if calendar_year.date.strftime("%Y") not in year_list:
        year_list.append(calendar_year.date.strftime("%Y"))
    filtered_list = []
    for student in month_list:
        added_to_existing = False
        for merged in filtered_list:
            if merged['year'] == student['year']:
                added_to_existing = True
            if added_to_existing:
                break
        if not added_to_existing:
            filtered_list.append(student)
    return jsonify({
        "data": {
            "months": filtered_list,
            "years": year_list,
            "current_year": calendar_year.date.strftime("%Y"),
            "current_month": calendar_month.date.strftime("%m"),
        }
    })


@group_classroom_attendance_bp.route(f'/attendances_classroom/<int:group_id>', methods=['GET', "POST"])
def attendances_classroom(group_id):
    update_lesson_plan(group_id)
    students = db.session.query(Students).join(Students.group).options(contains_eager(Students.group)).filter(
        Groups.id == group_id).order_by(Students.id).all()
    student_list = [{
        "id": st.user.id,
        "img": None,
        "name": st.user.name.title(),
        "surname": st.user.surname.title(),
        "money": st.user.balance,
        "moneyType": ["green", "yellow", "red", "navy", "black"][st.debtor] if st.debtor else 0,
        "comment": st.user.comment,
        "reg_date": st.user.day.date.strftime("%Y-%m-%d"),
        "phone": st.user.phone[0].phone,
        "username": st.user.username,
        "age": st.user.age,
        "photo_profile": st.user.photo_profile,
        "role": Roles.query.filter(Roles.id == st.user.role_id).first().role
    } for st in students]

    gr_functions = Group_Functions(group_id=group_id)
    if request.method == "GET":
        current_month = datetime.now().month
        if len(str(current_month)) == 1:
            current_month = "0" + str(current_month)
        current_year = datetime.now().year

        return jsonify({

            "data": {
                "attendance_filter": gr_functions.attendance_filter(month=current_month, year=current_year),
                "students": student_list,
                "date": old_current_dates(group_id),
            }
        })
    else:
        year = get_json_field('year')

        month = get_json_field('month')
        return jsonify({

            "data": {
                "attendance_filter": gr_functions.attendance_filter(month=month, year=year),
                "students": student_list,
                "date": old_current_dates(group_id),
            }
        })


@group_classroom_attendance_bp.route(f'/group_time_table_classroom/<int:group_id>')
def group_time_table_classroom(group_id):
    group = Groups.query.filter(Groups.id == group_id).first()
    week_days = Week.query.filter(Week.location_id == group.location_id).order_by(Week.order).all()
    table_list = []
    weeks = []
    for week in week_days:
        weeks.append(week.name)
    rooms = db.session.query(Rooms).join(Rooms.time_table).options(contains_eager(Rooms.time_table)).filter(
        Group_Room_Week.group_id == group_id, Rooms.location_id == group.location_id).all()
    for room in rooms:
        room_info = {
            "room": room.name,
            "id": room.id,
            "lesson": []
        }
        week_list = []
        for week in week_days:
            info = {
                "from": "",
                "to": ""
            }
            time_table = Group_Room_Week.query.filter(Group_Room_Week.group_id == group_id,
                                                      Group_Room_Week.week_id == week.id,
                                                      Group_Room_Week.room_id == room.id).order_by(
                Group_Room_Week.group_id).first()
            if time_table:
                info["from"] = time_table.start_time.strftime("%H:%M")
                info["to"] = time_table.end_time.strftime("%H:%M")

            week_list.append(info)
            room_info['lesson'] = week_list
        table_list.append(room_info)
    return jsonify({
        "success": True,
        "data": table_list,
        "days": weeks
    })


@group_classroom_attendance_bp.route(f'/combined_attendances_classroom/<int:student_id>/', methods=["POST", "GET"])
def combined_attendances_classroom(student_id):
    student = Students.query.filter(Students.user_id == student_id).first()
    st_functions = Student_Functions(student_id=student.id)
    if request.method == "GET":
        current_month = datetime.now().month
        if len(str(current_month)) == 1:
            current_month = "0" + str(current_month)
        current_year = datetime.now().year
        return jsonify({
            "data": st_functions.attendance_filter_student(month=current_month, year=current_year)
        })
    else:
        year = get_json_field('year')

        month = get_json_field('month')

        return jsonify({
            "data": st_functions.attendance_filter_student(month=month, year=year)
        })


@group_classroom_attendance_bp.route(f'/student_group_dates2_classroom/<int:student_id>/')
def student_group_dates2_classroom(student_id):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    year_list = []
    month_list = []
    student = Students.query.filter(Students.user_id == student_id).first()
    attendance_month = AttendanceHistoryStudent.query.filter(
        AttendanceHistoryStudent.student_id == student.id,
    ).order_by(AttendanceHistoryStudent.id).all()

    for attendance in attendance_month:
        year = AttendanceHistoryStudent.query.filter(AttendanceHistoryStudent.student_id == student.id,

                                                     AttendanceHistoryStudent.calendar_year == attendance.calendar_year).all()
        info = {
            'year': '',
            'months': []
        }
        if info['year'] != attendance.year.date.strftime("%Y"):
            info['year'] = attendance.year.date.strftime("%Y")
        for month in year:
            if attendance.year.date.strftime("%Y") not in year_list:
                year_list.append(attendance.year.date.strftime("%Y"))
            if month.month.date.strftime("%m") not in info['months']:
                info['months'].append(month.month.date.strftime("%m"))
                info['months'].sort()
        month_list.append(info)

    day_dict = {gr['year']: gr for gr in month_list}
    filtered_list = list(day_dict.values())
    return jsonify({
        "data": {
            "months": filtered_list,
            "years": year_list,
            "current_year": calendar_year.date.strftime("%Y"),
            "current_month": calendar_month.date.strftime("%m"),
        }
    })


@group_classroom_attendance_bp.route(
    f'/delete_attendance_classroom/<int:attendance_id>/<int:student_id>/<int:group_id>', methods=["GET"])
def delete_attendance_classroom(attendance_id, student_id, group_id):
    student = Students.query.filter(Students.user_id == student_id).first()
    attendancedays = AttendanceDays.query.filter(AttendanceDays.id == attendance_id).first()
    attendace_get = Attendance.query.filter(Attendance.id == attendancedays.attendance_id).first()
    group = Groups.query.filter(Groups.id == group_id).first()
    teacher = Teachers.query.filter(Teachers.id == group.teacher_id).first()
    black_salary = TeacherBlackSalary.query.filter(TeacherBlackSalary.teacher_id == teacher.id,
                                                   TeacherBlackSalary.student_id == student.id,
                                                   TeacherBlackSalary.calendar_month == attendace_get.calendar_month,
                                                   TeacherBlackSalary.calendar_year == attendace_get.calendar_year,
                                                   TeacherBlackSalary.status == False,
                                                   TeacherBlackSalary.location_id == student.user.location_id,
                                                   ).first()
    salary_per_day = attendancedays.salary_per_day
    if black_salary:
        if black_salary.total_salary:
            black_salary.total_salary -= salary_per_day
            db.session.commit()
        else:
            db.session.delete(black_salary)
            db.session.commit()
    salary_debt(student_id=student.id, group_id=group_id, attendance_id=attendance_id, status_attendance=True,
                type_attendance=True)
    st_functions = Student_Functions(student_id=student.id)
    st_functions.update_debt()
    st_functions.update_balance()

    update_salary(teacher_id=teacher.user_id)

    return jsonify({
        "success": True,
        "msg": "Davomat o'chirildi"
    })


@group_classroom_attendance_bp.route(f'/attendance_classroom/<int:group_id>')
def attendance_classroom(group_id):
    """
    filter Student and User table data
    :param group_id: Group primary key
    :return: Student table and User table data
    """
    today = datetime.today()

    hour = datetime.strftime(today, "%Y/%m/%d/%H/%M")
    hour2 = datetime.strptime(hour, "%Y/%m/%d/%H/%M")

    students = db.session.query(Students).join(Students.group).options(contains_eager(Students.group)).filter(
        Groups.id == group_id).filter(or_(Students.ball_time <= hour2, Students.ball_time == None)).order_by('id').all()

    group = Groups.query.filter(Groups.id == group_id).first()
    attendance_info = []
    for student in group.student:
        if group.subject.ball_number > 2:
            score = [
                {
                    "name": "homework",
                    "activeBall": 0
                },
                {
                    "name": "activity",
                    "activeBall": 0
                },
                {
                    "name": "dictionary",
                    "activeBall": 0
                }
            ]
        else:
            score = [
                {
                    "name": "homework",
                    "activeBall": 0
                },
                {
                    "name": "activity",
                    "activeBall": 0
                }
            ]
        att = {
            "id": student.user.id,
            "name": student.user.name,
            "surname": student.user.surname,
            "balance": student.user.balance,
            "score": score,
            "money_type": ["green", "yellow", "red", "navy", "black"][student.debtor] if student.debtor else 0,
            "type": ""
        }
        attendance_info.append(att)

    gr_functions = Group_Functions(group_id=group_id)
    gr_functions.update_list_balance()
    return jsonify({
        "date": old_current_dates(group_id),
        "users": attendance_info
    })


@group_classroom_attendance_bp.route(f'/make_attendance_classroom', methods=['POST'])
def make_attendance_classroom():
    """
    make attendance to students, update students' balance and teacher salary
    :return:
    """
    month = str(datetime.now().month)
    current_year = datetime.now().year
    old_year = datetime.now().year - 1

    day = request.get_json()['day']
    get_month = request.get_json()['month']
    current_day = datetime.now().day
    if len(month) == 1:
        month = "0" + str(month)

    group_id = int(request.get_json()['group_id'])
    group = Groups.query.filter(Groups.id == group_id).first()
    teacher = Teachers.query.filter(Teachers.id == group.teacher_id).first()
    errors = []
    student = Students.query.filter(Students.user_id == request.get_json()['id']).first()
    homework = 0
    dictionary = 0
    active = 0
    for score in request.get_json()['score']:
        if score['name'] == "homework":
            homework = score['activeBall']
        elif score['name'] == "activity":
            active = score['activeBall']
        elif score['name'] == "dictionary":
            dictionary = score['activeBall']
    type_attendance = request.get_json()['type']

    if type_attendance == "yes":
        type_status = True
    else:
        type_status = False

    discount = StudentCharity.query.filter(StudentCharity.group_id == group_id,
                                           StudentCharity.student_id == student.id).first()
    if get_month == "12" and month == "01":
        current_year = old_year
    if not get_month:
        get_month = month

    date_day = str(current_year) + "-" + str(get_month) + "-" + str(day)
    date_month = str(current_year) + "-" + str(get_month)
    date_year = str(current_year)
    date_day = datetime.strptime(date_day, "%Y-%m-%d")
    date_month = datetime.strptime(date_month, "%Y-%m")
    date_year = datetime.strptime(date_year, "%Y")
    calendar_day = CalendarDay.query.filter(CalendarDay.date == date_day).first()
    calendar_month = CalendarMonth.query.filter(CalendarMonth.date == date_month).first()
    calendar_year = CalendarYear.query.filter(CalendarYear.date == date_year).first()
    if not calendar_year:
        calendar_year = CalendarYear(date=date_year)
        db.session.add(calendar_year)
        db.session.commit()
    if not calendar_month:
        calendar_month = CalendarMonth(date=date_month, year_id=calendar_year.id)
        db.session.add(calendar_month)
        db.session.commit()
    if not calendar_day:
        calendar_day = CalendarDay(date=date_day, month_id=calendar_month.id)
        db.session.add(calendar_day)
        db.session.commit()
    balance_with_discount = 0
    discount_per_day = 0
    discount_status = False
    if discount:
        balance_with_discount = round(
            (group.price / group.attendance_days) - (discount.discount / group.attendance_days))
        discount_per_day = round(discount.discount / group.attendance_days)
        discount_status = True
    today = datetime.today()
    hour = datetime.strftime(today, "%Y/%m/%d/%H/%M")
    hour2 = datetime.strptime(hour, "%Y/%m/%d/%H/%M")
    balance_per_day = round(group.price / group.attendance_days)
    salary_per_day = round(group.teacher_salary / group.attendance_days)
    ball_time = hour2 + timedelta(minutes=0)
    Students.query.filter(Students.id == student.id).update({"ball_time": ball_time})
    subject = Subjects.query.filter(Subjects.id == group.subject_id).first()
    attendance = Attendance.query.filter(Attendance.student_id == student.id,
                                         Attendance.calendar_year == calendar_year.id,
                                         Attendance.location_id == group.location_id,
                                         Attendance.calendar_month == calendar_month.id,
                                         Attendance.teacher_id == group.teacher_id,
                                         Attendance.group_id == group.id, Attendance.subject_id == subject.id,
                                         Attendance.course_id == group.course_type_id).first()

    if not attendance:
        attendance = Attendance(student_id=student.id, calendar_year=calendar_year.id,
                                location_id=group.location_id,
                                calendar_month=calendar_month.id, teacher_id=teacher.id, group_id=group_id,
                                course_id=group.course_type_id, subject_id=subject.id)
        db.session.add(attendance)
        db.session.commit()

    exist_attendance = db.session.query(AttendanceDays).join(AttendanceDays.attendance).options(
        contains_eager(AttendanceDays.attendance)).filter(AttendanceDays.student_id == student.id,
                                                          AttendanceDays.calendar_day == calendar_day.id,
                                                          AttendanceDays.group_id == group_id,
                                                          Attendance.calendar_month == calendar_month.id,
                                                          Attendance.calendar_year == calendar_year.id).first()
    if exist_attendance:
        return jsonify(
            {"errors": [
                {
                    "active": True,
                    "message": f"{student.user.name} {student.user.surname} bu kunda davomat qilingan",
                    "status": "danger"
                }
            ]}), 400
    len_attendance = AttendanceDays.query.filter(AttendanceDays.student_id == student.id,
                                                 AttendanceDays.group_id == group_id,
                                                 AttendanceDays.location_id == group.location_id,
                                                 AttendanceDays.attendance_id == attendance.id,
                                                 ).count()

    # if len_attendance >= group.attendance_days:
    #     return jsonify({"errors": [
    #         {
    #             "active": True,
    #             "message": f"{student.user.name} {student.user.surname} bu oyda 13 kun dan ko'p davomat qilindi",
    #             "status": "danger"
    #         }]
    #     }), 400
    ball = 5
    if int(day) < int(current_day):
        late_days = int(current_day) - int(day)

        ball -= late_days
        if ball < 0:
            ball = 0
    group_time_table = Group_Room_Week.query.filter(Group_Room_Week.group_id == group_id).order_by(
        Group_Room_Week.id).all()
    week_names = [time.week.eng_name for time in group_time_table]

    target_dates = [d.date() for d in get_dates_for_weekdays(week_names)]


    fine = 0
    today_lesson_plan = LessonPlan.query.filter(LessonPlan.group_id == group.id,
                                                LessonPlan.teacher_id == teacher.id,
                                                LessonPlan.date == calendar_day.date,
                                                LessonPlan.main_lesson == None, LessonPlan.homework == None,
                                                LessonPlan.activities == None, LessonPlan.objective == None,
                                                LessonPlan.resources == None, LessonPlan.assessment == None).first()
    # if today_lesson_plan or ball < 5:
    #     fine = round(salary_per_day / group.attendance_days)
    if not type_status:
        attendance_add = AttendanceDays(teacher_id=teacher.id, student_id=student.id,
                                        calendar_day=calendar_day.id, attendance_id=attendance.id,
                                        reason="",
                                        status=0, balance_per_day=balance_per_day,
                                        balance_with_discount=balance_with_discount,
                                        salary_per_day=salary_per_day, group_id=group_id,
                                        location_id=group.location_id,
                                        discount_per_day=discount_per_day, teacher_ball=ball,
                                        fine=fine,

                                        discount=discount_status)
        db.session.add(attendance_add)
        db.session.commit()
    elif homework == 0 and dictionary == 0 and active == 0:
        attendance_add = AttendanceDays(teacher_id=teacher.id, student_id=student.id,
                                        calendar_day=calendar_day.id, attendance_id=attendance.id,
                                        status=1, balance_per_day=balance_per_day, teacher_ball=ball,
                                        balance_with_discount=balance_with_discount,
                                        salary_per_day=salary_per_day, group_id=group_id,
                                        location_id=group.location_id, discount=discount_status,
                                        discount_per_day=discount_per_day,
                                        fine=fine,
                                        )
        db.session.add(attendance_add)
        db.session.commit()
    else:
        average_ball = round((homework + dictionary + active) / subject.ball_number)
        attendance_add = AttendanceDays(student_id=student.id, attendance_id=attendance.id,
                                        dictionary=dictionary, teacher_ball=ball,
                                        calendar_day=calendar_day.id,
                                        status=2, balance_per_day=balance_per_day, homework=homework,
                                        average_ball=average_ball, activeness=active, group_id=group_id,
                                        location_id=group.location_id, teacher_id=teacher.id,
                                        balance_with_discount=balance_with_discount,
                                        salary_per_day=salary_per_day, discount=discount_status,
                                        discount_per_day=discount_per_day,
                                        fine=fine,
                                        )
        db.session.add(attendance_add)
        db.session.commit()

    user = Users.query.filter(Users.id == student.user_id).first()
    if user.school_user_id:
        update_school_salary(user, group, calendar_day, calendar_month, calendar_year, attendance_add)
    attendance_days = AttendanceDays.query.filter(AttendanceDays.attendance_id == attendance.id,
                                                  AttendanceDays.teacher_ball != None).all()
    total_ball = 0
    for attendance_day in attendance_days:
        total_ball += attendance_day.teacher_ball
    result = round(total_ball / len(attendance_days))
    Attendance.query.filter(Attendance.id == attendance.id).update({
        "ball_percentage": result
    })
    db.session.commit()
    st_functions = Student_Functions(student_id=student.id)
    st_functions.update_debt()
    st_functions.update_balance()

    salary_location = salary_debt(student_id=student.id, group_id=group_id, attendance_id=attendance_add.id,
                                  status_attendance=False, type_attendance="add")

    update_salary(teacher_id=teacher.user_id)

    if student.debtor == 2:
        black_salary = TeacherBlackSalary.query.filter(TeacherBlackSalary.teacher_id == teacher.id,
                                                       TeacherBlackSalary.student_id == student.id,
                                                       TeacherBlackSalary.calendar_month == calendar_month.id,
                                                       TeacherBlackSalary.calendar_year == calendar_year.id,
                                                       TeacherBlackSalary.status == False,
                                                       TeacherBlackSalary.location_id == student.user.location_id,
                                                       TeacherBlackSalary.salary_id == salary_location.id).first()
        if not black_salary:
            black_salary = TeacherBlackSalary(teacher_id=teacher.id, total_salary=salary_per_day,
                                              student_id=student.id, salary_id=salary_location.id,
                                              calendar_month=calendar_month.id,
                                              calendar_year=calendar_year.id,
                                              location_id=student.user.location_id
                                              )
            black_salary.add()
        else:
            black_salary.total_salary += salary_per_day
            db.session.commit()
    send_telegram_message(student.id, attendance_add.id, group_id)
    return jsonify({
        "message": f"{student.user.name} {student.user.surname} davomat qilindi",
        "status": "success",
        "errors": errors,
        "info": {
            "attendance_id": attendance_add.id,
            "student_id": student.id,
            "group_id": group_id
        }
    })


@group_classroom_attendance_bp.route(f'/make_attendance_classroom_mobile', methods=['POST'])
def make_attendance_classroom_mobile():
    """
    make attendance to students, update students' balance and teacher salary
    :return:
    """
    month = str(datetime.now().month)
    current_year = datetime.now().year
    old_year = datetime.now().year - 1
    data = request.get_json()['data']
    day = data['day']
    get_month = data['month']
    current_day = datetime.now().day
    if len(month) == 1:
        month = "0" + str(month)

    group_id = int(data['group_id'])
    group = Groups.query.filter(Groups.id == group_id).first()
    teacher = Teachers.query.filter(Teachers.id == group.teacher_id).first()
    errors = []
    students = data['students']
    for st in students:
        student = Students.query.filter(Students.user_id == st['id']).first()
        homework = 0
        dictionary = 0
        active = 0
        if 'homework' in st:
            homework = st['homework']
        if 'dictionary' in st:
            dictionary = st['dictionary']
        if 'active' in st:
            active = st['active']
        type_attendance = st['type']

        if type_attendance == "yes":
            type_status = True
        else:
            type_status = False

        discount = StudentCharity.query.filter(StudentCharity.group_id == group_id,
                                               StudentCharity.student_id == student.id).first()
        if get_month == "12" and month == "01":
            current_year = old_year
        if not get_month:
            get_month = month

        date_day = str(current_year) + "-" + str(get_month) + "-" + str(day)
        date_month = str(current_year) + "-" + str(get_month)
        date_year = str(current_year)
        date_day = datetime.strptime(date_day, "%Y-%m-%d")
        date_month = datetime.strptime(date_month, "%Y-%m")
        date_year = datetime.strptime(date_year, "%Y")
        calendar_day = CalendarDay.query.filter(CalendarDay.date == date_day).first()
        calendar_month = CalendarMonth.query.filter(CalendarMonth.date == date_month).first()
        calendar_year = CalendarYear.query.filter(CalendarYear.date == date_year).first()
        if not calendar_year:
            calendar_year = CalendarYear(date=date_year)
            db.session.add(calendar_year)
            db.session.commit()
        if not calendar_month:
            calendar_month = CalendarMonth(date=date_month, year_id=calendar_year.id)
            db.session.add(calendar_month)
            db.session.commit()
        if not calendar_day:
            calendar_day = CalendarDay(date=date_day, month_id=calendar_month.id)
            db.session.add(calendar_day)
            db.session.commit()
        balance_with_discount = 0
        discount_per_day = 0
        discount_status = False
        if discount:
            balance_with_discount = round(
                (group.price / group.attendance_days) - (discount.discount / group.attendance_days))
            discount_per_day = round(discount.discount / group.attendance_days)
            discount_status = True
        today = datetime.today()
        hour = datetime.strftime(today, "%Y/%m/%d/%H/%M")
        hour2 = datetime.strptime(hour, "%Y/%m/%d/%H/%M")
        balance_per_day = round(group.price / group.attendance_days)
        salary_per_day = round(group.teacher_salary / group.attendance_days)
        ball_time = hour2 + timedelta(minutes=0)
        Students.query.filter(Students.id == student.id).update({"ball_time": ball_time})
        subject = Subjects.query.filter(Subjects.id == group.subject_id).first()
        attendance = Attendance.query.filter(Attendance.student_id == student.id,
                                             Attendance.calendar_year == calendar_year.id,
                                             Attendance.location_id == group.location_id,
                                             Attendance.calendar_month == calendar_month.id,
                                             Attendance.teacher_id == group.teacher_id,
                                             Attendance.group_id == group.id, Attendance.subject_id == subject.id,
                                             Attendance.course_id == group.course_type_id).first()

        if not attendance:
            attendance = Attendance(student_id=student.id, calendar_year=calendar_year.id,
                                    location_id=group.location_id,
                                    calendar_month=calendar_month.id, teacher_id=teacher.id, group_id=group_id,
                                    course_id=group.course_type_id, subject_id=subject.id)
            db.session.add(attendance)
            db.session.commit()

        exist_attendance = db.session.query(AttendanceDays).join(AttendanceDays.attendance).options(
            contains_eager(AttendanceDays.attendance)).filter(AttendanceDays.student_id == student.id,
                                                              AttendanceDays.calendar_day == calendar_day.id,
                                                              AttendanceDays.group_id == group_id,
                                                              Attendance.calendar_month == calendar_month.id,
                                                              Attendance.calendar_year == calendar_year.id).first()
        if exist_attendance:
            return jsonify(
                {"errors": [
                    {
                        "active": True,
                        "message": f"{student.user.name} {student.user.surname} bu kunda davomat qilingan",
                        "status": "danger"
                    }
                ]}), 400
        len_attendance = AttendanceDays.query.filter(AttendanceDays.student_id == student.id,
                                                     AttendanceDays.group_id == group_id,
                                                     AttendanceDays.location_id == group.location_id,
                                                     AttendanceDays.attendance_id == attendance.id,
                                                     ).count()

        if len_attendance >= group.attendance_days:
            return jsonify({"errors": [
                {
                    "active": True,
                    "message": f"{student.user.name} {student.user.surname} bu oyda 13 kun dan ko'p davomat qilindi",
                    "status": "danger"
                }]
            }), 400
        ball = 5
        if int(day) < int(current_day):
            late_days = int(current_day) - int(day)

            ball -= late_days
            if ball < 0:
                ball = 0
        group_time_table = Group_Room_Week.query.filter(Group_Room_Week.group_id == group_id).order_by(
            Group_Room_Week.id).all()
        week_names = [time.week.eng_name for time in group_time_table]

        target_dates = [d.date() for d in get_dates_for_weekdays(week_names)]

        lesson_plans = LessonPlan.query.filter(
            LessonPlan.group_id == group.id,
            LessonPlan.date.in_(target_dates),
            LessonPlan.main_lesson == None,
            LessonPlan.homework == None
        ).all()
        fine = 0
        today_lesson_plan = LessonPlan.query.filter(LessonPlan.group_id == group.id,
                                                    LessonPlan.teacher_id == teacher.id,
                                                    LessonPlan.date == calendar_day.date,
                                                    LessonPlan.main_lesson == None, LessonPlan.homework == None,
                                                    LessonPlan.activities == None, LessonPlan.objective == None,
                                                    LessonPlan.resources == None, LessonPlan.assessment == None).first()
        if today_lesson_plan or ball < 5:
            fine = round(salary_per_day / group.attendance_days)
        if not type_status:
            attendance_add = AttendanceDays(teacher_id=teacher.id, student_id=student.id,
                                            calendar_day=calendar_day.id, attendance_id=attendance.id,
                                            reason="",
                                            status=0, balance_per_day=balance_per_day,
                                            balance_with_discount=balance_with_discount,
                                            salary_per_day=salary_per_day, group_id=group_id,
                                            location_id=group.location_id,
                                            discount_per_day=discount_per_day, teacher_ball=ball,
                                            fine=fine,

                                            discount=discount_status)
            db.session.add(attendance_add)
            db.session.commit()
        elif homework == 0 and dictionary == 0 and active == 0:
            attendance_add = AttendanceDays(teacher_id=teacher.id, student_id=student.id,
                                            calendar_day=calendar_day.id, attendance_id=attendance.id,
                                            status=1, balance_per_day=balance_per_day, teacher_ball=ball,
                                            balance_with_discount=balance_with_discount,
                                            salary_per_day=salary_per_day, group_id=group_id,
                                            location_id=group.location_id, discount=discount_status,
                                            discount_per_day=discount_per_day,
                                            fine=fine,
                                            )
            db.session.add(attendance_add)
            db.session.commit()
        else:
            average_ball = round((homework + dictionary + active) / subject.ball_number)
            attendance_add = AttendanceDays(student_id=student.id, attendance_id=attendance.id,
                                            dictionary=dictionary, teacher_ball=ball,
                                            calendar_day=calendar_day.id,
                                            status=2, balance_per_day=balance_per_day, homework=homework,
                                            average_ball=average_ball, activeness=active, group_id=group_id,
                                            location_id=group.location_id, teacher_id=teacher.id,
                                            balance_with_discount=balance_with_discount,
                                            salary_per_day=salary_per_day, discount=discount_status,
                                            discount_per_day=discount_per_day,
                                            fine=fine,
                                            )
            db.session.add(attendance_add)
            db.session.commit()

        user = Users.query.filter(Users.id == student.user_id).first()
        if user.school_user_id:
            update_school_salary(user, group, calendar_day, calendar_month, calendar_year, attendance_add)
        attendance_days = AttendanceDays.query.filter(AttendanceDays.attendance_id == attendance.id,
                                                      AttendanceDays.teacher_ball != None).all()
        total_ball = 0
        for attendance_day in attendance_days:
            total_ball += attendance_day.teacher_ball
        result = round(total_ball / len(attendance_days))
        Attendance.query.filter(Attendance.id == attendance.id).update({
            "ball_percentage": result
        })
        db.session.commit()
        st_functions = Student_Functions(student_id=student.id)
        st_functions.update_debt()
        st_functions.update_balance()

        salary_location = salary_debt(student_id=student.id, group_id=group_id, attendance_id=attendance_add.id,
                                      status_attendance=False, type_attendance="add")

        update_salary(teacher_id=teacher.user_id)

        if student.debtor == 2:
            black_salary = TeacherBlackSalary.query.filter(TeacherBlackSalary.teacher_id == teacher.id,
                                                           TeacherBlackSalary.student_id == student.id,
                                                           TeacherBlackSalary.calendar_month == calendar_month.id,
                                                           TeacherBlackSalary.calendar_year == calendar_year.id,
                                                           TeacherBlackSalary.status == False,
                                                           TeacherBlackSalary.location_id == student.user.location_id,
                                                           TeacherBlackSalary.salary_id == salary_location.id).first()
            if not black_salary:
                black_salary = TeacherBlackSalary(teacher_id=teacher.id, total_salary=salary_per_day,
                                                  student_id=student.id, salary_id=salary_location.id,
                                                  calendar_month=calendar_month.id,
                                                  calendar_year=calendar_year.id,
                                                  location_id=student.user.location_id
                                                  )
                black_salary.add()
            else:
                black_salary.total_salary += salary_per_day
                db.session.commit()
        send_telegram_message(student.id, attendance_add.id, group_id)
    return jsonify({
        "message": "Attendance added successfully",
        "status": "success",
        "errors": errors,
    })
