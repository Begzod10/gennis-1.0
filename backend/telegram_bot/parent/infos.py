from app import app, api, desc, jsonify, db
from backend.models.models import Parent


@app.route(f'{api}/bot_parents_students/<parent_id>')
def bot_parents_students(parent_id):
    parent = Parent.query.filter(Parent.id == parent_id).first()
    return parent.convert_json()
