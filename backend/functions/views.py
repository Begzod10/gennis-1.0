from backend.functions.filters import student_functions_bp


def register_filters_views(api, app):
    app.register_blueprint(student_functions_bp, url_prefix=f"/{api}/filters")
