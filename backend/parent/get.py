from flask import Blueprint
from flask import jsonify, request
from sqlalchemy import desc

from backend.account.models import StudentPayments
from backend.models.models import Users, Roles
from backend.parent.models import Parent
from backend.student.models import Students

get_parent_bp = Blueprint('parent_get', __name__)


@get_parent_bp.route('/get_list/<int:location_id>', defaults={'deleted': False}, methods=['GET'])
@get_parent_bp.route('/get_list/<int:location_id>/<deleted>', methods=['GET'])
def parent_list(location_id, deleted):
    role = Roles.query.filter(Roles.type_role == 'parent').first()
    if not role:
        role = Roles(role='pa21s122s', type_role='parent')
        role.add()
    parents = Parent.query.join(Users).filter(Users.location_id == location_id, Users.deleted == deleted,
                                              Users.role_id == role.id).order_by(desc(Parent.id)).all()
    parents_list = [parent.convert_json() for parent in parents]
    return jsonify(parents_list)


@get_parent_bp.route('/student_list/<int:id>', methods=['GET'])
def student_list(id):
    user = Users.query.get_or_404(id)
    parent = Parent.query.filter(Parent.user_id == user.id).first()

    existing_student_ids = [s.id for s in parent.student]

    available_students = Students.query.filter(~Students.id.in_(existing_student_ids)).all()

    return jsonify([student.convert_json() for student in available_students]), 200


@get_parent_bp.route('/student_payments', methods=['GET'])
def get_student_payments():
    id = request.args.get('id', type=int)
    payment_status = request.args.get('payment', type=lambda v: v.lower() == 'true')

    user = Users.query.filter(Users.id == id).first()
    student = Students.query.filter(Students.user_id == user.id).first()

    payments = StudentPayments.query.filter_by(
        student_id=student.id,
        payment=payment_status
    ).all()

    return jsonify([p.convert_json() for p in payments]), 200
