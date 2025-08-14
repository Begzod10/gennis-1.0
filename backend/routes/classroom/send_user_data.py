from app import app, request, jsonify, db
from backend.functions.utils import api
from backend.models.models import Users, Students, Teachers, Subjects, SubjectLevels
from backend.parent.models import Parent
from flask import Blueprint

classroom_basic_bp = Blueprint('classroom_basic', __name__)


@classroom_basic_bp.route(f'/send_user_data/<user_id>')
def send_user_data(user_id):
    user = Users.query.filter(Users.id == user_id).first()

    if user.student:
        get_user = Students.query.filter(Students.user_id == user_id).first()
    else:
        get_user = Teachers.query.filter(Teachers.user_id == user_id).first()
    print(get_user.convert_groups())
    return jsonify({"status": "true", "user": get_user.convert_groups()})


@classroom_basic_bp.route(f'/send_parent_data/<user_id>')
def send_parent_data(user_id):
    user = Users.query.filter(Users.id == user_id).first()

    if user.parent:
        get_user = Parent.query.filter(Parent.user_id == user_id).first()
    return jsonify({"status": "true", "user": get_user.convert_json()})


@classroom_basic_bp.route(f'/send_student_data/<user_id>')
def send_student_data(user_id):
    user = Users.query.filter(Users.id == user_id).first()

    return jsonify({"status": "true", "user": user.convert_json()})


@classroom_basic_bp.route(f'/subjects_add', methods=['POST'])
def subjects_add():
    subjects = request.get_json()['subjects']
    for sub in subjects:
        get_subject = Subjects.query.filter(Subjects.classroom_id == sub['id']).first()
        if not get_subject:
            get_subject = Subjects.query.filter(Subjects.name == sub['name']).first()
        if not get_subject:
            get_subject = Subjects(name=sub['name'], ball_number=2, classroom_id=sub['id'])
            get_subject.add()
        else:
            get_subject.disabled = sub['disabled']
            get_subject.classroom_id = sub['id']
            get_subject.name = sub['name']
            db.session.commit()
    return jsonify({"msg": "Fanlar o'zgartirildi"})


@classroom_basic_bp.route(f'/get_datas', methods=['POST'])
def get_datas():
    type_info = request.get_json()['type']
    if type_info == "subject":
        response = request.get_json()['subject']
        for res in response:
            get_subject = Subjects.query.filter(Subjects.classroom_id == res['id']).first()
            if not get_subject:
                get_subject = Subjects.query.filter(Subjects.name == res['name']).first()
            if not get_subject:
                get_subject = Subjects(name=res['name'], ball_number=2, classroom_id=res['id'])
                get_subject.add()
            else:

                get_subject.disabled = res['disabled']
                get_subject.classroom_id = res['id']
                get_subject.name = res['name']
                db.session.commit()
    else:
        response = request.get_json()['levels']
        for level in response:
            get_subject = Subjects.query.filter(Subjects.classroom_id == level['subject']['id']).first()
            if not get_subject:

                get_subject = Subjects.query.filter(Subjects.name == level['subject']['name']).first()

            elif not get_subject:
                get_subject = Subjects(name=level['subject']['name'], ball_number=2,
                                       classroom_id=level['subject']['id'])
                get_subject.add()
            else:
                get_subject.disabled = level['subject']['disabled']
                get_subject.classroom_id = level['subject']['id']
                get_subject.name = level['subject']['name']
                db.session.commit()
            get_level = SubjectLevels.query.filter(SubjectLevels.classroom_id == level['id'],
                                                   SubjectLevels.subject_id == get_subject.id).first()
            if not get_level:
                get_level = SubjectLevels.query.filter(SubjectLevels.name == level['name'],
                                                       SubjectLevels.subject_id == get_subject.id).first()

            if not get_level:
                get_level = SubjectLevels(name=level['name'], subject_id=get_subject.id, classroom_id=level['id'])
                get_level.add()
            else:
                get_level.disabled = level['disabled']
                get_level.classroom_id = level['id']
                get_level.name = level['name']
                db.session.commit()
    return jsonify({
        "msg": "Zo'r"
    })
