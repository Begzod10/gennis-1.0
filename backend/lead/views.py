from .crud import lead_bp


def register_lead_views(api, app):
    app.register_blueprint(lead_bp, url_prefix=f"/{api}/lead")
