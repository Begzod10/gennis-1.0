from backend.for_programmers.basic import for_programmers_basic_bp
from backend.for_programmers.for_programmers import for_programmers


def register_programmers_views(api, app):
    app.register_blueprint(for_programmers_basic_bp, url_prefix=f"/{api}/programmers_basic")
    app.register_blueprint(for_programmers, url_prefix=f"/{api}/programmers")
