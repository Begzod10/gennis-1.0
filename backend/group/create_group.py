from sqlalchemy import and_, or_, extract
from backend.functions.utils import remove_items_create_group
from backend.models.models import Subjects, CourseTypes, Rooms, Week, Teachers, Group_Room_Week, Students, Users, \
    StudentHistoryGroups, Groups, RegisterDeletedStudents, Roles, Locations, DeletedStudents, GroupReason, CalendarDay, \
    TeacherGroupStatistics, db, student_subject, student_group, Assistent
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.functions.utils import get_json_field, find_calendar_date
from datetime import datetime
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import contains_eager, joinedload
from pprint import pprint
from sqlalchemy import delete

group_create_bp = Blueprint('group_create_bp', __name__)


@group_create_bp.route(f'/create_group_tools')
# @jwt_required()
def create_group_tools():
    course_types = CourseTypes.query.order_by('id').all()
    subjects = Subjects.query.order_by('id').all()
    subject_list = []
    course_list = []
    for subject in subjects:
        info = {
            "name": subject.name,
            "id": subject.id
        }
        subject_list.append(info)

    for course in course_types:
        info = {
            "name": course.name,
            "id": course.id
        }
        course_list.append(info)
    filters = {
        "subjects": subject_list,
        "course_types": course_list,
    }
    return jsonify({
        "createGroupTools": filters
    })


@group_create_bp.route(f'/check_time_assistent/<int:teacher_id>/<int:location_id>/', methods=['POST'])
@jwt_required()
def check_time_asistent(teacher_id, location_id):
    lessons = request.get_json()['lessons']

    # Single query to get all assistants with their schedules
    assistents = db.session.query(Assistent).join(
        Assistent.user
    ).outerjoin(
        Assistent.time_table
    ).options(
        contains_eager(Assistent.user),
        contains_eager(Assistent.time_table).joinedload(Group_Room_Week.week),
        contains_eager(Assistent.time_table).joinedload(Group_Room_Week.group),
        joinedload(Assistent.subjects)
    ).filter(
        or_(Assistent.deleted == False, Assistent.deleted == None),
        Assistent.teacher_id == teacher_id,
        Users.location_id == location_id
    ).all()

    if not assistents:
        return jsonify({'error': 'Assistent mavjud emas'})

    assistent_errors = []

    for assistent in assistents:
        # Build base info once per assistant
        info = {
            "id": assistent.user.id,
            "name": assistent.user.name.title(),
            "surname": assistent.user.surname.title(),
            "username": assistent.user.username,
            "language": assistent.user.language.name,
            "age": assistent.user.age,
            "reg_date": assistent.user.day.date.strftime("%Y-%m-%d") if assistent.user.day else None,
            "comment": assistent.user.comment,
            'money': assistent.user.balance,
            "role": assistent.user.role_info.type_role,
            "subjects": [subject.name for subject in assistent.subjects],
            "photo_profile": assistent.user.photo_profile,
            "color": "green",
            "error": False,
            "shift": "",
            "conflicts": []  # Track all conflicts
        }

        # Check conflicts for each lesson
        for lesson in lessons:
            start_time = datetime.strptime(lesson.get('startTime'), "%H:%M").time()
            end_time = datetime.strptime(lesson.get('endTime'), "%H:%M").time()
            week_id = lesson['selectedDay'].get('id')

            # Check conflicts in already-loaded time_table
            for schedule in assistent.time_table:
                if (schedule.week_id == week_id and
                        schedule.location_id == location_id):

                    schedule_start = schedule.start_time.time() if isinstance(schedule.start_time,
                                                                              datetime) else schedule.start_time
                    schedule_end = schedule.end_time.time() if isinstance(schedule.end_time,
                                                                          datetime) else schedule.end_time

                    # Check for time overlap
                    if (schedule_start <= start_time < schedule_end or
                            schedule_start < end_time <= schedule_end or
                            (start_time <= schedule_start and end_time >= schedule_end)):
                        conflict_msg = (
                            f"{schedule.week.name} da soat: '{schedule_start.strftime('%H:%M')} dan "
                            f"{schedule_end.strftime('%H:%M')}' gacha "
                            f"{schedule.group.name} da darsi bor."
                        )

                        info["conflicts"].append(conflict_msg)
                        info["color"] = "red"
                        info["error"] = True

        # Set shift to first conflict if any
        if info["conflicts"]:
            info["shift"] = info["conflicts"][0]

        assistent_errors.append(info)

    return jsonify({"assistent_errors": assistent_errors})


