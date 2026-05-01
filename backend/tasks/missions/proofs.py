from flask import Blueprint, request, jsonify, current_app
from backend.tasks.models.models import MissionProof, Mission, db
from backend.tasks.missions.utils import allowed_file
from backend.tasks.models.management import sync_proof_to_management, sync_proof_update_to_management, sync_proof_delete_to_management
from backend.models.config import BASE_URL
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from backend.tasks.missions.marshmallow import ProofSchema
from backend.models.models import Users

proofs_bp = Blueprint("proofs", __name__)


# CREATE
@proofs_bp.route("/", methods=["POST"])
def create_proof():
    mission_id = request.form.get("mission_id")
    file = request.files.get("file")
    comment = request.form.get("comment")

    if not mission_id or not file:
        return jsonify({"detail": "mission_id and file are required"}), 400

    if not allowed_file(file.filename):
        return jsonify({"detail": "invalid file"}), 400

    # secure + unique filename
    ext = file.filename.rsplit(".", 1)[1]
    filename = f"{datetime.utcnow().timestamp()}_{mission_id}.{ext}"
    filename = secure_filename(filename)

    # save file
    dst = os.path.join(current_app.config['PROOFS_FOLDER'], filename)
    file.save(dst)

    # relative URL for frontend
    file_url = f"/uploads/proofs/{filename}"

    creator_id = request.form.get("creator_id")
    creator_name = None
    if creator_id:
        user = Users.query.filter(Users.id == creator_id).first()
        creator_name = f"{user.name} {user.surname}".strip() if user else None

    p = MissionProof(mission_id=mission_id, file_path=file_url, comment=comment, creator_name=creator_name)
    db.session.add(p)
    db.session.commit()

    # Sync to management DB if mission originated from management
    mission = Mission.query.get(int(mission_id))
    if mission and mission.management_id:
        mgmt_id = sync_proof_to_management(
            mission_management_id=mission.management_id,
            file_url=f"{BASE_URL}{file_url}",
            comment=comment,
            creator_name=creator_name,
        )
        if mgmt_id:
            p.management_id = mgmt_id
            db.session.commit()

    schema = ProofSchema()
    result = schema.dump(p)

    return jsonify(result), 201


# UPDATE
@proofs_bp.route("/<int:pk>/", methods=["PATCH"])
def update_proof(pk):
    p = MissionProof.query.get_or_404(pk)

    comment = request.form.get("comment")
    if comment:
        p.comment = comment

    file = request.files.get("file")
    if file and allowed_file(file.filename):
        # remove old file
        if p.file_path:
            try:
                old_file_path = os.path.join(
                    current_app.root_path,
                    p.file_path.lstrip("/")
                )
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
            except Exception as e:
                print("Old file remove error:", e)

        # secure + unique filename
        ext = file.filename.rsplit(".", 1)[1]
        filename = f"{datetime.utcnow().timestamp()}_{p.mission_id}.{ext}"
        filename = secure_filename(filename)

        dst = os.path.join(current_app.config['PROOFS_FOLDER'], filename)
        file.save(dst)

        # relative URL
        p.file_path = f"/uploads/proofs/{filename}"

    db.session.commit()

    if p.management_id:
        sync_proof_update_to_management(
            management_id=p.management_id,
            file=f"{BASE_URL}{p.file_path}" if file and p.file_path else None,
            comment=comment if comment else None,
        )

    schema = ProofSchema()
    result = schema.dump(p)
    return jsonify(result), 200


# DELETE
@proofs_bp.route("/<int:pk>/", methods=["DELETE"])
def delete_proof(pk):
    p = MissionProof.query.get_or_404(pk)
    mgmt_id = p.management_id

    try:
        os.remove(p.file_path)
    except:
        pass

    db.session.delete(p)
    db.session.commit()

    if mgmt_id:
        sync_proof_delete_to_management(mgmt_id)

    return jsonify({"detail": "deleted"}), 200
