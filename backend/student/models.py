from backend.models.models import Column, Integer, ForeignKey, String, Boolean, relationship, DateTime, db
from backend.models.utils import clone_group_info


class StudentHistoryGroups(db.Model):
    __tablename__ = "studenthistorygroups"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'))
    group_id = Column(Integer, ForeignKey('groups.id'))
    teacher_id = Column(Integer, ForeignKey('teachers.id'))
    joined_day = Column(DateTime)
    left_day = Column(DateTime)
    reason = Column(String)
    old_id = Column(Integer)


class StudentExcuses(db.Model):
    __tablename__ = "studentexcuses"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    reason = Column(String)
    to_date = Column(DateTime)
    added_date = Column(DateTime)
    old_id = Column(Integer)

    def convert_json(self, entire=False):
        info = {
            'id': self.id,
            'student_id': self.student_id,
            'comment': self.reason,
            'to_date': self.to_date.strftime("%Y-%m-%d") if self.to_date else None,
            'added_date': self.added_date.strftime("%Y-%m-%d") if self.added_date else None,
            'old_id': self.old_id
        }
        return info


class StudentDebt(db.Model):
    __tablename__ = "student_debt"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime)
    student_id = Column(Integer, ForeignKey("students.id"))
    student_debt_comments = relationship("StudentDebtComment", backref="student_debt", order_by="StudentDebtComment.id")

    def add(self):
        db.session.add(self)
        db.session.commit()


class StudentDebtComment(db.Model):
    __tablename__ = "student_debt_comment"
    id = Column(Integer, primary_key=True)
    student_debt_id = Column(Integer, ForeignKey("student_debt.id"))
    comment = Column(String)
    debt_date = Column(DateTime)
    date = Column(DateTime)

    def add(self):
        db.session.add(self)
        db.session.commit()

    def json(self):
        if self.date and self.date == None:
            date = self.date.strftime('%Y-%m-%d')
        else:
            date = None
        info = {
            'comment': self.comment,
            'date': date
        }
        return info


class Students(db.Model):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    subject = relationship('Subjects', secondary="student_subject", backref="student", order_by="Subjects.id")
    group = relationship('Groups', secondary="student_group", backref="student", lazy="select")
    parent_get = relationship('Parent', secondary="parent_child", backref="student", lazy="select")
    ball_time = Column(DateTime)
    attendance = relationship("Attendance", backref="student", order_by="Attendance.id")
    attendance_days = relationship("AttendanceDays", backref="student", order_by="AttendanceDays.id")
    student_payment = relationship('StudentPayments', backref="student", order_by="StudentPayments.id")
    attendance_history = relationship("AttendanceHistoryStudent", backref="student",
                                      order_by="AttendanceHistoryStudent.id")
    charity = relationship('StudentCharity', backref="student", order_by="StudentCharity.id", lazy="select")
    history_group = relationship('StudentHistoryGroups', backref="student", order_by="StudentHistoryGroups.id")
    deleted_payments = relationship("DeletedStudentPayments", backref="student", order_by="DeletedStudentPayments.id")
    excuses = relationship("StudentExcuses", backref="student", order_by="StudentExcuses.id")
    combined_debt = Column(Integer)
    debtor = Column(Integer)
    extra_payment = Column(Integer)
    deleted_from_group = relationship("DeletedStudents", backref="student", order_by="DeletedStudents.id")
    deleted_from_register = relationship("RegisterDeletedStudents", backref="student",
                                         order_by="RegisterDeletedStudents.id")
    representative_name = Column(String)
    representative_surname = Column(String)
    contract_word_url = Column(String)
    contract_pdf_url = Column(String)
    old_debt = Column(Integer)
    old_money = Column(Integer)
    old_id = Column(Integer)
    morning_shift = Column(Boolean)
    night_shift = Column(Boolean)
    reasons_list = relationship("StudentExcuses", backref="student_get", order_by="StudentExcuses.id", lazy="select")
    time_table = relationship("Group_Room_Week", secondary="time_table_student", backref="student",
                              order_by="Group_Room_Week.id",
                              lazy="select")
    book_payments = relationship("BookPayments", backref='student', order_by='BookPayments.id', lazy='select')
    del_book_payments = relationship("DeletedBookPayments", backref='student', order_by='DeletedBookPayments.id',
                                     lazy='select')
    book_order = relationship("BookOrder", backref="student", order_by="BookOrder.id", lazy="select")
    black_salary = relationship("TeacherBlackSalary", backref="student", order_by="TeacherBlackSalary.id",
                                lazy="select")
    lesson_plan = relationship("LessonPlanStudents", uselist=False, backref="student", order_by="LessonPlanStudents.id")
    student_certificate = relationship("StudentCertificate", backref="student", order_by="StudentCertificate.id")
    student_debts = relationship("StudentDebt", backref="student", order_by="StudentDebt.id", lazy="select")
    student_tests = relationship("StudentTest", backref="student", order_by="StudentTest.id", lazy="select")
    student_calling_info = relationship("StudentCallingInfo", backref="student", order_by="StudentCallingInfo.id")
    students_tasks = relationship("TaskStudents", backref="student", order_by="TaskStudents.id")

    def convert_json(self, entire=False):
        # phone = self.user.phone[0].phone if self.user.phone[0].phone != 0 else self.user.phone[1].phone
        return {
            "id": self.user.id,
            "name": self.user.name.title(),
            "surname": self.user.surname.title(),
            "username": self.user.username,
            "language": self.user.language.name,
            "age": self.user.age,
            "reg_date": self.user.day.date.strftime("%Y-%m-%d"),
            "comment": self.user.comment,
            "role": self.user.role_info.type_role,
            "photo_profile": self.user.photo_profile,
            "location_id": self.user.location_id,
            "balance": self.user.balance,
            "moneyType": ["green", "yellow", "red", "navy", "black"][self.debtor] if self.debtor != None else 0,
            'subjects': [subject.name for subject in self.subject],
            "phone": self.user.phone[0].phone if self.user.phone[0].phone != 0 else 0,
            "parent": self.user.phone[1].phone if self.user.phone[1].phone != 0 else 0,
            "reason": self.excuses[len(self.excuses) - 1].reason if self.excuses else None,
            "debtor": self.debtor
        }

    def convert_groups(self):
        info = {
            "subjects": [],
            "group": [],
            "deleted_groups": [],
            "debtor": self.debtor,
            "name": self.user.name,
            "surname": self.user.surname,
            'father_name': self.user.father_name
        }
        for subject in self.subject:
            info['subjects'].append(
                {
                    "id": subject.id,
                    "name": subject.name,
                    "ball_number": subject.ball_number
                }
            )
        for group in self.group:
            if not group.deleted:
                group_info = clone_group_info(group)
                info['group'].append(group_info)
            else:
                info['deleted_groups'].append(clone_group_info(group))
        return info


