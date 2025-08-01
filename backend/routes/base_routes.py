from datetime import datetime
from datetime import timedelta
from pprint import pprint

import requests
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity, create_refresh_token, \
    unset_jwt_cookies
from werkzeug.security import generate_password_hash, check_password_hash

from app import app, api, db, jsonify, contains_eager, request, or_, desc
from backend.functions.filters import new_students_filters, teacher_filter, staff_filter, collection, \
    accounting_payments, group_filter, \
    deleted_students_filter, debt_students, deleted_reg_students_filter
from backend.functions.utils import find_calendar_date, get_json_field, check_exist_id
from backend.functions.utils import refresh_age, iterate_models, refreshdatas, hour2, update_salary
from backend.models.models import CourseTypes, Students, Users, Staff, \
    PhoneList, Roles, Group_Room_Week, Locations, Professions, Teachers, Subjects, Week, AccountingInfo, Groups, \
    AttendanceHistoryStudent, PaymentTypes, StudentExcuses, EducationLanguage, Contract_Students, \
    CalendarYear, TeacherData, StudentTest, GroupTest, AttendanceDays, CalendarDay, CalendarMonth, \
    CertificateLinks
from backend.student.class_model import Student_Functions
from backend.functions.functions import update_user_time_table
from backend.student.register_for_tes.populate import create_school


@app.errorhandler(404)
def not_found(e):
    return app.send_static_file('index.html')


@app.errorhandler(413)
def img_larger(e):
    return jsonify({
        "success": False,
        "msg": "rasm hajmi kotta"
    })


@app.route('/', methods=['POST', 'GET'])
def index():
    refreshdatas()

    # list = ['Co-working zone', 'Friendly atmosphere', 'Football games in 3 branches', 'Different interesting events',
    #         'Cybersport']
    # for name in list:
    #     advantage = Advantages.query.filter(Advantages.name == name).first()
    #     if not advantage:
    #         add = Advantages(name=name)
    #         db.session.add(add)
    #         db.session.commit()
    # link_names = ['Youtube', 'Telegram', 'Instagram', 'Facebook']
    # for link_name in link_names:
    #     link = Link.query.filter(Link.name == link_name).first()
    #     if not link:
    #         new = Link(name=link_name)
    #         db.session.add(new)
    #         db.session.commit()
    return app.send_static_file("index.html")


@app.route(f'{api}/check_user_id/<user_id>/<username>')
def calendar(user_id, username):
    user_id = check_exist_id(user_id)
    Users.query.filter(Users.username == username).update({'user_id': user_id})
    db.session.commit()
    print(user_id)
    return jsonify({
        "user_id": user_id,
    })


@app.route(f'{api}/locations')
def locations():
    locations_list = Locations.query.order_by(Locations.id).all()
    years = CalendarYear.query.order_by(CalendarYear.id).all()

    return jsonify({
        "locations": iterate_models(locations_list)
    })


@app.route(f"{api}/filters/<name>/<int:location_id>/", defaults={"type_filter": None}, methods=["GET"])
@app.route(f"{api}/filters/<name>/<int:location_id>/<type_filter>", methods=["GET"])
@jwt_required()
def filters(name, location_id, type_filter):
    """
    :param type_filter: 
    :param name: filter type
    :param location_id: Location table primary key
    :return: returns filter block
    """

    filter_block = ""
    if name == "newStudents":
        filter_block = new_students_filters()
    if name == "teachers":
        filter_block = teacher_filter()
    if name == "employees":
        filter_block = staff_filter()
    if name == 'groups':
        filter_block = group_filter(location_id)
    if name == "accounting_payment":
        filter_block = accounting_payments(type_filter)
    if name == "collection":
        filter_block = collection()
    if name == "debt_students":
        filter_block = debt_students(location_id)
    if name == "deletedGroupStudents":
        filter_block = deleted_students_filter(location_id)
    if name == "deleted_reg_students":
        filter_block = deleted_reg_students_filter(location_id)

    return jsonify({
        "filters": filter_block,
    })


