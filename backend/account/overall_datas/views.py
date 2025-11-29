from .home_screen import home_screen_bp


def register_overall_datas_routes(api, app):
    app.register_blueprint(home_screen_bp, url_prefix=f"/{api}/account/home/")
