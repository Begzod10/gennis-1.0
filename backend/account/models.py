from backend.group.models import Groups
from backend.models.models import Column, Integer, ForeignKey, String, Boolean, relationship, DateTime, db, \
    BigInteger, Date
from backend.models.models import func
from backend.student.models import Students


class Category(db.Model):
    __tablename__ = "category"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    number = Column(Integer)
    img = Column(String)
    number_category = Column(String)
    capitals = relationship("Capital", backref="capital_category", order_by="Capital.id", lazy="select")

    def convert_json(self, location_id=None):
        addition_categories = ConnectedCategory.query.filter(
            ConnectedCategory.main_category_id == self.id).order_by(ConnectedCategory.id).all()
        addition_categories2 = ConnectedCategory.query.filter(
            ConnectedCategory.addition_category_id == self.id).order_by(ConnectedCategory.id).all()
        all_capex_down = \
            db.session.query(func.sum(Capital.total_down_cost).filter(Capital.category_id == self.id,
                                                                      Capital.location_id == location_id,
                                                                      Capital.deleted != True)).first()[0]
        info = {
            "id": self.id,
            'name': self.name,
            "img": self.img,
            "is_delete": True if not addition_categories or not addition_categories2 else False,
            "number_category": self.number_category,
            "is_sub": True if addition_categories2 else False,
            'addition_categories': [addition_category.convert_json() for addition_category in addition_categories],
            "capitals": [],
            "total_down_cost": all_capex_down
        }
        for capital in self.capitals:
            if not capital.deleted:
                info['capitals'].append(capital.convert_json(location_id=location_id))
        return info


class ConnectedCategory(db.Model):
    __tablename__ = "connected_category"
    id = Column(Integer, primary_key=True)
    addition_category_id = Column(Integer, ForeignKey('category.id'))
    main_category_id = Column(Integer, ForeignKey('category.id'))
    first = db.relationship("Category", foreign_keys=[addition_category_id])
    second = db.relationship("Category", foreign_keys=[main_category_id])

    def convert_json(self):
        addition_categories = ConnectedCategory.query.filter(
            ConnectedCategory.main_category_id == self.addition_category_id).order_by(ConnectedCategory.id).all()
        info = {
            "id": self.first.id,
            'name': self.first.name,
            'number_category': self.first.number_category,
            "img": self.first.img,
            "is_delete": True if not self.first else False,
            "is_sub": True if self.second else False,
            'addition_categories': [addition_category.convert_json() for addition_category in addition_categories]
        }
        return info


class PaymentTypes(db.Model):
    __tablename__ = "paymenttypes"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    student_payments = relationship('StudentPayments', backref="payment_type", order_by="StudentPayments.id")
    teacher_salaries = relationship('TeacherSalaries', backref="payment_type", order_by="TeacherSalaries.id")
    overhead_data = relationship('Overhead', backref="payment_type", order_by="Overhead.id")
    overhead_type_log_payments = relationship(
        'OverheadTypeLogPayment', backref="payment_type", order_by="OverheadTypeLogPayment.id",
    )
    accounting = relationship("AccountingInfo", backref="payment_type", order_by="AccountingInfo.id")
    staff_salaries = relationship("StaffSalaries", backref="payment_type", order_by="StaffSalaries.id")
    capital = relationship("CapitalExpenditure", backref="payment_type", order_by="CapitalExpenditure.id")
    deleted_payments = relationship("DeletedStudentPayments", backref="payment_type")
    deleted_teacher_salaries = relationship("DeletedTeacherSalaries", backref="payment_type")
    deleted_capital = relationship("DeletedCapitalExpenditure", backref="payment_type")
    deleted_overhead = relationship("DeletedOverhead", backref="payment_type")
    deleted_staff_salaries = relationship("DeletedStaffSalaries", backref="payment_type")
    old_id = Column(Integer)
    center_balances_overheads = relationship("CenterBalanceOverhead", backref="payment_type", lazy="select",
                                             order_by="CenterBalanceOverhead.id")
    book_overhead = relationship("BookOverhead", backref="payment_type", order_by="BookOverhead.id", lazy="select")
    branch_payments = relationship("BranchPayment", backref="payment_type", order_by="BranchPayment.id", lazy="select")
    editor_balance = relationship("EditorBalance", backref="payment_type", order_by="EditorBalance.id", lazy="select")
    collected_payment = relationship("CollectedBookPayments", backref="payment_type",
                                     order_by="CollectedBookPayments.id",
                                     lazy="select")
    capitals = relationship("Capital", backref="payment_type", order_by="Capital.id", lazy="select")
    investment = relationship("Investment", backref="payment_type", order_by="Investment.id")
    camp_staff_salaries = relationship("CampStaffSalaries", backref="payment_type", order_by="CampStaffSalaries.id")
    account_payable = relationship("AccountPayable", backref="payment_type", order_by="AccountPayable.id")
    dividend = relationship("Dividend", backref="payment_type", order_by="Dividend.id")
    account_report = relationship("AccountReport", backref="payment_type", order_by="AccountReport.id")
    main_overhead = relationship("MainOverhead", backref="payment_type", order_by="MainOverhead.id")
    account_payable_history = relationship("AccountPayableHistory", backref="payment_type",
                                           order_by="AccountPayableHistory.id")
    assistent_salary = relationship("AssistentSalaries", backref="payment_type", order_by="AssistentSalaries.id")
    deleted_assistent_salary = relationship("DeletedAsistentSalaries", backref="payment_type",
                                            order_by="DeletedAsistentSalaries.id")


