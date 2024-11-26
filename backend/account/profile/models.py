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
            "user_id": self.user_id,
            "profession_id": self.profession_id,
            "profession_name": self.profession.name,
            "salary": self.salary,
            "deleted": self.deleted,
            "deleted_comment": self.deleted_comment
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
            "amount_sum": self.amount_sum,
            "camp_staff_id": self.camp_staff_id,
            "year_id": self.year_id,
            "month_id": self.month_id,
            "month_name": self.month.name,
            "year_name": self.year.name
        }


class BranchReport(db.Model):
    __tablename__ = "branch_report"
    id = db.Column(db.BigInteger, primary_key=True)
    payment_type_id = db.Column(db.BigInteger, ForeignKey("paymenttypes.id"), nullable=False)
    month_id = db.Column(db.Integer, ForeignKey("calendarmonth.id"), nullable=False)
    year_id = db.Column(db.Integer, ForeignKey("calendaryear.id"), nullable=False)
    location_id = db.Column(db.Integer, ForeignKey("locations.id"), nullable=False)
    all_divident = db.Column(db.BigInteger, nullable=False)

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "payment_type_id": self.payment_type_id,
            "payment_type_name": self.payment_type.name,
            "month_id": self.month_id,
            "year_id": self.year_id,
            "year_name": self.year.name,
            "month_name": self.month.name,
            "location_id": self.location_id,
            "all_divident": self.all_divident
        }


class CampStaffSalaries(db.Model):
    __tablename__ = "camp_staff_salaries"
    id = db.Column(db.BigInteger, primary_key=True)
    reason = db.Column(db.BigInteger, nullable=False)
    account_period_id = db.Column(db.BigInteger, ForeignKey("accountingperiod.id"), nullable=False)
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
            "desc": self.desc,
            "status": self.status,
            "reason": self.reason
        }


class AccountPayable(db.Model):
    __tablename__ = "account_payable"
    id = db.Column(db.BigInteger, primary_key=True)
    payment_type_id = db.Column(db.BigInteger, ForeignKey("paymenttypes.id"), nullable=False)
    status = db.Column(db.Boolean, nullable=False)
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
            "day": self.day.date.strftime("%Y-%m-%d"),
            "month": self.month.date.strftime("%Y-%m"),
            "year_id": self.year.date.strftime("%Y"),
            "location_id": self.location_id,
            "location_name": self.location.name if self.location else "",
            "amount_sum": self.amount_sum,
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
    deleted = Column(Boolean, default=False)
    deleted_comment = Column(String)

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "day": self.day.date.strftime("%Y-%m-%d"),
            "month": self.month.date.strftime("%Y-%m"),
            "year_id": self.year.date.strftime("%Y"),
            "location_id": self.location_id,
            "location_name": self.location.name,
            "amount_sum": self.amount_sum,
            "payment_type_id": self.payment_type_id,
            "payment_type_name": self.payment_type.name,
            "desc": self.desc

        }
