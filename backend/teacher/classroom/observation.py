from datetime import datetime

from flask import Blueprint

from app import jsonify, db, request
from backend.functions.filters import old_current_dates
from backend.functions.utils import find_calendar_date, iterate_models, get_json_field, filter_month_day
from backend.models.models import Users, Week, Groups, Group_Room_Week, \
    CalendarMonth, or_, CalendarDay
from backend.teacher.models import TeacherObservation, ObservationOptions, ObservationInfo, \
    TeacherObservationDay, Teachers

observetion_bp = Blueprint('observation', __name__)


@observetion_bp.route(f'/observe_info_classroom')
def observe_info_classroom():
    info = [
        {
            "title": "Teacher follows her or his lesson plan"
        },
        {
            "title": "Teacher is actively circulating in the room"
        },
        {
            "title": "Teacher uses feedback to encourage critical thinking"
        },
        {
            "title": "Students are collaborating with each other and engaged in"
        },
        {
            "title": "Teacher talking time is 1/3"
        },
        {
            "title": "Teacher uses a variety of media and resources for learning"
        },
        {
            "title": "Teacher uses different approach of method"
        },
        {
            "title": "Teacher has ready made materials for the lesson"
        },
        {
            "title": "Lesson objective is present and communicated to students"
        }
    ]
    for item in info:
        if not ObservationInfo.query.filter(ObservationInfo.title == item['title']).first():
            add_observation = ObservationInfo(**item)
            add_observation.add()

    options = [
        {
            "name": "Missing",
            "value": 1
        },
        {
            "name": "Done but poorly",
            "value": 2
        },
        {
            "name": "Acceptable",
            "value": 3
        },
        {
            "name": "Sample for others",
            "value": 4
        },
    ]
    for item in options:
        if not ObservationOptions.query.filter(ObservationOptions.name == item['name']).first():
            add_observation_options = ObservationOptions(**item)
            add_observation_options.add()
    observations = ObservationInfo.query.order_by(ObservationInfo.id).all()
    options = ObservationOptions.query.order_by(ObservationOptions.id).all()
    return jsonify({
        "observations": iterate_models(observations),
        "options": iterate_models(options)
    })


@observetion_bp.route(f'/groups_to_observe_classroom/<int:user_id>/', defaults={"location_id": None},
                      methods=['POST', 'GET'])
@observetion_bp.route(f'/groups_to_observe_classroom/<int:user_id>/<location_id>', methods=['POST', 'GET'])
def groups_to_observe_classroom(user_id, location_id):
    print(True)
    identity = user_id
    user = Users.query.filter(Users.id == identity).first()
    if type(location_id) == str:
        location_id = None
    if not location_id:

        location_id = user.location_id
    else:

        location_id = location_id
    teacher = Teachers.query.filter(Teachers.user_id == user.id).first()

    if request.method == "POST":
        date_year, date_month, date_day = filter_month_day()

        calendar_year, calendar_month, calendar_day = find_calendar_date(date_day=date_day, date_year=date_year,
                                                                         date_month=date_month)

        week_day_name = calendar_day.date.strftime("%A")
        get_week_day = Week.query.filter(Week.eng_name == week_day_name,
                                         Week.location_id == location_id).first()
    else:
        current_date = datetime.now()
        week_day_name = current_date.strftime("%A")

        get_week_day = Week.query.filter(Week.eng_name == week_day_name,
                                         Week.location_id == location_id).first()

    groups = Groups.query.join(Groups.time_table).filter(
        Group_Room_Week.week_id == get_week_day.id,
        Groups.status == True,
        Groups.location_id == user.location_id,
        Groups.teacher_id != teacher.id,
    ).filter(or_(Groups.deleted == False, Groups.deleted == None)).order_by(Groups.id).all()
    if request.method == "GET":
        return jsonify({
            "groups": iterate_models(groups, entire=True),
            "observation_tools": old_current_dates(observation=True)
        })
    else:
        return jsonify({
            "groups": iterate_models(groups, entire=True),
        })


@observetion_bp.route(f'/teacher_observe_classroom/<int:user_id>/<int:group_id>', methods=['POST', 'GET'])
def teacher_observe_classroom(user_id, group_id):
    identity = user_id
    user = Users.query.filter_by(id=identity).first()
    group = Groups.query.filter(Groups.id == group_id).first()
    if request.method == "POST":
        date_year, date_month, date_day = filter_month_day()

        calendar_year, calendar_month, calendar_day = find_calendar_date(date_day=date_day, date_year=date_year,
                                                                         date_month=date_month)
        teacher_observation_day = TeacherObservationDay.query.filter(
            TeacherObservationDay.teacher_id == group.teacher_id,
            TeacherObservationDay.calendar_day == calendar_day.id, TeacherObservationDay.group_id == group.id,
        ).first()
        if not teacher_observation_day:
            teacher_observation_day = TeacherObservationDay(teacher_id=group.teacher_id, group_id=group_id,
                                                            calendar_day=calendar_day.id,
                                                            calendar_month=calendar_month.id,
                                                            calendar_year=calendar_year.id, user_id=user.id)
            teacher_observation_day.add()
        result = 0
        for item in get_json_field('list'):
            info = {
                "observation_info_id": item.get('id'),
                "observation_options_id": item.get('value'),
                "comment": item.get('comment'),
                "observation_id": teacher_observation_day.id
            }

            observation_options = ObservationOptions.query.filter(ObservationOptions.id == item.get('value')).first()
            result += observation_options.value
            if not TeacherObservation.query.filter(TeacherObservation.observation_info_id == item.get('id'),
                                                   TeacherObservation.observation_id == teacher_observation_day.id
                                                   ).first():
                teacher_observation = TeacherObservation(**info)
                teacher_observation.add()
            else:
                TeacherObservation.query.filter(TeacherObservation.observation_info_id == item.get('id'),
                                                TeacherObservation.observation_id == teacher_observation_day.id).update(
                    {
                        "observation_options_id": item.get('value'),
                        "comment": item.get('comment')
                    })
                db.session.commit()
        observation_infos = ObservationInfo.query.count()
        result = round(result / observation_infos)
        teacher_observation_day.average = result
        db.session.commit()
        return jsonify({
            "msg": "Teacher has been observed",
            "success": True
        })
    else:
        return jsonify({
            "observation_tools": old_current_dates(group_id=group_id, observation=True)
        })