class StudentPayments(db.Model):
    __tablename__ = "studentpayments"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'))
    location_id = Column(Integer, ForeignKey('locations.id'))
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    payment_sum = Column(Integer)
    payment_type_id = Column(Integer, ForeignKey('paymenttypes.id'))
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))
    payment = Column(Boolean)
    by_who = Column(Integer, ForeignKey("users.id"))
    payment_data = Column(DateTime)
    old_id = Column(Integer)

    def convert_json(self, entire=False):
        from backend.models.models import CalendarDay
        info = {
            "id": self.id,
            'name': self.student.user.name,
            'surname': self.student.user.surname,
            "type_name": "To'lov",
            "student_id": self.student_id,
            "location_id": self.location_id,
            "date": CalendarDay.query.get(self.calendar_day).date.strftime("%d.%m.%Y"),
            "calendar_month": self.calendar_month,
            "calendar_year": self.calendar_year,
            "amount": self.payment_sum,
            "payment_type_id": self.payment_type_id,
            "payment_type": PaymentTypes.query.get(self.payment_type_id).name,
            "account_period_id": self.account_period_id,
            "payment": self.payment,
            "by_who": self.by_who,
            "payment_data": self.payment_data,
            "old_id": self.old_id
        }
        return info


class StudentCharity(db.Model):
    __tablename__ = "studentcharity"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'))
    discount = Column(Integer)
    group_id = Column(Integer, ForeignKey('groups.id'))
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))
    location_id = Column(Integer, ForeignKey('locations.id'))
    old_id = Column(Integer)


class BookPayments(db.Model):
    __tablename__ = "book_payments"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'))
    location_id = Column(Integer, ForeignKey('locations.id'))
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    payment_sum = Column(Integer)
    book_order_id = Column(Integer, ForeignKey('book_order.id'))
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))

    def add(self):
        db.session.add(self)
        db.session.commit()


class UserBooks(db.Model):
    __tablename__ = "user_books"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    location_id = Column(Integer, ForeignKey('locations.id'))
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    payment_sum = Column(Integer)
    book_order_id = Column(Integer, ForeignKey('book_order.id'))
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))
    salary_location_id = Column(Integer, ForeignKey("teachersalary.id"))
    salary_id = Column(Integer, ForeignKey('staffsalary.id'))

    def convert_json(self):
        return {
            "id": self.id,
            "salary": self.payment_sum,
            "reason": "kitobga",
            "date": self.day.date.strftime("%Y-%m-%d"),
            "status": True
        }

    def add(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class CenterBalance(db.Model):
    __tablename__ = "center_balance"
    id = Column(Integer, primary_key=True)
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))
    location_id = Column(Integer, ForeignKey('locations.id'))
    exist_money = Column(Integer)
    taken_money = Column(Integer)
    total_money = Column(Integer)
    type_income = Column(String)
    orders = relationship("CenterOrders", lazy="select", backref="balance", order_by="CenterOrders.id")
    overheads = relationship("CenterBalanceOverhead", lazy="select", backref="balance",
                             order_by="CenterBalanceOverhead.id")

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "month": self.month.date.strftime("%Y-%m"),
            "year": self.year.date.strftime("%Y"),
            "location": self.location.convert_json(),
            "exist_money": self.exist_money,
            "taken_money": self.taken_money,
            "total_money": self.total_money,
            "type_income": self.type_income,
        }

    def add(self):
        db.session.add(self)
        db.session.commit()


class EditorBalance(db.Model):
    __tablename__ = "editor_balance"
    id = Column(Integer, primary_key=True)
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))
    balance = Column(Integer, default=0)
    payment_type_id = Column(Integer, ForeignKey('paymenttypes.id'))
    payments_sum = Column(Integer)
    overheads_sum = Column(Integer)
    payments = relationship("BranchPayment", lazy="select", backref="editor_balance", order_by="BranchPayment.id")
    overheads = relationship("BookOverhead", lazy="select", backref="editor_balance", order_by="BookOverhead.id")

    def add(self):
        db.session.add(self)
        db.session.commit()

    def convert_json(self, entire=False):
        return {
            "balance": self.balance,
            "id": self.id,
            "payment_type": {
                "id": self.payment_type.id,
                "name": self.payment_type.name
            },
            "payments_sum": self.payments_sum,
            "overheads_sum": self.overheads_sum,
            "year": self.year.date.strftime("%Y"),
            "month": self.month.date.strftime("%m"),
        }


