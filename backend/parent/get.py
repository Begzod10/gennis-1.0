from app import jsonify, request, db
from backend.parent.models import Parent
from backend.models.models import Users, Teachers
from sqlalchemy import desc
from flask import Blueprint

get_parent_bp = Blueprint('parent_get', __name__)


@get_parent_bp.route('/get_list/<int:location_id>', defaults={'deleted': False}, methods=['GET'])
@get_parent_bp.route('/get_list/<int:location_id>/<deleted>', methods=['GET'])
def parent_list(location_id, deleted):
    parents = Parent.query.filter(Parent.location_id == location_id, Parent.deleted == deleted).order_by(
        desc(Parent.id)).all()
    parents_list = [parent.convert_json() for parent in parents]
    return jsonify(parents_list)