@observetion_bp.route(f'/observed_group_classroom/<int:group_id>/', defaults={"date": None})
@observetion_bp.route(f'/observed_group_classroom/<int:group_id>/<date>')
def observed_group_classroom(group_id, date):
    group = Groups.query.filter(Groups.id == group_id).first()

    days_list = []
    month_list = []
    years_list = []
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    if date and date != "None":
        calendar_month = datetime.strptime(date, "%Y-%m")
        calendar_month = CalendarMonth.query.filter(CalendarMonth.date == calendar_month).first()
    else:
        calendar_month = calendar_month
    teacher_observation_all = TeacherObservationDay.query.filter(TeacherObservationDay.teacher_id == group.teacher_id,

                                                                 TeacherObservationDay.group_id == group_id).order_by(
        TeacherObservationDay.id).all()
    teacher_observation = TeacherObservationDay.query.filter(TeacherObservationDay.teacher_id == group.teacher_id,
                                                             TeacherObservationDay.calendar_month == calendar_month.id,
                                                             TeacherObservationDay.group_id == group_id).order_by(
        TeacherObservationDay.id).all()

    for data in teacher_observation:
        days_list.append(data.day.date.strftime("%d"))
    days_list.sort()

    for plan in teacher_observation_all:
        if plan.calendar_month:
            month_list.append(plan.month.date.strftime("%m"))
            years_list.append(plan.month.date.strftime("%Y"))

    month_list = list(dict.fromkeys(month_list))
    years_list = list(dict.fromkeys(years_list))
    month_list.sort()
    years_list.sort()
    if len(month_list) != 0:
        month = calendar_month.date.strftime("%m") if month_list[len(month_list) - 1] == calendar_month.date.strftime(
            "%m") else month_list[len(month_list) - 1]
    else:
        month = calendar_month.date.strftime("%m")
    return jsonify({
        "month_list": month_list,
        "years_list": years_list,
        "month": month,
        "year": calendar_month.date.strftime("%Y"),
        "days": days_list
    })


@observetion_bp.route(f'/observed_group_info_classroom/<int:group_id>', methods=["POST"])
def observed_group_info_classroom(group_id):
    day = get_json_field('day')
    month = get_json_field('month')
    year = get_json_field('year')
    print(day)
    date = datetime.strptime(year + "-" + month + "-" + day, "%Y-%m-%d")
    calendar_day = CalendarDay.query.filter(CalendarDay.date == date).first()
    observation_list = []
    observation_options = ObservationOptions.query.order_by(ObservationOptions.id).all()
    observation_infos = ObservationInfo.query.order_by(ObservationInfo.id).all()
    average = 0
    observer = {
        "name": "",
        "surname": ""
    }
    if calendar_day:
        teacher_observation_day = TeacherObservationDay.query.filter(
            TeacherObservationDay.calendar_day == calendar_day.id, TeacherObservationDay.group_id == group_id).first()
        average = teacher_observation_day.average
        observer['name'] = teacher_observation_day.user.name if teacher_observation_day else ""
        observer['surname'] = teacher_observation_day.user.surname if teacher_observation_day else ""
        for item in observation_infos:
            teacher_observations = TeacherObservation.query.filter(
                TeacherObservation.observation_id == teacher_observation_day.id,
                TeacherObservation.observation_info_id == item.id
            ).first()
            info = {
                "title": item.title,
                "values": [],
                "comment": teacher_observations.comment
            }

            for option in observation_options:
                teacher_observations = TeacherObservation.query.filter(
                    TeacherObservation.observation_id == teacher_observation_day.id,
                    TeacherObservation.observation_options_id == option.id,
                    TeacherObservation.observation_info_id == item.id
                ).first()
                info["values"].append({
                    "name": option.name,
                    "value": teacher_observations.observation_option.value if teacher_observations and teacher_observations.observation_option else "",
                })
            observation_list.append(info)
    return jsonify({
        "info": observation_list,
        "observation_options": iterate_models(observation_options),
        "average": average,
        "observer": observer
    })
