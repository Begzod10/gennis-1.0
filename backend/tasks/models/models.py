from sqlalchemy import String, Integer, Boolean, Column, ForeignKey, DateTime, or_, and_, desc, func, ARRAY, JSON
from sqlalchemy.orm import relationship
from backend.models.models import db
from datetime import date, datetime, timedelta


class Tasks(db.Model):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    role = Column(String)
    tasks_statistics = relationship("TasksStatistics", backref="task", order_by='TasksStatistics.id')
    task_ratings = relationship("TaskRatings", backref="task", order_by='TaskRatings.id')


class TasksStatistics(db.Model):
    __tablename__ = "tasksstatistics"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    calendar_year = Column(Integer, ForeignKey('calendaryear.id'))
    calendar_month = Column(Integer, ForeignKey('calendarmonth.id'))
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    completed_tasks = Column(Integer, default=0)
    in_progress_tasks = Column(Integer)
    completed_tasks_percentage = Column(Integer, default=0)
    location_id = Column(Integer, ForeignKey('locations.id'))
    task_students = relationship("TaskStudents", backref="tasksstatistics", order_by='TaskStudents.id')
    total_tasks = Column(Integer, default=0)

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "user_id": self.user_id if self.user_id else None,
            "calendar_year": self.calendar_year,
            "calendar_month": self.calendar_month,
            "calendar_day": self.calendar_day,
            "completed_tasks": self.completed_tasks,
            "in_progress_tasks": self.in_progress_tasks,
            "completed_tasks_percentage": self.completed_tasks_percentage,
            "location_id": self.location_id,
            "total_tasks": self.total_tasks
        }


class TaskDailyStatistics(db.Model):
    __tablename__ = "taskdailystatistics"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    calendar_year = Column(Integer, ForeignKey('calendaryear.id'))
    calendar_month = Column(Integer, ForeignKey('calendarmonth.id'))
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    location_id = Column(Integer, ForeignKey('locations.id'))
    completed_tasks = Column(Integer, default=0)
    in_progress_tasks = Column(Integer)
    completed_tasks_percentage = Column(Integer, default=0)
    total_tasks = Column(Integer, default=0)

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "user_id": self.user_id if self.user_id else None,
            "calendar_year": self.calendar_year,
            "calendar_month": self.calendar_month,
            "calendar_day": self.calendar_day,
            "completed_tasks": self.completed_tasks,
            "in_progress_tasks": self.in_progress_tasks,
            "completed_tasks_percentage": self.completed_tasks_percentage,
            "location_id": self.location_id,
            "total_tasks": self.total_tasks
        }


class TaskStudents(db.Model):
    __tablename__ = "task_students"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'))
    tasksstatistics_id = Column(Integer, ForeignKey('tasksstatistics.id'))
    task_id = Column(Integer, ForeignKey('tasks.id'))
    status = Column(Boolean, default=False)
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))

    # __table_args__ = (
    #     db.UniqueConstraint('task_id', 'student_id', 'tasksstatistics_id', 'calendar_day',
    #                         name='unique_task_student_per_day'),
    # )

    def add(self):
        db.session.add(self)
        db.session.commit()

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "tasksstatistics_id": self.tasksstatistics_id,
            "task_id": self.task_id,
            "status": self.status
            # "calendar_day": self.calendar_day.date.strftime("%Y-%m-%d")
        }


class BlackStudents(db.Model):
    __tablename__ = "black_students"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'))
    calendar_year = Column(Integer, ForeignKey('calendaryear.id'))
    calendar_month = Column(Integer, ForeignKey('calendarmonth.id'))
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    location_id = Column(Integer, ForeignKey('locations.id'))
    comment = Column(String)
    deleted = Column(Boolean, default=False)

    def add(self):
        db.session.add(self)
        db.session.commit()


class BlackStudentsStatistics(db.Model):
    __tablename__ = "black_students_statistics"
    id = Column(Integer, primary_key=True)
    calendar_year = Column(Integer, ForeignKey('calendaryear.id'))
    calendar_month = Column(Integer, ForeignKey('calendarmonth.id'))
    total_black_students = Column(Integer, default=0)
    location_id = Column(Integer, ForeignKey('locations.id'))

    def add(self):
        db.session.add(self)
        db.session.commit()