class BranchPayment(db.Model):
    __tablename__ = "branch_payment"
    id = Column(Integer, primary_key=True)
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    payment_type_id = Column(Integer, ForeignKey('paymenttypes.id'))
    location_id = Column(Integer, ForeignKey('locations.id'))
    editor_balance_id = Column(Integer, ForeignKey('editor_balance.id'))
    book_order_id = Column(Integer, ForeignKey('book_order.id'))
    payment_sum = Column(Integer)

    def add(self):
        db.session.add(self)
        db.session.commit()


class CenterOrders(db.Model):
    __tablename__ = "center_orders"
    id = Column(Integer, primary_key=True)
    balance_id = Column(Integer, ForeignKey('center_balance.id'))
    order_id = Column(Integer, ForeignKey('book_order.id'))

    def add(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class CollectedBookPayments(db.Model):
    __tablename__ = "collected_book_payments"
    id = Column(Integer, primary_key=True)
    book_orders = db.relationship("BookOrder", backref="collected", order_by="BookOrder.id", lazy="select")
    debt = Column(Integer, default=0)
    location_id = Column(Integer, ForeignKey('locations.id'))
    status = Column(Boolean, default=False)
    created_date = Column(Integer, ForeignKey('calendarday.id'))
    received_date = Column(Integer, ForeignKey('calendarday.id'))
    created = relationship("CalendarDay", foreign_keys=[created_date])
    received = relationship("CalendarDay", foreign_keys=[received_date])
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))
    payment_type_id = Column(Integer, ForeignKey('paymenttypes.id'))

    def convert_json(self, entire=False):
        received = None
        if self.received:
            received = self.received.date.strftime("%Y-%m-%d")
        payment = None
        if self.payment_type:
            payment = {
                "id": self.payment_type.id,
                "name": self.payment_type.name,
            }

        return {
            "id": self.id,
            "debt": self.debt,
            "status": self.status,
            "created": self.created.date.strftime("%Y-%m-%d"),
            "received": received,
            "month": self.month.date.strftime("%Y-%m"),
            "year": self.year.date.strftime("%Y"),
            "payment_type": payment
        }

    def add(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class CenterBalanceOverhead(db.Model):
    __tablename__ = "center_balance_overhead"
    id = Column(Integer, primary_key=True)
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    balance_id = Column(Integer, ForeignKey('center_balance.id'))
    payment_type_id = Column(Integer, ForeignKey('paymenttypes.id'))
    payment_sum = Column(Integer)
    reason = Column(String)
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))
    deleted = Column(Boolean, default=False)
    location_id = Column(Integer, ForeignKey('locations.id'))

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "day": self.day.date.strftime("%Y-%m-%d"),
            "payment_type": {
                "id": self.payment_type.id,
                "name": self.payment_type.name,
            },
            "payment_sum": self.payment_sum,
            "reason": self.reason

        }

    def add(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class DeletedBookPayments(db.Model):
    __tablename__ = "deleted_book_payments"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'))
    location_id = Column(Integer, ForeignKey('locations.id'))
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    payment_sum = Column(Integer)
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))


class DeletedStudentPayments(db.Model):
    __tablename__ = "deletedstudentpayments"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'))
    location_id = Column(Integer, ForeignKey('locations.id'))
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    payment_sum = Column(Integer)
    payment_type_id = Column(Integer, ForeignKey('paymenttypes.id'))
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))
    payment = Column(Boolean)
    deleted_date = Column(DateTime)
    reason = Column(String)


class TeacherSalaries(db.Model):
    __tablename__ = "teachersalaries"
    id = Column(Integer, primary_key=True)
    payment_sum = Column(Integer)
    reason = Column(String)
    payment_type_id = Column(Integer, ForeignKey('paymenttypes.id'))
    salary_location_id = Column(Integer, ForeignKey("teachersalary.id"))
    teacher_id = Column(Integer, ForeignKey('teachers.id'))
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
            "name": self.teacher.user.name if self.teacher and self.teacher.user else None,
            "surname": self.teacher.user.surname if self.teacher and self.teacher.user else None,
        }


class DeletedTeacherSalaries(db.Model):
    __tablename__ = "deletedteachersalaries"
    id = Column(Integer, primary_key=True)
    payment_sum = Column(Integer)
    reason = Column(String)
    payment_type_id = Column(Integer, ForeignKey('paymenttypes.id'))
    group_id = Column(Integer, ForeignKey("groups.id"))
    salary_location_id = Column(Integer, ForeignKey("teachersalary.id"))
    teacher_id = Column(Integer, ForeignKey('teachers.id'))
    location_id = Column(Integer, ForeignKey('locations.id'))
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))
    deleted_date = Column(DateTime)
    reason_deleted = Column(String)