class StudentCallingInfo(db.Model):
    __tablename__ = "studentcallinginfo"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'))
    comment = Column(String)
    day = Column(DateTime)
    date = Column(DateTime)

    def add(self):
        db.session.add(self)
        db.session.commit()

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "comment": self.comment,
            "to_date": self.day.strftime("%Y-%m-%d"),
            "added_date": self.date.strftime("%Y-%m-%d")
        }


class Contract_Students(db.Model):
    __tablename__ = "contract_students"
    id = Column(Integer, primary_key=True)
    created_date = Column(DateTime)
    expire_date = Column(DateTime)
    student_id = Column(Integer, ForeignKey("students.id"))
    given_place = Column(String)
    given_time = Column(String)
    place = Column(String)
    father_name = Column(String)
    passport_series = Column(String)


class Contract_Students_Data(db.Model):
    __tablename__ = "contract_students_data"
    id = Column(Integer, primary_key=True)
    year = Column(DateTime)
    number = Column(Integer)
    location_id = Column(Integer, ForeignKey('locations.id'))


class Debtor_Reasons(db.Model):
    __tablename__ = "debtor_reasons"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    reason = Column(String)
    calendar_day = Column(Integer, ForeignKey("calendarday.id"))


class DeletedStudents(db.Model):
    __tablename__ = "deleted_students"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'))
    reason = Column(String)
    group_id = Column(Integer, ForeignKey("groups.id"))
    teacher_id = Column(Integer, ForeignKey("teachers.id"))
    calendar_day = Column(Integer, ForeignKey("calendarday.id"))
    reason_id = Column(Integer, ForeignKey('group_reason.id'))


class RegisterDeletedStudents(db.Model):
    __tablename__ = "register_deleted_students"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'))
    reason = Column(String)
    calendar_day = Column(Integer, ForeignKey("calendarday.id"))  # relationship qilinmagan


class StudentTest(db.Model):
    __tablename__ = "student_test"
    id = Column(Integer, primary_key=True)
    percentage = Column(String)
    true_answers = Column(Integer)
    student_id = Column(Integer, ForeignKey('students.id'))
    group_test_id = Column(Integer, ForeignKey('group_test.id'))
    group_id = Column(Integer, ForeignKey('groups.id'))
    subject_id = Column(Integer, ForeignKey('subjects.id'))
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))

    def add(self):
        db.session.add(self)
        db.session.commit()

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "percentage": f"{self.percentage}%",
            "true_answers": self.true_answers,
            "student_name": self.student.user.name,
            "student_surname": self.student.user.surname,
            "student_id": self.student.user.id,
            "test_info": {
                "id": self.group_test.id if self.group_test else None,
                "name": self.group_test.name if self.group_test else None,
                "level": self.group_test.level if self.group_test else None
            },
            "date": self.day.date.strftime("%Y-%m-%d"),
            "group_id": self.group_id,
            "subject_id": self.subject_id,
            "group_name": self.group.name,
            "subject_name": self.subject.name
        }
