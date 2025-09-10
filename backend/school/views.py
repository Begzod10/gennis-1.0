from .school import school_bp


def register_school_views(api, app):
    app.register_blueprint(school_bp, url_prefix=f"/{api}/school")
