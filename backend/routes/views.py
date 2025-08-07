from .classroom.send_user_data import classroom_basic_bp
from .base_routes import base_bp
from .checks import basics_checks


def register_router_views(api, app):
    app.register_blueprint(base_bp, url_prefix=f"/{api}/base")
    app.register_blueprint(classroom_basic_bp, url_prefix=f"/{api}/classroom")
    app.register_blueprint(basics_checks, url_prefix=f"/{api}/checks")
