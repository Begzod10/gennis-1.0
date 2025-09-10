from .debts import task_debts
from .new_students import task_new_students_bp
from .leads import task_leads_bp
from .tasks_rating import task_rating_bp


def register_task_rating_views(api, app):
    app.register_blueprint(task_rating_bp, url_prefix=f"/{api}task_rating")
    app.register_blueprint(task_debts, url_prefix=f"/{api}task_debts")
    app.register_blueprint(task_new_students_bp, url_prefix=f"/{api}task_new_students")
    app.register_blueprint(task_leads_bp, url_prefix=f"/{api}task_leads")
