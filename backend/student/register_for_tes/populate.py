import requests
from app import db, app  # Import app instance
from backend.student.register_for_tes.models import  School










def create_school():
    for i in range(1, 81):
        school = School.query.filter_by(number=i).first()
        if not school:
            new_school = School(number=i, name=f"{i} - Maktab")
            db.session.add(new_school)
    db.session.commit()

# Run the script within the application context