class StaffSalaries(db.Model):
    __tablename__ = "staffsalaries"
    id = Column(Integer, primary_key=True)
    payment_sum = Column(Integer)
    reason = Column(String)
    payment_type_id = Column(Integer, ForeignKey('paymenttypes.id'))
    salary_id = Column(Integer, ForeignKey('staffsalary.id'))
    staff_id = Column(Integer, ForeignKey('staff.id'))
    location_id = Column(Integer, ForeignKey('locations.id'))
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    profession_id = Column(Integer, ForeignKey("professions.id"))
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))
    by_who = Column(Integer, ForeignKey("users.id"))
    old_id = Column(Integer)
    order_id = Column(Integer, ForeignKey('book_order.id'))

    def convert_json(self, entire=False):
        from backend.models.models import CalendarDay
        return {
            "id": self.id,
            "amount": self.payment_sum,
            "type_name": "Staff salaries",
            "payment_type": self.payment_type.name,
            'date': CalendarDay.query.get(self.calendar_day).date.strftime("%d.%m.%Y"),
            "name": self.staff.user.name if self.staff and self.staff.user else None,
            "surname": self.staff.user.surname if self.staff and self.staff.user else None,
        }


class DeletedStaffSalaries(db.Model):
    __tablename__ = "deletedstaffsalaries"
    id = Column(Integer, primary_key=True)
    payment_sum = Column(Integer)
    reason = Column(String)
    payment_type_id = Column(Integer, ForeignKey('paymenttypes.id'))
    salary_id = Column(Integer, ForeignKey('staffsalary.id'))
    staff_id = Column(Integer, ForeignKey('staff.id'))
    location_id = Column(Integer, ForeignKey('locations.id'))
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    profession_id = Column(Integer, ForeignKey("professions.id"))
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))
    deleted_date = Column(DateTime)
    reason_deleted = Column(String)


class OverheadType(db.Model):
    __tablename__ = "overheadtype"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    cost = Column(Integer, nullable=True)
    changeable = Column(Boolean, default=True, nullable=False)
    location_id = Column(Integer, ForeignKey('locations.id'), nullable=True)
    deleted = Column(Boolean, default=False)
    management_id = Column(Integer, nullable=True)
    overhead_data = relationship('Overhead', backref="overhead_type", order_by="Overhead.id")
    logs = relationship('OverheadTypeLog', backref="overhead_type", order_by="OverheadTypeLog.id")


class OverheadTypeLog(db.Model):
    __tablename__ = "overheadtypelog"
    id = Column(Integer, primary_key=True)
    overhead_type_id = Column(Integer, ForeignKey('overheadtype.id'), nullable=False)
    cost = Column(Integer, nullable=False)
    is_paid = Column(Boolean, default=False, nullable=False)
    is_prepaid = Column(Boolean, default=False, nullable=False)
    paid_date = Column(DateTime, nullable=True)
    overhead_id = Column(Integer, ForeignKey('overhead.id'), nullable=True)
    location_id = Column(Integer, ForeignKey('locations.id'), nullable=True)
    calendar_month = Column(Integer, ForeignKey('calendarmonth.id'), nullable=False)
    calendar_year = Column(Integer, ForeignKey('calendaryear.id'), nullable=False)
    deleted = Column(Boolean, default=False)
    payments = relationship(
        'OverheadTypeLogPayment',
        backref='overhead_type_log',
        order_by='OverheadTypeLogPayment.id',
    )

    @property
    def paid_amount(self) -> int:
        return sum(p.amount for p in self.payments if not p.deleted)

    @property
    def remaining_amount(self) -> int:
        return max(0, (self.cost or 0) - self.paid_amount)

    @property
    def payment_status(self) -> str:
        paid = self.paid_amount
        if paid <= 0:
            return "unpaid"
        if paid < (self.cost or 0):
            return "partial"
        return "paid"

    def convert_json(self):
        return {
            "id": self.id,
            "overhead_type_id": self.overhead_type_id,
            "overhead_type_name": self.overhead_type.name,
            "cost": self.cost,
            "is_paid": self.is_paid,
            "is_prepaid": self.is_prepaid,
            "paid_date": self.paid_date.strftime("%d.%m.%Y") if self.paid_date else None,
            "overhead_id": self.overhead_id,
            "location_id": self.location_id,
            "calendar_month": self.calendar_month,
            "calendar_year": self.calendar_year,
            "paid_amount": self.paid_amount,
            "remaining_amount": self.remaining_amount,
            "payment_status": self.payment_status,
            "payments": [p.convert_json() for p in self.payments if not p.deleted],
        }


