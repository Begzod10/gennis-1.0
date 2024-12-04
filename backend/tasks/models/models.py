from sqlalchemy import String, Integer, Boolean, Column, ForeignKey, DateTime, or_, and_, desc, func, ARRAY, JSON
from sqlalchemy.orm import relationship

from backend.models.models import db


class Tasks(db.Model):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    role = Column(String)
    tasks_statistics = relationship("TasksStatistics", backref="task", order_by='TasksStatistics.id')


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

    def add(self):
        db.session.add(self)
        db.session.commit()


class BlackStudents(db.Model):
    __tablename__ = "black_students"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'))
    calendar_year = Column(Integer, ForeignKey('calendaryear.id'))
    calendar_month = Column(Integer, ForeignKey('calendarmonth.id'))
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    location_id = Column(Integer, ForeignKey('locations.id'))
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
