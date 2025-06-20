from app import app, api, or_, db, contains_eager, extract, jsonify, request, desc
from backend.student.models import Students
from backend.parent.models import Parent

from flask import Blueprint

crud_parent_bp = Blueprint('parent_crud', __name__)


@crud_parent_bp.route('/crud/', defaults={'pk': None}, methods=['GET', 'POST', 'PUT', 'DELETE'])
@crud_parent_bp.route('/crud/<int:id>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def parent_detail(id):
    parent = Parent.query.get_or_404(id)

    if request.method == 'POST':
        data = request.json
        check_username = Parent.query.filter(Parent.username == data.get('username'))
        if check_username:
            return jsonify({'error': 'Username mavjud'})

        new_parent = Parent(
            name=data.get('name'),
            surname=data.get('surname'),
            username=data.get('username'),
            phone=data.get('phone'),
            address=data.get('address'),
            location_id=data.get('location_id'),
            born_date=data.get('born_date'),
            sex=data.get('sex')
        )
        new_parent.add()
        return jsonify(new_parent.convert_json())
    if request.method == 'GET':
        return jsonify(parent.convert_json())

    if request.method == 'PUT':
        data = request.json
        if 'name' in data:
            parent.name = data['name']
        if 'surname' in data:
            parent.surname = data['surname']
        if 'phone' in data:
            parent.phone = data['phone']
        if 'address' in data:
            parent.address = data['address']
        if 'location_id' in data:
            parent.location_id = data['location_id']
        if 'born_date' in data:
            parent.born_date = data['born_date']
        if 'sex' in data:
            parent.sex = data['sex']

        db.session.commit()
        return jsonify(parent.convert_json())

    if request.method == 'DELETE':
        parent.students = []
        db.session.commit()
        db.session.delete(parent)
        db.session.commit()
        return jsonify({'message': 'Parent deleted successfully'}), 204


@crud_parent_bp.route('/add_students/<int:id>', methods=['POST'])
def add_students_to_parent(id):
    parent = Parent.query.get_or_404(id)
    data = request.json
    student_ids = data.get('student_ids', [])

    students = Students.query.filter(Students.id.in_(student_ids)).all()

    for st in students:
        if st not in parent.students:
            parent.students.append(st)

    db.session.commit()
    return jsonify(parent.convert_json()), 200


@crud_parent_bp.route('/remove_students/<int:id>', methods=['POST'])
def remove_students_from_parent(id):
    parent = Parent.query.get_or_404(id)
    data = request.json
    student_ids = data.get('student_ids', [])

    students = Students.query.filter(Students.id.in_(student_ids)).all()
    for st in students:
        if st in parent.students:
            parent.students.remove(st)

    db.session.commit()
    return jsonify(parent.convert_json()), 200
