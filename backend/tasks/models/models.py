from sqlalchemy import String, Integer, Boolean, Column, ForeignKey, DateTime, or_, and_, desc, func, ARRAY, JSON
from sqlalchemy.orm import relationship

from backend.models.models import db


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
