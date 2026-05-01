from backend.models.models import Teachers, Group_Room_Week, Students, Groups, Subjects, Locations, Roles, \
    EducationLanguage, CourseTypes, Rooms, Week, db, time_table_student, time_table_teacher, student_group, Users, \
    Assistent
from sqlalchemy import desc, and_, or_
from sqlalchemy.orm import contains_eager, joinedload
from flask_jwt_extended import jwt_required
from datetime import datetime
from pprint import pprint
from backend.functions.utils import get_json_field, remove_items_create_group, api, find_calendar_date
from flask import Blueprint, jsonify, request
from sqlalchemy import delete

group_change_bp = Blueprint('group_change', __name__)


# from datetime import datetime


@group_change_bp.route(f'/change_group_info/<int:group_id>', methods=['POST'])
@jwt_required()
def change_group_info(group_id):
    name = get_json_field('name')
    teacher_salary = int(get_json_field('teacherQuota'))
    price = int(get_json_field('groupCost'))
    teacher_id = int(get_json_field('teacher'))
    language = get_json_field('eduLang')
    course_type = get_json_field('courseType')
    status = get_json_field('status')
    if 'assistentSalary' in request.get_json():
        assistent_salary = int(get_json_field('assistentSalary'))
    else:
        assistent_salary = None
    level_id = None

    if 'level_id' in request.get_json():
        level_id = get_json_field('level_id')

    if level_id == {}:
        level_id = None
    teacher = Teachers.query.filter(Teachers.user_id == teacher_id).first()
    language = EducationLanguage.query.filter(EducationLanguage.id == language).first()
    course_type = CourseTypes.query.filter(CourseTypes.id == course_type).first()
    group = Groups.query.filter(Groups.id == group_id).first()
    old_teacher = Teachers.query.filter(Teachers.id == group.teacher_id).first()

    Groups.query.filter(Groups.id == group_id).update({
        "name": name,
        "teacher_salary": teacher_salary,
        "price": price,
        "teacher_id": teacher.id,
        "education_language": language.id,
        "course_type_id": course_type.id,
        "status": status,
        "level_id": level_id,
        "assistent_salary": assistent_salary
    })
    if old_teacher.id != teacher.id:
        if group in old_teacher.group:
            old_teacher.group.remove(group)
            db.session.commit()
        teacher.group.append(group)
    db.session.commit()

    return jsonify({
        "success": True,
        "msg": "Guruh ma'lumotlari o'zgartirildi"
    })


@group_change_bp.route(f'/add_teacher_group/<int:teacher_id>/<int:group_id>')
@jwt_required()
def add_teacher_group(teacher_id, group_id):
    group = Groups.query.filter(Groups.id == group_id).first()
    new_teacher = Teachers.query.filter(Teachers.user_id == teacher_id).first()
    old_teacher = Teachers.query.filter(Teachers.id == group.teacher_id).first()
    time_table = Group_Room_Week.query.filter(Group_Room_Week.group_id == group_id).all()
    asistent = group.assistent
    if group in old_teacher.group:
        old_teacher.group.remove(group)
        db.session.commit()
    if asistent:
        if group in asistent.groups:
            asistent.groups.remove(group)
            db.session.commit()
    if group not in new_teacher.group:
        new_teacher.group.append(group)
        db.session.commit()
    for time in time_table:
        if time not in new_teacher.time_table:
            new_teacher.time_table.append(time)
            db.session.commit()
        if time in old_teacher.time_table:
            old_teacher.time_table.remove(time)
            db.session.commit()
        if asistent:
            if time in asistent.time_table:
                asistent.time_table.remove(time)
                db.session.commit()
    Groups.query.filter(Groups.id == group_id).update({
        "teacher_id": new_teacher.id
    })
    db.session.commit()
    return jsonify({
        "msg": "O'qtuvchi o'zgartirildi",
        "success": True
    })


