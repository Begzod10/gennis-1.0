from .parent import parent_mobile_bp
from .missions.missions import missions_bp


def register_parent_mobile_views(api, app):
    app.register_blueprint(parent_mobile_bp, url_prefix=f"/api/mobile")
    app.register_blueprint(missions_bp, url_prefix=f"/api/mobile")
