from app import db


class Defenation(db.Model):
    __tablename__ = 'defenation'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    def __str__(self):
        return self.name


class School(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    number = db.Column(db.Integer, nullable=False)

    def __str__(self):
        return self.name


class StudentTestBlock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    father_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(100), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey('school.id'), nullable=False)
    defenation_id = db.Column(db.Integer, db.ForeignKey('defenation.id'), nullable=False)
    unique_id = db.Column(db.String(300), unique=True, nullable=True)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    language = db.Column(db.String(100), nullable=False)
    school = db.relationship('School')
    university = db.relationship('University')
    faculty = db.relationship('Faculty')
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    defenation = db.relationship('Defenation')
