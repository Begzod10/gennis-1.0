from backend.models.models import Column, Integer, db, String, ForeignKey, Boolean, desc, DateTime, relationship


class Parent(db.Model):
    __tablename__ = "parent"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    student_get = relationship("Students", secondary="parent_child", backref="parent", order_by="Students.id")

    def convert_json(self, entire=False):
        return {
            "parent_id": self.id,
            "id": self.user.id,
            "name": self.user.name,
            "surname": self.user.surname,
            "username": self.user.username,
            "phone": self.user.phone[0].phone,
            "location": {
                "id": self.user.location_id,
                "name": self.user.location.name
            },
            'date': str(self.user.born_day) + '.' + str(self.user.born_month) + '.' + str(self.user.born_year),
            'address': self.user.address,
            "children": [
                {
                    "student_id": st.id,
                    "user": st.user.convert_json(),
                    # "user_id": st.user_id,
                    # "name": st.user.name,
                    # "surname": st.user.surname,
                    # "balance": st.user.balance,
                    # "password": st.user.password,
                    # "age": st.user.age,
                    # "father_name": st.user.father_name,
                    # "born_day" : st.user.born_day,
                    # "born_month" : st.user.born_month,
                    # "born_year" : st.user.born_year,
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
