def clone_group_info(group):
    group_info = {
        "id": group.id,
        "name": group.name,
        "teacher_salary": group.teacher_salary,
        "location": {
            "id": group.location.id,
            "name": group.location.name,
        },
        "status": group.status,
        "education_language": {
            "id": group.language.id,
            "name": group.language.name
        },
        "attendance_days": group.attendance_days,
        "price": group.price,
        "teacher_id": group.teacher_id,
        "subjects": {
            "id": group.subject.id,
            "name": group.subject.name,
            "ball_number": group.subject.ball_number
        },
        "course": {}
    }
    if group.level:
        level_info = {
            "id": group.level.id,
            "name": group.level.name
        }
        group_info['course'] = level_info
    return group_info