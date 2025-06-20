from app import jsonify, request
from backend.parent.models import Parent

from flask import Blueprint

get_parent_bp = Blueprint('parent_get', __name__)


@get_parent_bp.route('/get_list/<int:location_id>', methods=['GET'])
def parent_list(location_id):
    if request.method == 'GET':
        parents = Parent.query.filter(Parent.location_id == location_id).all()
        parents_list = [parent.convert_json() for parent in parents]
        return jsonify(parents_list)
