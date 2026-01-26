from backend.models.models import db

assistent_subject = db.Table('assistent_subject',
                             db.Column('assistent_id', db.Integer, db.ForeignKey('assistent.id'), primary_key=True),
                             db.Column('subject_id', db.Integer, db.ForeignKey('subjects.id'), primary_key=True))


class Assistent(db.Model):
    __tablename__ = 'assistent'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'))

    subjects = db.relationship('Subjects', secondary=assistent_subject,
                               backref=db.backref('assistents', lazy='dynamic'), lazy='dynamic')

    def add(self):
        db.session.add(self)
        db.session.commit()

    def convert_json(self):
        return {"id": self.user.id,
                "name": self.user.name,
                "surname": self.user.surname,
                "username": self.user.username,
                "phone": self.user.phone[0].phone,

                'date': str(self.user.born_day) + '.' + str(self.user.born_month) + '.' + str(self.user.born_year),
                'address': self.user.address,
                'location': {
                    'id': self.user.location.id if self.user.location else None,
                    'name': self.user.location.name if self.user.location else None,
                },

                "language": self.user.language.name if self.user.language else None,
                "user_id": self.user_id, "subjects": [s.name for s in self.subjects]
                }
