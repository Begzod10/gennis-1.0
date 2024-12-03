from backend.models.models import Column, Integer, ForeignKey, String, Boolean, relationship, DateTime, db, \
    contains_eager, BigInteger, JSON


class CampStaff(db.Model):
    __tablename__ = "camp_staff"
    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.BigInteger, ForeignKey("users.id"), nullable=False)
    salaries = db.relationship('CampStaffSalary', backref='camp_staff', lazy=True)
    role_id = Column(Integer, ForeignKey("roles.id"))
    staff_salaries = db.relationship('CampStaffSalaries', backref='camp_staff', lazy=True)
    salary = Column(Integer)
    deleted = Column(Boolean, default=False)
    deleted_comment = Column(String)

    def add(self):
        db.session.add(self)
        db.session.commit()

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "surname": self.user.surname,
            "name": self.user.name,
            "username": self.user.username,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "role": self.role_info.type_role,
            "salary": self.salary,
            "deleted": self.deleted,
            "deleted_comment": self.deleted_comment,
            "phone": self.user.phone[0].phone
        }


class CampStaffSalary(db.Model):
    __tablename__ = "camp_staff_salary"
    id = db.Column(db.BigInteger, primary_key=True)
    total_salary = db.Column(db.BigInteger, nullable=False)
    remaining_salary = db.Column(db.BigInteger, nullable=False)
    taken_money = db.Column(db.BigInteger, nullable=False)
    camp_staff_id = db.Column(db.BigInteger, db.ForeignKey("camp_staff.id"), nullable=False)
    year_id = db.Column(db.BigInteger, ForeignKey("calendaryear.id"), nullable=False)
    month_id = db.Column(db.BigInteger, ForeignKey("calendarmonth.id"), nullable=False)

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "salary": self.total_salary,
            "residue": self.remaining_salary,
            "camp_staff_id": self.camp_staff_id,
            "taken_salary": self.taken_money,
            "year_id": self.year_id,
            "month_id": self.month_id,
            "date": self.month.date.strftime("%Y-%m"),
        }


class AccountReport(db.Model):
    __tablename__ = "account_report"
    id = db.Column(db.BigInteger, primary_key=True)
    payment_type_id = db.Column(db.BigInteger, ForeignKey("paymenttypes.id"), nullable=False)
    month_id = db.Column(db.Integer, ForeignKey("calendarmonth.id"), nullable=False)
    year_id = db.Column(db.Integer, ForeignKey("calendaryear.id"), nullable=False)
    all_dividend = db.Column(db.BigInteger, nullable=False)
    all_salaries = Column(db.BigInteger, nullable=False)
    all_overheads = Column(db.BigInteger, nullable=False)
    paid_payables = Column(db.BigInteger, nullable=False)
    unpaid_payables = Column(db.BigInteger, nullable=False)
    returned_receivables = Column(db.BigInteger, nullable=False)
    unreturned_receivables = Column(db.BigInteger, nullable=False)
    balance = Column(db.BigInteger, nullable=False)


    def add(self):
        db.session.add(self)
        db.session.commit()

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "payment_type_id": self.payment_type_id,
            "payment_type_name": self.payment_type.name,
            "month_id": self.month_id,
            "year_id": self.year_id,
            "date": self.month.date.strftime("%Y-%m"),
            "all_dividend": self.all_dividend,
            "all_salaries": self.all_salaries,
            "all_overheads": self.all_overheads,
            "balance": self.balance
        }


class CampStaffSalaries(db.Model):
    __tablename__ = "camp_staff_salaries"
    id = db.Column(db.BigInteger, primary_key=True)
    reason = db.Column(db.String, nullable=False)
    day_id = db.Column(db.BigInteger, ForeignKey("calendarday.id"), nullable=False)
    amount_sum = db.Column(db.BigInteger, nullable=False)
    month_id = db.Column(db.BigInteger, ForeignKey("calendarmonth.id"), nullable=False)
    year_id = db.Column(db.BigInteger, ForeignKey("calendaryear.id"), nullable=False)
    salary_id = db.Column(db.BigInteger, ForeignKey("camp_staff_salary.id"), db.ForeignKey("camp_staff_salary.id"),
                          nullable=False)
    payment_type_id = db.Column(db.BigInteger, ForeignKey("paymenttypes.id"), nullable=False)
    camp_staff_id = db.Column(db.BigInteger, db.ForeignKey("camp_staff.id"), nullable=False)
    deleted = Column(Boolean, default=False)
    deleted_comment = Column(String)

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "day": self.day.date.strftime("%Y-%m-%d"),
            "month": self.month.date.strftime("%Y-%m"),
            "year_id": self.year.date.strftime("%Y"),
            "amount_sum": self.amount_sum,
            "payment_type_id": self.payment_type_id,
            "payment_type_name": self.payment_type.name,
            "salary_id": self.salary_id,
            "camp_staff_id": self.camp_staff_id,
            "reason": self.reason,
            "status": self.deleted,
            "name": self.camp_staff.user.name,
            "surname": self.camp_staff.user.surname
        }


