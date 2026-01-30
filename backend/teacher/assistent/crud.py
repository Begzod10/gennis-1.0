from flask import Blueprint
from flask import jsonify, request
from sqlalchemy import desc
from werkzeug.security import generate_password_hash
from flask_jwt_extended import jwt_required
from backend.functions.utils import check_exist_id
from backend.models.models import Users, Roles, PhoneList, db, Subjects, Teachers, Locations
from backend.teacher.assistent.models import Assistent

crud_assistent_bp = Blueprint('assistent', __name__)


@crud_assistent_bp.route('/crud/', methods=['POST'])
@crud_assistent_bp.route('/crud/<int:id>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@jwt_required()
def assistent_detail(id=None):
    role = Roles.query.filter(Roles.type_role == 'assistent').first()
    if not role:
        role = Roles(role='ass21s122s', type_role='assistent')
        role.add()
    if request.method == 'POST':
        data = request.json

        check_username = Users.query.filter(Users.username == data.get('username')).first()

        if check_username:
            return jsonify({'error': 'Username mavjud'})

        user_add = Users(
            user_id=check_exist_id(),
            role_id=role.id,
            username=data.get('username'),

            password=generate_password_hash('12345678'), name=data.get('name'),
            surname=data.get('surname'),
            born_day=data.get('birth_day')[8:10],
            born_month=data.get('birth_day')[5:7],
            born_year=data.get('birth_day')[0:4],
            location_id=data.get('location'),
            father_name=data.get('father_name'),
            address=data.get('address'),
            comment=data.get('comment'),
            education_language=data.get('language')
        )
        user_add.add()
        phone = PhoneList(user_id=user_add.id, phone=data.get('phone'))
        phone.add()

        new_assistent = Assistent(user_id=user_add.id, teacher_id=data['teacher'])
        new_assistent.add()
        db.session.flush()
        subject = Subjects.query.get(data['selectedSubjects'])
        if subject:
            new_assistent.subjects.append(subject)

        db.session.commit()

        return jsonify({'message': 'Assistent created successfully'}), 200

    if request.method == 'GET':
        user = Users.query.get_or_404(id)
        parent = Assistent.query.filter(Assistent.user_id == user.id).first()
        return jsonify(parent.convert_json())
    user = Users.query.get_or_404(id)
    assistent = Assistent.query.filter(Assistent.user_id == user.id).first()

    if request.method == 'PUT':

        data = request.json
        if 'name' in data:
            user.name = data['name']
        if 'surname' in data:
            user.surname = data['surname']
        if 'phone' in data:
            user.phone[0].phone = data['phone']
        if 'address' in data:
            user.address = data['address']

        if 'born_date' in data:
            user.born_day = data['born_date'][8:10]
            user.born_month = data['born_date'][5:7]
            user.born_year = data['born_date'][0:4]
        if 'username' in data:
            user.username = data['username']
        if 'teacher' in data:
            assistent.teacher_id = data['teacher']
        db.session.commit()
        return jsonify(assistent.convert_json())

    if request.method == 'DELETE':
        user.deleted = True
        db.session.commit()
        return jsonify({'message': 'Assistent deleted successfully'}), 200


@crud_assistent_bp.route('/get_list/<int:location_id>', defaults={'deleted': False}, methods=['GET'])
@crud_assistent_bp.route('/get_list/<int:location_id>/<deleted>', methods=['GET'])
@jwt_required()
def assistent_list(location_id, deleted):
    role = Roles.query.filter(Roles.type_role == 'assistent').first()
    if not role:
        role = Roles(role='ass21s122s', type_role='assistent')
        role.add()

    assistents = Assistent.query.join(Users).filter(Users.location_id == location_id, Users.deleted == deleted,
                                                    Users.role_id == role.id).order_by(desc(Assistent.id)).all()
    assistent_list = [assistent.convert_json() for assistent in assistents]
    return jsonify(assistent_list)


@crud_assistent_bp.route('/get_teacher/<int:subject_id>/<int:location_id>', methods=['GET'])
@jwt_required()
def get_teacher(subject_id, location_id):
    teachers = Teachers.query.join(
        Teachers.subject
    ).filter(
        Subjects.id == subject_id
    ).join(
        Teachers.locations
    ).filter(
        Locations.id == location_id,
        Teachers.deleted == None
    ).all()

    list_teachers = []
    for teach in teachers:
        info = {
            "id": teach.id,
            "name": teach.user.name.title(),
            "surname": teach.user.surname.title(),
        }
        list_teachers.append(info)

    return jsonify({
        "teachers": list_teachers,
    })
