from app import app, db, jsonify, request, jwt_required, or_
from backend.functions.utils import api, iterate_models, check_exist_id
from backend.school.models import SchoolInfo, Region, District, SchoolUser
from backend.models.models import Users, Roles
from backend.student.register_for_tes.models import School
from flask_jwt_extended import get_jwt_identity
from werkzeug.security import generate_password_hash


@app.route(f'{api}/school_details', defaults={'region_id': None})
@app.route(f'{api}/school_details/<region_id>')
def school_details(region_id):
    school_numbers = School.query.order_by(School.number).all()
    regions = Region.query.order_by(Region.id).all()
    region_id = int(region_id) if region_id else regions[0].id
    districts = District.query.filter(District.province_id == region_id).order_by(District.id).all()

    return jsonify({"school_numbers": iterate_models(school_numbers), "regions": iterate_models(regions),
                    "districts": iterate_models(districts)})


@app.route(f'{api}/crud_school', defaults={'pk': None}, methods=['POST', "PUT", 'GET', "DELETE"])
@app.route(f'{api}/crud_school/<pk>', methods=['POST', "PUT", 'GET', "DELETE"])
@jwt_required()
def crud_school(pk):
    user = Users.query.filter(Users.user_id == get_jwt_identity()).first()
    if request.method == "POST":
        number = request.get_json()['number']
        region_id = request.get_json()['region']
        district_id = request.get_json()['district']
        phone = request.get_json()['phone']

        school = SchoolInfo(number=number, region_id=region_id, district_id=district_id, phone_number=phone,
                            location_id=user.location_id)
        school.add()
        return {"message": "School created", "id": school.id}, 200

    elif request.method == "GET":
        if pk:
            school = SchoolInfo.query.filter(SchoolInfo.id == pk).first()
            school_user_director = SchoolUser.query.filter(SchoolUser.type_user == "director",
                                                           SchoolUser.school_id == school.id,
                                                           ).filter(
                or_(SchoolUser.deleted == False, SchoolUser.deleted == None)).first()
            school_user_teachers = SchoolUser.query.filter(SchoolUser.type_user == "teacher",
                                                           SchoolUser.deleted == False,
                                                           SchoolUser.school_id == school.id).filter(
                or_(SchoolUser.deleted == False, SchoolUser.deleted == None)).all()
            school_user_students = SchoolUser.query.filter(SchoolUser.type_user == "student",
                                                           SchoolUser.deleted == False,
                                                           SchoolUser.school_id == school.id).all()
            return jsonify({"school": school.convert_json(entire=True) if school else {},
                            "director": school_user_director.convert_json() if school_user_director else {},
                            "teachers": iterate_models(school_user_teachers),
                            "students": iterate_models(school_user_students)})
        schools = SchoolInfo.query.filter(SchoolInfo.deleted == False,
                                          SchoolInfo.location_id == user.location_id).order_by(SchoolInfo.id).all()
        return jsonify({"schools": iterate_models(schools)})
    elif request.method == "PUT":
        number = request.get_json()['number']
        region_id = request.get_json()['region']
        district_id = request.get_json()['district']
        phone = request.get_json()['phone']
        school = SchoolInfo.query.filter(SchoolInfo.id == pk).first()
        school.number = number
        school.region_id = region_id
        school.district_id = district_id
        school.phone_number = phone
        db.session.commit()
        return {"message": "School updated"}, 200
    else:
        school = SchoolInfo.query.filter(SchoolInfo.id == pk).first()
        school.deleted = True
        db.session.commit()
        return {"message": "School deleted"}, 200


