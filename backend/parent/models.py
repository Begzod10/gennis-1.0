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

    def convert_json(self, entire=False):
        return {
            "id": self.user.id,
            "name": self.user.name,
            "surname": self.user.surname,
            "username": self.user.username,
            "phone": self.user.phone,
            "address": self.user.language.name,
            "location": {
                "id": self.location_id,
                "name": self.location.name
            }
            ,
            "born_date": self.born_date.strftime("%Y-%m-%d"),
            "sex": self.sex,
            "children": [
                {
                    "name": st.user.name,
                    "surname": st.user.surname,
                    "balance": st.user.balance,
                    "lesson_time": st.time_table[0].start_time.strftime("%H:%M"),
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