class OverheadTypeLogPayment(db.Model):
    __tablename__ = "overheadtypelog_payment"
    id = Column(Integer, primary_key=True)
    overhead_type_log_id = Column(
        Integer, ForeignKey('overheadtypelog.id'), nullable=False,
    )
    payment_type_id = Column(Integer, ForeignKey('paymenttypes.id'), nullable=True)
    overhead_id = Column(Integer, ForeignKey('overhead.id'), nullable=True)
    amount = Column(Integer, nullable=False)
    paid_date = Column(DateTime, nullable=False)
    note = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, server_default=db.func.now())
    deleted = Column(Boolean, default=False, nullable=False)
    management_id = Column(Integer, nullable=True, unique=True)

    def convert_json(self):
        return {
            "id": self.id,
            "overhead_type_log_id": self.overhead_type_log_id,
            "payment_type_id": self.payment_type_id,
            "payment_type_name": self.payment_type.name if self.payment_type_id and self.payment_type else None,
            "overhead_id": self.overhead_id,
            "amount": self.amount,
            "paid_date": self.paid_date.strftime("%d.%m.%Y") if self.paid_date else None,
            "note": self.note,
        }


class Overhead(db.Model):
    __tablename__ = "overhead"
    id = Column(Integer, primary_key=True)
    item_sum = Column(Integer)
    item_name = Column(String)
    overhead_type_id = Column(Integer, ForeignKey('overheadtype.id'), nullable=True)
    payment_type_id = Column(Integer, ForeignKey('paymenttypes.id'))
    location_id = Column(Integer, ForeignKey('locations.id'))
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))
    by_who = Column(Integer, ForeignKey("users.id"))
    paid_for_month = Column(Integer, ForeignKey('calendarmonth.id'), nullable=True)
    paid_for_year = Column(Integer, ForeignKey('calendaryear.id'), nullable=True)
    old_id = Column(Integer)

    def convert_json(self, entire=False):
        from backend.models.models import CalendarDay

        return {
            "id": self.id,
            "amount": self.item_sum,
            "price": self.item_sum,
            "item_name": self.item_name,
            "name": self.item_name,
            "type_name": "Overhead",
            "type": "Overhead",
            "date": CalendarDay.query.get(self.calendar_day).date.strftime("%d.%m.%Y"),
            "day": self.calendar_day,
            "month": self.calendar_month,
            "year": self.calendar_year,
            "paid_for_month": self.paid_for_month,
            "paid_for_year": self.paid_for_year,
            "typePayment": self.payment_type.name,
            "overhead_type_id": self.overhead_type_id,
            "overhead_type_name": self.overhead_type.name if self.overhead_type else None,
            "reason": "",

        }


class DeletedOverhead(db.Model):
    __tablename__ = "deletedoverhead"
    id = Column(Integer, primary_key=True)
    item_sum = Column(Integer)
    item_name = Column(String)
    payment_type_id = Column(Integer, ForeignKey('paymenttypes.id'))
    location_id = Column(Integer, ForeignKey('locations.id'))
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))
    deleted_date = Column(DateTime)
    reason = Column(String)


class BranchLoan(db.Model):
    __tablename__ = "branch_loan"
    id = Column(Integer, primary_key=True)
    location_id = Column(Integer, ForeignKey('locations.id'), nullable=False)

    counterparty_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    counterparty_name = Column(String, nullable=True)
    counterparty_surname = Column(String, nullable=True)
    counterparty_phone = Column(String, nullable=True)

    direction = Column(String(8), nullable=False)  # 'out' = lent, 'in' = borrowed
    principal_amount = Column(Integer, nullable=False)

    issued_date = Column(DateTime, nullable=False)
    due_date = Column(DateTime, nullable=True)
    settled_date = Column(DateTime, nullable=True)

    reason = Column(String, nullable=True)
    notes = Column(String, nullable=True)

    status = Column(String(12), default='active')  # active | settled | cancelled
    cancelled_reason = Column(String, nullable=True)

    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    management_id = Column(Integer, unique=True, nullable=True)
    deleted = Column(Boolean, default=False)

    transactions = relationship(
        'BranchTransaction',
        backref='loan',
        primaryjoin='BranchLoan.id == BranchTransaction.loan_id',
        foreign_keys='BranchTransaction.loan_id',
    )

    def paid_total(self):
        opposite_is_give = (self.direction == 'in')
        total = 0
        for tx in self.transactions or []:
            if tx.deleted:
                continue
            if tx.is_give == opposite_is_give:
                total += int(tx.amount or 0)
        return total

    def remaining_amount(self):
        return max(0, int(self.principal_amount or 0) - self.paid_total())

    def is_settled(self):
        return self.paid_total() >= int(self.principal_amount or 0)

    def recompute_status(self):
        from datetime import date
        if self.status == 'cancelled':
            return
        if self.is_settled():
            self.status = 'settled'
            if not self.settled_date:
                self.settled_date = date.today()
        else:
            self.status = 'active'
            self.settled_date = None

    def counterparty_payload(self):
        from backend.models.models import Users
        if self.counterparty_id:
            user = Users.query.get(self.counterparty_id)
            return {
                'id': self.counterparty_id,
                'name': user.name if user else None,
                'surname': user.surname if user else None,
                'phone': getattr(user, 'phone', None) if user else None,
            }
        return {
            'id': None,
            'name': self.counterparty_name,
            'surname': self.counterparty_surname,
            'phone': self.counterparty_phone,
        }

    def convert_json(self, with_transactions=False):
        principal = int(self.principal_amount or 0)
        paid = self.paid_total()
        data = {
            'id': self.id,
            'location_id': self.location_id,
            'counterparty': self.counterparty_payload(),
            'direction': self.direction,
            'principal_amount': principal,
            'paid_total': paid,
            'remaining_amount': max(0, principal - paid),
            'is_settled': paid >= principal,
            'issued_date': self.issued_date.strftime('%Y-%m-%d') if self.issued_date else None,
            'due_date': self.due_date.strftime('%Y-%m-%d') if self.due_date else None,
            'settled_date': self.settled_date.strftime('%Y-%m-%d') if self.settled_date else None,
            'reason': self.reason,
            'notes': self.notes,
            'status': self.status,
            'cancelled_reason': self.cancelled_reason,
            'management_id': self.management_id,
        }
        if with_transactions:
            data['transactions'] = [
                tx.convert_json() for tx in (self.transactions or [])
                if not tx.deleted
            ]
        return data