@group_create_bp.route(f'/get_students/<int:location_id>', methods=['POST'])
def get_students(location_id):
    lessons = request.get_json()['lessons']

    # Get roles once
    role_student = Roles.query.filter(Roles.type_role == "student").first()
    role_teacher = Roles.query.filter(Roles.type_role == "teacher").first()

    gr_errors = []

    # Check room conflicts for all lessons at once
    for lesson in lessons:
        start_time = datetime.strptime(lesson.get('startTime'), "%H:%M").time()
        end_time = datetime.strptime(lesson.get('endTime'), "%H:%M").time()

        # Single query for room conflicts
        room_conflicts = db.session.query(Group_Room_Week).options(
            joinedload(Group_Room_Week.week),
            joinedload(Group_Room_Week.room),
            joinedload(Group_Room_Week.group)
        ).filter(
            Group_Room_Week.week_id == lesson['selectedDay'].get('id'),
            Group_Room_Week.room_id == lesson['selectedRoom'].get('id')
        ).all()

        for conflict in room_conflicts:
            conflict_start = conflict.start_time.time() if isinstance(conflict.start_time,
                                                                      datetime) else conflict.start_time
            conflict_end = conflict.end_time.time() if isinstance(conflict.end_time, datetime) else conflict.end_time

            # Check for overlap
            if (conflict_start <= start_time < conflict_end or
                    conflict_start < end_time <= conflict_end or
                    (start_time <= conflict_start and end_time >= conflict_end)):
                error = f"{conflict.week.name} kuni {conflict.room.name} da soat: '{conflict_start.strftime('%H:%M')} - {conflict_end.strftime('%H:%M')}' da {conflict.group.name} ni darsi bor."
                gr_errors.append(error)

    # Get all teachers with their schedules in ONE query
    teachers = db.session.query(Teachers).join(
        Teachers.user
    ).outerjoin(
        Teachers.time_table
    ).join(
        Teachers.locations
    ).options(
        contains_eager(Teachers.user).joinedload(Users.language),
        contains_eager(Teachers.user).joinedload(Users.day),
        contains_eager(Teachers.locations),
        contains_eager(Teachers.time_table).joinedload(Group_Room_Week.week),
        contains_eager(Teachers.time_table).joinedload(Group_Room_Week.group),
        joinedload(Teachers.subject)
    ).filter(
        Teachers.deleted == None,
        Locations.id == location_id
    ).all()

    teacher_errors = []
    for teacher in teachers:
        info = {
            "id": teacher.user.id,
            "teacher_id": teacher.id,
            "name": teacher.user.name.title(),
            "surname": teacher.user.surname.title(),
            "username": teacher.user.username,
            "language": teacher.user.language.name,
            "age": teacher.user.age,
            "reg_date": teacher.user.day.date.strftime("%Y-%m-%d"),
            "comment": teacher.user.comment,
            'money': teacher.user.balance,
            "role": role_teacher.role,
            "subjects": [subject.name for subject in teacher.subject],
            "photo_profile": teacher.user.photo_profile,
            "color": "green",
            "error": False,
            "shift": "",
            "conflicts": []
        }

        # Check conflicts against each lesson
        for lesson in lessons:
            start_time = datetime.strptime(lesson.get('startTime'), "%H:%M").time()
            end_time = datetime.strptime(lesson.get('endTime'), "%H:%M").time()
            week_id = lesson['selectedDay'].get('id')
            room_id = lesson['selectedRoom'].get('id')

            # ✅ Count how many lessons teacher already has at this time
            conflicting_lessons = []

            for schedule in teacher.time_table:
                if schedule.week_id == week_id and schedule.location_id == location_id:
                    schedule_start = schedule.start_time.time() if isinstance(schedule.start_time,
                                                                              datetime) else schedule.start_time
                    schedule_end = schedule.end_time.time() if isinstance(schedule.end_time,
                                                                          datetime) else schedule.end_time

                    # Check if there's a time overlap
                    has_time_overlap = (
                            schedule_start <= start_time < schedule_end or
                            schedule_start < end_time <= schedule_end or
                            (start_time <= schedule_start and end_time >= schedule_end)
                    )

                    if has_time_overlap:
                        conflicting_lessons.append(schedule)

            # ✅ Now check if adding this new lesson would cause a conflict
            if conflicting_lessons:
                if len(conflicting_lessons) >= 2:
                    # Already has 2 lessons at this time - can't add a 3rd
                    first_schedule = conflicting_lessons[0]
                    schedule_start = first_schedule.start_time.time() if isinstance(first_schedule.start_time,
                                                                                    datetime) else first_schedule.start_time
                    schedule_end = first_schedule.end_time.time() if isinstance(first_schedule.end_time,
                                                                                datetime) else first_schedule.end_time

                    conflict_msg = (
                        f"{first_schedule.week.name} da soat: '{schedule_start.strftime('%H:%M')} dan "
                        f"{schedule_end.strftime('%H:%M')}' gacha allaqachon 2 ta dars bor - "
                        f"maksimum 2 ta dars bir vaqtda bo'lishi mumkin"
                    )
                    info["conflicts"].append(conflict_msg)
                    info["color"] = "red"
                    info["error"] = True

                elif len(conflicting_lessons) == 1:
                    # Can add 2nd lesson only if the conflicting group has an assistant covering it
                    schedule = conflicting_lessons[0]
                    if not schedule.group.assistent:
                        schedule_start = schedule.start_time.time() if isinstance(schedule.start_time, datetime) else schedule.start_time
                        schedule_end = schedule.end_time.time() if isinstance(schedule.end_time, datetime) else schedule.end_time
                        conflict_msg = (
                            f"{schedule.week.name} da soat: '{schedule_start.strftime('%H:%M')} dan "
                            f"{schedule_end.strftime('%H:%M')}' gacha {schedule.group.name} da darsi bor "
                            f"(assistant yo'q - 2 ta dars bir vaqtda bo'lishi mumkin emas)"
                        )
                        info["conflicts"].append(conflict_msg)
                        info["color"] = "red"
                        info["error"] = True

        if info["conflicts"]:
            info["shift"] = info["conflicts"][0]

        teacher_errors.append(info)

    # Determine shift type from first lesson
    first_lesson = lessons[0]
    start_time = datetime.strptime(first_lesson.get('startTime'), "%H:%M")
    end_time = datetime.strptime(first_lesson.get('endTime'), "%H:%M")

    time_start_night = datetime.strptime("14:00", "%H:%M")

    night_shift = start_time >= time_start_night

    # Get available students based on shift
    if night_shift:
        students_available = db.session.query(Students).join(
            Students.user
        ).options(
            contains_eager(Students.user).joinedload(Users.language),
            contains_eager(Students.user).joinedload(Users.day),
            joinedload(Students.subject)
        ).filter(
            or_(Students.night_shift == True, Students.night_shift == None),
            Users.location_id == location_id,
            Students.group == None,
            Students.deleted_from_register == None
        ).order_by(Users.calendar_day).all()

        students_not_available = db.session.query(Students).join(
            Students.user
        ).options(
            contains_eager(Students.user).joinedload(Users.language),
            contains_eager(Students.user).joinedload(Users.day),
            joinedload(Students.subject)
        ).filter(
            Students.night_shift == False,
            Users.location_id == location_id,
            Students.group == None,
            Students.deleted_from_register == None
        ).order_by(Users.calendar_day).all()

        shift_error_msg = "Studentga ertalabki smen belgilangan."
    else:
        students_available = db.session.query(Students).join(
            Students.user
        ).options(
            contains_eager(Students.user).joinedload(Users.language),
            contains_eager(Students.user).joinedload(Users.day),
            joinedload(Students.subject)
        ).filter(
            or_(Students.morning_shift == True, Students.morning_shift == None),
            Users.location_id == location_id,
            Students.group == None,
            Students.deleted_from_register == None
        ).order_by(Users.calendar_day).all()

        students_not_available = db.session.query(Students).join(
            Students.user
        ).options(
            contains_eager(Students.user).joinedload(Users.language),
            contains_eager(Students.user).joinedload(Users.day),
            joinedload(Students.subject)
        ).filter(
            Students.morning_shift == False,
            Users.location_id == location_id,
            Students.group == None,
            Students.deleted_from_register == None
        ).order_by(Users.calendar_day).all()

        shift_error_msg = "Studentga kechki smen belgilangan."

    student_errors = []

    # Add available students
    for student in students_available:
        info = {
            "id": student.user.id,
            "name": student.user.name.title(),
            "surname": student.user.surname.title(),
            "username": student.user.username,
            "language": student.user.language.name,
            "age": student.user.age,
            "reg_date": student.user.day.date.strftime("%Y-%m-%d"),
            "comment": student.user.comment,
            'money': student.user.balance,
            "role": role_student.role,
            "subjects": [subject.name for subject in student.subject],
            "photo_profile": student.user.photo_profile,
            "color": "green",
            "error": False,
            "shift": ""
        }
        student_errors.append(info)

    # Add unavailable students (wrong shift)
    for student in students_not_available:
        info = {
            "id": student.user.id,
            "name": student.user.name.title(),
            "surname": student.user.surname.title(),
            "username": student.user.username,
            "language": student.user.language.name,
            "age": student.user.age,
            "reg_date": student.user.day.date.strftime("%Y-%m-%d"),
            "comment": student.user.comment,
            'money': student.user.balance,
            "role": role_student.role,
            "subjects": [subject.name for subject in student.subject],
            "photo_profile": student.user.photo_profile,
            "color": "red",
            "error": True,
            "shift": shift_error_msg
        }
        student_errors.append(info)

    # Get students already in groups with their schedules
    students_in_groups = db.session.query(Students).join(
        Students.user
    ).outerjoin(
        Students.time_table
    ).options(
        contains_eager(Students.user).joinedload(Users.language),
        contains_eager(Students.user).joinedload(Users.day),
        contains_eager(Students.time_table).joinedload(Group_Room_Week.week),
        contains_eager(Students.time_table).joinedload(Group_Room_Week.group),
        joinedload(Students.subject)
    ).filter(
        Students.group != None,
        Students.deleted_from_register == None,
        Users.location_id == location_id
    ).all()

    for student in students_in_groups:
        info = {
            "id": student.user.id,
            "name": student.user.name.title(),
            "surname": student.user.surname.title(),
            "username": student.user.username,
            "language": student.user.language.name,
            "age": student.user.age,
            "reg_date": student.user.day.date.strftime("%Y-%m-%d"),
            "comment": student.user.comment,
            'money': student.user.balance,
            "role": role_student.role,
            "subjects": [subject.name for subject in student.subject],
            "photo_profile": student.user.photo_profile,
            "color": "green",
            "error": False,
            "shift": "",
            "conflicts": []
        }

        # Check for schedule conflicts
        for lesson in lessons:
            start_time = datetime.strptime(lesson.get('startTime'), "%H:%M").time()
            end_time = datetime.strptime(lesson.get('endTime'), "%H:%M").time()
            week_id = lesson['selectedDay'].get('id')

            for schedule in student.time_table:
                if schedule.week_id == week_id:
                    schedule_start = schedule.start_time.time() if isinstance(schedule.start_time,
                                                                              datetime) else schedule.start_time
                    schedule_end = schedule.end_time.time() if isinstance(schedule.end_time,
                                                                          datetime) else schedule.end_time

                    if (schedule_start <= start_time < schedule_end or
                            schedule_start < end_time <= schedule_end or
                            (start_time <= schedule_start and end_time >= schedule_end)):
                        conflict_msg = f"{schedule.week.name} da soat: '{schedule_start.strftime('%H:%M')} dan {schedule_end.strftime('%H:%M')}' gacha {schedule.group.name} da darsi bor."
                        info["conflicts"].append(conflict_msg)
                        info["color"] = "red"
                        info["error"] = True

        if info["conflicts"]:
            info["shift"] = info["conflicts"][0]

        student_errors.append(info)

    filtered_students = remove_items_create_group(student_errors)
    filtered_teachers = remove_items_create_group(teacher_errors)

    return jsonify({
        "success": True,
        "data": {
            'gr_errors': gr_errors,
            "students": filtered_students,
            "teachers": filtered_teachers,
        }
    })