class TaskRatings(db.Model):
    __tablename__ = "task_ratings"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'))
    calendar_year = Column(Integer, ForeignKey('calendaryear.id'))
    calendar_month = Column(Integer, ForeignKey('calendarmonth.id'))
    location_id = Column(Integer, ForeignKey('locations.id'))
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    in_progress_tasks = Column(Integer, default=0)
    completed_tasks_percentage = Column(Integer, default=0)

    def add(self):
        db.session.add(self)
        db.session.commit()

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "calendar_year": self.calendar_year,
            "calendar_month": self.calendar_month,
            "calendar_month_name": self.month.date.strftime("%B"),
            "location_id": self.location_id,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "in_progress_tasks": self.in_progress_tasks,
            "location_name": self.location.name,
            "completed_tasks_percentage": self.completed_tasks_percentage
        }


class TaskRatingsMonthly(db.Model):
    __tablename__ = "task_ratings_monthly"
    id = Column(Integer, primary_key=True)
    calendar_year = Column(Integer, ForeignKey('calendaryear.id'))
    calendar_month = Column(Integer, ForeignKey('calendarmonth.id'))
    location_id = Column(Integer, ForeignKey('locations.id'))
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    in_progress_tasks = Column(Integer, default=0)
    completed_tasks_percentage = Column(Integer, default=0)

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "calendar_year": self.calendar_year,
            "calendar_month": self.calendar_month,
            "location_id": self.location_id,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "in_progress_tasks": self.in_progress_tasks,
            "location_name": self.location.name,
            "completed_tasks_percentage": self.completed_tasks_percentage,
            "calendar_month_name": self.month.date.strftime("%B"),
        }

    def add(self):
        db.session.add(self)
        db.session.commit()


mission_tags = db.Table(
    "mission_tags",
    db.Column("mission_id", db.Integer, db.ForeignKey("missions.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id"), primary_key=True),
)


class Tag(db.Model):
    __tablename__ = "tags"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)


class Mission(db.Model):
    __tablename__ = "missions"
    id = db.Column(db.Integer, primary_key=True)
    management_id = db.Column(db.BigInteger, nullable=True, unique=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)

    category = db.Column(db.String(50), default="academic")
    tags = db.relationship("Tag", secondary=mission_tags, backref=db.backref("missions", lazy="dynamic"))

    creator_name = db.Column(db.String(255), nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    executor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reviewer_name = db.Column(db.String(255), nullable=True)

    original_executor_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )
    is_redirected = db.Column(db.Boolean, default=False)
    redirected_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )
    redirected_at = db.Column(db.DateTime, nullable=True)

    location_id = db.Column(db.Integer, db.ForeignKey("locations.id"))

    start_datetime = db.Column(db.DateTime, default=datetime.utcnow)
    deadline_datetime = db.Column(db.DateTime, nullable=False)
    finish_datetime = db.Column(db.DateTime)

    status = db.Column(db.String(30), default="not_started")

    kpi_weight = db.Column(db.Integer, default=10)
    penalty_per_day = db.Column(db.Integer, default=2)
    early_bonus_per_day = db.Column(db.Integer, default=1)
    max_bonus = db.Column(db.Integer, default=3)
    max_penalty = db.Column(db.Integer, default=10)
    delay_days = db.Column(db.Integer, default=0)

    # Recurring
    is_recurring = db.Column(db.Boolean, default=False)
    recurring_type = db.Column(db.String(20), nullable=True)
    repeat_every = db.Column(db.Integer, default=1)  # days
    last_generated = db.Column(db.Date, nullable=True)

    final_sc = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), server_onupdate=func.now())
    comments = db.relationship("MissionComment", backref="mission", cascade="all, delete")
    notifications = db.relationship("Notification", backref="mission", cascade="all, delete")
    proofs = db.relationship("MissionProof", backref="mission", cascade="all, delete")
    attachments = db.relationship("MissionAttachment", backref="mission", cascade="all, delete")
    subtasks = db.relationship("MissionSubtask", backref="mission", cascade="all, delete")
    creator = db.relationship("Users", foreign_keys=[creator_id], backref="created_missions")
    executor = db.relationship("Users", foreign_keys=[executor_id], backref="executed_missions")
    reviewer = db.relationship("Users", foreign_keys=[reviewer_id], backref="reviewed_missions")
    redirected_by = db.relationship("Users", foreign_keys=[redirected_by_id], backref="redirected_by_missions")

    def calculate_delay(self):
        if self.finish_datetime and self.deadline_datetime:
            diff = self.finish_datetime - self.deadline_datetime
            self.delay_minutes = int(diff.total_seconds() // 60)
        else:
            self.delay_minutes = 0
        return self.delay_minutes

    def compute_final_score(self):
        self.calculate_delay()
        delay_days = self.delay_minutes // 1440
        base = self.kpi_weight

        if delay_days < 0:
            bonus = min(abs(delay_days) * self.early_bonus_per_day, self.max_bonus)
            return base + bonus

        if delay_days == 0:
            return base

        penalty = min(delay_days * self.penalty_per_day, self.max_penalty)
        return max(0, base - penalty)

    def remaining_days(self):
        if not self.deadline_datetime:
            return None
        return (self.deadline_datetime.date() - date.today()).days

    def status_color(self):
        if not self.deadline_datetime:
            return "green"

        remaining = (self.deadline_datetime.date() - date.today()).days

        if remaining <= 1:
            return "red"
        elif remaining <= 4:
            return "yellow"
        return "green"


class MissionSubtask(db.Model):
    __tablename__ = "mission_subtasks"
    id = db.Column(db.Integer, primary_key=True)
    management_id = db.Column(db.BigInteger, nullable=True, unique=True)
    mission_id = db.Column(db.Integer, db.ForeignKey("missions.id"), nullable=False)
    title = db.Column(db.String(255))
    is_done = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer, default=0)
    creator_name = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MissionAttachment(db.Model):
    __tablename__ = "mission_attachments"
    id = db.Column(db.Integer, primary_key=True)
    management_id = db.Column(db.BigInteger, nullable=True, unique=True)
    mission_id = db.Column(db.Integer, db.ForeignKey("missions.id"), nullable=False)
    file_path = db.Column(db.String(255))
    note = db.Column(db.String(255), nullable=True)
    creator_name = db.Column(db.String(255), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)


