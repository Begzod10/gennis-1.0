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
from sqlalchemy.orm import contains_eager, joinedload
from datetime import datetime
from backend.functions.filters import update_lesson_plan, old_current_dates
from backend.group.class_model import Group_Functions, GroupAttendance
from backend.student.class_model import Student_Functions
from backend.functions.debt_salary_update import salary_debt
from flask import Blueprint, request
from backend.celery.tasks import process_attendance_post_save

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


@group_classroom_attendance_bp.route(f'/attendances_classroom/<int:group_id>', methods=['GET', 'POST'])
def attendances_classroom(group_id):
    update_lesson_plan(group_id)

    # Students query optimization - fetch only needed fields
    students = db.session.query(Students).join(
        Students.group
    ).options(
        contains_eager(Students.group),
        joinedload(Students.user).joinedload(Users.phone)  # Use User.phone instead of 'phone'
    ).filter(
        Groups.id == group_id
    ).order_by(Students.id).all()

    # Student list building - role query optimization
    roles_cache = {}  # Cache roles to avoid repeated queries
    student_list = []

    for st in students:
        # Role caching
        role_id = st.user.role_id
        if role_id not in roles_cache:
            role = Roles.query.filter(Roles.id == role_id).first()
            roles_cache[role_id] = role.role if role else None

        student_list.append({
            "id": st.user.id,
            "img": None,
            "name": st.user.name.title(),
            "surname": st.user.surname.title(),
            "money": st.user.balance,
            "moneyType": ["green", "yellow", "red", "navy", "black"][st.debtor] if st.debtor else 0,
            "comment": st.user.comment,
            "reg_date": st.user.day.date.strftime("%Y-%m-%d"),
            "phone": st.user.phone[0].phone if st.user.phone else None,
            "username": st.user.username,
            "age": st.user.age,
            "photo_profile": st.user.photo_profile,
            "role": roles_cache[role_id]
        })

    # Common logic for both GET and POST
    if request.method == "GET":
        year = datetime.now().year
        month = datetime.now().month
    else:
        year = get_json_field('year')
        month = get_json_field('month')

    # String formatting optimization
    # month_str = f"{month:02d}"  # Ensures "01", "02", ... "12" format
    date_str = f"{year}-{month}"

    year_date = datetime.strptime(str(year), "%Y")
    month_date = datetime.strptime(date_str, "%Y-%m")

    # Single query with joins instead of multiple queries
    group_attendance = db.session.query(GroupAttendance).join(
        CalendarYear, GroupAttendance.calendar_year == CalendarYear.id
    ).join(
        CalendarMonth, GroupAttendance.calendar_month == CalendarMonth.id
    ).filter(
        GroupAttendance.group_id == group_id,
        CalendarYear.date == year_date,
        CalendarMonth.date == month_date
    ).first()

    gr_functions = Group_Functions(group_id=group_id)

    # Simplified condition logic
    attendance_filter = (
        gr_functions.attendance_filter(month=month, year=year)
        if not group_attendance or not group_attendance.status
        else group_attendance.to_json
    )

    return jsonify({
        "data": {
            "attendance_filter": attendance_filter,
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


@group_classroom_attendance_bp.route('/make_attendance_classroom', methods=['POST'])
def make_attendance_classroom():
    """
    Make attendance for students, update balance and teacher salary.
    Optimized version with Celery async tasks for time-consuming operations.
    """
    # Parse request data once
    data = request.get_json()
    day = data['day']
    get_month = data.get('month')
    group_id = int(data['group_id'])
    student_user_id = data['id']
    type_attendance = data['type']
    scores = {score['name']: score['activeBall'] for score in data['score']}

    homework = scores.get('homework', 0)
    active = scores.get('activity', 0)
    dictionary = scores.get('dictionary', 0)
    type_status = type_attendance == "yes"

    # Date calculations
    now = datetime.now()
    current_day = now.day
    month = f"{now.month:02d}"
    current_year = now.year
    old_year = now.year - 1

    # Adjust year for December/January boundary
    if get_month == "12" and month == "01":
        current_year = old_year
    if not get_month:
        get_month = month

    # Parse dates
    date_day = datetime.strptime(f"{current_year}-{get_month}-{day}", "%Y-%m-%d")
    date_month = datetime.strptime(f"{current_year}-{get_month}", "%Y-%m")
    date_year = datetime.strptime(str(current_year), "%Y")

    # OPTIMIZATION: Single query with eager loading for group, teacher, and subject
    group = db.session.query(Groups).options(
        joinedload(Groups.teacher),
        joinedload(Groups.subject),
        joinedload(Groups.course_type)
    ).filter(Groups.id == group_id).first()

    if not group:
        return jsonify({"errors": [{"active": True, "message": "Group not found", "status": "danger"}]}), 404

    teacher = group.teacher_id
    subject = group.subject
    teacher = Teachers.query.filter(Teachers.id == teacher).first()
    # OPTIMIZATION: Single query for student with user relationship
    student = db.session.query(Students).options(
        joinedload(Students.user)
    ).filter(Students.user_id == student_user_id).first()

    if not student:
        return jsonify({"errors": [{"active": True, "message": "Student not found", "status": "danger"}]}), 404

    # Get or create calendar entries (optimized with bulk check)
    calendar_year = CalendarYear.query.filter(CalendarYear.date == date_year).first()
    if not calendar_year:
        calendar_year = CalendarYear(date=date_year)
        db.session.add(calendar_year)
        db.session.flush()

    calendar_month = CalendarMonth.query.filter(
        CalendarMonth.date == date_month,
        CalendarMonth.year_id == calendar_year.id
    ).first()
    if not calendar_month:
        calendar_month = CalendarMonth(date=date_month, year_id=calendar_year.id)
        db.session.add(calendar_month)
        db.session.flush()

    calendar_day = CalendarDay.query.filter(
        CalendarDay.date == date_day,
        CalendarDay.month_id == calendar_month.id
    ).first()
    if not calendar_day:
        calendar_day = CalendarDay(date=date_day, month_id=calendar_month.id)
        db.session.add(calendar_day)
        db.session.flush()

    # Check for discount
    discount = StudentCharity.query.filter(
        StudentCharity.group_id == group_id,
        StudentCharity.student_id == student.id
    ).first()

    # Calculate financial values
    balance_per_day = round(group.price / group.attendance_days)
    salary_per_day = round(group.teacher_salary / group.attendance_days)

    balance_with_discount = 0
    discount_per_day = 0
    discount_status = False

    if discount:
        discount_per_day = round(discount.discount / group.attendance_days)
        balance_with_discount = balance_per_day - discount_per_day
        discount_status = True

    # Get or create attendance record
    attendance = Attendance.query.filter(
        Attendance.student_id == student.id,
        Attendance.calendar_year == calendar_year.id,
        Attendance.location_id == group.location_id,
        Attendance.calendar_month == calendar_month.id,
        Attendance.teacher_id == teacher.id,
        Attendance.group_id == group.id,
        Attendance.subject_id == subject.id,
        Attendance.course_id == group.course_type_id
    ).first()

    if not attendance:
        attendance = Attendance(
            student_id=student.id,
            calendar_year=calendar_year.id,
            location_id=group.location_id,
            calendar_month=calendar_month.id,
            teacher_id=teacher.id,
            group_id=group_id,
            course_id=group.course_type_id,
            subject_id=subject.id
        )
        db.session.add(attendance)
        db.session.flush()

    # Check existing attendance
    exist_attendance = db.session.query(AttendanceDays).join(
        Attendance, AttendanceDays.attendance_id == Attendance.id
    ).filter(
        AttendanceDays.student_id == student.id,
        AttendanceDays.calendar_day == calendar_day.id,
        AttendanceDays.group_id == group_id,
        Attendance.calendar_month == calendar_month.id,
        Attendance.calendar_year == calendar_year.id
    ).first()

    if exist_attendance:
        return jsonify({
            "errors": [{
                "active": True,
                "message": f"{student.user.name} {student.user.surname} bu kunda davomat qilingan",
                "status": "danger"
            }]
        }), 400

    # Check attendance count limit
    len_attendance = AttendanceDays.query.filter(
        AttendanceDays.student_id == student.id,
        AttendanceDays.group_id == group_id,
        AttendanceDays.location_id == group.location_id,
        AttendanceDays.attendance_id == attendance.id
    ).count()

    if len_attendance >= group.attendance_days:
        return jsonify({
            "errors": [{
                "active": True,
                "message": f"{student.user.name} {student.user.surname} bu oyda 13 kun dan ko'p davomat qilindi",
                "status": "danger"
            }]
        }), 400

    # Calculate teacher ball based on lateness
    ball = 5
    if int(day) < current_day:
        late_days = current_day - int(day)
        ball = max(0, ball - late_days)

    # Check for lesson plan and calculate fine
    today_lesson_plan = LessonPlan.query.filter(
        LessonPlan.group_id == group.id,
        LessonPlan.teacher_id == teacher.id,
        LessonPlan.date == calendar_day.date,
        LessonPlan.main_lesson == None,
        LessonPlan.homework == None,
        LessonPlan.activities == None,
        LessonPlan.objective == None,
        LessonPlan.resources == None,
        LessonPlan.assessment == None
    ).first()

    fine = 0
    if today_lesson_plan or ball < 5:
        fine = round(salary_per_day / group.attendance_days)

    # Update student ball_time
    ball_time = now + timedelta(minutes=0)
    student.ball_time = ball_time

    # Create attendance day record based on type
    if not type_status:
        # Absent
        attendance_add = AttendanceDays(
            teacher_id=teacher.id,
            student_id=student.id,
            calendar_day=calendar_day.id,
            attendance_id=attendance.id,
            reason="",
            status=0,
            balance_per_day=balance_per_day,
            balance_with_discount=balance_with_discount,
            salary_per_day=salary_per_day,
            group_id=group_id,
            location_id=group.location_id,
            discount_per_day=discount_per_day,
            teacher_ball=ball,
            fine=fine,
            discount=discount_status
        )
    elif homework == 0 and dictionary == 0 and active == 0:
        # Present without scores
        attendance_add = AttendanceDays(
            teacher_id=teacher.id,
            student_id=student.id,
            calendar_day=calendar_day.id,
            attendance_id=attendance.id,
            status=1,
            balance_per_day=balance_per_day,
            teacher_ball=ball,
            balance_with_discount=balance_with_discount,
            salary_per_day=salary_per_day,
            group_id=group_id,
            location_id=group.location_id,
            discount=discount_status,
            discount_per_day=discount_per_day,
            fine=fine
        )
    else:
        # Present with scores
        average_ball = round((homework + dictionary + active) / subject.ball_number)
        attendance_add = AttendanceDays(
            student_id=student.id,
            attendance_id=attendance.id,
            dictionary=dictionary,
            teacher_ball=ball,
            calendar_day=calendar_day.id,
            status=2,
            balance_per_day=balance_per_day,
            homework=homework,
            average_ball=average_ball,
            activeness=active,
            group_id=group_id,
            location_id=group.location_id,
            teacher_id=teacher.id,
            balance_with_discount=balance_with_discount,
            salary_per_day=salary_per_day,
            discount=discount_status,
            discount_per_day=discount_per_day,
            fine=fine
        )

    db.session.add(attendance_add)
    db.session.flush()

    # Update group attendance status
    year_date = attendance.year.date
    month_date = attendance.month.date

    group_attendance = db.session.query(GroupAttendance).join(
        CalendarYear, GroupAttendance.calendar_year == CalendarYear.id
    ).join(
        CalendarMonth, GroupAttendance.calendar_month == CalendarMonth.id
    ).filter(
        GroupAttendance.group_id == group_id,
        CalendarYear.date == year_date,
        CalendarMonth.date == month_date
    ).first()

    if group_attendance:
        group_attendance.status = False

    # Handle school user updates (synchronous - quick operation)
    if student.user.school_user_id:
        update_school_salary(student.user, group, calendar_day, calendar_month, calendar_year, attendance_add)

    # Calculate ball percentage with single query
    attendance_days = AttendanceDays.query.filter(
        AttendanceDays.attendance_id == attendance.id,
        AttendanceDays.teacher_ball != None
    ).all()

    if attendance_days:
        total_ball = sum(ad.teacher_ball for ad in attendance_days)
        result = round(total_ball / len(attendance_days))
        attendance.ball_percentage = result

    # Commit all changes at once
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "errors": [{
                "active": True,
                "message": f"Database error: {str(e)}",
                "status": "danger"
            }]
        }), 500

    # =====================================================
    # ASYNC TASKS - Process in background with Celery
    # =====================================================

    # Trigger all post-attendance operations asynchronously
    # This includes: debt/balance updates, salary calculations, black salary, notifications
    process_attendance_post_save.delay(
        student_id=student.id,
        group_id=group_id,
        attendance_day_id=attendance_add.id,
        teacher_user_id=teacher.user_id,
        is_debtor=(student.debtor == 2),
        teacher_id=teacher.id,
        calendar_month_id=calendar_month.id,
        calendar_year_id=calendar_year.id,
        location_id=student.user.location_id,
        salary_per_day=salary_per_day
    )

    # Return immediately to user - background tasks will complete asynchronously
    return jsonify({
        "message": f"{student.user.name} {student.user.surname} davomat qilindi",
        "status": "success",
        "errors": [],
        "info": {
            "attendance_id": attendance_add.id,
            "student_id": student.id,
            "group_id": group_id,
            "processing": "Background tasks initiated for salary and notifications"
        }
    })


@group_classroom_attendance_bp.route(f'/make_attendance_classroom_mobile', methods=['POST'])
def make_attendance_classroom_mobile():
    """
    Make attendance for multiple students - optimized mobile version with Celery async tasks.
    """
    # Parse request data
    data = request.get_json()['data']
    day = data['day']
    get_month = data.get('month')
    group_id = int(data['group_id'])
    students = data['students']

    # Date calculations
    now = datetime.now()
    current_day = now.day
    month = f"{now.month:02d}"
    current_year = now.year
    old_year = now.year - 1

    # Adjust year for December/January boundary
    if get_month == "12" and month == "01":
        current_year = old_year
    if not get_month:
        get_month = month

    # Parse dates
    date_day = datetime.strptime(f"{current_year}-{get_month}-{day}", "%Y-%m-%d")
    date_month = datetime.strptime(f"{current_year}-{get_month}", "%Y-%m")
    date_year = datetime.strptime(str(current_year), "%Y")

    # OPTIMIZATION: Single query with eager loading for group, teacher, and subject
    group = db.session.query(Groups).options(
        joinedload(Groups.teacher),
        joinedload(Groups.subject),
        joinedload(Groups.course_type)
    ).filter(Groups.id == group_id).first()

    if not group:
        return jsonify({
            "errors": [{
                "active": True,
                "message": "Group not found",
                "status": "danger"
            }]
        }), 404

    teacher = group.teacher
    subject = group.subject

    # Get or create calendar entries (optimized with single transaction)
    calendar_year = CalendarYear.query.filter(CalendarYear.date == date_year).first()
    if not calendar_year:
        calendar_year = CalendarYear(date=date_year)
        db.session.add(calendar_year)
        db.session.flush()

    calendar_month = CalendarMonth.query.filter(
        CalendarMonth.date == date_month,
        CalendarMonth.year_id == calendar_year.id
    ).first()
    if not calendar_month:
        calendar_month = CalendarMonth(date=date_month, year_id=calendar_year.id)
        db.session.add(calendar_month)
        db.session.flush()

    calendar_day = CalendarDay.query.filter(
        CalendarDay.date == date_day,
        CalendarDay.month_id == calendar_month.id
    ).first()
    if not calendar_day:
        calendar_day = CalendarDay(date=date_day, month_id=calendar_month.id)
        db.session.add(calendar_day)
        db.session.flush()

    # OPTIMIZATION: Bulk fetch all students at once
    student_user_ids = [st['id'] for st in students]
    students_dict = {
        s.user_id: s for s in db.session.query(Students).options(
            joinedload(Students.user)
        ).filter(Students.user_id.in_(student_user_ids)).all()
    }

    # OPTIMIZATION: Bulk fetch all discounts at once
    student_ids = list(students_dict.values())
    student_id_list = [s.id for s in student_ids]
    discounts_dict = {
        d.student_id: d for d in StudentCharity.query.filter(
            StudentCharity.group_id == group_id,
            StudentCharity.student_id.in_(student_id_list)
        ).all()
    }

    # OPTIMIZATION: Bulk fetch all attendances at once
    attendances_dict = {
        a.student_id: a for a in Attendance.query.filter(
            Attendance.student_id.in_(student_id_list),
            Attendance.calendar_year == calendar_year.id,
            Attendance.location_id == group.location_id,
            Attendance.calendar_month == calendar_month.id,
            Attendance.teacher_id == teacher.id,
            Attendance.group_id == group_id,
            Attendance.subject_id == subject.id,
            Attendance.course_id == group.course_type_id
        ).all()
    }

    # OPTIMIZATION: Bulk check existing attendances
    existing_attendances = {
        ad.student_id for ad in db.session.query(AttendanceDays.student_id).join(
            Attendance, AttendanceDays.attendance_id == Attendance.id
        ).filter(
            AttendanceDays.student_id.in_(student_id_list),
            AttendanceDays.calendar_day == calendar_day.id,
            AttendanceDays.group_id == group_id,
            Attendance.calendar_month == calendar_month.id,
            Attendance.calendar_year == calendar_year.id
        ).all()
    }

    # OPTIMIZATION: Bulk count attendance days
    attendance_counts = dict(
        db.session.query(
            AttendanceDays.student_id,
            func.count(AttendanceDays.id)
        ).filter(
            AttendanceDays.student_id.in_(student_id_list),
            AttendanceDays.group_id == group_id,
            AttendanceDays.location_id == group.location_id
        ).group_by(AttendanceDays.student_id).all()
    )

    # Calculate financial values (same for all students)
    balance_per_day = round(group.price / group.attendance_days)
    salary_per_day = round(group.teacher_salary / group.attendance_days)

    # Calculate teacher ball based on lateness
    ball = 5
    if int(day) < current_day:
        late_days = current_day - int(day)
        ball = max(0, ball - late_days)

    # Check for lesson plan (same for all students)
    today_lesson_plan = LessonPlan.query.filter(
        LessonPlan.group_id == group.id,
        LessonPlan.teacher_id == teacher.id,
        LessonPlan.date == calendar_day.date,
        LessonPlan.main_lesson == None,
        LessonPlan.homework == None,
        LessonPlan.activities == None,
        LessonPlan.objective == None,
        LessonPlan.resources == None,
        LessonPlan.assessment == None
    ).first()

    fine = 0
    if today_lesson_plan or ball < 5:
        fine = round(salary_per_day / group.attendance_days)

    errors = []
    attendances_to_create = []
    attendance_days_to_add = []
    students_to_update = []
    async_tasks_data = []

    ball_time = now + timedelta(minutes=0)

    # Process each student
    for st in students:
        student = students_dict.get(st['id'])
        if not student:
            errors.append({
                "active": True,
                "message": f"Student with ID {st['id']} not found",
                "status": "warning"
            })
            continue

        # Check if already has attendance today
        if student.id in existing_attendances:
            errors.append({
                "active": True,
                "message": f"{student.user.name} {student.user.surname} bu kunda davomat qilingan",
                "status": "warning"
            })
            continue

        # Get or prepare attendance record
        attendance = attendances_dict.get(student.id)
        if not attendance:
            attendance = Attendance(
                student_id=student.id,
                calendar_year=calendar_year.id,
                location_id=group.location_id,
                calendar_month=calendar_month.id,
                teacher_id=teacher.id,
                group_id=group_id,
                course_id=group.course_type_id,
                subject_id=subject.id
            )
            attendances_to_create.append(attendance)
            attendances_dict[student.id] = attendance

        # Check attendance count limit
        current_count = attendance_counts.get(student.id, 0)
        if current_count >= group.attendance_days:
            errors.append({
                "active": True,
                "message": f"{student.user.name} {student.user.surname} bu oyda {group.attendance_days} kun dan ko'p davomat qilindi",
                "status": "warning"
            })
            continue

        # Get scores
        homework = st.get('homework', 0)
        dictionary = st.get('dictionary', 0)
        active = st.get('active', 0)
        type_status = st['type'] == "yes"

        # Calculate discount
        discount = discounts_dict.get(student.id)
        balance_with_discount = 0
        discount_per_day = 0
        discount_status = False

        if discount:
            discount_per_day = round(discount.discount / group.attendance_days)
            balance_with_discount = balance_per_day - discount_per_day
            discount_status = True

        # Update student ball_time
        student.ball_time = ball_time
        students_to_update.append(student)

        # Create attendance day record based on type
        if not type_status:
            # Absent
            attendance_day = AttendanceDays(
                teacher_id=teacher.id,
                student_id=student.id,
                calendar_day=calendar_day.id,
                attendance_id=None,  # Will be set after flush
                reason="",
                status=0,
                balance_per_day=balance_per_day,
                balance_with_discount=balance_with_discount,
                salary_per_day=salary_per_day,
                group_id=group_id,
                location_id=group.location_id,
                discount_per_day=discount_per_day,
                teacher_ball=ball,
                fine=fine,
                discount=discount_status
            )
        elif homework == 0 and dictionary == 0 and active == 0:
            # Present without scores
            attendance_day = AttendanceDays(
                teacher_id=teacher.id,
                student_id=student.id,
                calendar_day=calendar_day.id,
                attendance_id=None,
                status=1,
                balance_per_day=balance_per_day,
                teacher_ball=ball,
                balance_with_discount=balance_with_discount,
                salary_per_day=salary_per_day,
                group_id=group_id,
                location_id=group.location_id,
                discount=discount_status,
                discount_per_day=discount_per_day,
                fine=fine
            )
        else:
            # Present with scores
            average_ball = round((homework + dictionary + active) / subject.ball_number)
            attendance_day = AttendanceDays(
                student_id=student.id,
                attendance_id=None,
                dictionary=dictionary,
                teacher_ball=ball,
                calendar_day=calendar_day.id,
                status=2,
                balance_per_day=balance_per_day,
                homework=homework,
                average_ball=average_ball,
                activeness=active,
                group_id=group_id,
                location_id=group.location_id,
                teacher_id=teacher.id,
                balance_with_discount=balance_with_discount,
                salary_per_day=salary_per_day,
                discount=discount_status,
                discount_per_day=discount_per_day,
                fine=fine
            )

        attendance_days_to_add.append((student, attendance, attendance_day))

    # OPTIMIZATION: Bulk commit all changes
    try:
        # Add new attendances first
        if attendances_to_create:
            db.session.add_all(attendances_to_create)
            db.session.flush()

        # Now add attendance days with proper attendance_id
        for student, attendance, attendance_day in attendance_days_to_add:
            attendance_day.attendance_id = attendance.id
            db.session.add(attendance_day)

        db.session.flush()

        # Handle school user updates (synchronous - quick operation)
        for student, attendance, attendance_day in attendance_days_to_add:
            if student.user.school_user_id:
                update_school_salary(student.user, group, calendar_day, calendar_month, calendar_year, attendance_day)

            # Prepare async task data
            async_tasks_data.append({
                'student_id': student.id,
                'attendance_day_id': attendance_day.id,
                'is_debtor': student.debtor == 2,
                'attendance_id': attendance.id
            })

        # OPTIMIZATION: Bulk update ball percentages
        attendance_ids = list(set(a.id for a in attendances_dict.values()))
        for attendance_id in attendance_ids:
            attendance_days = AttendanceDays.query.filter(
                AttendanceDays.attendance_id == attendance_id,
                AttendanceDays.teacher_ball != None
            ).all()

            if attendance_days:
                total_ball = sum(ad.teacher_ball for ad in attendance_days)
                result = round(total_ball / len(attendance_days))
                Attendance.query.filter(Attendance.id == attendance_id).update({
                    "ball_percentage": result
                })

        # Commit all changes at once
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "errors": [{
                "active": True,
                "message": f"Database error: {str(e)}",
                "status": "danger"
            }]
        }), 500

    # =====================================================
    # ASYNC TASKS - Process in background with Celery
    # =====================================================

    # Trigger all post-attendance operations asynchronously for each student
    for task_data in async_tasks_data:
        process_attendance_post_save.delay(
            student_id=task_data['student_id'],
            group_id=group_id,
            attendance_day_id=task_data['attendance_day_id'],
            teacher_user_id=teacher.user_id,
            is_debtor=task_data['is_debtor'],
            teacher_id=teacher.id,
            calendar_month_id=calendar_month.id,
            calendar_year_id=calendar_year.id,
            location_id=group.location_id,
            salary_per_day=salary_per_day
        )

    # Return immediately to user - background tasks will complete asynchronously
    return jsonify({
        "message": "Attendance added successfully",
        "status": "success",
        "errors": errors,
        "info": {
            "students_processed": len(attendance_days_to_add),
            "students_skipped": len(errors),
            "processing": "Background tasks initiated for salary and notifications"
        }
    })