@group_create_bp.route(f'/create_group_time/<int:location_id>', methods=['POST'])
def create_group_time(location_id):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    group_name = request.get_json()['groupInfo']['groupName']
    group_price = request.get_json()['groupInfo']['groupPrice']
    subject = request.get_json()['groupInfo']['subject']
    type_course = request.get_json()['groupInfo']['typeCourse']
    teacher_salary = int(request.get_json()['groupInfo']['teacherDolya'])
    if 'assistentSalary' in request.get_json()['groupInfo']:
        assistent_salary = int(request.get_json()['groupInfo']['assistentSalary'])
    else:
        assistent_salary = None
    if 'assistent_id' in request.get_json()['groupInfo']:
        assistent_id = request.get_json()['groupInfo']['assistent_id']
        assistent = Assistent.query.filter(Assistent.user_id == assistent_id).first()
        assistent_id = assistent.id
    else:
        assistent_id = None
        assistent = None
    subject = Subjects.query.filter(Subjects.name == subject).first()
    type_course = CourseTypes.query.filter(CourseTypes.name == type_course).first()
    teacher = Teachers.query.filter(Teachers.user_id == request.get_json()['teacher']['id']).first()
    add = Groups(name=group_name, course_type_id=type_course.id, subject_id=subject.id, location_id=location_id,
                 education_language=teacher.user.education_language, calendar_day=calendar_day.id, attendance_days=13,
                 calendar_month=calendar_month.id, calendar_year=calendar_year.id, teacher_id=teacher.id,
                 assistent_id=assistent_id,
                 assistent_salary=assistent_salary,
                 price=group_price, teacher_salary=teacher_salary)
    db.session.add(add)
    db.session.commit()
    for time in request.get_json()['time']:
        start_time = time['startTime']
        end_time = time['endTime']
        start_time = datetime.strptime(start_time, "%H:%M")
        end_time = datetime.strptime(end_time, "%H:%M")
        room = Rooms.query.filter(Rooms.id == time['selectedRoom']['id']).first()
        week_day = Week.query.filter(Week.id == time['selectedDay']['id']).first()

        time_table = Group_Room_Week(group_id=add.id, room_id=room.id, week_id=week_day.id, start_time=start_time,
                                     end_time=end_time, location_id=location_id)
        db.session.add(time_table)
        db.session.commit()
        teacher.time_table.append(time_table)
        db.session.commit()
        if assistent:
            assistent.time_table.append(time_table)
            db.session.commit()
        student_list = request.get_json()['students']
        student_id_list = []

        for loc in student_list:
            student_id_list.append(int(loc['id']))

        students_checked = db.session.query(Students).join(Students.user).options(contains_eager(Students.user)).filter(
            Users.id.in_([user_id for user_id in student_id_list])).order_by('id').all()

        for st in students_checked:
            st.joined_day_id = calendar_day.id
            for sub in st.subject:
                if sub.name == subject.name:
                    st.subject.remove(subject)
            st.group.append(add)
            st.time_table.append(time_table)
            group_history = StudentHistoryGroups.query.filter(StudentHistoryGroups.teacher_id == teacher.id,
                                                              StudentHistoryGroups.student_id == st.id,
                                                              StudentHistoryGroups.group_id == add.id,
                                                              StudentHistoryGroups.joined_day == calendar_day.date).first()
            if not group_history:
                group_history = StudentHistoryGroups(teacher_id=teacher.id, student_id=st.id, group_id=add.id,
                                                     joined_day=calendar_day.date)
                db.session.add(group_history)
                db.session.commit()
    teacher.group.append(add)
    db.session.commit()
    return jsonify({
        "success": True,
        "msg": "Guruh muvaffiqiyatli yaratildi, Kassani bosila"
    })


