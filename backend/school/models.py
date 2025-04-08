from backend.models.models import Column, Integer, ForeignKey, String, relationship, db, Date
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

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "number": self.number,
            "region_":
                {
                    "id": self.region_id,
                    "name": self.region.name
                },
            "district": {
                "id": self.district_id,
                "name": self.district.name
            }
        }

    def add(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class SchoolStudent(db.Model):
    __tablename__ = "school_student"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    surname = Column(String)
    phone = Column(String)
    school_id = Column(Integer, ForeignKey('school_info.id'))

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "name": self.name,
            "surname": self.surname,
            "phone": self.phone,
            "school": {
                "id": self.school_id,
                "number": self.school.number
            }
        }

    def add(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class SchoolTeacher(db.Model):
    __tablename__ = "school_teacher"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    surname = Column(String)
    phone = Column(String)
    school_id = Column(Integer, ForeignKey('school_info.id'))
    teacher_salary = relationship("SchoolTeacherSalary", backref="teacher_school", order_by="SchoolTeacherSalary.id",
                                  lazy="select")
    teacher_salary_day = relationship("SchoolTeacherSalaryDay", backref="teacher", order_by="SchoolTeacherSalaryDay.id",
                                      lazy="select")
    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "name": self.name,
            "surname": self.surname,
            "phone": self.phone,
            "school": {
                "id": self.school_id,
                "number": self.school.number
            }
        }

    def add(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class SchoolTeacherSalary(db.Model):
    __tablename__ = "school_teacher_salary"
    id = Column(Integer, primary_key=True)
    salary = Column(Integer)
    remaining = Column(Integer)
    taken = Column(Integer)
    calendar_month = Column(Integer, ForeignKey('calendarmonth.id'))
    calendar_year = Column(Integer, ForeignKey('calendaryear.id'))
    teacher_id = Column(Integer, ForeignKey('school_teacher.id'))
    teacher_salary_day = relationship("SchoolTeacherSalaryDay", backref="teacher_salary",
                                      order_by="SchoolTeacherSalaryDay.id",
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


class SchoolTeacherSalaryDay(db.Model):
    __tablename__ = "school_teacher_salary_day"
    id = Column(Integer, primary_key=True)
    salary = Column(Integer)
    calendar_day = Column(Integer, ForeignKey('calendarday.id'))
    teacher_id = Column(Integer, ForeignKey('school_teacher.id'))
    payment_type_id = Column(Integer, ForeignKey('paymenttypes.id'))
    salary_id = Column(Integer, ForeignKey('school_teacher_salary.id'))

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