@group_change_bp.route(f'/add_assistent_group/<int:assistent_id>/<int:group_id>')
@jwt_required()
def add_assistent_group(assistent_id, group_id):
    group = Groups.query.filter(Groups.id == group_id).first()
    new_assistent = Assistent.query.filter(Assistent.user_id == assistent_id).first()
    old_assistent = Assistent.query.filter(Assistent.id == group.assistent_id).first()
    time_table = Group_Room_Week.query.filter(Group_Room_Week.group_id == group_id).all()
    if old_assistent:
        if group in old_assistent.groups:
            old_assistent.groups.remove(group)
            db.session.commit()

    if group not in new_assistent.groups:
        new_assistent.groups.append(group)
        db.session.commit()
    for time in time_table:
        if time not in new_assistent.time_table:
            new_assistent.time_table.append(time)
            db.session.commit()
        if old_assistent:
            if time in old_assistent.time_table:
                old_assistent.time_table.remove(time)
                db.session.commit()
    Groups.query.filter(Groups.id == group_id).update({
        "assistent_id": new_assistent.id
    })
    db.session.commit()
    return jsonify({
        "msg": "Assistent o'zgartirildi",
        "success": True
    })


@group_change_bp.route(f'/delete_group/<int:group_id>')
@jwt_required()
def delete_group(group_id):
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    group = Groups.query.filter(Groups.id == group_id).first()
    assistent = group.assistent
    Groups.query.filter(Groups.id == group_id).update({"deleted": True, "calendar_day": calendar_day.id})
    subject = Subjects.query.filter(Subjects.id == group.subject_id).first()
    db.session.commit()
    teacher = Teachers.query.filter(Teachers.id == group.teacher_id).first()
    stduents = db.session.query(Students).join(Students.group).options(contains_eager(Students.group)).filter(
        Groups.id == group.id).all()
    time_table = Group_Room_Week.query.filter(Group_Room_Week.group_id == group.id).all()
    for st in stduents:
        db.session.execute(
            delete(student_group).where(
                student_group.c.group_id == group.id,
                student_group.c.student_id == st.id
            )
        )
        db.session.commit()
        st.subject.append(subject)
        db.session.commit()
        for time in time_table:
            if time in st.time_table:
                st.time_table.remove(time)
                db.session.commit()
    for time in time_table:
        if time in teacher.time_table:
            teacher.time_table.remove(time)
            db.session.commit()
        if assistent:
            if time in assistent.time_table:
                assistent.time_table.remove(time)
                db.session.commit()
    if group in teacher.group:
        teacher.group.remove(group)
        db.session.commit()
    if assistent:
        if group in assistent.groups:
            assistent.groups.remove(group)
            db.session.commit()
    for time in time_table:
        Group_Room_Week.query.filter(Group_Room_Week.id == time.id).delete()
        db.session.commit()
    return jsonify({
        "success": True,
        "msg": "Guruh o'chirildi"
    })


