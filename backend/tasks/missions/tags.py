from flask import Blueprint, request, jsonify
from backend.tasks.models.models import Tag, db

tags_bp = Blueprint("tags", __name__)


@tags_bp.route("/", methods=["GET", "POST"])
def tags_list_create():
    if request.method == "GET":
        tags = Tag.query.all()
        return jsonify([{"id": t.id, "name": t.name} for t in tags])
    data = request.get_json() or {}
    name = data.get("name")
    t = Tag(name=name)
    db.session.add(t)
    db.session.commit()
    return jsonify({"id": t.id, "name": t.name}), 201


@tags_bp.route("/<int:id>", methods=["PUT", "DELETE"])
def tags_update_delete(id):
    t = Tag.query.get_or_404(id)
    if request.method == "PUT":
        data = request.get_json() or {}
        t.name = data.get("name", t.name)
        db.session.commit()
        return jsonify({"id": t.id, "name": t.name}), 200
    db.session.delete(t)
    db.session.commit()
    return jsonify({"detail": "deleted"}), 200