@app.route(f'{api}/crud_school_user/', defaults={'pk': None}, methods=['POST', "PUT", 'GET', "DELETE"])
@app.route(f'{api}/crud_school_user/<pk>', methods=['POST', "PUT", 'GET', "DELETE"])
@jwt_required()
def crud_school_user(pk):
    user = Users.query.filter(Users.user_id == get_jwt_identity()).first()
    if request.method == "POST" or request.method == "PUT":
        school_id = request.get_json()['school_id']
        username = request.get_json()['username']
        name = request.get_json()['name']
        surname = request.get_json()['surname']
        phone = request.get_json()['phone']
        type_user = request.get_json()['type_user']
        school = SchoolInfo.query.filter(SchoolInfo.id == school_id).first()
        percentage = 0
        if type_user == "teacher":
            percentage = 8
        elif type_user == "director":
            percentage = 2
        if request.method == "POST":

            add_user = SchoolUser(school_id=school_id, percentage=percentage, name=name, surname=surname, phone=phone,
                                  type_user=type_user, by_who=user.id, location_id=school.location_id)
            add_user.add()
            if type_user == "director" or type_user == "teacher":
                if type_user == "teacher":
                    role = "ad23qaw212"
                    exist_role = Roles.query.filter(Roles.role == role, Roles.type_role == "school_teacher").first()
                    if not exist_role:
                        role = Roles(role=role, type_role="school_teacher")
                        role.add()
                else:
                    role = "as24qaw223"
                    exist_role = Roles.query.filter(Roles.role == role, Roles.type_role == "school_director").first()
                    if not exist_role:
                        role = Roles(role=role, type_role="school_director")
                        role.add()
                exist_user = Users.query.filter(Users.username == username).filter(
                    or_(Users.deleted == False, Users.deleted == None)).first()
                if not exist_user:
                    user_add = Users(name=name, surname=surname, username=username,
                                     password=generate_password_hash("12345678"),
                                     role_id=exist_role.id,
                                     school_user_id=add_user.id,
                                     user_id=check_exist_id(), location_id=user.location_id)
                    user_add.add()
                else:
                    return {"message": "Username already exists", 'status': False}, 200
                return {"message": "User registered", "id": add_user.id, 'user': add_user.convert_json()}, 200
            return {"message": "User registered"}, 200
        else:
            add_user = SchoolUser.query.filter(SchoolUser.id == pk).first()
            add_user.name = name
            add_user.surname = surname
            add_user.phone = phone
            add_user.type_user = type_user
            db.session.commit()
            user = Users.query.filter(Users.school_user_id == add_user.id).first()

            user.username = username
            user.name = name
            user.surname = surname
            db.session.commit()
            return {"message": "User updated", 'user': add_user.convert_json()}, 200
    elif request.method == "GET":

        school_user = SchoolUser.query.filter(SchoolUser.id == pk).first()
        school_user_students = SchoolUser.query.filter(SchoolUser.type_user == "student",
                                                       SchoolUser.deleted == False,
                                                       SchoolUser.school_id == school_user.school_id).order_by(
            SchoolUser.id).all()
        return jsonify({"user": school_user.convert_json(), "students": iterate_models(school_user_students)})
    else:
        user = SchoolUser.query.filter(SchoolUser.id == pk).first()
        user.deleted = True
        get_user = Users.query.filter(Users.school_user_id == user.id).first()
        get_user.deleted = True
        db.session.commit()
        return {"message": "User deleted"}, 200


@app.route(f'{api}/crud_student_school/', defaults={'pk': None}, methods=['POST', "PUT", 'GET', "DELETE"])
@app.route(f'{api}/crud_student_school/<pk>', methods=['POST', "PUT", 'GET', "DELETE"])
def crud_student_school(pk):
    if request.method == "POST" or request.method == "PUT":
        name = request.get_json()['name']
        surname = request.get_json()['surname']
        phone = request.get_json()['phone']
        teacher_id = request.get_json()['teacher_id']
        user = Users.query.filter(Users.school_user_id == teacher_id).first()
        school_user = SchoolUser.query.filter(SchoolUser.id == teacher_id).first()
        school = SchoolInfo.query.filter(SchoolInfo.id == school_user.school_id).first()
        if request.method == "POST":
            student = SchoolUser(name=name, surname=surname, phone=phone, school_id=school_user.school_id,
                                 by_who=user.id, location_id=user.location_id,
                                 type_user="student", percentage=0)
            student.add()
            return {"message": "Student registered", 'user': student.convert_json()}, 200

        elif request.method == "PUT":
            name = request.get_json()['name']
            surname = request.get_json()['surname']
            phone = request.get_json()['phone']
            student = SchoolUser.query.filter(SchoolUser.id == pk).first()
            student.name = name
            student.surname = surname
            student.phone = phone
            db.session.commit()
            return {"message": "Student updated", 'user': student.convert_json()}, 200
    elif request.method == "GET":
        student = SchoolUser.query.filter(SchoolUser.id == pk).first()
        return jsonify({"student": student.convert_json()})
    else:
        student = SchoolUser.query.filter(SchoolUser.id == pk).first()
        student.deleted = True
        get_user = Users.query.filter(Users.school_user_id == student.id).first()
        if get_user:
            get_user.deleted = True
            db.session.commit()
        return {"message": "Student deleted"}, 200

    pass


@app.route(f'{api}/get_district_region/<region_id>')
def get_district_region(region_id):
    districts = District.query.filter(District.province_id == region_id).order_by(District.id).all()
    return jsonify({"districts": iterate_models(districts)})


@app.route(f'{api}/school_students/<location_id>')
@jwt_required()
def school_students(location_id):
    school_users = SchoolUser.query.filter(SchoolUser.location_id == location_id).filter(
        SchoolUser.type_user == "student").order_by(SchoolUser.id).all()
    return jsonify({"school_users": iterate_models(school_users)})