@group_create_bp.route(f'/create_group', methods=['POST'])
@jwt_required()
def create_group():
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    group_name = get_json_field('groupName')
    group_price = int(get_json_field('groupPrice'))
    subject = get_json_field('subject')
    teacher = int(get_json_field('teacher'))
    type_course = get_json_field('typeCourse')
    teacher_dolya = int(get_json_field('teacherDolya'))
    # attendance_days = int(json_request['attendanceDays'])
    student_list = get_json_field('checkedStudents')
    location = 0
    student_id_list = []

    for loc in student_list:
        location = int(loc['location_id'])
        student_id_list.append(int(loc['id']))
    teacher_get = Teachers.query.filter(Teachers.user_id == teacher).first()
    location_get = Locations.query.filter(Locations.id == location).first()
    subject_get = Subjects.query.filter(Subjects.name == subject).first()
    course_type_get = CourseTypes.query.filter(CourseTypes.name == type_course).first()
    add = Groups(name=group_name, course_type_id=course_type_get.id, subject_id=subject_get.id,
                 teacher_salary=teacher_dolya, location_id=location_get.id, calendar_day=calendar_day.id,
                 calendar_month=calendar_month.id, calendar_year=calendar_year.id, price=group_price,
                 education_language=teacher_get.user.education_language, teacher_id=teacher_get.id,
                 attendance_days=13)
    db.session.add(add)
    db.session.commit()
    teacher_get.group.append(add)
    students_checked = db.session.query(Students).join(Students.user).options(contains_eager(Students.user)).filter(
        Users.id.in_([user_id for user_id in student_id_list])).order_by('id').all()

    for st in students_checked:
        st.created_day_id = calendar_day.id
        db.session.commit()
        for sub in st.subject:
            if sub.name == subject_get.name:
                st.subject.remove(subject_get)
        st.group.append(add)
        group_history = StudentHistoryGroups(teacher_id=teacher_get.id, student_id=st.id, group_id=add.id,
                                             joined_day=calendar_day.date)

        db.session.add(group_history)
        db.session.commit()
    db.session.commit()

    return jsonify({
        "success": True,
        "msg": "Guruh muvaffiqiyatli yaratildi, Kassani bosila"
    })


