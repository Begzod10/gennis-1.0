from .platform.payments import student_bp


from .platform.change import chang_student_bp
from backend.student.student_functions import student_functions
from backend.student.change_student import change_student_bp

from backend.student.calling_to_students import calling_to_students_bp


def register_student_views(api, app):
    app.register_blueprint(student_bp, url_prefix=f"/{api}/student")
    app.register_blueprint(chang_student_bp, url_prefix=f"/{api}/student")
    app.register_blueprint(student_functions, url_prefix=f"/{api}/student")
    app.register_blueprint(change_student_bp, url_prefix=f"/{api}/student")
    app.register_blueprint(calling_to_students_bp, url_prefix=f"/{api}/student")
