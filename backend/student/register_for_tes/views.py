from backend.student.register_for_tes.resources import student_bp_test_school


def register_for_tes_views(api, app):
    app.register_blueprint(student_bp_test_school, url_prefix=f"/{api}/student")