@group_create_bp.route(f'/add_group_students2/<int:group_id>', methods=['POST', 'GET'])
def add_group_students2(group_id):
    calendar_year, calendar_month, calendar_day = find_calendar_date()

    # Get group with subject eagerly loaded
    group = db.session.query(Groups).options(
        joinedload(Groups.subject)
    ).filter(Groups.id == group_id).first()

    if not group:
        return jsonify({"success": False, "error": "Group not found"}), 404

    if request.method == "POST":
        student_list = get_json_field('checkedStudents')
        student_id_list = [int(loc['id']) for loc in student_list]

        msg = "O'quvchilar guruhga qo'shildi" if len(student_id_list) > 1 else "O'quvchi guruhga qo'shildi"

        # Get all students in one query
        students_checked = db.session.query(Students).join(
            Students.user
        ).options(
            contains_eager(Students.user)
        ).filter(
            Users.id.in_(student_id_list)
        ).order_by(Students.id).all()

        # Get time_table once
        time_table = db.session.query(Group_Room_Week).filter(
            Group_Room_Week.group_id == group.id
        ).all()

        # Bulk operations
        for st in students_checked:
            # Delete existing student-subject relationship
            db.session.execute(
                delete(student_subject).where(
                    student_subject.c.subject_id == group.subject_id,
                    student_subject.c.student_id == st.id
                )
            )

            # Add to group
            st.group.append(group)

            # Add group history
            group_history = StudentHistoryGroups(
                teacher_id=group.teacher_id,
                student_id=st.id,
                group_id=group.id,
                joined_day=calendar_day.date
            )
            db.session.add(group_history)

            # Set joined day
            st.joined_day_id = calendar_day.id

            # Add all time_table entries
            for time in time_table:
                st.time_table.append(time)

        # Single commit for all operations
        db.session.commit()

        return jsonify({
            "success": True,
            "msg": msg
        })

    # GET request - fetch available students
    location_id = group.location_id
    role = Roles.query.filter(Roles.type_role == "student").first()

    # Get group's time_table once
    time_table = db.session.query(Group_Room_Week).options(
        joinedload(Group_Room_Week.week)
    ).filter(
        Group_Room_Week.group_id == group.id
    ).all()

    if not time_table:
        return jsonify({"data": [], "success": True})

    # Determine shift based on first time slot
    first_time = time_table[0]
    time_start_night = datetime.strptime("14:00", "%H:%M")
    time_end_night = datetime.strptime("07:00", "%H:%M")

    startTime = first_time.start_time
    endTime = first_time.end_time
    night_shift = startTime >= time_start_night or endTime <= time_end_night

    # Get available students (no group) in ONE query
    if night_shift:
        students_available = db.session.query(Students).join(
            Students.user
        ).join(
            Students.subject
        ).options(
            contains_eager(Students.user).joinedload(Users.language),
            contains_eager(Students.user).joinedload(Users.day),
            contains_eager(Students.subject)
        ).filter(
            or_(Students.night_shift == True, Students.night_shift == None),
            Users.location_id == location_id,
            Students.group == None,
            Students.deleted_from_register == None,
            Subjects.id == group.subject_id
        ).order_by(Users.calendar_day).all()

        students_not_available = db.session.query(Students).join(
            Students.user
        ).join(
            Students.subject
        ).options(
            contains_eager(Students.user).joinedload(Users.language),
            contains_eager(Students.user).joinedload(Users.day),
            contains_eager(Students.subject)
        ).filter(
            Students.night_shift == False,
            Users.location_id == location_id,
            Students.group == None,
            Students.deleted_from_register == None,
            Subjects.id == group.subject_id
        ).order_by(Users.calendar_day).all()

        shift_error_msg = "Studentga ertalabki smen belgilangan."
    else:
        students_available = db.session.query(Students).join(
            Students.user
        ).join(
            Students.subject
        ).options(
            contains_eager(Students.user).joinedload(Users.language),
            contains_eager(Students.user).joinedload(Users.day),
            contains_eager(Students.subject)
        ).filter(
            or_(Students.morning_shift == True, Students.morning_shift == None),
            Users.location_id == location_id,
            Students.group == None,
            Students.deleted_from_register == None,
            Subjects.id == group.subject_id
        ).order_by(Users.calendar_day).all()

        students_not_available = db.session.query(Students).join(
            Students.user
        ).join(
            Students.subject
        ).options(
            contains_eager(Students.user).joinedload(Users.language),
            contains_eager(Students.user).joinedload(Users.day),
            contains_eager(Students.subject)
        ).filter(
            Students.morning_shift == False,
            Users.location_id == location_id,
            Students.group == None,
            Students.deleted_from_register == None,
            Subjects.id == group.subject_id
        ).order_by(Users.calendar_day).all()

        shift_error_msg = "Studentga kechki smen belgilangan."

    student_errors = []

    # Add available students
    for student in students_available:
        info = {
            "id": student.user.id,
            "name": student.user.name.title(),
            "surname": student.user.surname.title(),
            "username": student.user.username,
            "language": student.user.language.name,
            "age": student.user.age,
            "reg_date": student.user.day.date.strftime("%Y-%m-%d"),
            "comment": student.user.comment,
            'money': student.user.balance,
            "role": role.role,
            "subjects": [subject.name for subject in student.subject],
            "photo_profile": student.user.photo_profile,
            "color": "green",
            "error": False,
            "shift": ""
        }
        student_errors.append(info)

    # Add students with wrong shift
    for student in students_not_available:
        info = {
            "id": student.user.id,
            "name": student.user.name.title(),
            "surname": student.user.surname.title(),
            "username": student.user.username,
            "language": student.user.language.name,
            "age": student.user.age,
            "reg_date": student.user.day.date.strftime("%Y-%m-%d"),
            "comment": student.user.comment,
            'money': student.user.balance,
            "role": role.role,
            "subjects": [subject.name for subject in student.subject],
            "photo_profile": student.user.photo_profile,
            "color": "red",
            "error": True,
            "shift": shift_error_msg
        }
        student_errors.append(info)

    # Get students already in groups with their schedules in ONE query
    students_in_groups = db.session.query(Students).join(
        Students.user
    ).join(
        Students.subject
    ).outerjoin(
        Students.time_table
    ).options(
        contains_eager(Students.user).joinedload(Users.language),
        contains_eager(Students.user).joinedload(Users.day),
        contains_eager(Students.subject),
        contains_eager(Students.time_table).joinedload(Group_Room_Week.week),
        contains_eager(Students.time_table).joinedload(Group_Room_Week.group)
    ).filter(
        Students.group != None,
        Students.deleted_from_register == None,
        Subjects.id == group.subject_id,
        Users.location_id == location_id
    ).all()

    # Check conflicts for students in groups (in-memory)
    for student in students_in_groups:
        info = {
            "id": student.user.id,
            "name": student.user.name.title(),
            "surname": student.user.surname.title(),
            "username": student.user.username,
            "language": student.user.language.name,
            "age": student.user.age,
            "reg_date": student.user.day.date.strftime("%Y-%m-%d"),
            "comment": student.user.comment,
            'money': student.user.balance,
            "role": role.role,
            "subjects": [subject.name for subject in student.subject],
            "photo_profile": student.user.photo_profile,
            "color": "green",
            "error": False,
            "shift": "",
            "conflicts": []
        }

        # Check each time slot against student's schedule
        for time_slot in time_table:
            slot_start = time_slot.start_time.time() if isinstance(time_slot.start_time,
                                                                   datetime) else time_slot.start_time
            slot_end = time_slot.end_time.time() if isinstance(time_slot.end_time, datetime) else time_slot.end_time

            for schedule in student.time_table:
                if schedule.week_id == time_slot.week_id:
                    schedule_start = schedule.start_time.time() if isinstance(schedule.start_time,
                                                                              datetime) else schedule.start_time
                    schedule_end = schedule.end_time.time() if isinstance(schedule.end_time,
                                                                          datetime) else schedule.end_time

                    # Check for overlap
                    if (schedule_start <= slot_start < schedule_end or
                            schedule_start < slot_end <= schedule_end or
                            (slot_start <= schedule_start and slot_end >= schedule_end)):
                        conflict_msg = (
                            f"{schedule.week.name} da soat: '{schedule_start.strftime('%H:%M')} dan "
                            f"{schedule_end.strftime('%H:%M')}' gacha {schedule.group.name} da darsi bor."
                        )
                        info["conflicts"].append(conflict_msg)
                        info["color"] = "red"
                        info["error"] = True

        if info["conflicts"]:
            info["shift"] = info["conflicts"][0]

        student_errors.append(info)

    filtered_students = remove_items_create_group(student_errors)

    return jsonify({
        "data": filtered_students,
        "success": True
    })


