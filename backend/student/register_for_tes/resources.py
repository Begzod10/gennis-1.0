from flask_restful import Resource, reqparse

from app import db, apis as api, request
from backend.student.register_for_tes.models import Defenation, School, StudentTestBlock


class StudentResource(Resource):
    def get(self):
        school_id = request.args.get('school_id', None)
        defenation_id = request.args.get('defenation_id', None)
        language = request.args.get('languages_id', None)
        location_id = request.args.get('location_id', None)

        students_query = StudentTestBlock.query

        if school_id is not None:
            students_query = students_query.filter(StudentTestBlock.school_id == school_id)
        if language is not None:
            students_query = students_query.filter(StudentTestBlock.language == language)
        if defenation_id is not None:
            students_query = students_query.filter(StudentTestBlock.defenation_id == defenation_id)

        if location_id is not None:
            students_query = students_query.filter(StudentTestBlock.location_id == location_id)

        students = students_query.all()

        return [
            {
                "id": student.id,
                "name": student.name,
                "surname": student.surname,
                "father_name": student.father_name,
                "phone": student.phone,
                "school_id": student.school_id,
                "defenation_id": student.defenation_id,
                "unique_id": student.unique_id,
                'school_name': student.school.name,
                'defenation_name': student.defenation.name,
                "language": student.language
            }
            for student in students
        ], 200

    def post(self):
        data = request.get_json()
        if not data:
            return {"error": "Request payload must be in JSON format"}, 400

        required_fields = ['name', 'surname', 'father_name', 'phone', 'school_id', 'defenation_id']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return {"error": f"Missing fields in request: {', '.join(missing_fields)}"}, 400
        import random

        def generate_numeric_id(length=7):
            return str(random.randint(10 ** (length - 1), 10 ** length - 1))

        def generate_unique_numeric_id():
            while True:
                unique_id = generate_numeric_id()
                if not StudentTestBlock.query.filter(StudentTestBlock.unique_id == unique_id).first():
                    return unique_id

        student = StudentTestBlock(
            name=data['name'],
            surname=data['surname'],
            father_name=data['father_name'],
            phone=data['phone'],
            school_id=data['school_id'],
            defenation_id=data['defenation_id'],
            unique_id=generate_unique_numeric_id(),
            location_id=data['location_id'],
            language=data['language']
        )

        db.session.add(student)
        db.session.commit()
        return {"message": "Student added", "student_id": student.id, 'unique_id': student.unique_id}, 201


api.add_resource(StudentResource, '/api/students_test')


class SchoolResource(Resource):
    def get(self, school_id=None):
        if school_id:
            school = School.query.get(school_id)
            if not school:
                return {"message": "School not found"}, 404
            return {"id": school.id, "name": school.name, "number": school.number}
        else:
            schools = School.query.all()
            return [{"id": school.id, "name": school.name, "number": school.number} for school in schools]

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True, help="Name is required")
        parser.add_argument('number', type=int, required=True, help="Number is required")
        data = parser.parse_args()

        school = School(name=data['name'], number=data['number'])
        db.session.add(school)
        db.session.commit()
        return {"message": "School created", "id": school.id}, 201

    def put(self, school_id):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True)
        parser.add_argument('number', type=int, required=True)
        data = parser.parse_args()

        school = School.query.get(school_id)
        if not school:
            return {"message": "School not found"}, 404
        school.name = data['name']
        school.number = data['number']
        db.session.commit()
        return {"message": "School updated"}

    def delete(self, school_id):
        school = School.query.get(school_id)
        if not school:
            return {"message": "School not found"}, 404
        db.session.delete(school)
        db.session.commit()
        return {"message": "School deleted"}


api.add_resource(SchoolResource, '/api/schools', '/api/schools/<int:school_id>')


class DefenationResource(Resource):
    def get(self, defenation_id=None):
        if defenation_id:
            defenation = Defenation.query.get(defenation_id)
            if not defenation:
                return {"message": "Defenation not found"}, 404
            return {
                "id": defenation.id,
                "name": defenation.name
            }
        else:
            defenations = Defenation.query.all()
            return [
                {"id": defenation.id, "name": defenation.name}
                for defenation in defenations
            ]

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True, help="Name is required")
        data = parser.parse_args()

        defenation = Defenation(name=data['name'])
        db.session.add(defenation)
        db.session.commit()
        return {"message": "Defenation created", "id": defenation.id}, 201

    def put(self, defenation_id):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True)
        data = parser.parse_args()

        defenation = Defenation.query.get(defenation_id)
        if not defenation:
            return {"message": "Defenation not found"}, 404
        defenation.name = data['name']
        db.session.commit()
        return {"message": "Defenation updated"}

    def delete(self, defenation_id):
        defenation = Defenation.query.get(defenation_id)
        if not defenation:
            return {"message": "Defenation not found"}, 404
        db.session.delete(defenation)
        db.session.commit()
        return {"message": "Defenation deleted"}


api.add_resource(DefenationResource, '/api/defenations', '/api/defenations/<int:defenation_id>')
