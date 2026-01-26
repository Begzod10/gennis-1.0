from .home_screen import home_screen_bp
from .daily_datas import daily_datas


def register_overall_datas_routes(api, app):
    app.register_blueprint(home_screen_bp, url_prefix=f"/api/account/home/")
    app.register_blueprint(daily_datas, url_prefix=f"/api/account/daily_datas/")
