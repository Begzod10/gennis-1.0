from flask_restful import Resource, reqparse

from app import db, apis as api
from backend.student.register_for_tes.models import Region, University, Faculty, School, StudentTestBlock


class StudentResource(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('school_id', type=int, required=False, help="Filter by school ID")
        parser.add_argument('university_id', type=int, required=False, help="Filter by university ID")
        parser.add_argument('faculty_id', type=int, required=False, help="Filter by faculty ID")
        filters = parser.parse_args()

        query = StudentTestBlock.query

        # Filter by school_id if provided
        if filters['school_id'] is not None:
            query = query.filter(StudentTestBlock.school_id == filters['school_id'])

        # Filter by university_id if provided
        if filters['university_id'] is not None:
            query = query.filter(StudentTestBlock.university_id == filters['university_id'])

        # Filter by faculty_id if provided
        if filters['faculty_id'] is not None:
            query = query.filter(StudentTestBlock.faculty_id == filters['faculty_id'])

        students = query.all()
        return [
            {
                "id": student.id,
                "name": student.name,
                "surname": student.surname,
                "father_name": student.father_name,
                "phone": student.phone,
                "school_id": student.school_id,
                "university_id": student.university_id,
                "faculty_id": student.faculty_id,
                "unique_id": student.unique_id
            }
            for student in students
        ]

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True, help="Name is required")
        parser.add_argument('surname', type=str, required=True, help="Surname is required")
        parser.add_argument('father_name', type=str, required=True, help="Father name is required")
        parser.add_argument('phone', type=str, required=True, help="Phone is required")
        parser.add_argument('school_id', type=int, required=True, help="School ID is required")
        parser.add_argument('university_id', type=int, required=True, help="University ID is required")
        parser.add_argument('faculty_id', type=int, required=True, help="Faculty ID is required")

        data = parser.parse_args()
        student = StudentTestBlock(**data)
        db.session.add(student)
        db.session.commit()
        return {"message": "Student added", "student_id": student.id}, 201


api.add_resource(StudentResource, '/api/students_test')


# ----- Region Resource -----

class RegionResource(Resource):
    def get(self, region_id=None):
        if region_id:
            region = Region.query.get(region_id)
            if not region:
                return {"message": "Region not found"}, 404
            return {"id": region.id, "name": region.name}
        else:
            regions = Region.query.all()
            return [{"id": region.id, "name": region.name} for region in regions]

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True, help="Name is required")
        data = parser.parse_args()

        region = Region(name=data['name'])
        db.session.add(region)
        db.session.commit()
        return {"message": "Region created", "id": region.id}, 201

    def put(self, region_id):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True)
        data = parser.parse_args()

        region = Region.query.get(region_id)
        if not region:
            return {"message": "Region not found"}, 404
        region.name = data['name']
        db.session.commit()
        return {"message": "Region updated"}

    def delete(self, region_id):
        region = Region.query.get(region_id)
        if not region:
            return {"message": "Region not found"}, 404
        db.session.delete(region)
        db.session.commit()
        return {"message": "Region deleted"}


api.add_resource(RegionResource, '/api/regions', '/api/regions/<int:region_id>')


# ----- School Resource -----

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


# ----- University Resource -----

class UniversityResource(Resource):
    def get(self, university_id=None):
        if university_id:
            university = University.query.get(university_id)
            if not university:
                return {"message": "University not found"}, 404
            return {"id": university.id, "name": university.name, "region_id": university.region_id,
                    "university_id": university.university_id}
        else:
            universities = University.query.all()
            return [{"id": university.id, "name": university.name, "region_id": university.region_id,
                     "university_id": university.university_id} for university in universities]

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True, help="Name is required")
        parser.add_argument('region_id', type=int, required=True, help="Region ID is required")
        parser.add_argument('university_id', type=int, required=True, help="University ID is required")
        data = parser.parse_args()

        university = University(name=data['name'], region_id=data['region_id'], university_id=data['university_id'])
        db.session.add(university)
        db.session.commit()
        return {"message": "University created", "id": university.id}, 201

    def put(self, university_id):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True)
        parser.add_argument('region_id', type=int, required=True)
        parser.add_argument('university_id', type=int, required=True)
        data = parser.parse_args()

        university = University.query.get(university_id)
        if not university:
            return {"message": "University not found"}, 404
        university.name = data['name']
        university.region_id = data['region_id']
        university.university_id = data['university_id']
        db.session.commit()
        return {"message": "University updated"}

    def delete(self, university_id):
        university = University.query.get(university_id)
        if not university:
            return {"message": "University not found"}, 404
        db.session.delete(university)
        db.session.commit()
        return {"message": "University deleted"}


api.add_resource(UniversityResource, '/api/universities', '/api/universities/<int:university_id>')


# ----- Faculty Resource -----

class FacultyResource(Resource):
    def get(self, faculty_id=None):
        if faculty_id:
            faculty = Faculty.query.get(faculty_id)
            if not faculty:
                return {"message": "Faculty not found"}, 404
            return {"id": faculty.id, "name": faculty.name, "university_id": faculty.university_id,
                    "mvdir": faculty.mvdir}
        else:
            faculties = Faculty.query.all()
            return [
                {"id": faculty.id, "name": faculty.name, "university_id": faculty.university_id, "mvdir": faculty.mvdir}
                for faculty in faculties]

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True, help="Name is required")
        parser.add_argument('university_id', type=int, required=True, help="University ID is required")
        parser.add_argument('mvdir', type=str, required=True, help="Mvdir is required")
        data = parser.parse_args()

        faculty = Faculty(name=data['name'], university_id=data['university_id'], mvdir=data['mvdir'])
        db.session.add(faculty)
        db.session.commit()
        return {"message": "Faculty created", "id": faculty.id}, 201

    def put(self, faculty_id):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True)
        parser.add_argument('university_id', type=int, required=True)
        parser.add_argument('mvdir', type=str, required=True)
        data = parser.parse_args()

        faculty = Faculty.query.get(faculty_id)
        if not faculty:
            return {"message": "Faculty not found"}, 404
        faculty.name = data['name']
        faculty.university_id = data['university_id']
        faculty.mvdir = data['mvdir']
        db.session.commit()
        return {"message": "Faculty updated"}

    def delete(self, faculty_id):
        faculty = Faculty.query.get(faculty_id)
        if not faculty:
            return {"message": "Faculty not found"}, 404
        db.session.delete(faculty)
        db.session.commit()
        return {"message": "Faculty deleted"}


api.add_resource(FacultyResource, '/api/faculties', '/api/faculties/<int:faculty_id>')
