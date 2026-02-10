from backend.models.models import db, Integer, String, Column, func, Boolean, ForeignKey, relationship, Students, \
    DateTime

assistent_subject = db.Table('assistent_subject',
                             db.Column('assistent_id', db.Integer, db.ForeignKey('assistent.id'), primary_key=True),
                             db.Column('subject_id', db.Integer, db.ForeignKey('subjects.id'), primary_key=True))


class Assistent(db.Model):
    __tablename__ = 'assistent'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'))

    subjects = db.relationship('Subjects', secondary=assistent_subject,
                               backref=db.backref('assistent', lazy='select'), lazy='select')
    percentage = db.Column(db.Integer, default=0)
    groups = db.relationship("Groups", backref="assistent", order_by="Groups.id")
    deleted = db.Column(db.Boolean, default=False)
    assistent_given_salary = relationship('AssistentSalaries', backref="assistent", order_by="AssistentSalaries.id")
    deleted_assistent_salaries = relationship("DeletedAsistentSalaries", backref="assistent",
                                              order_by="DeletedAsistentSalaries.id")
    time_table = relationship("Group_Room_Week", secondary="time_table_assistent", backref="assistent",
                              order_by="Group_Room_Week.id",
                              lazy="select")

    def add(self):
        db.session.add(self)
        db.session.commit()

    def convert_json(self):
        can_delete = True
        if self.time_table:
            can_delete = False
        if self.groups:
            can_delete = False
        return {"id": self.user.id,
                "name": self.user.name,
                "surname": self.user.surname,
                "username": self.user.username,
                "phone": self.user.phone[0].phone,
                "percentage": self.percentage,
                "can_delete": can_delete,
                'date': str(self.user.born_day) + '.' + str(self.user.born_month) + '.' + str(self.user.born_year),
                'address': self.user.address,
                'location': {
                    'id': self.user.location.id if self.user.location else None,
                    'name': self.user.location.name if self.user.location else None,
                },

                "language": self.user.language.name if self.user.language else None,
                "user_id": self.user_id, "subjects": [s.name for s in self.subjects]
                }


class AssistentSalary(db.Model):
    __tablename__ = "asistent_salary"
    id = Column(Integer, primary_key=True)
    assisten_id = Column(Integer, ForeignKey('assistent.id'))
    total_salary = Column(Integer)
    remaining_salary = Column(Integer)
    location_id = Column(Integer, ForeignKey('locations.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    status = Column(Boolean, default=False)

    assistent_cash = relationship('AssistentSalaries', backref="salary", order_by="AssistentSalaries.id")
    deleted_asistent_salary = relationship("DeletedAsistentSalaries", backref="salary",
                                           order_by="DeletedAsistentSalaries.id")
    taken_money = Column(Integer)
    debt = Column(Integer)
    old_id = Column(Integer)
    extra = Column(Integer)
    total_fine = Column(Integer, default=0)

    def convert_json(self, entire=False):
        total = db.session.query(
            func.sum(AssistentBlackSalary.total_salary)
        ).filter(
            AssistentBlackSalary.calendar_month == self.calendar_month,
            AssistentBlackSalary.assistent_id == self.assisten_id,
            AssistentBlackSalary.location_id == self.location_id,
            AssistentBlackSalary.status == False
        ).scalar()
        return {
            "id": self.id,
            "total_salary": self.total_salary + self.extra if self.extra else self.total_salary,
            "remaining_salary": self.remaining_salary,
            "taken_money": self.taken_money,
            "debt": self.debt,
            "month": self.month.date.strftime("%Y-%m"),
            "black_salary": total if total else 0
        }


class AssistentBlackSalary(db.Model):
    __tablename__ = "asistent_black_salary"
    id = Column(Integer, primary_key=True)
    assistent_id = Column(Integer, ForeignKey('assistent.id'))
    total_salary = Column(Integer)
    location_id = Column(Integer, ForeignKey('locations.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    student_id = Column(Integer, ForeignKey("students.id"))
    salary_id = Column(Integer, ForeignKey('asistent_salary.id'))
    payment_id = Column(Integer, ForeignKey('studentpayments.id'))
    status = Column(Boolean, default=False)

    def add(self):
        db.session.add(self)
        db.session.commit()

    def convert_json(self, entire=False):
        from backend.models.models import Groups
        student = Students.query.filter(Students.id == self.student_id).first()
        group = Groups.query.filter(Groups.teacher_id == self.teacher_id).first()
        return {
            "id": self.id,
            "total_salary": self.total_salary,
            "student_name": self.student.user.name,
            "student_surname": self.student.user.surname,
            "student_id": self.student.id,
            "group_name": [gr.name if gr.teacher_id == group.teacher_id else "" for gr in student.group],
            "month": self.month.date.strftime("%Y-%m")

        }


class AssistentSalaries(db.Model):
    __tablename__ = "assistent_salaries"
    id = Column(Integer, primary_key=True)
    payment_sum = Column(Integer)
    reason = Column(String)
    payment_type_id = Column(Integer, ForeignKey('paymenttypes.id'))
    salary_location_id = Column(Integer, ForeignKey("asistent_salary.id"))
    assistent_id = Column(Integer, ForeignKey('assistent.id'))
    location_id = Column(Integer, ForeignKey('locations.id'))
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))
    by_who = Column(Integer, ForeignKey("users.id"))
    old_id = Column(Integer)
    order_id = Column(Integer, ForeignKey('book_order.id'))

    def convert_json(self, entire=False):
        from backend.models.models import CalendarDay
        return {
            "id": self.id,
            "amount": self.payment_sum,
            "type_name": "Teacher salaries",
            "payment_type": self.payment_type.name,
            "reason": self.reason,
            'date': CalendarDay.query.get(self.calendar_day).date.strftime("%d.%m.%Y"),
            "name": self.assistent.user.name if self.assistent and self.assistent.user else None,
            "surname": self.assistent.user.surname if self.assistent and self.assistent.user else None,
        }


class DeletedAsistentSalaries(db.Model):
    __tablename__ = "deleted_asistent_salaries"
    id = Column(Integer, primary_key=True)
    payment_sum = Column(Integer)
    reason = Column(String)
    payment_type_id = Column(Integer, ForeignKey('paymenttypes.id'))
    group_id = Column(Integer, ForeignKey("groups.id"))
    salary_location_id = Column(Integer, ForeignKey("asistent_salary.id"))
    assistent_id = Column(Integer, ForeignKey('assistent.id'))
    location_id = Column(Integer, ForeignKey('locations.id'))
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))
    deleted_date = Column(DateTime)
    reason_deleted = Column(String)
