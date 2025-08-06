from .basic import group_bp
from .change import group_change_bp
from .create_group import group_create_bp
from .test import group_test_bp

from .classroom.attendance import group_classroom_attendance_bp

from .classroom.profile import group_classroom_profile_bp

from .classroom.test import group_classroom_test_bp


def register_group_views(api, app):
    app.register_blueprint(group_bp, url_prefix=f"/{api}/group")
    app.register_blueprint(group_change_bp, url_prefix=f"/{api}/group_change")
    app.register_blueprint(group_create_bp, url_prefix=f"/{api}/create_group")
    app.register_blueprint(group_test_bp, url_prefix=f"/{api}/group_test")
    app.register_blueprint(group_classroom_attendance_bp, url_prefix=f"/{api}/group_classroom_attendance")
    app.register_blueprint(group_classroom_profile_bp, url_prefix=f"/{api}/group_classroom_profile")
    app.register_blueprint(group_classroom_test_bp, url_prefix=f"/{api}/group_classroom_test")
