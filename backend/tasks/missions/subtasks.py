from flask import Blueprint, request, jsonify
from backend.tasks.models.models import MissionSubtask, Mission, db
from backend.tasks.missions.marshmallow import SubtaskSchema

subtasks_bp = Blueprint("subtasks", __name__)


@subtasks_bp.route("/", methods=["POST"])
def create_subtask():
    json = request.get_json() or {}
    mission_id = json.get("mission_id")
    t = Mission.query.get_or_404(mission_id)
    st = MissionSubtask(mission_id=mission_id, title=json.get("title"), order=json.get("order", 0))
    db.session.add(st)
    db.session.commit()
    schema = SubtaskSchema()
    result = schema.dump(st)
    return jsonify(result), 201


@subtasks_bp.route("/<int:pk>/", methods=["PATCH"])
def update_subtask(pk):
    st = MissionSubtask.query.get_or_404(pk)
    json = request.get_json() or {}
    if "is_done" in json:
        st.is_done = bool(json["is_done"])
    if "title" in json:
        st.title = json["title"]
    db.session.commit()
    schema = SubtaskSchema()
    result = schema.dump(st)
    return jsonify(result), 200


@subtasks_bp.route("/<int:pk>/", methods=["DELETE"])
def delete_subtask(pk):
    st = MissionSubtask.query.get_or_404(pk)
    db.session.delete(st)
    db.session.commit()
    return jsonify({"detail": "deleted"}), 200