class MissionComment(db.Model):
    __tablename__ = "mission_comments"
    id = db.Column(db.Integer, primary_key=True)
    management_id = db.Column(db.BigInteger, nullable=True, unique=True)
    mission_id = db.Column(db.Integer, db.ForeignKey("missions.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    text = db.Column(db.Text)
    attachment_path = db.Column(db.String(255), nullable=True)
    creator_name = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("Users", backref="mission_comments", foreign_keys=[user_id])


class MissionProof(db.Model):
    __tablename__ = "mission_proofs"
    id = db.Column(db.Integer, primary_key=True)
    management_id = db.Column(db.BigInteger, nullable=True, unique=True)
    mission_id = db.Column(db.Integer, db.ForeignKey("missions.id"), nullable=False)
    file_path = db.Column(db.String(255))
    comment = db.Column(db.String(255), nullable=True)
    creator_name = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MissionHistory(db.Model):
    __tablename__ = "mission_history"
    id = db.Column(db.Integer, primary_key=True)
    management_id = db.Column(db.BigInteger, nullable=True, unique=True)
    mission_id = db.Column(db.Integer, db.ForeignKey("missions.id"), nullable=False)
    executor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    management_executor_id = db.Column(db.BigInteger, nullable=True)
    management_executor_name = db.Column(db.String(255), nullable=True)
    management_reviewer_id = db.Column(db.BigInteger, nullable=True)
    management_reviewer_name = db.Column(db.String(255), nullable=True)
    turon_executor_id = db.Column(db.BigInteger, nullable=True)
    turon_executor_name = db.Column(db.String(255), nullable=True)
    turon_reviewer_id = db.Column(db.BigInteger, nullable=True)
    turon_reviewer_name = db.Column(db.String(255), nullable=True)
    changed_by_name = db.Column(db.String(255), nullable=True)
    note = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    executor = db.relationship("Users", foreign_keys=[executor_id])
    reviewer = db.relationship("Users", foreign_keys=[reviewer_id])


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    mission_id = db.Column(db.Integer, db.ForeignKey("missions.id"), nullable=True)
    message = db.Column(db.Text)
    role = db.Column(db.String(20))  # executor/creator/reviewer
    deadline = db.Column(db.Date, nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