class BranchTransaction(db.Model):
    __tablename__ = "branchtransaction"
    id = Column(Integer, primary_key=True)
    amount = Column(Integer, nullable=False)
    is_give = Column(Boolean, nullable=False)
    reason = Column(String, nullable=True)
    person_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    person_name = Column(String, nullable=True)
    person_surname = Column(String, nullable=True)
    person_phone = Column(String, nullable=True)
    payment_type_id = Column(Integer, ForeignKey('paymenttypes.id'), nullable=False)
    location_id = Column(Integer, ForeignKey('locations.id'), nullable=False)
    calendar_day = Column(Integer, ForeignKey('calendarday.id'), nullable=False)
    calendar_month = Column(Integer, ForeignKey('calendarmonth.id'), nullable=False)
    calendar_year = Column(Integer, ForeignKey('calendaryear.id'), nullable=False)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    loan_id = Column(Integer, ForeignKey('branch_loan.id'), nullable=True)
    deleted = Column(Boolean, default=False)
    payment_type = relationship('PaymentTypes', foreign_keys=[payment_type_id])

    def convert_json(self):
        from backend.models.models import CalendarDay, Users
        person = None
        if self.person_id:
            user = Users.query.get(self.person_id)
            if user:
                person = {'id': user.id, 'name': user.name, 'surname': user.surname}
        else:
            person = {
                'id': None,
                'name': self.person_name,
                'surname': self.person_surname,
                'phone': self.person_phone
            }
        return {
            'id': self.id,
            'amount': self.amount,
            'is_give': self.is_give,
            'direction': 'give' if self.is_give else 'receive',
            'reason': self.reason,
            'person': person,
            'payment_type': self.payment_type.name,
            'location_id': self.location_id,
            'date': CalendarDay.query.get(self.calendar_day).date.strftime('%d.%m.%Y'),
            'calendar_day': self.calendar_day,
            'calendar_month': self.calendar_month,
            'calendar_year': self.calendar_year,
            'loan_id': self.loan_id,
        }


class CapitalCategory(db.Model):
    __tablename__ = "capital_category"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    number = Column(String)

    def convert_json(self, entire=False):
        info = {
            "name": self.name,
            "number": self.number,
            "capitals": []
        }
        for capital in self.capitals:
            info['capitals'].append(capital.convert_json())
        return info

    def add(self):
        db.session.add(self)
        db.session.commit()


