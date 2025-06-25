from backend.models.models import Column, Integer, db, String, ForeignKey, Boolean, desc, DateTime, relationship


class Parent(db.Model):
    __tablename__ = "parent"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    surname = Column(String)
    phone = Column(Integer)
    address = Column(String)
    location_id = Column(Integer, ForeignKey('locations.id'))
    born_date = Column(DateTime)
    sex = Column(String)
    username = Column(String)
    password = Column(String)
    deleted = Column(Boolean, default=False)

    def convert_json(self, entire=False):
        return {
            "id": self.id,
            "name": self.name,
            "surname": self.surname,
            "username": self.username,
            "phone": self.phone,
            "address": self.address,
            "location": {
                "id": self.location_id,
                "name": self.location.name
            }
            ,
            "birth_day": self.born_date.strftime("%Y-%m-%d"),
            "sex": self.sex,
            "children": [
                {
                    "id": st.id,
                    "name": st.user.name,
                    "surname": st.user.surname,
                    "balance": st.user.balance,
                    "lesson_times": [{"time": ls.start_time.strftime("%H:%M")} for ls in st.time_table],
                    "subjects": [subject.name for subject in st.subject]
                } for st in self.student
            ]
        }

    def add(self):
        db.session.add(self)
        db.session.commit()


db.Table('parent_child',
         db.Column('parent_id', db.Integer, db.ForeignKey('parent.id')),
         db.Column('student_id', db.Integer, db.ForeignKey('students.id'))
         )