@group_change_bp.route(f'/check_time_group/<int:group_id>', methods=['POST'])
@jwt_required()
def check_time_group(group_id):
    # Get group info
    group = Groups.query.filter(Groups.id == group_id).first()
    if not group:
        return jsonify({"success": False, "error": "Group not found"}), 404

    lessons = get_json_field('lessons')

    # Get role once
    role_student = Roles.query.filter(Roles.type_role == "student").first()

    # Get teacher with their schedule in ONE query
    teacher = db.session.query(Teachers).outerjoin(
        Teachers.time_table
    ).options(
        joinedload(Teachers.user),
        contains_eager(Teachers.time_table).joinedload(Group_Room_Week.week),
        contains_eager(Teachers.time_table).joinedload(Group_Room_Week.group),
        contains_eager(Teachers.time_table).joinedload(Group_Room_Week.room)
    ).filter(
        Teachers.id == group.teacher_id
    ).first()

    # Get all students in this group with their schedules in ONE query
    students = db.session.query(Students).join(
        Students.user
    ).outerjoin(
        Students.time_table
    ).options(
        contains_eager(Students.user).joinedload(Users.language),
        contains_eager(Students.user).joinedload(Users.day),
        contains_eager(Students.time_table).joinedload(Group_Room_Week.week),
        contains_eager(Students.time_table).joinedload(Group_Room_Week.group),
        contains_eager(Students.time_table).joinedload(Group_Room_Week.room),
        joinedload(Students.subject)
    ).join(Students.group).filter(
        Groups.id == group_id
    ).all()

    # Get all potential room conflicts for all lessons at once
    week_ids = [lesson['selectedDay'].get('id') for lesson in lessons]
    room_ids = [lesson['selectedRoom'].get('id') for lesson in lessons]

    all_room_schedules = db.session.query(Group_Room_Week).options(
        joinedload(Group_Room_Week.week),
        joinedload(Group_Room_Week.room),
        joinedload(Group_Room_Week.group)
    ).filter(
        Group_Room_Week.week_id.in_(week_ids),
        Group_Room_Week.room_id.in_(room_ids),
        Group_Room_Week.group_id != group_id
    ).all()

    # Process conflicts
    gr_errors = []
    teacher_errors = []
    student_errors = []

    for lesson in lessons:
        start_time = datetime.strptime(lesson['startTime'], "%H:%M").time()
        end_time = datetime.strptime(lesson['endTime'], "%H:%M").time()
        week_id = lesson['selectedDay'].get('id')
        room_id = lesson['selectedRoom'].get('id')

        # Check teacher conflicts (in-memory)
        conflicting_schedules = []
        for schedule in teacher.time_table:
            if (schedule.week_id == week_id and
                    schedule.location_id == group.location_id and
                    schedule.group_id != group_id):

                schedule_start = schedule.start_time.time() if isinstance(schedule.start_time,
                                                                          datetime) else schedule.start_time
                schedule_end = schedule.end_time.time() if isinstance(schedule.end_time,
                                                                      datetime) else schedule.end_time

                if check_time_overlap(start_time, end_time, schedule_start, schedule_end):
                    conflicting_schedules.append(schedule)

        if len(conflicting_schedules) >= 2:
            s = conflicting_schedules[0]
            s_start = s.start_time.time() if isinstance(s.start_time, datetime) else s.start_time
            s_end = s.end_time.time() if isinstance(s.end_time, datetime) else s.end_time
            teacher_errors.append(
                f"{s.room.name} da soat: '{s_start.strftime('%H:%M')} - "
                f"{s_end.strftime('%H:%M')}' da allaqachon 2 ta dars bor"
            )
        elif len(conflicting_schedules) == 1:
            s = conflicting_schedules[0]
            if not s.group.assistent:
                s_start = s.start_time.time() if isinstance(s.start_time, datetime) else s.start_time
                s_end = s.end_time.time() if isinstance(s.end_time, datetime) else s.end_time
                teacher_errors.append(
                    f"{s.room.name} da soat: '{s_start.strftime('%H:%M')} - "
                    f"{s_end.strftime('%H:%M')}' da {s.group.name} ni darsi bor"
                )

        # Check room conflicts (in-memory)
        for schedule in all_room_schedules:
            if schedule.week_id == week_id and schedule.room_id == room_id:
                if schedule.group.teacher_id == group.teacher_id:
                    continue  # same teacher can share a room across their own groups
                schedule_start = schedule.start_time.time() if isinstance(schedule.start_time,
                                                                          datetime) else schedule.start_time
                schedule_end = schedule.end_time.time() if isinstance(schedule.end_time,
                                                                      datetime) else schedule.end_time

                if check_time_overlap(start_time, end_time, schedule_start, schedule_end):
                    gr_error = (
                        f"{schedule.room.name} da soat: '{schedule_start.strftime('%H:%M')} - "
                        f"{schedule_end.strftime('%H:%M')}' da {schedule.group.name} ni darsi bor"
                    )
                    gr_errors.append(gr_error)
                    break

    # Check student conflicts (in-memory)
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
            "role": role_student.role,
            "subjects": [subject.name for subject in student.subject],
            "photo_profile": student.user.photo_profile,
            "color": "green",
            "error": False,
            "shift": "",
            "conflicts": []
        }

        # Check each lesson time against student's schedule
        for lesson in lessons:
            start_time = datetime.strptime(lesson['startTime'], "%H:%M").time()
            end_time = datetime.strptime(lesson['endTime'], "%H:%M").time()
            week_id = lesson['selectedDay'].get('id')

            for schedule in student.time_table:
                if schedule.week_id == week_id and schedule.group_id != group_id:
                    schedule_start = schedule.start_time.time() if isinstance(schedule.start_time,
                                                                              datetime) else schedule.start_time
                    schedule_end = schedule.end_time.time() if isinstance(schedule.end_time,
                                                                          datetime) else schedule.end_time

                    if check_time_overlap(start_time, end_time, schedule_start, schedule_end):
                        conflict_msg = (
                            f"{schedule.week.name} da soat: '{schedule_start.strftime('%H:%M')} dan "
                            f"{schedule_end.strftime('%H:%M')}' gacha {schedule.group.name} da darsi bor"
                        )
                        info["conflicts"].append(conflict_msg)
                        info["color"] = "red"
                        info["error"] = True

        if info["conflicts"]:
            info["shift"] = info["conflicts"][0]

        student_errors.append(info)

    filtered_students = remove_items_create_group(student_errors)

    return jsonify({
        "success": True,
        "students": filtered_students,
        "group": gr_errors[0] if gr_errors else '',
        "teacher": teacher_errors[0] if teacher_errors else ''
    })