class Capital(db.Model):
    __tablename__ = "capital"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    number = Column(String)
    price = Column(BigInteger)
    term = Column(Integer)
    img = Column(String)
    category_id = Column(Integer, ForeignKey('category.id'))
    location_id = Column(Integer, ForeignKey('locations.id'))
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    calendar_year = Column(Integer, ForeignKey('calendaryear.id'))
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))
    payment_type_id = Column(Integer, ForeignKey('paymenttypes.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    total_down_cost = Column(BigInteger)
    deleted = Column(Boolean, default=False)
    term_info = relationship("CapitalTerm", backref="capital", order_by="CapitalTerm.id", lazy="select")

    def convert_json(self, entire=False, location_id=None):

        if location_id and self.location_id == location_id:
            return {
                "id": self.id,
                "name": self.name,
                "type_name": "Capital",
                "number": self.number,
                "price": self.price,
                "amount": self.price,
                "date": self.day.date.strftime("%Y-%m-%d"),
                "term": self.term,
                "category": {
                    "id": self.capital_category.id,
                    "name": self.capital_category.name,

                },
                "total_down_cost": self.total_down_cost,
                "img": self.img,
                "day": self.day.date.strftime("%d"),
                "month": self.day.date.strftime("%m"),
                "year": self.day.date.strftime("%Y"),
                "payment_type": {
                    "id": self.payment_type.id,
                    "name": self.payment_type.name,
                }

            }
        else:
            return {
                "id": self.id,
                "type_name": "Capital",
                "amount": self.price,
                'date': self.day.date.strftime("%d.%m.%Y"),
            }

    def add(self):
        db.session.add(self)
        db.session.commit()


class CapitalTerm(db.Model):
    __tablename__ = "capital_term"
    id = Column(Integer, primary_key=True)
    capital_id = Column(Integer, ForeignKey('capital.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    down_cost = Column(Integer)
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))

    def add(self):
        db.session.add(self)
        db.session.commit()

    def convert_json(self, entire=False):
        return {
            "capital": self.capital.convert_json(),
            "date": self.month.date.strftime("%Y-%m"),
            "down_cost": -self.down_cost,
            "id": self.id
        }


class CapitalExpenditure(db.Model):
    __tablename__ = "capital_expenditure"
    id = Column(Integer, primary_key=True)
    item_sum = Column(Integer)
    item_name = Column(String)
    payment_type_id = Column(Integer, ForeignKey('paymenttypes.id'))
    location_id = Column(Integer, ForeignKey('locations.id'))
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))
    by_who = Column(Integer, ForeignKey("users.id"))
    old_id = Column(Integer)

    def convert_json(self, entire=False):
        return {
            "id": self.id,

            "date": self.day.date.strftime("%Y-%m-%d"),
            "day": self.calendar_day,
            "month": self.calendar_month,
            "name": self.item_name,
            "price": self.item_sum,
            "typePayment": self.payment_type.name,
            "year": self.calendar_year,

        }


class DeletedCapitalExpenditure(db.Model):
    __tablename__ = "deleted_capital"
    id = Column(Integer, primary_key=True)
    item_sum = Column(Integer)
    item_name = Column(String)
    payment_type_id = Column(Integer, ForeignKey('paymenttypes.id'))
    location_id = Column(Integer, ForeignKey('locations.id'))
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))
    deleted_date = Column(DateTime)
    reason = Column(String)


class AccountingInfo(db.Model):
    __tablename__ = "accountinginfo"
    id = Column(Integer, primary_key=True)
    payment_type_id = Column(Integer, ForeignKey('paymenttypes.id'))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    location_id = Column(Integer, ForeignKey('locations.id'))
    all_payments = Column(Integer, default=0)
    all_teacher_salaries = Column(BigInteger, default=0)
    all_staff_salaries = Column(BigInteger, default=0)
    all_overhead = Column(BigInteger, default=0)
    all_capital = Column(BigInteger, default=0)
    all_charity = Column(BigInteger, default=0)
    all_investment = Column(BigInteger, default=0)
    all_dividend = Column(BigInteger, default=0)
    current_cash = Column(BigInteger, default=0)
    old_cash = Column(Integer, default=0)
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))

    def add(self):
        db.session.add(self)
        db.session.commit()


class OtherInfo(db.Model):
    __tablename__ = "other_info"
    id = Column(Integer, primary_key=True)
    all_discount = Column(Integer, default=0)
    debtors_red_num = Column(Integer, default=0)
    debtors_yel_num = Column(Integer, default=0)
    registered_students = Column(Integer, default=0)
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    location_id = Column(Integer, ForeignKey('locations.id'))

    def add(self):
        db.session.add(self)
        db.session.commit()


