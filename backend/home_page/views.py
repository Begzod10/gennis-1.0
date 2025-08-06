from .route import home_page_bp


def register_home_views(api, app):
    app.register_blueprint(home_page_bp, url_prefix=f"/{api}/home_page")
