from backend.models.models import Parent
from flask import Blueprint

parent_bp = Blueprint('parent', __name__)


@parent_bp.route(f'students/<parent_id>')
def bot_parents_students(parent_id):
    parent = Parent.query.filter(Parent.id == parent_id).first()
    return parent.convert_json()