class TeacherSalary(db.Model):
    __tablename__ = "teachersalary"
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey('teachers.id'))
    total_salary = Column(Integer)
    remaining_salary = Column(Integer)
    location_id = Column(Integer, ForeignKey('locations.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    status = Column(Boolean, default=False)

    teacher_cash = relationship('TeacherSalaries', backref="salary", order_by="TeacherSalaries.id")
    deleted_teacher_salary = relationship("DeletedTeacherSalaries", backref="salary",
                                          order_by="DeletedTeacherSalaries.id")
    taken_money = Column(Integer)
    debt = Column(Integer)
    old_id = Column(Integer)
    extra = Column(Integer)
    total_fine = Column(Integer, default=0)

    def convert_json(self, entire=False):
        total = db.session.query(
            func.sum(TeacherBlackSalary.total_salary)
        ).filter(
            TeacherBlackSalary.calendar_month == self.calendar_month,
            TeacherBlackSalary.teacher_id == self.teacher_id,
            TeacherBlackSalary.location_id == self.location_id,
            TeacherBlackSalary.status == False
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


class TeacherBlackSalary(db.Model):
    __tablename__ = "teacher_black_salary"
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey('teachers.id'))
    total_salary = Column(Integer)
    location_id = Column(Integer, ForeignKey('locations.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    student_id = Column(Integer, ForeignKey("students.id"))
    salary_id = Column(Integer, ForeignKey('teachersalary.id'))
    payment_id = Column(Integer, ForeignKey('studentpayments.id'))
    status = Column(Boolean, default=False)

    def add(self):
        db.session.add(self)
        db.session.commit()

    def convert_json(self, entire=False):
        student = Students.query.filter(Students.id == self.student_id).first()
        for gr in student.group:
            if gr.teacher_id == self.teacher_id:
                group_name = gr.name
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


class StaffSalary(db.Model):
    __tablename__ = "staffsalary"
    id = Column(Integer, primary_key=True)
    staff_id = Column(Integer, ForeignKey('staff.id'))
    total_salary = Column(Integer)
    remaining_salary = Column(Integer)
    location_id = Column(Integer, ForeignKey('locations.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    status = Column(Boolean, default=False)
    taken_money = Column(Integer)
    staff_given_salary = relationship("StaffSalaries", backref="staff_salary", order_by="StaffSalaries.id")
    staff_deleted_salary = relationship("DeletedStaffSalaries", backref="staff_salary",
                                        order_by="DeletedStaffSalaries.id")
    old_id = Column(Integer)


class Investment(db.Model):
    __tablename__ = "investment"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    amount = Column(Integer)
    location_id = Column(Integer, ForeignKey('locations.id'))
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))
    payment_type_id = Column(Integer, ForeignKey('paymenttypes.id'))
    deleted_status = Column(Boolean, default=False)
    reason = Column(String)

    def add(self):
        db.session.add(self)
        db.session.commit()

    def convert_json(self, entire=False, relationship=None):
        return {
            "id": self.id,
            "name": self.name,
            "amount": self.amount,
            "month": self.month.date.strftime("%Y-%m"),
            "year": self.year.date.strftime("%Y"),
            "date": self.day.date.strftime("%Y-%m-%d"),
            "typePayment": self.payment_type.name,
            # "location": self.location.name if self.location else self.reason,
            "reason": self.location.name if self.location else self.reason,
            "type_name": "Investitsiya"
        }


class ManagementDividend(db.Model):
    __tablename__ = "management_dividend"
    id = Column(Integer, primary_key=True)
    management_id = Column(Integer, unique=True)
    amount = Column(Integer)
    date = Column(Date)
    description = Column(String)
    payment_type = Column(String(255))
    location_id = Column(Integer, ForeignKey('locations.id'))
    deleted = Column(Boolean, default=False)

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "management_id": self.management_id,
            "amount": self.amount,
            "type_name": "Management Dividend",
            "date": self.date.strftime("%Y-%m-%d") if self.date else None,
            "description": self.description,
            "payment_type": self.payment_type,
            "location_id": self.location_id,
            "deleted": self.deleted,
        }

    def add(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        self.deleted = True
        db.session.commit()


class ManagementInvestment(db.Model):
    __tablename__ = "management_investment"
    id = Column(Integer, primary_key=True)
    management_id = Column(Integer, unique=True)
    amount = Column(Integer)
    date = Column(Date)
    description = Column(String)
    payment_type = Column(String(255))
    location_id = Column(Integer, ForeignKey('locations.id'))
    deleted = Column(Boolean, default=False)

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "management_id": self.management_id,
            "amount": self.amount,
            "type_name": "Management Investment",
            "date": self.date.strftime("%Y-%m-%d") if self.date else None,
            "description": self.description,
            "payment_type": self.payment_type,
            "location_id": self.location_id,
            "deleted": self.deleted,
        }

    def add(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        self.deleted = True
        db.session.commit()


class FineReport(db.Model):
    __tablename__ = "finereport"
    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey('teachers.id'))
    assistant_id = Column(Integer, ForeignKey('assistent.id'))
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))
    teacher_salary_id = Column(Integer, ForeignKey('teachersalary.id'))
    assistent_salary_id = Column(Integer, ForeignKey('asistent_salary.id'))
    amount = Column(Integer)
    reason = Column(String)

    def add(self):
        db.session.add(self)
        db.session.commit()

    def convert_json(self, entire=False, relationship=None):
        return {
            "id": self.id,
            "salary": self.amount,
            "month": self.month.date.strftime("%Y-%m"),
            "year": self.year.date.strftime("%Y"),
            "date": self.day.date.strftime("%Y-%m-%d"),
            "reason": self.reason,
            "type_name": "Fines"
        }
