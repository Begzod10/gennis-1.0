from backend.tasks.missions.missions import missions_bp, up_bp
from backend.tasks.missions.comments import comments_bp
from backend.tasks.missions.proofs import proofs_bp
from backend.tasks.missions.attachments import attachments_bp
from backend.tasks.missions.subtasks import subtasks_bp
from backend.tasks.missions.tags import tags_bp
from backend.tasks.missions.notifications import notif_bp


def register_missions_views(api, app):
    app.register_blueprint(missions_bp, url_prefix=f"/api/missions")
    app.register_blueprint(comments_bp, url_prefix=f"/api/comment")
    app.register_blueprint(proofs_bp, url_prefix=f"/api/proofs")
    app.register_blueprint(attachments_bp, url_prefix=f"/api/attachments")
    app.register_blueprint(subtasks_bp, url_prefix=f"/api/subtasks")
    app.register_blueprint(tags_bp, url_prefix=f"/api/tags")
    app.register_blueprint(up_bp, url_prefix=f"/api/uploads")
    app.register_blueprint(notif_bp, url_prefix=f"/api/notifications")
