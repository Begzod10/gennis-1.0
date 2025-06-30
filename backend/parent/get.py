from app import jsonify, request, db
from backend.parent.models import Parent
from backend.models.models import Users, Teachers, Roles
from sqlalchemy import desc
from flask import Blueprint

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
