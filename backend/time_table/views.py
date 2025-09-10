from .route import time_table
from .room import room_bp


def register_time_table_views(api, app):
    app.register_blueprint(time_table, url_prefix=f"/{api}/time_table")
    app.register_blueprint(room_bp, url_prefix=f"/{api}/room")