@group_create_bp.route(f'/move_group/<int:new_group_id>/<int:old_group_id>', methods=['POST'])
@jwt_required()
def move_group(new_group_id, old_group_id):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    students = get_json_field('checkedStudents')
    reason = get_json_field('reason')
    student_list = []
    for st in students:
        if st['id'] not in student_list:
            student_list.append(st['id'])

    new_group = Groups.query.filter(Groups.id == new_group_id).first()
    old_group = Groups.query.filter(Groups.id == old_group_id).first()

    students_checked = db.session.query(Students).join(Students.user).options(
        contains_eager(Students.user)).filter(Users.id.in_([st_id for st_id in student_list])).all()
    for st in students_checked:
        db.session.execute(
            delete(student_group).where(
                student_group.c.group_id == old_group.id,
                student_group.c.student_id == st.id
            )
        )
        db.session.commit()
        st.group.append(new_group)
        StudentHistoryGroups.query.filter(StudentHistoryGroups.group_id == old_group.id,
                                          StudentHistoryGroups.student_id == st.id,
                                          StudentHistoryGroups.teacher_id == old_group.teacher_id).update(
            {'left_day': calendar_day.date,
             "reason": reason})
        db.session.commit()
        group_history = StudentHistoryGroups(teacher_id=new_group.teacher_id, student_id=st.id, group_id=new_group.id,
                                             joined_day=calendar_day.date)
        db.session.add(group_history)
        db.session.commit()
    db.session.commit()
    if len(student_list) > 1:
        return jsonify({
            "success": True,
            "msg": "O'quvchilar yangi guruhga qo'shilishdi"
        })
    else:
        return jsonify({
            "success": True,
            "msg": "O'quvchi yangi guruhga qo'shildi"
        })


@group_create_bp.route(f'/filtered_groups/<int:group_id>')
@jwt_required()
def filtered_groups(group_id):
    group = Groups.query.filter(Groups.id == group_id).first()
    groups = Groups.query.filter(Groups.location_id == group.location_id,
                                 Groups.id != group.id,
                                 Groups.teacher_id != None, Groups.time_table != None).filter(
        or_(Groups.deleted == None, Groups.deleted == False)).order_by('id').all()
    list_group = []
    for gr in groups:
        if gr.status:
            status = "True"
        else:
            status = "False"
        info = {
            "id": gr.id,
            "name": gr.name.title(),
            "teacherID": gr.teacher_id,
            "subjects": gr.subject.name.title(),
            "payment": gr.price,
            "typeOfCourse": gr.course_type.name,
            "studentsLength": len(gr.student),
            "status": status,
        }
        teacher = Teachers.query.filter(Teachers.id == gr.teacher_id).first()

        info['teacherName'] = teacher.user.name.title()
        info['teacherSurname'] = teacher.user.surname.title()
        list_group.append(info)
    return jsonify({
        "groups": list_group
    })


