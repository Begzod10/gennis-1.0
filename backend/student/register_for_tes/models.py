from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

from app import db


class Region(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    def __str__(self):
        return self.name


class University(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    region_id = db.Column(db.Integer, db.ForeignKey('region.id'), nullable=False)
    region = db.relationship('Region', backref=db.backref('universities', lazy=True))
    university_id = db.Column(db.Integer, nullable=False)

    def __str__(self):
        return self.name


class Faculty(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    university_id = db.Column(db.Integer, db.ForeignKey('university.id'), nullable=False)
    university = db.relationship('University', backref=db.backref('faculties', lazy=True))
    mvdir = db.Column(db.String(100))

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
    university_id = db.Column(db.Integer, db.ForeignKey('university.id'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    unique_id = db.Column(db.String(300), unique=True, nullable=False)

    school = db.relationship('School')
    university = db.relationship('University')
    faculty = db.relationship('Faculty')


import hashlib, uuid


def generate_short_hash():
    return hashlib.sha1(uuid.uuid4().bytes).hexdigest()[:5]


@event.listens_for(StudentTestBlock, 'before_insert')
def generate_short_unique_id(mapper, connection, target):
    retry_count = 0
    max_retries = 10
    while retry_count < max_retries:
        target.unique_id = generate_short_hash()
        try:
            connection.execute(
                db.insert(StudentTestBlock).values(unique_id=target.unique_id)
            )
            break
        except IntegrityError:
            retry_count += 1
            db.session.rollback()

    if retry_count == max_retries:
        raise ValueError("Unable to generate a unique ID after several attempts.")