def check_time_overlap(start1, end1, start2, end2):
    """Check if two time ranges overlap"""
    return (start1 <= start2 < end1 or
            start1 < end2 <= end1 or
            (start2 <= start1 and end2 >= end1))


@group_change_bp.route(f'/change_time_group/<int:group_id>', methods=["POST"])
@jwt_required()
def change_time_group(group_id):
    lessons = get_json_field('lessons')

    group = Groups.query.filter(Groups.id == group_id).first()
    students = db.session.query(Students).join(Students.group).options(
        contains_eager(Students.group)
    ).filter(Groups.id == group_id).all()
    teacher = Teachers.query.filter(Teachers.id == group.teacher_id).first()
    group_time_table_get = Group_Room_Week.query.filter(Group_Room_Week.group_id == group_id).all()

    # Remove from association tables using synchronize_session=False
    for time_get in group_time_table_get:
        db.session.execute(
            delete(time_table_student).where(
                time_table_student.c.group_room_week == time_get.id
            )
        )
        db.session.execute(
            delete(time_table_teacher).where(
                time_table_teacher.c.group_room_week == time_get.id
            )
        )

    db.session.flush()  # flush association deletes before deleting parent rows

    # Now delete the Group_Room_Week rows
    for time_get in group_time_table_get:
        db.session.delete(time_get)

    db.session.commit()

    # Re-fetch students after commit
    students = db.session.query(Students).join(Students.group).options(
        contains_eager(Students.group)
    ).filter(Groups.id == group_id).all()

    for lesson in lessons:
        start_time = datetime.strptime(lesson['startTime'], "%H:%M")
        end_time = datetime.strptime(lesson['endTime'], "%H:%M")
        add = Group_Room_Week(
            week_id=lesson['selectedDay'].get('id'),
            room_id=lesson['selectedRoom'].get('id'),
            start_time=start_time,
            end_time=end_time,
            group_id=group_id,
            location_id=group.location_id
        )
        db.session.add(add)
        db.session.flush()  # get the ID before appending relationships

        for student in students:
            student.time_table.append(add)

        teacher.time_table.append(add)

    db.session.commit()

    return jsonify({
        "success": True,
        "msg": "Guruh dars vaqtlari o'zgartirildi"
    })


