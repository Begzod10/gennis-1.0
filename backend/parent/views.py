from backend.parent.get import get_parent_bp
from backend.parent.crud import crud_parent_bp


def register_parent_views(api, app):
    app.register_blueprint(crud_parent_bp, url_prefix=f"/{api}/parent")
    app.register_blueprint(get_parent_bp, url_prefix=f"/{api}/parent")