class Account(db.Model):
    __tablename__ = "account"
    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.Text)
    balance = db.Column(db.BigInteger)
    payables = db.relationship('AccountPayable', backref='account', lazy=True)

    def convert_json(self, entire=False):
        return {
            "name": self.name,
            "balance": self.balance
        }

    def add(self):
        db.session.add(self)
        db.session.commit()


class AccountPayable(db.Model):
    __tablename__ = "account_payable"
    id = db.Column(db.BigInteger, primary_key=True)
    payment_type_id = db.Column(db.BigInteger, ForeignKey("paymenttypes.id"), nullable=False)
    account_id = db.Column(db.BigInteger, ForeignKey("account.id"), nullable=False)
    status = db.Column(db.Boolean, nullable=False)
    finished = db.Column(db.Boolean, nullable=False)
    location_id = db.Column(db.BigInteger, ForeignKey("locations.id"), nullable=False)
    desc = db.Column(db.Text, nullable=False)
    amount_sum = Column(Integer, default=0)
    day_id = db.Column(db.Integer, ForeignKey("calendarday.id"), nullable=False)
    month_id = db.Column(db.Integer, ForeignKey("calendarmonth.id"), nullable=False)
    year_id = db.Column(db.Integer, ForeignKey("calendaryear.id"), nullable=False)
    deleted = Column(Boolean, default=False)
    deleted_comment = Column(String)

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "date": self.day.date.strftime("%Y-%m-%d"),
            "month": self.month.date.strftime("%Y-%m"),
            "year_id": self.year.date.strftime("%Y"),
            "location_id": self.location_id,
            "location": self.location.name if self.location else "",
            "amount": self.amount_sum,
            "payment_type": {
                "id": self.payment_type_id,
                "name": self.payment_type.name
            },
            "payment_type_id": self.payment_type_id,
            "payment_type_name": self.payment_type.name,
            "desc": self.desc,
            "status": self.status
        }


class Dividend(db.Model):
    __tablename__ = "dividend"
    id = db.Column(db.BigInteger, primary_key=True)
    day_id = db.Column(db.Integer, ForeignKey("calendarday.id"), nullable=False)
    month_id = db.Column(db.Integer, ForeignKey("calendarmonth.id"), nullable=False)
    year_id = db.Column(db.Integer, ForeignKey("calendaryear.id"), nullable=False)
    location_id = db.Column(db.Integer, ForeignKey("locations.id"), nullable=False)
    amount_sum = db.Column(db.BigInteger, nullable=False)
    payment_type_id = db.Column(db.Integer, ForeignKey("paymenttypes.id"), nullable=False)
    desc = Column(String)
    account_period_id = Column(Integer, ForeignKey('accountingperiod.id'))
    deleted = Column(Boolean, default=False)
    deleted_comment = Column(String)

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "day": self.day.date.strftime("%Y-%m-%d"),
            "month": self.month.date.strftime("%Y-%m"),
            "year_id": self.year.date.strftime("%Y"),
            "location_id": self.location_id,
            "location": self.location.name,
            "amount": self.amount_sum,
            "payment_type": {
                "id": self.payment_type_id,
                "name": self.payment_type.name
            },
            "payment_type_id": self.payment_type_id,
            "payment_type_name": self.payment_type.name,
            "date": self.day.date.strftime("%Y-%m-%d"),
            "desc": self.desc,
            "status": self.deleted

        }


class MainOverhead(db.Model):
    __tablename__ = "main_overhead"
    id = db.Column(db.BigInteger, primary_key=True)
    day_id = db.Column(db.Integer, ForeignKey("calendarday.id"), nullable=False)
    month_id = db.Column(db.Integer, ForeignKey("calendarmonth.id"), nullable=False)
    year_id = db.Column(db.Integer, ForeignKey("calendaryear.id"), nullable=False)
    amount_sum = db.Column(db.BigInteger, nullable=False)
    payment_type_id = db.Column(db.Integer, ForeignKey("paymenttypes.id"), nullable=False)
    deleted = Column(Boolean, default=False)
    reason = Column(String)
    deleted_comment = Column(String)

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "day": self.day.date.strftime("%Y-%m-%d"),
            "month": self.month.date.strftime("%Y-%m"),
            "year_id": self.year.date.strftime("%Y"),
            "amount_sum": self.amount_sum,
            "payment_type_id": self.payment_type_id,
            "payment_type_name": self.payment_type.name,
            "status": self.deleted,
            "reason": self.reason
        }
