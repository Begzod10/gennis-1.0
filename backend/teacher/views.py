from backend.teacher.classroom.lesson_plan import lesson_plan_bp
from backend.teacher.classroom.observation import observetion_bp
from backend.teacher.lesson_plan import lesson_plan_gennis_bp
from backend.teacher.observation import gennis_observation_bp
from backend.teacher.teacher import teachers_bp
from backend.teacher.teacher_delete import teacher_delete_bp


from backend.teacher.teacher_home_page import teacher_home_page_bp

def register_teacher_views(api, app):
    app.register_blueprint(lesson_plan_bp, url_prefix=f"/{api}/teacher")
    app.register_blueprint(observetion_bp, url_prefix=f"/{api}/teacher")
    app.register_blueprint(teacher_delete_bp, url_prefix=f"/{api}/teacher")
    app.register_blueprint(teachers_bp, url_prefix=f"/{api}/teacher")
    app.register_blueprint(lesson_plan_gennis_bp, url_prefix=f"/{api}/teacher")
    app.register_blueprint(gennis_observation_bp, url_prefix=f"/{api}/teacher")
    app.register_blueprint(teacher_home_page_bp, url_prefix=f"/{api}/teacher")
