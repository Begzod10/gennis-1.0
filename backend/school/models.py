from backend.models.models import Column, Users, Integer, ForeignKey, String, relationship, db, Date, Boolean
from backend.school.list.regions import provinces_data, districts_data
from flask.cli import with_appcontext
import click
from flask_migrate import upgrade, migrate


@click.command("custom-migrate")
@with_appcontext
def custom_migrate():
    # Your custom logic
    print("Running pre-migrate tasks...")
    for region in provinces_data:
        region = Region(**region)
        region.add()
    for district in districts_data:
        district = District(**district)
        district.add()
    migrate()

    print("Migrate command completed!")


def register_commands(app):
    app.cli.add_command(custom_migrate)


class Region(db.Model):
    __tablename__ = "region"
    id = Column(Integer, primary_key=True)
    name_uz = Column(String, nullable=False)
    name_ru = Column(String, nullable=False)
    name_en = Column(String, nullable=False)
    name_oz = Column(String, nullable=False)
    schools = relationship("SchoolInfo", backref="region", order_by="SchoolInfo.id", lazy="select")

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "name": self.name_uz
        }

    def add(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class District(db.Model):
    __tablename__ = "district"
    id = Column(Integer, primary_key=True)
    name_uz = Column(String, nullable=False)
    name_ru = Column(String, nullable=False)
    name_en = Column(String, nullable=False)
    name_cyrillic = Column(String, nullable=False)
    province_id = Column(Integer, ForeignKey('region.id'), nullable=False)
    schools = relationship("SchoolInfo", backref="district", order_by="SchoolInfo.id", lazy="select")

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "name": self.name_uz
        }

    def add(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class SchoolInfo(db.Model):
    __tablename__ = "school_info"
    id = Column(Integer, primary_key=True)
    number = Column(Integer, nullable=False)
    region_id = Column(Integer, ForeignKey('region.id'), nullable=False)
    district_id = Column(Integer, ForeignKey('district.id'), nullable=False)
    deleted = Column(Boolean, default=False)
    phone_number = Column(String)
    location_id = Column(Integer, ForeignKey('locations.id'), nullable=True)
    school_users = relationship("SchoolUser", backref="school", order_by="SchoolUser.id", lazy="select")

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "number": self.number,
            'phone_number': self.phone_number,
            "region":
                {
                    "id": self.region_id,
                    "name": self.region.name_uz
                },
            "district": {
                "id": self.district_id,
                "name": self.district.name_uz
            }
        }

    def add(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class SchoolUser(db.Model):
    __tablename__ = "school_user"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    surname = Column(String)
    phone = Column(String)
    school_id = Column(Integer, ForeignKey('school_info.id'))
    type_user = Column(String, nullable=False)
    percentage = Column(Integer)
    deleted = Column(Boolean, default=False)
    by_who = Column(Integer, ForeignKey("users.id"))
    location_id = Column(Integer, ForeignKey('locations.id'), nullable=True)

    from sqlalchemy.orm import foreign

    users = relationship(
        "Users",
        backref="school_user",
        primaryjoin="foreign(Users.school_user_id) == SchoolUser.id",
        order_by="Users.id"
    )

    def convert_json(self, entire=False):
        user = Users.query.filter(Users.school_user_id == self.id).first()
        by_who = Users.query.filter(Users.id == self.by_who).first() if self.by_who else None
        teacher = SchoolUser.query.filter(SchoolUser.id == by_who.school_user_id).first() if by_who else None

        return {
            "id": self.id,
            "user_infos": user.convert_json() if user else None,
            "name": self.name,
            "surname": self.surname,
            "username": user.username if user else None,
            "phone": self.phone,
            "school": {
                "id": self.school_id,
                "number": self.school.number
            },
            "type": self.type_user,
            "percentage": self.percentage,
            "teacher": teacher.convert_json() if teacher else None

        }

    def add(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class SchoolUserSalary(db.Model):
    __tablename__ = "school_user_salary"
    id = Column(Integer, primary_key=True)
    salary = Column(Integer)
    remaining = Column(Integer)
    taken = Column(Integer)
    calendar_month = Column(Integer, ForeignKey('calendarmonth.id'))
    calendar_year = Column(Integer, ForeignKey('calendaryear.id'))
    school_user_id = Column(Integer, ForeignKey('school_user.id'))
    school_salary_day = relationship("SchoolUserSalaryDay", backref="teacher_salary",
                                     order_by="SchoolUserSalaryDay.id",
                                     lazy="select")

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "salary": self.salary,
            "date": self.month.date.strftime("%Y-%m"),
            "teacher": {
                "id": self.teacher_id,
                "name": self.teacher_school.name,
                "surname": self.teacher_school.surname
            }
        }

    def add(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class SchoolUserSalaryDay(db.Model):
    __tablename__ = "school_user_salary_day"
    id = Column(Integer, primary_key=True)
    salary = Column(Integer)
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    school_user_id = Column(Integer, ForeignKey('school_user.id'))
    payment_type_id = Column(Integer, ForeignKey('paymenttypes.id'))
    salary_id = Column(Integer, ForeignKey('school_user_salary.id'))
    deleted = Column(Boolean, default=False)

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "salary": self.salary,
            "date": self.day.date.strftime("%Y-%m-%d"),
            "teacher": {
                "id": self.teacher_id,
                "name": self.teacher_school.name,
                "surname": self.teacher_school.surname
            },
            "payment_type": {
                "id": self.payment_type_id,
                "name": self.payment_type.name
            }
        }

    def add(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class SchoolUserSalaryAttendance(db.Model):
    __tablename__ = "school_user_salary_attendance"
    id = Column(Integer, primary_key=True)
    school_user_id = Column(Integer, ForeignKey('school_user.id'))
    salary_per_day = Column(Integer)
    attendance_day_id = Column(Integer, ForeignKey('attendancedays.id'))
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    calendar_month = Column(Integer, ForeignKey("calendarmonth.id"))
    calendar_year = Column(Integer, ForeignKey("calendaryear.id"))

    def convert_json(self, entire=False):
        return {
            "id": self.id,
        }

    def add(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()
