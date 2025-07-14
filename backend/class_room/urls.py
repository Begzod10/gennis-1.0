from backend.class_room.views import classroom_bp


def register_classroom_views(api, app):
    app.register_blueprint(classroom_bp, url_prefix=f"/{api}/classroom")
