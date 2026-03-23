from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from backend.models.models import MissionComment, Mission, db, Users
from backend.tasks.missions.utils import allowed_file, create_notification
from backend.tasks.missions.marshmallow import CommentSchema
from backend.tasks.models.management import sync_comment_to_management
from werkzeug.utils import secure_filename
import os

comments_bp = Blueprint("comments", __name__)


@comments_bp.route("/", methods=["POST"])
def create_comment():
    try:
        mission_id = request.form.get("mission_id")
        user_id = request.form.get("user_id")
        text = request.form.get("text")

        if not mission_id or not user_id or not text:
            return jsonify({"detail": "mission_id, user_id, text required"}), 400

        file = request.files.get("attachment")
        attachment_path = None

        if file and allowed_file(file.filename):
            original = secure_filename(file.filename)

            ext = original.rsplit(".", 1)[1]
            new_name = f"{datetime.utcnow().timestamp()}_{user_id}.{ext}"

            save_path = os.path.join(current_app.config["COMMENTS_FOLDER"], new_name)
            file.save(save_path)

            attachment_path = f"/uploads/comments/{new_name}"

        user = Users.query.filter(Users.id == user_id).first()
        creator_name = f"{user.name} {user.surname}".strip() if user else None

        comment = MissionComment(
            mission_id=mission_id,
            user_id=user_id,
            text=text,
            attachment_path=attachment_path,
            creator_name=creator_name,
        )

        db.session.add(comment)
        db.session.commit()

        # Sync to management DB if mission originated from management
        mission = Mission.query.get(int(mission_id))
        print(f"[management sync] comment: mission={mission} management_id={mission.management_id if mission else 'no mission'}")
        if mission and mission.management_id:
            mgmt_id = sync_comment_to_management(
                mission_management_id=mission.management_id,
                text=text,
                attachment_url=attachment_path,
                creator_name=creator_name,
            )
            if mgmt_id:
                comment.management_id = mgmt_id
                db.session.commit()

        schema = CommentSchema()
        result = schema.dump(comment)
        return jsonify(result), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"detail": "Error creating comment", "error": str(e)}), 500


# LIST (by mission)
@comments_bp.route("/mission/<int:mission_id>/", methods=["GET"])
def list_comments(mission_id):
    comments = MissionComment.query.filter_by(mission_id=mission_id).order_by(MissionComment.created_at).all()

    return jsonify([
        {
            "id": c.id,
            "user_id": c.user_id,
            "creator_name": c.creator_name,
            "text": c.text,
            "attachment": c.attachment_path,
            "created_at": c.created_at.isoformat()
        }
        for c in comments
    ])


# UPDATE
@comments_bp.route("/<int:pk>/", methods=["PATCH"])
def update_comment(pk):
    c = MissionComment.query.get_or_404(pk)
    text = request.form.get("text")

    if text:
        c.text = text

    # File update (optional)
    file = request.files.get("attachment")
    if file and allowed_file(file.filename):
        # Remove old file
        if c.attachment_path:
            try:
                # Convert relative path to absolute path
                old_file_path = os.path.join(
                    current_app.root_path,  # backend root
                    c.attachment_path.lstrip("/"),  # remove leading slash
                )
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
            except Exception as e:
                print("Old file remove error:", e)

        # Save new file
        filename = secure_filename(file.filename)
        # Add timestamp to avoid collision
        ext = filename.rsplit(".", 1)[1]
        new_name = f"{datetime.utcnow().timestamp()}_{c.user_id}.{ext}"

        dst = os.path.join(current_app.config['COMMENTS_FOLDER'], new_name)
        file.save(dst)

        # Save relative URL for frontend
        c.attachment_path = f"/uploads/comments/{new_name}"

    db.session.commit()

    schema = CommentSchema()
    result = schema.dump(c)
    return jsonify(result), 200


# DELETE
@comments_bp.route("/<int:pk>/", methods=["DELETE"])
def delete_comment(pk):
    c = MissionComment.query.get_or_404(pk)
    db.session.delete(c)
    db.session.commit()
    return jsonify({"detail": "deleted"}), 200
