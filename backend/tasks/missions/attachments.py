from flask import Blueprint, request, jsonify, current_app
from backend.models.models import MissionAttachment, db
from backend.tasks.missions.utils import allowed_file
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from backend.tasks.missions.marshmallow import AttachmentSchema

attachments_bp = Blueprint("attachments", __name__)


@attachments_bp.route("/", methods=["POST"])
def create_attachment():
    mission_id = request.form.get("mission_id")
    file = request.files.get("file")
    note = request.form.get("note")

    if not mission_id or not file:
        return jsonify({"detail": "mission_id and file required"}), 400

    if not allowed_file(file.filename):
        return jsonify({"detail": "invalid file type"}), 400

    # secure + unique filename
    ext = file.filename.rsplit(".", 1)[1]
    filename = f"{datetime.utcnow().timestamp()}_{mission_id}.{ext}"
    filename = secure_filename(filename)

    dst = os.path.join(current_app.config['ATTACHMENTS_FOLDER'], filename)
    file.save(dst)

    # relative URL for frontend
    file_url = f"/uploads/attachments/{filename}"

    a = MissionAttachment(mission_id=mission_id, file_path=file_url, note=note)
    db.session.add(a)
    db.session.commit()
    schema = AttachmentSchema()
    result = schema.dump(a)
    return jsonify(result), 201


# UPDATE ATTACHMENT
@attachments_bp.route("/<int:pk>/", methods=["PATCH"])
def update_attachment(pk):
    a = MissionAttachment.query.get_or_404(pk)

    note = request.form.get("note")
    if note:
        a.note = note

    file = request.files.get("file")
    if file and allowed_file(file.filename):
        # Remove old file
        if a.file_path:
            try:
                old_file_path = os.path.join(
                    current_app.root_path,
                    a.file_path.lstrip("/")
                )
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
            except Exception as e:
                print("Old file remove error:", e)

        # Save new file
        ext = file.filename.rsplit(".", 1)[1]
        filename = f"{datetime.utcnow().timestamp()}_{a.mission_id}.{ext}"
        filename = secure_filename(filename)

        dst = os.path.join(current_app.config['ATTACHMENTS_FOLDER'], filename)
        file.save(dst)

        a.file_path = f"/uploads/attachments/{filename}"

    db.session.commit()
    schema = AttachmentSchema()
    result = schema.dump(a)
    return jsonify(result), 200


# DELETE
@attachments_bp.route("/<int:pk>/", methods=["DELETE"])
def delete_attachment(pk):
    a = MissionAttachment.query.get_or_404(pk)
    db.session.delete(a)
    db.session.commit()

    return jsonify({"detail": "deleted"}), 200
