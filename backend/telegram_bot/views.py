from .parent.infos import parent_bp
from .student.infos import student_bp
from .user.infos import user_bp
from .teacher.infos import teacher_bp


def register_telegram_bot_routes(api, app):
    app.register_blueprint(parent_bp, url_prefix=f"/{api}/bot/parents/")
    app.register_blueprint(student_bp, url_prefix=f"/{api}/bot/students/")
    app.register_blueprint(user_bp, url_prefix=f"/{api}/bot/users/")
    app.register_blueprint(teacher_bp, url_prefix=f"/{api}/bot/teachers/")
