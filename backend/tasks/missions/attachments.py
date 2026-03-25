from flask import Blueprint, request, jsonify, current_app
from backend.models.models import MissionAttachment, Mission, db
from backend.tasks.missions.utils import allowed_file
from backend.tasks.models.management import sync_attachment_to_management, sync_attachment_update_to_management, sync_attachment_delete_to_management
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from backend.tasks.missions.marshmallow import AttachmentSchema
from backend.models.models import Users

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

    creator_id = request.form.get("creator_id")
    creator_name = None
    if creator_id:
        user = Users.query.filter(Users.id == creator_id).first()
        creator_name = f"{user.name} {user.surname}".strip() if user else None

    a = MissionAttachment(mission_id=mission_id, file_path=file_url, note=note, creator_name=creator_name)
    db.session.add(a)
    db.session.commit()

    # Sync to management DB if mission originated from management
    mission = Mission.query.get(int(mission_id))
    if mission and mission.management_id:
        mgmt_id = sync_attachment_to_management(
            mission_management_id=mission.management_id,
            file_url=file_url,
            note=note,
            creator_name=creator_name,
        )
        if mgmt_id:
            a.management_id = mgmt_id
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

    if a.management_id:
        sync_attachment_update_to_management(
            management_id=a.management_id,
            file=a.file_path if file else None,
            note=note if note else None,
        )

    schema = AttachmentSchema()
    result = schema.dump(a)
    return jsonify(result), 200


# DELETE
@attachments_bp.route("/<int:pk>/", methods=["DELETE"])
def delete_attachment(pk):
    a = MissionAttachment.query.get_or_404(pk)
    mgmt_id = a.management_id
    db.session.delete(a)
    db.session.commit()

    if mgmt_id:
        sync_attachment_delete_to_management(mgmt_id)

    return jsonify({"detail": "deleted"}), 200