@app.route(f"{api}/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """
    refresh jwt token
    :return:
    """
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    username_sign = Users.query.filter_by(user_id=identity).first()
    create_school()
    role = Roles.query.filter(Roles.id == username_sign.role_id).first() if username_sign else {}
    if username_sign and username_sign.teacher:
        data = TeacherData.query.filter(TeacherData.teacher_id == username_sign.teacher.id).first()
    else:
        data = None
    return jsonify({
        "username": username_sign.username,
        "surname": username_sign.surname.title(),
        "name": username_sign.name.title(),
        "id": username_sign.id,
        "access_token": access_token,
        "refresh_token": create_refresh_token(identity=username_sign.user_id),
        "role": role.role if role else "",
        "profile_photo": username_sign.photo_profile,
        "observer": username_sign.observer,
        "location_id": username_sign.location_id,
        "teacher_info": data.convert_json() if data else {}

    })


@app.route(f"{api}/logout", methods=["POST"])
def logout():
    response = jsonify({"msg": "logout successful"})
    unset_jwt_cookies(response)
    return response


@app.route(f'{api}/register', methods=['POST', 'GET'])
def register():
    refreshdatas()
    calendar_year, calendar_month, calendar_day = find_calendar_date()

    if request.method == 'POST':
        json_request = request.get_json()

        username = json_request['username']
        username_check = Users.query.filter_by(username=username).filter(
            or_(Users.deleted == False, Users.deleted == None)).first()
        selectedSubjects = json_request['selectedSubjects']
        if not selectedSubjects:
            return jsonify({"message": "Please select at least one subject"})
        morning_shift = None
        night_shift = None
        time = json_request['shift']
        if time == "1-smen":
            morning_shift = True
        elif time == "2-smen":
            night_shift = True

        if username_check:
            return jsonify({
                "message": "Username is already exists",
                "isUsername": True,
                "isError": True
            })

        name = json_request['name']
        surname = json_request['surname']
        fatherName = json_request['father_name']
        year = json_request['birth_day'][:4]
        month = json_request['birth_day'][5:7]
        day = json_request['birth_day'][8:]
        birthDay = int(day)
        birthMonth = int(month)
        birthYear = int(year)
        phone = json_request['phone']
        phoneParent = json_request['phoneParent']
        confirmPassword = json_request['password_confirm']
        comment = json_request['comment']
        location = json_request['location']
        studyLang = json_request['language']
        school_user_id = json_request['school_user_id'] if 'school_user_id' in json_request else None
        if not studyLang:
            studyLang = "Uz"
        language = EducationLanguage.query.filter_by(id=studyLang).first()

        password = generate_password_hash(confirmPassword, method="sha256")

        if not location:
            location = Locations.query.first()
        location = Locations.query.filter_by(id=location).first()

        a = datetime.today().year
        age = a - birthYear
        users = Users.query.all()

        if len(users) == 0:
            director = True
            role = Roles.query.filter(Roles.type_role == "director").first()
        else:
            director = False
            role = Roles.query.filter(Roles.type_role == "student").first()
        user_id = check_exist_id()
        if username == "monstrCoder" or username == "rimeprogrammer":
            role = Roles.query.filter(Roles.type_role == "programmer").first()
        ball_time = hour2() + timedelta(minutes=-5)
        add = Users(name=name, surname=surname, password=password, education_language=language.id,
                    location_id=location.id, user_id=user_id, username=username, born_day=birthDay,
                    born_month=birthMonth, comment=comment, calendar_day=calendar_day.id, director=director,
                    calendar_month=calendar_month.id, calendar_year=calendar_year.id, role_id=role.id,
                    school_user_id=school_user_id,
                    born_year=birthYear, age=age, father_name=fatherName, balance=0)
        db.session.add(add)

        db.session.commit()
        if director == False and not role.type_role == "programmer":
            student = Students(user_id=add.id, ball_time=ball_time)
            db.session.add(student)
            db.session.commit()

            Students.query.filter(Students.id == student.id).update({
                "morning_shift": morning_shift,
                "night_shift": night_shift,
            })
            db.session.commit()

            selectedSubjects = json_request['selectedSubjects']
            for sub in selectedSubjects:
                subject = Subjects.query.filter_by(name=sub['name']).first()
                student.subject.append(subject)
                db.session.commit()
        add_phone = PhoneList(phone=phone, user_id=add.id, personal=True)
        parent_phone = PhoneList(phone=phoneParent, user_id=add.id, parent=True)
        db.session.add(parent_phone)
        db.session.add(add_phone)
        db.session.commit()
        profession = Professions.query.filter(Professions.name == "programmer").first()
        if role.type_role == "programmer":
            add = Staff(profession_id=profession.id, user_id=add.id)
            db.session.add(add)
            db.session.commit()
        return jsonify({
            "success": True,
            "msg": "Registration was successful"
        })
    if request.method == "GET":
        subjects = Subjects.query.all()
        locations = Locations.query.order_by('id').all()
        languages = EducationLanguage.query.order_by('id').all()
        professions = Professions.query.order_by('id').all()

        data = {}
        subjects_list = [{"id": sub.id, "name": sub.name} for sub in subjects]
        locations_list = [{"id": sub.id, "name": sub.name} for sub in locations]
        languages_list = [{"id": sub.id, "name": sub.name} for sub in languages]
        professions_list = [{"id": sub.id, "name": sub.name} for sub in professions]
        data['subject'] = subjects_list
        data['location'] = locations_list
        data['language'] = languages_list
        data['jobs'] = professions_list
        return jsonify({
            "data": data
        })


@app.route(f'{api}/register_teacher', methods=['POST', 'GET'])
def register_teacher():
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    if request.method == "POST":
        get_json = request.get_json()
        username = get_json['username']
        username_check = Users.query.filter_by(username=username).filter(
            or_(Users.deleted == False, Users.deleted == None)).first()
        if username_check:
            return jsonify({
                "message": "Username is already exists",
                "isUsername": True,
                "isError": True
            })
        name = get_json['name']
        surname = get_json['surname']
        fatherName = get_json['father_name']
        year = get_json['birth_day'][:4]
        month = get_json['birth_day'][5:7]
        day = get_json['birth_day'][8:]
        birthDay = int(day)
        birthMonth = int(month)
        birthYear = int(year)
        phone = get_json['phone']
        confirmPassword = get_json['password_confirm']

        location = int(get_json['location'])

        studyLang = get_json['language']
        comment = get_json['comment']
        if not studyLang:
            studyLang = "Uz"
        a = datetime.today().year
        age = a - birthYear
        user_id = check_exist_id()
        if not location:
            location = Locations.query.first()
        hash = generate_password_hash(confirmPassword, method='sha256')
        location = Locations.query.filter_by(id=location).first()
        language = EducationLanguage.query.filter_by(id=studyLang).first()
        role = Roles.query.filter(Roles.type_role == "teacher").first()
        add = Users(name=name, surname=surname, username=username, password=hash,
                    education_language=language.id, born_day=birthDay, born_month=birthMonth,
                    calendar_day=calendar_day.id, role_id=role.id,
                    calendar_month=calendar_month.id, calendar_year=calendar_year.id,
                    born_year=birthYear, location_id=location.id, age=age, user_id=user_id, comment=comment,
                    father_name=fatherName, balance=0)
        db.session.add(add)
        db.session.commit()
        teacher = Teachers(user_id=add.id)
        db.session.add(teacher)
        db.session.commit()
        selectedSubjects = get_json['selectedSubjects']
        for sub in selectedSubjects:
            subject = Subjects.query.filter_by(name=sub['name']).first()
            teacher.subject.append(subject)
            db.session.commit()
        add_phone = PhoneList(phone=phone, user_id=add.id, personal=True)
        db.session.add(add_phone)
        db.session.commit()

        return jsonify({
            "msg": "Registration was successful",
            "success": True
        })


@app.route(f'{api}/register_staff', methods=['POST'])
def register_staff():
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    get_json = request.get_json()
    username = get_json['username']
    username_check = Users.query.filter_by(username=username).filter(
        or_(Users.deleted == False, Users.deleted == None)).first()
    if username_check:
        return jsonify({
            "message": "Username is already exists",
            "isUsername": True,
            "isError": True,
        })
    name = get_json['name']
    surname = get_json['surname']
    fatherName = get_json['father_name']
    year = get_json['birth_day'][:4]
    month = get_json['birth_day'][5:7]
    day = get_json['birth_day'][8:]
    birthDay = int(day)
    birthMonth = int(month)
    birthYear = int(year)
    phone = get_json['phone']
    confirmPassword = get_json['password_confirm']
    location = get_json['location']
    studyLang = get_json['language']
    comment = get_json['comment']
    if not studyLang:
        studyLang = "Uz"
    if not location:
        location = Locations.query.first()
    a = datetime.today().year
    age = a - birthYear
    user_id = check_exist_id()
    hash = generate_password_hash(confirmPassword)
    location = Locations.query.filter_by(id=location).first()
    language = EducationLanguage.query.filter_by(id=studyLang).first()
    selectedSubjects = get_json['job']
    profession = Professions.query.filter_by(name=selectedSubjects).first()
    if selectedSubjects == "Administrator":
        role = Roles.query.filter(Roles.type_role == "admin").first()
    elif selectedSubjects == "Muxarir":
        role = Roles.query.filter(Roles.type_role == "muxarir").first()
    elif selectedSubjects == "Buxgalter":
        role = Roles.query.filter(Roles.type_role == "accountant").first()
    else:
        role = Roles.query.filter(Roles.type_role == "user").first()
    add = Users(name=name, surname=surname, username=username, password=hash,
                education_language=language.id, born_day=birthDay, born_month=birthMonth,
                calendar_day=calendar_day.id, role_id=role.id,
                calendar_month=calendar_month.id, calendar_year=calendar_year.id,
                born_year=birthYear, location_id=location.id, age=age, user_id=user_id, comment=comment,
                father_name=fatherName, balance=0)
    db.session.add(add)
    db.session.commit()
    staff = Staff(user_id=add.id, profession_id=profession.id)
    db.session.add(staff)

    add_phone = PhoneList(user_id=add.id, phone=phone, personal=True)
    db.session.add(add_phone)
    db.session.commit()

    return jsonify({
        "msg": "Registration was successful",
        "success": True
    })


@app.route(f'{api}/my_profile/<int:user_id>')
@jwt_required()
def my_profile(user_id):
    links = []
    refreshdatas()
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    user = Users.query.filter(Users.id == user_id).first()
    role = Roles.query.filter(Roles.id == user.role_id).first()
    student_get = Students.query.filter(Students.user_id == user.id).first()
    teacher = Teachers.query.filter(Teachers.user_id == user_id).first()
    staff = Staff.query.filter(Staff.user_id == user_id).first()

    combined_debt = student_get.combined_debt if student_get and student_get.combined_debt else 0

    subject_list = [{"name": sub.name} for sub in student_get.subject] if student_get and student_get.subject else []
    current_rates = AttendanceHistoryStudent.query.filter(
        AttendanceHistoryStudent.calendar_year == calendar_year.id,
        AttendanceHistoryStudent.calendar_month == calendar_month.id,
        AttendanceHistoryStudent.student_id == student_get.id).all() if student_get else []
    rate_list = [{"subject": rate.subject.name, "degree": rate.average_ball} for rate in current_rates]

    changes = {}
    contract_url = ""
    if not student_get:
        link4 = {
            "link": "changeInfo",
            "title": "Ma'lumotlarni o'zgratirish",
            "iconClazz": "fa-pen",
            "type": "link"
        }
        links.append(link4)
        link6 = {
            "link": "changePhoto",
            "title": "Rasmni yangilash",
            "iconClazz": "fa-camera",
            "type": "link"
        }
        links.append(link6)

    if teacher:
        link = {
            "link": "employeeSalary",
            "title": "To'lov",
            "iconClazz": "fa-dollar-sign",
            "type": "link"
        }
        links.append(link)
    if student_get:
        link2 = {
            "link": "studentAccount",
            "title": "To'lov va Qarzlari",
            "iconClazz": "fa-wallet",
            "type": "link"
        }

        links.append(link2)
        link4 = {
            "link": "changeInfo",
            "title": "Ma'lumotlarni o'zgratirish",
            "iconClazz": "fa-pen",
            "type": "link"
        }
        link5 = {
            "link": "studentGroupsAttendance",
            "title": "Student davomatlari",
            "iconClazz": "fa-calendar-alt",
            "type": "link"
        }
        link6 = {
            "link": "changePhoto",
            "title": "Rasmni yangilash",
            "iconClazz": "fa-camera",
            "type": "link"
        }
        links.append(link4)
        links.append(link5)
        links.append(link6)
    if student_get:
        update_user_time_table(student_get.id)
        info = {
            "username": True
        }
        contract_url = {"contract_url": student_get.contract_pdf_url}

        changes = info
    if staff or user.director or teacher:
        info = {
            "username": True,
            "name": True,
            "surname": True,
            "fathersName": True,
            "birth": True,
            "phone": True,
            "birthDate": True,
        }
        changes = info
    phone_list = {}
    parent_phone = {}
    for tel in user.phone:
        if tel.parent:
            parent_phone = {
                "name": "Ota-onasining tel raqam",
                "value": tel.phone,
                "order": 6
            }
        elif tel.personal:
            phone_list = {
                "name": "Tel raqam",
                "value": tel.phone,
                "order": 5
            }
    balance = student_get.user.balance if student_get and student_get.user.balance else 0
    combined_payment = {
        "name": "Umumiy summa",
        "value": combined_debt,
        "order": 11
    } if student_get else {}
    balance_info = {
        "name": "Hisobi",
        "value": balance,
        "order": 12
    } if student_get else {}
    return jsonify({
        "id": user.id,
        "username": user.username,
        "role": role.role,
        "name": user.name.title(),
        "surname": user.surname.title(),
        "location": user.location_id,
        'profile_photo': user.photo_profile,
        "rate": rate_list,
        "contract_url": contract_url,
        "location_id": user.location_id,
        "balance": user.balance,
        "extraInfo": {
            "username": {
                "name": "Foydalanuvchi",
                "value": user.username,
                "order": 0
            },
            "name": {
                "name": "Ism",
                "value": user.name.title(),
                "order": 1
            },
            "surname": {
                "name": "Familya",
                "value": user.surname.title(),
                "order": 2
            },
            "fathersName": {
                "name": "Otasining Ismi",
                "value": user.father_name.title(),
                "order": 3
            },
            "age": {
                "name": "age",
                "value": user.age,
                "order": 4
            },
            "birthDate": {
                "name": "Tug'ulgan kun",
                "value": str(user.born_year) + "-" + str(user.born_month) + "-" + str(user.born_day),
                "order": 7,
            },
            "birthDay": {
                "name": "Tug'ulgan kun",
                "value": user.born_day,
                "order": 8,
                "display": "none"
            },
            "birthMonth": {
                "name": "Tug'ulgan oy",
                "value": user.born_month,
                "order": 9,
                "display": "none"
            },

            "birthYear": {
                "name": "Tug'ulgan yil",
                "value": user.born_year,
                "order": 10,
                "display": "none"
            },
            "combined_payment": combined_payment,
            'balance': balance_info,
            "phone": phone_list,
            "parentPhone": parent_phone,
            "subjects": subject_list,

        },
        "links": links,

        "activeToChange": changes
    })


@app.route(f'{api}/get_price_course/', methods=['POST'])
@jwt_required()
def get_price_course():
    body = {}
    course_type = int(request.get_json()['course_type'])
    course = CourseTypes.query.filter_by(id=course_type).first()
    body['price'] = course.cost
    return jsonify(body)


@app.route(f'{api}/profile/<int:user_id>')
@jwt_required()
def profile(user_id):
    refreshdatas()
    calendar_year, calendar_month, calendar_day = find_calendar_date()
    user_get = Users.query.filter(Users.id == user_id).first()
    student_get = Students.query.filter(Students.user_id == user_id).first()
    teacher_get = Teachers.query.filter(Teachers.user_id == user_id).first()
    staff_get = Staff.query.filter(Staff.user_id == user_id).first()
    director_get = Users.query.filter(Users.id == user_id).first()
    old_month = CalendarMonth.query.filter(CalendarMonth.date == datetime.strptime("2025-01", "%Y-%m")).first()
    refresh_age(user_get.id)
    att_count = 0
    if teacher_get:
        groups = Groups.query.filter(Groups.teacher_id == teacher_get.id,
                                     Groups.status == True).order_by(Groups.id).all()
        att_count = db.session.query(AttendanceDays).join(AttendanceDays.group).options(
            contains_eager(AttendanceDays.group)).filter(
            Groups.teacher_id == teacher_get.id, Groups.id.in_([group.id for group in groups])).join(
            AttendanceDays.day).filter(CalendarDay.month_id == old_month.id).count() if old_month else 0

    salary_status = True
    role = ''
    group_list = []
    links = []
    username = ''
    contract_data = {}
    link = ''
    phone_list = {}
    parent_phone = {}
    type_role = ''
    for tel in user_get.phone:
        if tel.personal:
            phone_list = {
                "name": "Tel raqam",
                "value": tel.phone,
                "order": 5
            }

        if tel.parent:
            parent_phone = {
                "name": "Ota-onasining tel raqam",
                "value": tel.phone,
                "order": 6
            }

    if student_get:
        update_user_time_table(student_get.id)

        salary_status = False
        contract_yes = True if student_get.contract_pdf_url and student_get.contract_word_url else False
        type_role = "Student"
        shift = "1-smen" if student_get.morning_shift else "2-smen" if student_get.night_shift else "Hamma vaqt"
        role = Roles.query.filter(Roles.id == user_get.role_id).first()
        group_list = [{"id": gr.id, "nameGroup": gr.name.title(), "teacherImg": ""} for gr in student_get.group]

        current_rates = AttendanceHistoryStudent.query.filter(
            AttendanceHistoryStudent.calendar_year == calendar_year.id,
            AttendanceHistoryStudent.calendar_month == calendar_month.id,
            AttendanceHistoryStudent.student_id == student_get.id).all()

        rate_list = [{"subject": rate.subject.name, "degree": rate.average_ball} for rate in current_rates]
        group_tests = GroupTest.query.filter(GroupTest.calendar_month == calendar_month.id,
                                             GroupTest.calendar_year == calendar_year.id,
                                             GroupTest.group_id.in_(
                                                 [gr_id.id for gr_id in student_get.group])).order_by(
            GroupTest.id).all()
        student_tests = StudentTest.query.filter(
            StudentTest.group_test_id.in_([test_id.id for test_id in group_tests]),
            StudentTest.student_id == student_get.id).order_by(StudentTest.id).all()
        link = {
            "link": "studentPayment",
            "title": "To'lov",
            "iconClazz": "fa-dollar-sign",
            "listAttendance": "fa-calendar-alt",
            "type": "link"
        }
        links.append(link)
        link2 = {
            "link": "studentAccount",
            "title": "To'lov va Qarzlari",
            "iconClazz": "fa-wallet",
            "type": "link"
        }
        username = student_get.user.username
        links.append(link2)
        link4 = {
            "link": "changeInfo",
            "title": "Ma'lumotlarni o'zgratirish",
            "iconClazz": "fa-pen",
            "type": "link"
        }
        link5 = {
            "link": "studentGroupsAttendance",
            "title": "Student davomatlari",
            "iconClazz": "fa-calendar-alt",
            "type": "link"
        }
        link6 = {
            "link": "changePhoto",
            "title": "Rasmni yangilash",
            "iconClazz": "fa-camera",
            "type": "link"
        }
        links.append(link4)
        links.append(link5)
        links.append(link6)
        link7 = {
            "link": "ballHistory",
            "title": "Oylik baholari",
            "iconClazz": "fas fa-star",
            "type": "link"
        }
        links.append(link7)
        link8 = {
            "link": "groupHistory",
            "title": "Guruhlar tarixi",
            "iconClazz": "fas fa-history",
            "type": "link"
        }
        links.append(link8)
        link9 = {
            "link": "timeTable",
            "title": "Dars Jadvali",
            "iconClazz": "fas fa-user-clock",
            "type": "link"
        }
        links.append(link9)

        if student_get.debtor == 2:
            link3 = {
                "name": "delayDay",
                "title": "Kun uzaytirish",
                "iconClazz": "fa-money-check",
                "type": "btn"
            }
            links.append(link3)
        if student_get.debtor == 1 or student_get.debtor == 2:
            link4 = {
                "name": "paymentExcuse",
                "title": "To'lov Sababi",
                "iconClazz": "fa-file-invoice-dollar",
                "type": "btn"
            }
            links.append(link4)
        blocked = True if student_get.debtor == 4 else False
        subject_list = [{"name": sub.name.title()} for sub in student_get.subject]
        old_balance = student_get.old_debt if student_get.old_debt else student_get.old_money if student_get.old_money else 0
        contract = Contract_Students.query.filter(Contract_Students.student_id == student_get.id).first()

        if contract:
            contract_data = {
                "representative_name": student_get.representative_name,
                "representative_surname": student_get.representative_surname,
                "representative_fatherName": contract.father_name,
                "representative_passportSeries": contract.passport_series,
                "representative_givenTime": contract.given_time,
                "representative_givenPlace": contract.given_place,
                "representative_place": contract.place,
                "ot": contract.created_date.strftime("%Y-%m-%d"),
                "do": contract.expire_date.strftime("%Y-%m-%d")
            }
        user = {
            "id": user_get.id,
            "role": role.role,
            "isSalary": salary_status,
            "photo_profile": user_get.photo_profile,
            "contract_data": contract_data,
            "activeToChange": {
                "username": True,
                "name": True,
                "surname": True,
                "fathersName": True,
                "age": True,
                "phone": True,
                "birth": True,
                "parent_phone": True,
                "subject": True,
                "comment": True,
                "language": True,
                "shift": True
            },
            "username": user_get.username,
            "type_role": type_role,
            "isBlocked": blocked,
            "contract_url": student_get.contract_pdf_url,
            "location_id": user_get.location_id,
            "balance": user_get.balance,
            "info": {
                "name": {
                    "name": "Ism",
                    "value": user_get.name.title(),
                    "order": 1
                },
                "surname": {
                    "name": "Familya",
                    "value": user_get.surname.title(),
                    "order": 2
                },
                "fathersName": {
                    "name": "Otasining Ismi",
                    "value": user_get.father_name.title() if user_get.father_name else "",
                    "order": 3
                },
                "age": {
                    "name": "Yosh",
                    "value": user_get.age,
                    "order": 4
                },
                "phone": phone_list,
                "parentPhone": parent_phone,

                "birthDate": {
                    "name": "Tug'ulgan kun",
                    "value": str(user_get.born_year) + "-" + str(user_get.born_month) + "-" + str(user_get.born_day),
                    "order": 7
                },
                "username": {
                    "name": "Foydalanuvchi",
                    "value": username,
                    "order": 0
                },
                "subject": {
                    "name": "Fan",
                    "value": subject_list,
                    "order": 8
                },
                "combined_payment": {
                    "name": "Umumiy summa",
                    "value": student_get.combined_debt,
                    "order": 9
                },
                'balance': {
                    "name": "Hisobi",
                    "value": student_get.user.balance,
                    "order": 10
                },

                # "extra_payment": {
                #     "name": "Qo'chimcha to'lovi",
                #     "value": student_get.extra_payment,
                #     "order": 11
                # },
                'old_debt': {
                    "name": "Eski platforma hisobi",
                    "value": old_balance,
                    "order": 11
                },
                "contract": {
                    "name": "Shartnoma",
                    "value": contract_yes,
                    "order": 12,
                    "type": "icon"
                },
                "shift": {
                    "name": "Smen",
                    "value": shift,
                    "order": 13
                },
                "birthDay": {
                    "name": "Tug'ilgan kun",
                    "value": user_get.born_day,
                    "display": "none"
                },
                "birthMonth": {
                    "name": "Tug'ilgan oy",
                    "value": user_get.born_month,
                    "display": "none"
                },
                "birthYear": {
                    "name": "Tug'ilgan yil",
                    "value": user_get.born_year,
                    "display": "none"
                },

            },

            "rate": rate_list,
            "tests": iterate_models(student_tests),
            "groups": group_list,
            "subjects": subject_list,
            "links": links,

        }
    else:
        i = 0
        location_list = [loc.id for loc in teacher_get.locations] if teacher_get else []
        subject_list = []
        if teacher_get:
            salary_status = False
            link = {
                "link": "employeeSalary",
                "title": "To'lov",
                "iconClazz": "fa-dollar-sign",
                "type": "link"
            }
            subject_list = [{"name": sub.name.title()} for sub in teacher_get.subject]
            username = teacher_get.user.username
            role = Roles.query.filter(Roles.id == user_get.role_id).first()

            group_list = [{"id": gr.id, "nameGroup": gr.name.title(), "teacherImg": "", "count": len(gr.student)}
                          for gr in teacher_get.group if
                          not gr.deleted]

            for count in group_list:
                i += count["count"]

            type_role = "Teacher"
        location_list = list(dict.fromkeys(location_list))

        if staff_get:
            role = Roles.query.filter(Roles.id == user_get.role_id).first()
            link = {
                "link": "employeeSalary",
                "title": "To'lov",
                "iconClazz": "fa-dollar-sign",
                "type": "link"
            }
            username = staff_get.user.username
            type_role = role.type_role

        if director_get.director:
            role = Roles.query.filter(Roles.id == user_get.role_id).first()
            link = {
                "link": "employeeSalary",
                "title": "To'lov",
                "iconClazz": "fa-dollar-sign",
                "type": "link"
            }
            username = director_get.username
            type_role = "Director"
        if hasattr(role, 'role') and role.role:
            role = role.role
        else:
            role = type_role
        if not user_get.camp_staffs:
            links_f = [
                {
                    "link": "changeInfo",
                    "title": "Ma'lumotlarni o'zgratirish",
                    "iconClazz": "fa-pen",
                    "type": "link"
                },
                link,
                {
                    "link": "changePhoto",
                    "title": "Rasmni yangilash",
                    "iconClazz": "fa-camera",
                    "type": "link"
                },
                {
                    "link": "timeTable",
                    "title": "Dars Jadvali",
                    "iconClazz": "fas fa-user-clock",
                    "type": "link"
                }
            ]
        else:
            links_f = [
                {
                    "link": "changeInfo",
                    "title": "Ma'lumotlarni o'zgratirish",
                    "iconClazz": "fa-pen",
                    "type": "link"
                },
                link,
                {
                    "link": "changePhoto",
                    "title": "Rasmni yangilash",
                    "iconClazz": "fa-camera",
                    "type": "link"
                },
                {
                    "link": "../../staffSalary",
                    "title": "Salary",
                    "iconClazz": "fa-dollar-sign",
                    "type": "link"
                }
            ]
        user = {
            "isSalary": salary_status,
            "id": user_get.id,
            "role": role,
            "photo_profile": user_get.photo_profile,
            "observer": user_get.observer,
            "att_count": att_count,
            "activeToChange": {
                "username": True,
                "name": True,
                "surname": True,
                "fathersName": True,
                "age": True,
                "phone": True,
                "birth": True,
                "comment": True,
                "language": True,
                "color": True,
                "subject": True
            },
            "username": user_get.username,
            "type_role": type_role,
            "location_id": user_get.location_id,
            "info": {
                "name": {
                    "name": "Ism",
                    "value": user_get.name.title(),
                    "order": 1
                },
                "surname": {
                    "name": "Familya",
                    "value": user_get.surname.title(),
                    "order": 2
                },
                "fathersName": {
                    "name": "Otasining Ismi",
                    "value": user_get.father_name,
                    "order": 3
                },
                "age": {
                    "name": "Yosh",
                    "value": user_get.age,
                    "order": 4
                },
                "phone": phone_list,

                "birthDate": {
                    "name": "Tug'ulgan kun",
                    "value": str(user_get.born_year) + "-" + str(user_get.born_month) + "-" + str(user_get.born_day),
                    "order": 7
                },
                "username": {
                    "name": "Foydalanuvchi",
                    "value": username,
                    "order": 0
                },

                "birthDay": {
                    "name": "Tug'ilgan kun",
                    "value": user_get.born_day,
                    "display": "none"
                },
                "birthMonth": {
                    "name": "Tug'ilgan oy",
                    "value": user_get.born_month,
                    "display": "none"
                },
                "birthYear": {
                    "name": "Tug'ilgan yil",
                    "value": user_get.born_year,
                    "display": "none"
                },
                "subject": {
                    "name": "Fan",
                    "value": subject_list,
                    "order": 8
                },

            },

            "links": links_f,
            "location_list": location_list,
            "groups": group_list,
            "subjects": subject_list,

        }
        if type_role == "Teacher":
            if user['info'].get("students") is None:
                user['info']["students"] = {}
            user['info']["students"] = {
                "name": "O'quvchilar soni",
                "value": i,
                "order": 8
            }

    if student_get:
        st_functions = Student_Functions(student_id=student_get.id)
        st_functions.filter_charity()
        st_functions.update_debt()
        st_functions.update_balance()
    if teacher_get:
        update_salary(user_id)
    return jsonify({
        "user": user
    })


@app.route(f'{api}/user_time_table/<int:user_id>/<int:location_id>')
@jwt_required()
def user_time_table(user_id, location_id):
    student = Students.query.filter(Students.user_id == user_id).first()
    teacher = Teachers.query.filter(Teachers.user_id == user_id).first()
    table_list = []
    weeks = []

    if student:
        week_days = Week.query.filter(Week.location_id == location_id).order_by(Week.order).all()
        for week in week_days:
            weeks.append(week.name)
        groups = db.session.query(Groups).join(Groups.student).options(contains_eager(Groups.student)).filter(
            Students.id == student.id).order_by(Groups.id).all()

        for group in groups:
            group_info = {
                "name": group.name,
                "id": group.id,
                "lesson": []
            }
            week_list = []
            for week in week_days:
                info = {
                    "from": "",
                    "to": "",
                    "room": ""
                }
                time_table = db.session.query(Group_Room_Week).join(Group_Room_Week.student).options(
                    contains_eager(Group_Room_Week.student)).filter(Students.id == student.id,
                                                                    Group_Room_Week.week_id == week.id,
                                                                    ).order_by(
                    Group_Room_Week.group_id).first()

                if time_table:
                    info["from"] = time_table.start_time.strftime("%H:%M")
                    info["to"] = time_table.end_time.strftime("%H:%M")
                    info['room'] = time_table.room.name

                week_list.append(info)
                group_info['lesson'] = week_list
            table_list.append(group_info)
    else:
        week_days = Week.query.filter(Week.location_id == location_id).order_by(Week.order).all()
        for week in week_days:
            weeks.append(week.name)
        groups = db.session.query(Groups).join(Groups.teacher).options(contains_eager(Groups.teacher)).filter(
            Teachers.id == teacher.id, Groups.deleted != True).order_by(Groups.id).all()
        for group in groups:
            group_info = {
                "name": group.name,
                "id": group.id,
                "lesson": []
            }
            week_list = []
            for week in week_days:
                info = {
                    "from": "",
                    "to": "",
                    "room": ""
                }
                time_table = db.session.query(Group_Room_Week).join(Group_Room_Week.teacher).options(
                    contains_eager(Group_Room_Week.teacher)).filter(Teachers.id == teacher.id,
                                                                    Group_Room_Week.group_id == group.id,
                                                                    Groups.location_id == location_id,
                                                                    Group_Room_Week.week_id == week.id,
                                                                    ).order_by(
                    Group_Room_Week.group_id).first()

                if time_table:
                    info["from"] = time_table.start_time.strftime("%H:%M")
                    info["to"] = time_table.end_time.strftime("%H:%M")
                    info['room'] = time_table.room.name

                week_list.append(info)
                group_info['lesson'] = week_list
            table_list.append(group_info)

    return jsonify({
        "success": True,
        "data": table_list,
        "days": weeks
    })


@app.route(f'{api}/user_time_table_classroom/<int:user_id>/<location_id>')
def user_time_table_classroom(user_id, location_id):
    student = Students.query.filter(Students.user_id == user_id).first()
    teacher = Teachers.query.filter(Teachers.user_id == user_id).first()
    table_list = []
    weeks = []

    if student:
        week_days = Week.query.filter(Week.location_id == student.user.location_id).order_by(Week.order).all()
        for week in week_days:
            weeks.append(week.name)
        groups = db.session.query(Groups).join(Groups.student).options(contains_eager(Groups.student)).filter(
            Students.id == student.id).order_by(Groups.id).all()

        for group in groups:
            group_info = {
                "name": group.name,
                "id": group.id,
                "lesson": []
            }
            week_list = []
            for week in week_days:
                info = {
                    "from": "",
                    "to": "",
                    "room": ""
                }
                time_table = db.session.query(Group_Room_Week).join(Group_Room_Week.student).options(
                    contains_eager(Group_Room_Week.student)).filter(Students.id == student.id,
                                                                    Group_Room_Week.week_id == week.id,
                                                                    ).order_by(
                    Group_Room_Week.group_id).first()

                if time_table:
                    info["from"] = time_table.start_time.strftime("%H:%M")
                    info["to"] = time_table.end_time.strftime("%H:%M")
                    info['room'] = time_table.room.name

                week_list.append(info)
                group_info['lesson'] = week_list
            table_list.append(group_info)
    else:
        week_days = Week.query.filter(Week.location_id == location_id).order_by(Week.order).all()
        for week in week_days:
            weeks.append(week.name)
        groups = db.session.query(Groups).join(Groups.teacher).options(contains_eager(Groups.teacher)).filter(
            Teachers.id == teacher.id, Groups.deleted != True).order_by(Groups.id).all()
        for group in groups:
            group_info = {
                "name": group.name,
                "id": group.id,
                "lesson": []
            }
            week_list = []
            for week in week_days:
                info = {
                    "from": "",
                    "to": "",
                    "room": ""
                }
                time_table = db.session.query(Group_Room_Week).join(Group_Room_Week.teacher).options(
                    contains_eager(Group_Room_Week.teacher)).filter(Teachers.id == teacher.id,
                                                                    Group_Room_Week.group_id == group.id,
                                                                    Groups.location_id == location_id,
                                                                    Group_Room_Week.week_id == week.id,
                                                                    ).order_by(
                    Group_Room_Week.group_id).first()

                if time_table:
                    info["from"] = time_table.start_time.strftime("%H:%M")
                    info["to"] = time_table.end_time.strftime("%H:%M")
                    info['room'] = time_table.room.name

                week_list.append(info)
                group_info['lesson'] = week_list
            table_list.append(group_info)

    return jsonify({
        "success": True,
        "data": table_list,
        "days": weeks
    })


@app.route(f'{api}/extend_att_date/<int:student_id>', methods=['POST'])
@jwt_required()
def extend_att_date(student_id):
    student = Students.query.filter(Students.user_id == student_id).first()
    reason = get_json_field('reason')
    date = get_json_field('date')
    year = date[0:4]
    month = date[5:7]
    day = date[8:10]
    result_date = year + '-' + month + '-' + day

    date = datetime.strptime(result_date, "%Y-%m-%d")
    add = StudentExcuses(student_id=student.id, reason=reason, to_date=date)
    db.session.add(add)
    db.session.commit()

    return jsonify({
        "success": True,
        "msg": "Davomat limit kuni belgilandi"

    })