@group_create_bp.route(f'/filtered_groups2/<int:location_id>')
# @jwt_required()
def filtered_groups2(location_id):
    groups = Groups.query.filter(Groups.location_id == location_id,

                                 Groups.teacher_id != None, Groups.time_table != None).filter(
        or_(Groups.deleted == None, Groups.deleted == False)).order_by('id').all()
    list_group = []
    for gr in groups:
        if gr.status:
            status = "True"
        else:
            status = "False"
        info = {
            "id": gr.id,
            "name": gr.name.title(),
            "teacherID": gr.teacher_id,
            "subjects": gr.subject.name.title(),
            "payment": gr.price,
            "typeOfCourse": gr.course_type.name,
            "studentsLength": len(gr.student),
            "status": status,
        }
        teacher = Teachers.query.filter(Teachers.id == gr.teacher_id).first()

        info['teacherName'] = teacher.user.name.title()
        info['teacherSurname'] = teacher.user.surname.title()
        list_group.append(info)
    return jsonify({
        "groups": list_group
    })


@group_create_bp.route(f'/moving_students/<int:old_id>/<int:new_id>')
def moving_students(old_id, new_id):
    # Get both groups
    old_group = Groups.query.filter(Groups.id == old_id).first()
    new_group = Groups.query.filter(Groups.id == new_id).first()

    if not old_group or not new_group:
        return jsonify({"success": False, "error": "Group not found"}), 404

    # Get role once
    role = Roles.query.filter(Roles.type_role == "student").first()

    # Get new group's time_table with eager loading
    time_table = db.session.query(Group_Room_Week).options(
        joinedload(Group_Room_Week.week)
    ).filter(
        Group_Room_Week.group_id == new_group.id
    ).all()

    if not time_table:
        return jsonify({"students": [], "success": True})

    # Get all students from old group with their schedules in ONE query
    students = db.session.query(Students).join(
        Students.user
    ).outerjoin(
        Students.time_table
    ).options(
        contains_eager(Students.user).joinedload(Users.language),
        contains_eager(Students.user).joinedload(Users.day),
        contains_eager(Students.time_table).joinedload(Group_Room_Week.week),
        contains_eager(Students.time_table).joinedload(Group_Room_Week.group),
        joinedload(Students.subject)
    ).join(Students.group).filter(
        Groups.id == old_group.id
    ).all()

    student_errors = []

    # Check conflicts for each student (in-memory)
    for student in students:
        info = {
            "id": student.user.id,
            "name": student.user.name.title(),
            "surname": student.user.surname.title(),
            "username": student.user.username,
            "language": student.user.language.name,
            "age": student.user.age,
            "reg_date": student.user.day.date.strftime("%Y-%m-%d"),
            "comment": student.user.comment,
            'money': student.user.balance,
            "role": role.role,
            "subjects": [subject.name for subject in student.subject],
            "photo_profile": student.user.photo_profile,
            "color": "green",
            "error": False,
            "shift": "",
            "conflicts": []
        }

        # Check each time slot in new group against student's existing schedule
        for new_time in time_table:
            new_start = new_time.start_time.time() if isinstance(new_time.start_time, datetime) else new_time.start_time
            new_end = new_time.end_time.time() if isinstance(new_time.end_time, datetime) else new_time.end_time

            # Check student's existing schedule for conflicts
            for schedule in student.time_table:
                # Skip if it's from the old group (they're leaving that group)
                if (schedule.week_id == new_time.week_id and
                        schedule.group_id != old_group.id):

                    schedule_start = schedule.start_time.time() if isinstance(schedule.start_time,
                                                                              datetime) else schedule.start_time
                    schedule_end = schedule.end_time.time() if isinstance(schedule.end_time,
                                                                          datetime) else schedule.end_time

                    # Check for time overlap
                    if (schedule_start <= new_start < schedule_end or
                            schedule_start < new_end <= schedule_end or
                            (new_start <= schedule_start and new_end >= schedule_end)):
                        conflict_msg = (
                            f"{schedule.week.name} da soat: '{schedule_start.strftime('%H:%M')} dan "
                            f"{schedule_end.strftime('%H:%M')}' gacha {schedule.group.name} da darsi bor."
                        )
                        info["conflicts"].append(conflict_msg)
                        info["color"] = "red"
                        info["error"] = True

        # Set shift to first conflict if any
        if info["conflicts"]:
            info["shift"] = info["conflicts"][0]

        student_errors.append(info)

    filtered_students = remove_items_create_group(student_errors)

    return jsonify({
        "students": filtered_students,
        "success": True
    })


@group_create_bp.route(f'/move_group_time/<int:old_group_id>/<int:new_group_id>', methods=['POST'])
@jwt_required()
def move_group_time(old_group_id, new_group_id):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    students = get_json_field('checkedStudents')
    reason = get_json_field('reason')
    student_list = []

    for st in students:
        if st['id'] not in student_list:
            student_list.append(st['id'])

    new_group = Groups.query.filter(Groups.id == new_group_id).first()
    old_group = Groups.query.filter(Groups.id == old_group_id).first()

    students_checked = db.session.query(Students).join(Students.user).options(
        contains_eager(Students.user)).filter(Users.id.in_([st_id for st_id in student_list])).all()

    old_time_table = Group_Room_Week.query.filter(Group_Room_Week.group_id == old_group.id).all()
    new_time_table = Group_Room_Week.query.filter(Group_Room_Week.group_id == new_group.id).all()
    for st in students_checked:
        db.session.execute(
            delete(student_group).where(
                student_group.c.group_id == old_group.id,
                student_group.c.student_id == st.id
            )
        )
        db.session.commit()
        st.group.append(new_group)
        StudentHistoryGroups.query.filter(StudentHistoryGroups.group_id == old_group.id,
                                          StudentHistoryGroups.student_id == st.id,
                                          StudentHistoryGroups.teacher_id == old_group.teacher_id).update(
            {'left_day': calendar_day.date,
             "reason": reason})

        group_history = StudentHistoryGroups(teacher_id=new_group.teacher_id, student_id=st.id, group_id=new_group.id,
                                             joined_day=calendar_day.date)
        db.session.add(group_history)
        for time in old_time_table:
            if time in st.time_table:
                st.time_table.remove(time)
        for time in new_time_table:
            if time in st.time_table:
                st.time_table.append(time)
    db.session.commit()
    if len(student_list) > 1:
        return jsonify({
            "success": True,
            "msg": "O'quvchilar yangi guruhga qo'shilishdi"
        })
    else:
        return jsonify({
            "success": True,
            "msg": "O'quvchi yangi guruhga qo'shildi"
        })


