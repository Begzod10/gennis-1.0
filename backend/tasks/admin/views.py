from .debts import *
from .new_students import *
from .leads import *
from .tasks_rating import task_rating_bp


def register_task_rating_views(api,app):
    app.register_blueprint(task_rating_bp, url_prefix=f"/{api}task_rating")
