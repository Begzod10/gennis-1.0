from flask import jsonify, request
from backend.student.models import Students
from backend.parent.models import Parent
from backend.models.models import Users, Roles, PhoneList, db
from werkzeug.security import generate_password_hash
from backend.functions.utils import check_exist_id
from flask import Blueprint
import pprint

crud_parent_bp = Blueprint('parent_crud', __name__)


@crud_parent_bp.route('/crud/', methods=['POST'])
@crud_parent_bp.route('/crud/<int:id>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def parent_detail(id=None):
    role = Roles.query.filter(Roles.type_role == 'parent').first()
    if not role:
        role = Roles(role='pa21s122s', type_role='parent')
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
            password=generate_password_hash('12345678'),
            name=data.get('name'),
            surname=data.get('surname'),
            born_day=data.get('birth_day')[8:10],
            born_month=data.get('birth_day')[5:7],
            born_year=data.get('birth_day')[0:4],
            location_id=data.get('location_id'),
            father_name=data.get('father_name'),
            address=data.get('address'),
        )
        user_add.add()
        phone = PhoneList(
            user_id=user_add.id,
            phone=data.get('phone')
        )
        phone.add()

        new_parent = Parent(user_id=user_add.id)
        new_parent.add()
        return jsonify(new_parent.convert_json())

    if request.method == 'GET':
        user = Users.query.get_or_404(id)
        parent = Parent.query.filter(Parent.user_id == user.id).first()
        return jsonify(parent.convert_json())
    user = Users.query.get_or_404(id)
    parent = Parent.query.filter(Parent.user_id == user.id).first()

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
        db.session.commit()
        return jsonify(parent.convert_json())

    if request.method == 'DELETE':
        parent.students = []
        user.deleted = True
        db.session.commit()
        return jsonify({'message': 'Parent deleted successfully'}), 204


@crud_parent_bp.route('/add_students/<int:id>', methods=['POST'])
def add_students_to_parent(id):
    user = Users.query.get_or_404(id)
    parent = Parent.query.filter(Parent.user_id == user.id).first()

    data = request.json
    student_ids = data.get('student_ids', [])

    students = Students.query.filter(Students.id.in_(student_ids)).all()

    for st in students:
        if st not in parent.student:
            parent.student.append(st)

    db.session.commit()
    return jsonify(parent.convert_json()), 200


@crud_parent_bp.route('/remove_students/<int:id>', methods=['POST'])
def remove_students_from_parent(id):
    user = Users.query.get_or_404(id)
    parent = Parent.query.filter(Parent.user_id == user.id).first()
    data = request.json
    student_id = data.get('student_id', [])

    student = Students.query.filter(Students.id == student_id).first()
    if student in parent.student:
        parent.student.remove(student)

    db.session.commit()
    return jsonify(parent.convert_json()), 200