@group_create_bp.route(f'/delete_student', methods=['POST'])
@jwt_required()
def delete_student():
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    type_delete = get_json_field('typeLocation')
    student_id = int(get_json_field('student_id'))
    student = Students.query.filter(Students.user_id == student_id).first()
    if type_delete == "deletedStudents":
        reason = get_json_field('typeReason')
        groupId = int(get_json_field('groupId'))

        group = Groups.query.filter(Groups.id == groupId).first()
        if reason == "Boshqa":
            reason = get_json_field('otherReason')
            group_reason = GroupReason.query.filter(GroupReason.reason == "Boshqa").first()
        else:
            group_reason = GroupReason.query.filter(GroupReason.reason == reason).first()
        add = DeletedStudents(student_id=student.id, group_id=group.id, reason=reason, teacher_id=group.teacher_id,
                              calendar_day=calendar_day.id, reason_id=group_reason.id)
        db.session.add(add)
        db.session.commit()
        db.session.execute(
            delete(student_group).where(
                student_group.c.group_id == group.id,
                student_group.c.student_id == student.id
            )
        )
        db.session.commit()
        db.session.commit()
        time_table = Group_Room_Week.query.filter(Group_Room_Week.group_id == group.id).all()
        for time in time_table:
            if time in student.time_table:
                student.time_table.remove(time)
                db.session.commit()
        teacher_get = Teachers.query.filter(Teachers.id == group.teacher_id).first()
        deleted_students_total = DeletedStudents.query.filter(
            DeletedStudents.teacher_id == teacher_get.id).join(DeletedStudents.day).filter(
            extract("month", CalendarDay.date) == int(calendar_month.date.strftime("%m")),
            extract("year", CalendarDay.date) == int(calendar_month.date.strftime("%Y"))).count()
        deleted_students_list = DeletedStudents.query.filter(DeletedStudents.teacher_id == teacher_get.id,
                                                             DeletedStudents.reason_id == group_reason.id,
                                                             ).join(DeletedStudents.day).filter(
            extract("month", CalendarDay.date) == int(calendar_month.date.strftime("%m")),
            extract("year", CalendarDay.date) == int(calendar_month.date.strftime("%Y"))).count()
        if deleted_students_total:
            result = round((deleted_students_list / deleted_students_total) * 100)
            teacher_statistics = TeacherGroupStatistics.query.filter(
                TeacherGroupStatistics.reason_id == group_reason.id,
                TeacherGroupStatistics.calendar_month == calendar_month.id,
                TeacherGroupStatistics.calendar_year == calendar_year.id,
                TeacherGroupStatistics.teacher_id == teacher_get.id).first()
            if not teacher_statistics:
                teacher_statistics = TeacherGroupStatistics(
                    reason_id=group_reason.id,
                    calendar_month=calendar_month.id,
                    calendar_year=calendar_year.id,
                    percentage=result,
                    number_students=deleted_students_list,
                    teacher_id=teacher_get.id)
                teacher_statistics.add()
            else:
                teacher_statistics.number_students = deleted_students_list
                teacher_statistics.percentage = result
                db.session.commit()
    elif type_delete == "newStudents":
        groupId = int(request.get_json()['groupId'])

        group = Groups.query.filter(Groups.id == groupId).first()
        subject = Subjects.query.filter(Subjects.id == group.subject_id).first()
        student.subject.append(subject)
        db.session.commit()

        db.session.execute(
            delete(student_group).where(
                student_group.c.group_id == group.id,
                student_group.c.student_id == student.id
            )
        )
        db.session.commit()
        time_table = Group_Room_Week.query.filter(Group_Room_Week.group_id == group.id).all()
        for time in time_table:
            if time in student.time_table:
                student.time_table.remove(time)
                db.session.commit()
    else:
        reason = request.get_json()['otherReason']
        student.user.comment = reason
        add = RegisterDeletedStudents(student_id=student.id, reason=reason, calendar_day=calendar_day.id)
        db.session.add(add)
        db.session.commit()

    if type_delete == "newStudents" or type_delete == "deletedStudents":
        return jsonify({
            "success": True,
            "msg": "Student guruhdan o'chirildi"
        })
    else:
        return jsonify({
            "success": True,
            "msg": "Student ro'yxatdan o'chirildi"
        })


@group_create_bp.route(f'/delete_asistent_group/<asistent_id>/<group_id>', methods=['DELETE'])
@jwt_required()
def delete_asistent_group(asistent_id, group_id):
    assistent = Assistent.query.filter(Assistent.id == asistent_id).first()
    group = Groups.query.filter(Groups.id == group_id).first()
    time_tables = Group_Room_Week.query.filter(Group_Room_Week.group_id == group.id).all()
    for time in time_tables:
        if time in assistent.time_table:
            assistent.time_table.remove(time)
            db.session.commit()
    if group in assistent.groups:
        assistent.groups.remove(group)
        db.session.commit()
    return jsonify({
        "success": True,
        "msg": "Assistent guruhdan o'chirildi"
    })