@group_change_bp.route(f'/check_teacher_time/<int:group_id>', methods=['GET'])
@jwt_required()
def check_teacher_time(group_id):
    # Get group info
    group = Groups.query.filter(Groups.id == group_id).first()
    if not group:
        return jsonify({"success": False, "error": "Group not found"}), 404

    # Get the group's schedule
    time_table_group = db.session.query(Group_Room_Week).options(
        joinedload(Group_Room_Week.week)
    ).filter(
        Group_Room_Week.group_id == group_id
    ).all()

    if not time_table_group:
        return jsonify({"success": True, "teachers": []}), 200

    # Get role once
    role_teacher = Roles.query.filter(Roles.type_role == "teacher").first()

    # Get all eligible teachers with their schedules in ONE query
    teachers = db.session.query(Teachers).join(
        Teachers.user
    ).join(
        Teachers.locations
    ).join(
        Teachers.subject
    ).outerjoin(
        Teachers.time_table
    ).options(
        contains_eager(Teachers.user).joinedload(Users.language),
        contains_eager(Teachers.user).joinedload(Users.day),
        contains_eager(Teachers.locations),
        contains_eager(Teachers.subject),
        contains_eager(Teachers.time_table).joinedload(Group_Room_Week.week),
        contains_eager(Teachers.time_table).joinedload(Group_Room_Week.group)
    ).filter(
        Locations.id == group.location_id,
        Teachers.id != group.teacher_id,
        Subjects.id == group.subject_id
    ).order_by(Teachers.id).all()

    teacher_errors = []

    for teacher in teachers:
        info = {
            "id": teacher.user.id,
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

        # Check if teacher has assistants
        teacher_has_assistant = bool(teacher.assistent and len(teacher.assistent) > 0)

        # Check conflicts against group's schedule (in-memory)
        for group_time in time_table_group:
            group_start = group_time.start_time.time() if isinstance(group_time.start_time,
                                                                     datetime) else group_time.start_time
            group_end = group_time.end_time.time() if isinstance(group_time.end_time, datetime) else group_time.end_time
            group_room_id = group_time.room_id

            # ✅ Find all conflicting lessons for this time slot
            conflicting_lessons = []

            for teacher_schedule in teacher.time_table:
                # Skip if it's the current group or different week/location
                if (teacher_schedule.group_id == group_id or
                        teacher_schedule.week_id != group_time.week_id or
                        teacher_schedule.location_id != group.location_id):
                    continue

                schedule_start = teacher_schedule.start_time.time() if isinstance(teacher_schedule.start_time,
                                                                                  datetime) else teacher_schedule.start_time
                schedule_end = teacher_schedule.end_time.time() if isinstance(teacher_schedule.end_time,
                                                                              datetime) else teacher_schedule.end_time

                # Check for time overlap
                has_time_overlap = (
                        schedule_start <= group_start < schedule_end or
                        schedule_start < group_end <= schedule_end or
                        (group_start <= schedule_start and group_end >= schedule_end)
                )

                if has_time_overlap:
                    conflicting_lessons.append(teacher_schedule)

            # ✅ Analyze conflicts
            if conflicting_lessons:
                # Check for same room conflict (always a conflict)
                same_room_conflict = any(schedule.room_id == group_room_id for schedule in conflicting_lessons)

                if same_room_conflict:
                    # Same room - always a conflict
                    same_room_schedule = next(s for s in conflicting_lessons if s.room_id == group_room_id)
                    schedule_start = same_room_schedule.start_time.time() if isinstance(same_room_schedule.start_time,
                                                                                        datetime) else same_room_schedule.start_time
                    schedule_end = same_room_schedule.end_time.time() if isinstance(same_room_schedule.end_time,
                                                                                    datetime) else same_room_schedule.end_time

                    conflict_msg = (
                        f"{same_room_schedule.week.name} da soat: '{schedule_start.strftime('%H:%M')} dan "
                        f"{schedule_end.strftime('%H:%M')}' gacha {same_room_schedule.group.name} da "
                        f"bir xil xonada ({same_room_schedule.room.name}) darsi bor"
                    )
                    info["conflicts"].append(conflict_msg)
                    info["color"] = "red"
                    info["error"] = True

                # Check for "too many lessons" conflict
                elif len(conflicting_lessons) >= 2:
                    # Already has 2 lessons at this time - can't add a 3rd
                    first_schedule = conflicting_lessons[0]
                    schedule_start = first_schedule.start_time.time() if isinstance(first_schedule.start_time,
                                                                                    datetime) else first_schedule.start_time
                    schedule_end = first_schedule.end_time.time() if isinstance(first_schedule.end_time,
                                                                                datetime) else first_schedule.end_time

                    conflict_msg = (
                        f"{first_schedule.week.name} da soat: '{schedule_start.strftime('%H:%M')} dan "
                        f"{schedule_end.strftime('%H:%M')}' gacha allaqachon 2 ta dars bor - "
                        f"maksimum 2 ta dars bir vaqtda"
                    )
                    info["conflicts"].append(conflict_msg)
                    info["color"] = "red"
                    info["error"] = True

                elif len(conflicting_lessons) == 1:
                    # Already has 1 lesson - can add 2nd only if has assistant and different room
                    if not teacher_has_assistant:
                        # No assistant - can't have 2 lessons at once
                        schedule = conflicting_lessons[0]
                        schedule_start = schedule.start_time.time() if isinstance(schedule.start_time,
                                                                                  datetime) else schedule.start_time
                        schedule_end = schedule.end_time.time() if isinstance(schedule.end_time,
                                                                              datetime) else schedule.end_time

                        conflict_msg = (
                            f"{schedule.week.name} da soat: '{schedule_start.strftime('%H:%M')} dan "
                            f"{schedule_end.strftime('%H:%M')}' gacha {schedule.group.name} da darsi bor "
                            f"(assistant yo'q)"
                        )
                        info["conflicts"].append(conflict_msg)
                        info["color"] = "red"
                        info["error"] = True
                    # else: Has assistant and different room - NO CONFLICT ✅

        # Set shift to first conflict if any
        if info["conflicts"]:
            info["shift"] = info["conflicts"][0]

        teacher_errors.append(info)

    filtered_teachers = remove_items_create_group(teacher_errors)

    return jsonify({
        "success": True,
        "teachers": filtered_teachers
    })


@group_change_bp.route(f'/delete_time_table/<int:time_id>')
@jwt_required()
def delete_time_table(time_id):
    time_table = Group_Room_Week.query.filter(Group_Room_Week.id == time_id).first()
    group = Groups.query.filter(Groups.id == time_table.group_id).first()
    students = db.session.query(Students).join(Students.group).options(contains_eager(Students.group)).filter(
        Groups.id == group.id).all()
    teacher = Teachers.query.filter(Teachers.id == group.teacher_id).first()
    if time_table in group.time_table:
        group.time_table.remove(time_table)
        db.session.commit()
    if time_table in teacher.time_table:
        teacher.time_table.remove(time_table)
        db.session.commit()
    for st in students:
        if time_table in st.time_table:
            st.time_table.remove(time_table)
            db.session.commit()
    room = Rooms.query.filter(Rooms.id == time_table.room_id).first()
    week_day = Week.query.filter(Week.id == time_table.week_id).first()
    if time_table in room.time_table:
        room.time_table.remove(time_table)
        db.session.commit()
    if time_table in week_day.time_table:
        week_day.time_table.remove(time_table)
        db.session.commit()
    db.session.delete(time_table)
    db.session.commit()
    return jsonify({
        "success": True,
        "msg": "Dars kuni o'chirildi"
    })


@group_change_bp.route(f'/check_time_assistent/<int:group_id>/', methods=['GET'])
@jwt_required()
def check_time_asistent_in_group(group_id):
    # Get group info
    group = Groups.query.filter(Groups.id == group_id).first()
    if not group:
        return jsonify({'error': 'Group topilmadi'}), 404

    teacher_id = group.teacher_id

    # Get the group's time table
    time_table_group = db.session.query(Group_Room_Week).options(
        joinedload(Group_Room_Week.week)
    ).filter(
        Group_Room_Week.group_id == group_id
    ).all()

    if not time_table_group:
        return jsonify({'error': 'Guruhda dars jadvali yo\'q'}), 404

    # Single query to get all assistants with their schedules
    assistents = db.session.query(Assistent).join(
        Assistent.user
    ).outerjoin(
        Assistent.time_table
    ).options(
        contains_eager(Assistent.user).joinedload(Users.language),
        contains_eager(Assistent.user).joinedload(Users.day),
        contains_eager(Assistent.user).joinedload(Users.role_info),
        contains_eager(Assistent.time_table).joinedload(Group_Room_Week.week),
        contains_eager(Assistent.time_table).joinedload(Group_Room_Week.group),
        joinedload(Assistent.subjects)
    ).filter(
        or_(Assistent.deleted == False, Assistent.deleted == None),
        Assistent.teacher_id == teacher_id,
        Users.location_id == group.location_id,
        Assistent.id != group.assistent_id
    ).all()

    if not assistents:
        return jsonify({'error': 'Assistent mavjud emas'})

    assistent_errors = []

    for assistent in assistents:
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
            "conflicts": []
        }

        # Check conflicts against group's time table
        for group_time in time_table_group:
            group_start = group_time.start_time.time() if isinstance(group_time.start_time,
                                                                     datetime) else group_time.start_time
            group_end = group_time.end_time.time() if isinstance(group_time.end_time, datetime) else group_time.end_time

            # Check conflicts in assistant's already-loaded time_table
            for schedule in assistent.time_table:
                if (schedule.week_id == group_time.week_id and
                        schedule.location_id == group.location_id and
                        schedule.group_id != group_id):  # Don't check against same group

                    schedule_start = schedule.start_time.time() if isinstance(schedule.start_time,
                                                                              datetime) else schedule.start_time
                    schedule_end = schedule.end_time.time() if isinstance(schedule.end_time,
                                                                          datetime) else schedule.end_time

                    # Check for time overlap
                    if (schedule_start <= group_start < schedule_end or
                            schedule_start < group_end <= schedule_end or
                            (group_start <= schedule_start and group_end >= schedule_end)):
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
