from app import *
from werkzeug.security import generate_password_hash, check_password_hash
from backend.functions.functions import *
import uuid
from backend.student.class_model import *
from datetime import datetime, timedelta, timezone
from flask_jwt_extended import jwt_required
import requests
from backend.student.class_model import *


@app.route(f'{api}/transfer')
def transfer():
    # without datetime

    # # subjects
    # subjects = Subjects.query.order_by(Subjects.id).all()
    # subjects_list = []
    # for sub in subjects:
    #     info = {
    #         "old_id": sub.id,
    #         "name": sub.name,
    #         "ball_number": sub.ball_number
    #     }
    #     subjects_list.append(info)
    # # subject_levels
    # subjects_levels = SubjectLevels.query.order_by(SubjectLevels.id).all()
    # subjects_levels_list = []
    # for level in subjects_levels:
    #     info = {
    #         "old_id": level.id,
    #         "name": level.name,
    #         "subject_id": level.subject_id
    #     }
    #     subjects_levels_list.append(info)
    # # role
    roles = Roles.query.filter(Roles.users_link != None).order_by(Roles.id).all()

    roles_list = []
    for role in roles:
        info = {
            "old_id": role.id,
            "role": role.role,
            "admin": role.admin,
            "student": role.student,
            "teacher": role.teacher,
            "director": role.director,
            "user": role.user,
            "programmer": role.programmer,
            "smm": role.smm
        }
        roles_list.append(info)
    #
    # # professions
    # professions = Professions.query.order_by(Professions.id).all()
    # professions_list = []
    # for profession in professions:
    #     info = {
    #         "old_id": profession.id,
    #         "name": profession.name
    #     }
    #     professions_list.append(info)
    # # payment_types
    # payment_types = PaymentTypes.query.order_by(PaymentTypes.id).all()
    # payment_type_list = []
    # for payment_type in payment_types:
    #     info = {
    #         "old_id": payment_type.id,
    #         "name": payment_type.name
    #     }
    #     payment_type_list.append(info)
    #
    # # education_language
    # education_languages = EducationLanguage.query.order_by(EducationLanguage.id).all()
    # education_languages_list = []
    # for language in education_languages:
    #     info = {
    #         "old_id": language.id,
    #         "name": language.name
    #     }
    #     education_languages_list.append(info)
    # # course_types
    # course_types_list = []
    # course_types = CourseTypes.query.order_by(CourseTypes.id).all()
    # for course_type in course_types:
    #     info = {
    #         "old_id": course_type.id,
    #         "name": course_type.name,
    #         "cost": course_type.cost
    #     }
    #     course_types_list.append(info)
    #
    # # with datetime
    # years = CalendarYear.query.order_by(CalendarYear.id).all()
    # years_list = []
    # for year in years:
    #     info = {
    #         "old_id": year.id,
    #         "date": year.date.strftime("%Y")
    #     }
    #     years_list.append(info)
    # months = CalendarMonth.query.order_by(CalendarMonth.id).all()
    # months_list = []
    # for month in months:
    #     info = {
    #         "old_id": month.id,
    #         "date": month.date.strftime("%Y-%m"),
    #         "year_id": month.year_id
    #     }
    #     months_list.append(info)
    #
    # days = CalendarDay.query.order_by(CalendarDay.id).all()
    # days_list = []
    # for day in days:
    #     info = {
    #         "old_id": day.id,
    #         "date": day.date.strftime("%Y-%m-%d"),
    #         "account_period_id": day.account_period_id,
    #         "month_id": day.month_id
    #     }
    #     days_list.append(info)
    #
    # accounting_periods = AccountingPeriod.query.order_by(AccountingPeriod.id).all()
    # accounting_periods_list = []
    # for period in accounting_periods:
    #     info = {
    #         "old_id": period.id,
    #         "from_date": period.from_date.strftime("%Y-%m-%d"),
    #         "to_date": period.to_date.strftime("%Y-%m-%d"),
    #         "year_id": period.year_id,
    #         "month_id": period.month_id
    #     }
    #     accounting_periods_list.append(info)
    #
    # # location
    # locations = Locations.query.order_by(Locations.id).all()
    # locations_list = []
    # for location in locations:
    #     info = {
    #         "old_id": location.id,
    #         "name": location.name,
    #         "calendar_day": location.calendar_day,
    #         "calendar_month": location.calendar_month,
    #         "calendar_year": location.calendar_year
    #     }
    #     locations_list.append(info)
    #
    # # rooms
    # rooms = Rooms.query.order_by(Rooms.id).all()
    # rooms_list = []
    # for room in rooms:
    #     info = {
    #         "old_id": room.id,
    #         "name": room.name,
    #         "electronic_board": room.electronic_board,
    #         "seats_number": room.seats_number,
    #         "location_id": room.location_id,
    #         "subjects": []
    #     }
    #     for sub in room.subject:
    #         extra_info = {
    #             "id": sub.id,
    #             "name": sub.name
    #         }
    #         info['subjects'].append(extra_info)
    #
    #     rooms_list.append(info)
    #
    # # room_subject
    #
    # # room_images
    # room_images = RoomImages.query.order_by(RoomImages.id).all()
    # room_images_list = []
    # for room in room_images:
    #     info = {
    #         "old_id": room.id,
    #         "room_id": room.room_id,
    #         "photo_url": room.photo_url
    #     }
    #     room_images_list.append(info)
    #
    # # week
    #
    # weeks = Week.query.order_by(Week.id).all()
    # week_list = []
    # for week in weeks:
    #     info = {
    #         "old_id": week.id,
    #         "name": week.name,
    #         "eng_name": week.eng_name,
    #         "location_id": week.location_id,
    #         "order": week.order
    #     }
    #     week_list.append(info)

    # users = Users.query.filter(and_(Users.id > 0, Users.id < 6000)).all()
    # users_list = []
    # for user in users:
    #     info = {
    #         "old_id": user.id,
    #         "location_id": user.location_id,
    #         "password": user.password,
    #         "education_language": user.education_language,
    #         "name": user.name,
    #         "surname": user.surname,
    #         "username": user.username,
    #         "user_id": user.user_id,
    #         "director": user.director,
    #         "photo_profile": user.photo_profile,
    #         "born_day": user.born_day,
    #         "born_month": user.born_month,
    #         "born_year": user.born_year,
    #         "age": user.age,
    #         "comment": user.comment,
    #         "father_name": user.father_name,
    #         "balance": user.balance,
    #         "calendar_day": user.calendar_day,
    #         "calendar_month": user.calendar_month,
    #         "calendar_year": user.calendar_year,
    #         "role_id": user.role_id,
    #         "phone_list": []
    #     }
    #     for phone in user.phone:
    #         extra_info = {
    #             "phone": phone.phone,
    #             "parent": phone.parent,
    #             "personal": phone.personal,
    #             "other": phone.other,
    #             "user_id": phone.user_id
    #         }
    #         info['phone_list'].append(extra_info)
    #     users_list.append(info)
    # print(len(users))

    # staffs = Staff.query.order_by(Staff.id).all()
    # staff_list = []
    # for staff in staffs:
    #     info = {
    #         "id": staff.id,
    #         "user_id": staff.user_id,
    #         "profession_id": staff.profession_id,
    #         "salary": staff.salary
    #     }
    #     staff_list.append(info)

    #

    # students = Students.query.filter(and_(Students.id > 0, Students.id < 6000)).order_by(Students.id).all()
    students_list = []
    # for st in students:
    #     info = {
    #         "old_id": st.id,
    #         "user_id": st.user_id,
    #         "ball_time": st.ball_time,
    #         "combined_debt": st.combined_debt,
    #         "debtor": st.debtor,
    #         "extra_payment": st.extra_payment,
    #         "representative_name": st.representative_name,
    #         "representative_surname": st.representative_surname,
    #         "contract_word_url": st.contract_word_url,
    #         "contract_pdf_url": st.contract_pdf_url,
    #         "old_debt": st.old_debt,
    #         "old_money": st.old_money,
    #         "morning_shift": st.morning_shift,
    #         "night_shift": st.night_shift,
    #         "groups": [],
    #         "subjects": [],
    #     }
    #     for sub in st.subject:
    #         subject_info = {
    #             "id": sub.id,
    #             "name": sub.name
    #         }
    #         info['subjects'].append(subject_info)
    #     for sub in st.group:
    #         group_info = {
    #             "old_id": sub.id,
    #             "name": sub.name,
    #             "course_type_id": sub.course_type_id,
    #             "subject_id": sub.subject_id,
    #             "teacher_salary": sub.teacher_salary,
    #             "location_id": sub.location_id,
    #             "status": sub.status,
    #             "education_language": sub.education_language,
    #             "calendar_day": sub.calendar_day,
    #             'calendar_month': sub.calendar_month,
    #             'calendar_year': sub.calendar_year,
    #             "teacher_id": sub.teacher_id,
    #             "price": sub.price,
    #             "deleted": sub.deleted,
    #             "teacher": {}
    #         }
    #         pprint(group_info)
    #         teacher = Teachers.query.filter(Teachers.id == sub.teacher_id).first()
    #         group_info['teacher'] = {
    #             "id": teacher.id,
    #             "table_color": teacher.table_color,
    #             "user_id": teacher.user_id,
    #             "locations": []
    #         }
    #         for location in teacher.locations:
    #             location_info = {
    #                 "id": location.id,
    #                 "name": location.name
    #             }
    #             group_info['teacher']['locations'].append(location_info)
    #         info['groups'].append(group_info)
    #     students_list.append(info)
    # print(len(students))
    # groups = Groups.query.order_by(Groups.id).all()
    # groups_list = []
    # for sub in groups:
    #
    #     group_info = {
    #         "old_id": sub.id,
    #         "name": sub.name,
    #         "course_type_id": sub.course_type_id,
    #         "subject_id": sub.subject_id,
    #         "teacher_salary": sub.teacher_salary,
    #         "location_id": sub.location_id,
    #         "status": sub.status,
    #         "education_language": sub.education_language,
    #         "calendar_day": sub.calendar_day,
    #         'calendar_month': sub.calendar_month,
    #         'calendar_year': sub.calendar_year,
    #         "teacher_id": sub.teacher_id,
    #         "price": sub.price,
    #         "deleted": sub.deleted,
    #         "teacher": {}
    #     }
    #     pprint(group_info)
    #     teacher = Teachers.query.filter(Teachers.id == sub.teacher_id).first()
    #     group_info['teacher'] = {
    #         "id": teacher.id,
    #         "table_color": teacher.table_color,
    #         "user_id": teacher.user_id,
    #         "locations": []
    #     }
    #     for location in teacher.locations:
    #         location_info = {
    #             "id": location.id,
    #             "name": location.name
    #         }
    #         group_info['teacher']['locations'].append(location_info)
    #     groups_list.append(group_info)

    # attendance_history_students = AttendanceHistoryStudent.query.filter(
    #     and_(AttendanceHistoryStudent.id > 9998, AttendanceHistoryStudent.id < 12000)).order_by(
    #     AttendanceHistoryStudent.id).all()
    # attendance_history_students_list = []
    # for attendance in attendance_history_students:
    #     info = {
    #         "old_id": attendance.id,
    #         "student_id": attendance.student_id,
    #         "total_debt": attendance.total_debt,
    #         "subject_id": attendance.subject_id,
    #         "group_id": attendance.group_id,
    #         "present_days": attendance.present_days,
    #         "absent_days": attendance.absent_days,
    #         "average_ball": attendance.average_ball,
    #         "payment": attendance.payment,
    #         "remaining_debt": attendance.remaining_debt,
    #         "location_id": attendance.location_id,
    #         "calendar_month": attendance.calendar_month,
    #         "calendar_year": attendance.calendar_year,
    #         "status": attendance.status,
    #         "total_discount": attendance.total_discount,
    #         "scored_days": attendance.scored_days
    #     }
    #     attendance_history_students_list.append(info)
    # all_attendances = AttendanceHistoryStudent.query.all()
    # print(len(all_attendances))

    # attendance_history_teachers = AttendanceHistoryTeacher.query.order_by(AttendanceHistoryTeacher.id).all()
    # attendance_history_teachers_list = []
    # for attendance in attendance_history_teachers:
    #     info = {
    #         "old_id": attendance.id,
    #         "teacher_id": attendance.teacher_id,
    #         "total_salary": attendance.total_salary,
    #         "subject_id": attendance.subject_id,
    #         "group_id": attendance.group_id,
    #         "taken_money": attendance.taken_money,
    #         "remaining_salary": attendance.remaining_salary,
    #         "location_id": attendance.location_id,
    #         "calendar_month": attendance.calendar_month,
    #         "calendar_year": attendance.calendar_year,
    #         "status": attendance.status
    #     }
    #     attendance_history_teachers_list.append(info)
    # print(len(attendance_history_teachers))

    month_filter = datetime.strptime("2022-12", "%Y-%m")
    # attendaces = db.session.query(Attendance).join(Attendance.month).options(contains_eager(Attendance.month)).filter(
    #     CalendarMonth.date > month_filter).order_by(desc(Attendance.id)).first()
    # print(attendaces.id)
    # attendaces = db.session.query(Attendance).join(Attendance.month).options(contains_eager(Attendance.month)).filter(
    #     CalendarMonth.date > month_filter).filter(and_(Attendance.id > 5999, Attendance.id < 12000)).order_by(
    #     Attendance.id).all()
    # attendance_list = []
    # for attendance in attendaces:
    #     info = {
    #         "old_id": attendance.id,
    #         "subject_id": attendance.subject_id,
    #         "student_id": attendance.student_id,
    #         "teacher_id": attendance.teacher_id,
    #         "group_id": attendance.group_id,
    #         "calendar_month": attendance.calendar_month,
    #         "calendar_year": attendance.calendar_year,
    #         "course_id": attendance.course_id,
    #         "location_id": attendance.location_id,
    #     }
    #     attendance_list.append(info)
    # attendaces = db.session.query(Attendance).join(Attendance.month).options(contains_eager(Attendance.month)).filter(
    #     CalendarMonth.date > month_filter).filter(and_(Attendance.id > 5999, Attendance.id < 12000)).order_by(Attendance.id).all()
    # print(len(attendaces))
    #
    # day_filter = datetime.strptime("2022-12-31", "%Y-%m-%d")
    # attendance_days = db.session.query(AttendanceDays).join(AttendanceDays.day).options(
    #     contains_eager(AttendanceDays.day)).filter(CalendarDay.date > day_filter).filter(
    #     and_(AttendanceDays.id > 102999, AttendanceDays.id < 104000)).order_by(AttendanceDays.id).all()
    # attendance_days_list = []
    # for attendance in attendance_days:
    #     info = {
    #         "old_id": attendance.id,
    #         "student_id": attendance.student_id,
    #         "attendance_id": attendance.attendance_id,
    #         "calendar_day": attendance.calendar_day,
    #         "status": attendance.status,
    #         "activeness": attendance.activeness,
    #         "dictionary": attendance.dictionary,
    #         "homework": attendance.homework,
    #         "average_ball": attendance.average_ball,
    #         "balance_per_day": attendance.balance_per_day,
    #         "salary_per_day": attendance.salary_per_day,
    #         "balance_with_discount": attendance.balance_with_discount,
    #         "discount_per_day": attendance.discount_per_day,
    #         "location_id": attendance.location_id,
    #         "teacher_id": attendance.teacher_id,
    #         "group_id": attendance.group_id,
    #         "reason": attendance.reason,
    #         "discount": attendance.discount
    #     }
    #
    #     attendance_days_list.append(info)

    # attendance_days = db.session.query(AttendanceDays).join(AttendanceDays.day).options(
    #     contains_eager(AttendanceDays.day)).filter(CalendarDay.date > day_filter).order_by(AttendanceDays.id).first()
    # print(attendance_days.id)
    # 58003
    # attendance_days = db.session.query(AttendanceDays).join(AttendanceDays.day).options(
    #     contains_eager(AttendanceDays.day)).filter(CalendarDay.date > day_filter).order_by(
    #     desc(AttendanceDays.id)).first()
    # print(attendance_days.id)
    # 103566
    # attendance_days = db.session.query(AttendanceDays).join(AttendanceDays.day).options(
    #     contains_eager(AttendanceDays.day)).filter(CalendarDay.date > day_filter).order_by(
    #     AttendanceDays.id).all()
    # print(len(attendance_days))

    # student_payments_list = []
    # student_payments = StudentPayments.query.filter(and_(StudentPayments.id > 7999, StudentPayments.id < 10000)).order_by(
    #     StudentPayments.id).all()
    # for payment in student_payments:
    #     info = {
    #         "old_id": payment.id,
    #         "student_id": payment.student_id,
    #         "location_id": payment.location_id,
    #         "calendar_day": payment.calendar_day,
    #         "calendar_month": payment.calendar_month,
    #         "calendar_year": payment.calendar_year,
    #         "payment_sum": payment.payment_sum,
    #         "payment_type_id": payment.payment_type_id,
    #         "account_period_id": payment.account_period_id,
    #         "payment": payment.payment,
    #         "by_who": payment.by_who
    #     }
    #     student_payments_list.append(info)
    # student_payments = StudentPayments.query.order_by(desc(StudentPayments.id)).all()
    # print(len(student_payments))

    #
    # deleted_student_payments_list = []
    # deleted_student_payments = DeletedStudentPayments.query.order_by(DeletedStudentPayments.id).all()
    # for payment in deleted_student_payments:
    #     info = {
    #         "old_id": payment.id,
    #         "student_id": payment.student_id,
    #         "location_id": payment.location_id,
    #         "calendar_day": payment.calendar_day,
    #         "calendar_month": payment.calendar_month,
    #         "calendar_year": payment.calendar_year,
    #         "payment_sum": payment.payment_sum,
    #         "payment_type_id": payment.payment_type_id,
    #         "account_period_id": payment.account_period_id,
    #         "payment": payment.payment,
    #         "reason": payment.reason
    #     }
    #     deleted_student_payments_list.append(info)
    # print(len(deleted_student_payments))

    # #
    # studentcharitys = StudentCharity.query.order_by(StudentCharity.id).all()
    # student_charity_list = []
    #
    # for charity in studentcharitys:
    #     info = {
    #         "old_id": charity.id,
    #         "student_id": charity.student_id,
    #         "discount": charity.discount,
    #         "group_id": charity.group_id,
    #         "calendar_day": charity.calendar_day,
    #         "calendar_month": charity.calendar_month,
    #         "calendar_year": charity.calendar_year,
    #         "account_period_id": charity.account_period_id,
    #         "location_id": charity.location_id
    #     }
    #     student_charity_list.append(info)
    # print(len(studentcharitys))
    #
    # student_history_groups = StudentHistoryGroups.query.order_by(StudentHistoryGroups.id).all()
    # student_history_groups_list = []
    # for history_group in student_history_groups:
    #     info = {
    #         "old_id": history_group.id,
    #         "student_id": history_group.student_id,
    #         "group_id": history_group.group_id,
    #         "teacher_id": history_group.teacher_id,
    #         "joined_day": history_group.joined_day,
    #         "left_day": history_group.left_day,
    #         "reason": history_group.reason
    #     }
    #     student_history_groups_list.append(info)
    # print(len(student_history_groups))

    # student_excuses = StudentExcuses.query.order_by(StudentExcuses.id).all()
    # student_excuses_list = []
    # for excuse in student_excuses:
    #     info = {
    #         "old_id": excuse.id,
    #         "student_id": excuse.student_id,
    #         "reason": excuse.reason,
    #         "to_date": excuse.to_date,
    #         "added_date": excuse.added_date
    #     }
    #     student_excuses_list.append(info)
    #
    # print(len(student_excuses))
    #

    # contract_students = Contract_Students.query.order_by(Contract_Students.id).all()
    # contract_students_list = []
    # for contract in contract_students:
    #     info = {
    #         "old_id": contract.id,
    #         "created_date": contract.created_date,
    #         "expire_date": contract.expire_date,
    #         "student_id": contract.student_id,
    #         "given_place": contract.given_place,
    #         "given_time": contract.given_time,
    #         "place": contract.place,
    #         "father_name": contract.father_name,
    #         "passport_series": contract.passport_series
    #     }
    #     contract_students_list.append(info)
    # print(len(contract_students))

    # deleted_students = DeletedStudents.query.order_by(DeletedStudents.id).all()
    # deleted_students_list = []
    # for deleted in deleted_students:
    #     info = {
    #         "id": deleted.id,
    #         "student_id": deleted.student_id,
    #         "reason": deleted.reason,
    #         "group_id": deleted.group_id,
    #         "teacher_id": deleted.teacher_id,
    #         "calendar_day": deleted.calendar_day
    #     }
    #     deleted_students_list.append(info)
    # print(len(deleted_students))

    # registered_deleted = RegisterDeletedStudents.query.order_by(RegisterDeletedStudents.id).all()
    # registered_deleted_list = []
    # for deleted in registered_deleted:
    #     info = {
    #         "id": deleted.id,
    #         "student_id": deleted.student_id,
    #         "reason": deleted.reason,
    #         "calendar_day": deleted.calendar_day
    #     }
    #     registered_deleted_list.append(info)
    # print(len(registered_deleted))

    # book_payments = BookPayments.query.order_by(BookPayments.id).all()
    # book_payments_list = []
    # for payment in book_payments:
    #     info = {
    #         "old_id": payment.id,
    #         "student_id": payment.student_id,
    #         "location_id": payment.location_id,
    #         "calendar_day": payment.calendar_day,
    #         "calendar_month": payment.calendar_month,
    #         "calendar_year": payment.calendar_year,
    #         "payment_sum": payment.payment_sum,
    #         "account_period_id": payment.account_period_id
    #     }
    #     book_payments_list.append(info)
    # print(len(book_payments))
    # deleted_book_payments = DeletedBookPayments.query.order_by(DeletedBookPayments.id).all()
    # deleted_book_payments_list = []
    # for payment in deleted_book_payments:
    #     info = {
    #         "old_id": payment.id,
    #         "student_id": payment.student_id,
    #         "location_id": payment.location_id,
    #         "calendar_day": payment.calendar_day,
    #         "calendar_month": payment.calendar_month,
    #         "calendar_year": payment.calendar_year,
    #         "payment_sum": payment.payment_sum,
    #         "account_period_id": payment.account_period_id
    #     }
    #     deleted_book_payments_list.append(info)
    # print(len(deleted_book_payments))

    # teacher_salaries = TeacherSalary.query.order_by(TeacherSalary.id).all()
    # teacher_salaries_list = []
    # for salary in teacher_salaries:
    #     info = {
    #         "old_id": salary.id,
    #         "teacher_id": salary.teacher_id,
    #         "total_salary": salary.total_salary,
    #         "remaining_salary": salary.remaining_salary,
    #         "location_id": salary.location_id,
    #         "calendar_month": salary.calendar_month,
    #         "calendar_year": salary.calendar_year,
    #         "status": salary.status,
    #         "taken_money": salary.taken_money
    #     }
    #     teacher_salaries_list.append(info)
    # print(len(teacher_salaries))
    # teachers = Teachers.query.order_by(Teachers.id).all()
    # teachers_list = []
    # for teacher in teachers:
    #     info = {
    #         "old_id": teacher.id,
    #         "user_id": teacher.user_id,
    #         "subject": []
    #     }
    #     for sub in teacher.subject:
    #         sub_info = {
    #             "id": sub.id,
    #             "name": sub.name
    #         }
    #         info['subject'].append(sub_info)
    #     teachers_list.append(info)
    # deleted_teachers = DeletedTeachers.query.order_by(DeletedTeachers.id).all()
    # deleted_teachers_list = []
    # for teacher in deleted_teachers:
    #     info = {
    #         "id": teacher.id,
    #         "teacher_id": teacher.teacher_id,
    #         "reason": teacher.reason,
    #         "calendar_day": teacher.calendar_day
    #     }
    #     deleted_teachers_list.append(info)
    # teacher_salaries_day = TeacherSalaries.query.order_by(TeacherSalaries.id).all()
    # teacher_salaries_day_list = []
    # for salary in teacher_salaries_day:
    #     info = {
    #         "old_id": salary.id,
    #         "payment_sum": salary.payment_sum,
    #         "reason": salary.reason,
    #         "payment_type_id": salary.payment_type_id,
    #         "salary_location_id": salary.salary_location_id,
    #         "teacher_id": salary.teacher_id,
    #         "location_id": salary.location_id,
    #         "calendar_day": salary.calendar_day,
    #         "calendar_month": salary.calendar_month,
    #         "calendar_year": salary.calendar_year,
    #         "account_period_id": salary.account_period_id,
    #         "by_who": salary.by_who,
    #         "day": salary.day.date
    #     }
    #     teacher_salaries_day_list.append(info)
    # print(len(teacher_salaries_day))

    # deleted_teacher_salaries_day = DeletedTeacherSalaries.query.order_by(DeletedTeacherSalaries.id).all()
    # deleted_teacher_salaries_day_list = []
    # for salary in deleted_teacher_salaries_day:
    #     info = {
    #         "old_id": salary.id,
    #         "payment_sum": salary.payment_sum,
    #         "reason": salary.reason,
    #         "payment_type_id": salary.payment_type_id,
    #         "salary_location_id": salary.salary_location_id,
    #         "teacher_id": salary.teacher_id,
    #         "location_id": salary.location_id,
    #         "calendar_day": salary.calendar_day,
    #         "calendar_month": salary.calendar_month,
    #         "calendar_year": salary.calendar_year,
    #         "account_period_id": salary.account_period_id,
    #         "group_id": salary.group_id,
    #         "deleted_date": salary.deleted_date,
    #         "reason_deleted": salary.reason_deleted,
    #     }
    #     deleted_teacher_salaries_day_list.append(info)
    # print(len(deleted_teacher_salaries_day))

    # staff_salaries = StaffSalary.query.order_by(StaffSalary.id).all()
    # staff_salaries_list = []
    # for salary in staff_salaries:
    #     info = {
    #         "old_id": salary.id,
    #         "staff_id": salary.staff_id,
    #         "total_salary": salary.total_salary,
    #         "remaining_salary": salary.remaining_salary,
    #         "location_id": salary.location_id,
    #         "calendar_month": salary.calendar_month,
    #         "calendar_year": salary.calendar_year,
    #         "status": salary.status,
    #         "taken_money": salary.taken_money
    #     }
    #     staff_salaries_list.append(info)
    # print(len(staff_salaries))
    # staff_salaries_day = StaffSalaries.query.order_by(StaffSalaries.id).all()
    # staff_salaries_day_list = []
    # for salary in staff_salaries_day:
    #     info = {
    #         "old_id": salary.id,
    #         "payment_sum": salary.payment_sum,
    #         "reason": salary.reason,
    #         "payment_type_id": salary.payment_type_id,
    #         "salary_id": salary.salary_id,
    #         "staff_id": salary.staff_id,
    #         "location_id": salary.location_id,
    #         "calendar_day": salary.calendar_day,
    #         "calendar_month": salary.calendar_month,
    #         "calendar_year": salary.calendar_year,
    #         "profession_id": salary.profession_id,
    #         "account_period_id": salary.account_period_id,
    #         "by_who": salary.by_who
    #     }
    #     staff_salaries_day_list.append(info)
    # print(len(staff_salaries_day))
    # deleted_staff_salaries_day = DeletedStaffSalaries.query.order_by(DeletedStaffSalaries.id).all()
    # deleted_staff_salaries_day_list = []
    # for salary in deleted_staff_salaries_day:
    #     info = {
    #         "old_id": salary.id,
    #         "payment_sum": salary.payment_sum,
    #         "reason": salary.reason,
    #         "payment_type_id": salary.payment_type_id,
    #         "salary_id": salary.salary_id,
    #         "staff_id": salary.staff_id,
    #         "location_id": salary.location_id,
    #         "calendar_day": salary.calendar_day,
    #         "calendar_month": salary.calendar_month,
    #         "calendar_year": salary.calendar_year,
    #         "profession_id": salary.profession_id,
    #         "account_period_id": salary.account_period_id,
    #         "deleted_date": salary.deleted_date,
    #         "reason_deleted": salary.reason_deleted
    #     }
    #     deleted_staff_salaries_day_list.append(info)
    # print(len(deleted_staff_salaries_day))
    #
    # group_room_weeks = Group_Room_Week.query.order_by(Group_Room_Week.id).all()
    # group_room_weeks_list = []
    # for time in group_room_weeks:
    #     info = {
    #         "old_id": time.id,
    #         "group_id": time.group_id,
    #         "room_id": time.room_id,
    #         "week_id": time.week_id,
    #         "start_time": time.start_time,
    #         "end_time": time.end_time,
    #         "location_id": time.location_id,
    #         "teachers": [],
    #         "students": []
    #     }
    #     for student in time.student:
    #         info['students'].append(student.id)
    #     for teacher in time.teacher:
    #         info['teachers'].append(teacher.id)
    #     group_room_weeks_list.append(info)
    # print(len(group_room_weeks))
    # #
    # capital_expenditures = CapitalExpenditure.query.order_by(CapitalExpenditure.id).all()
    # capital_expenditures_list = []
    # for capital in capital_expenditures:
    #     info = {
    #         "id": capital.id,
    #         "item_sum": capital.item_sum,
    #         "item_name": capital.item_name,
    #         "payment_type_id": capital.payment_type_id,
    #         "location_id": capital.location_id,
    #         "calendar_day": capital.calendar_day,
    #         "calendar_month": capital.calendar_month,
    #         "calendar_year": capital.calendar_year,
    #         "account_period_id": capital.account_period_id,
    #         "by_who": capital.by_who
    #     }
    #     capital_expenditures_list.append(info)
    # print(len(capital_expenditures))
    # deleted_capital_expenditures = DeletedCapitalExpenditure.query.order_by(DeletedCapitalExpenditure.id).all()
    # deleted_capital_expenditures_list = []
    # for capital in deleted_capital_expenditures:
    #     info = {
    #         "id": capital.id,
    #         "item_sum": capital.item_sum,
    #         "item_name": capital.item_name,
    #         "payment_type_id": capital.payment_type_id,
    #         "location_id": capital.location_id,
    #         "calendar_day": capital.calendar_day,
    #         "calendar_month": capital.calendar_month,
    #         "calendar_year": capital.calendar_year,
    #         "account_period_id": capital.account_period_id,
    #         "deleted_date": capital.deleted_date,
    #
    #         "reason": capital.reason
    #     }
    #     deleted_capital_expenditures_list.append(info)
    # print(len(deleted_capital_expenditures))
    # overheads = Overhead.query.order_by(Overhead.id).all()
    # overheads_list = []
    # for overhead in overheads:
    #     info = {
    #         "id": overhead.id,
    #         "item_sum": overhead.item_sum,
    #         "item_name": overhead.item_name,
    #         "payment_type_id": overhead.payment_type_id,
    #         "location_id": overhead.location_id,
    #         "calendar_day": overhead.calendar_day,
    #         "calendar_month": overhead.calendar_month,
    #         "calendar_year": overhead.calendar_year,
    #         "account_period_id": overhead.account_period_id,
    #         "by_who": overhead.by_who
    #     }
    #     overheads_list.append(info)
    # print(len(overheads))
    # deleted_overheads = DeletedOverhead.query.order_by(DeletedOverhead.id).all()
    # deleted_overheads_list = []
    # for overhead in deleted_overheads:
    #     info = {
    #         "id": overhead.id,
    #         "item_sum": overhead.item_sum,
    #         "item_name": overhead.item_name,
    #         "payment_type_id": overhead.payment_type_id,
    #         "location_id": overhead.location_id,
    #         "calendar_day": overhead.calendar_day,
    #         "calendar_month": overhead.calendar_month,
    #         "calendar_year": overhead.calendar_year,
    #         "account_period_id": overhead.account_period_id,
    #         "deleted_date": overhead.deleted_date,
    #         "reason": overhead.reason
    #     }
    #     deleted_overheads_list.append(info)
    # print(len(deleted_overheads))
    # accounting_infos = AccountingInfo.query.order_by(AccountingInfo.id).all()
    # accounting_infos_list = []
    #
    # for account in accounting_infos:
    #     info = {
    #         "id": account.id,
    #         "calendar_month": account.calendar_month,
    #         "calendar_year": account.calendar_year,
    #         "payment_type_id": account.payment_type_id,
    #         "location_id": account.location_id,
    #         "all_payments": account.all_payments,
    #         "all_teacher_salaries": account.all_teacher_salaries,
    #         "all_staff_salaries": account.all_staff_salaries,
    #         "all_overhead": account.all_overhead,
    #         "all_capital": account.all_capital,
    #         "current_cash": account.current_cash,
    #         "old_cash": account.old_cash,
    #         "all_discount": account.all_discount,
    #         "account_period_id": account.account_period_id
    #     }
    #     accounting_infos_list.append(info)
    #
    # comments = Comments.query.order_by(Comments.id).all()
    # comments_list = []
    # for link in comments:
    #     info = {
    #         "id": link.id,
    #         "comment": link.comment,
    #         "user_id": link.user_id
    #     }
    #     comments_list.append(info)
    #
    # commentlikes = CommentLikes.query.order_by(CommentLikes.id).all()
    # commentlikes_list = []
    # for link in commentlikes:
    #     info = {
    #         "id": link.id,
    #         "comment_id": link.comment_id,
    #         "user_id": link.user_id
    #     }
    #     commentlikes_list.append(info)
    #
    # gallery = Gallery.query.order_by(Gallery.id).all()
    # gallery_list = []
    # for link in gallery:
    #     info = {
    #         "id": link.id,
    #         "img": link.img
    #     }
    #     gallery_list.append(info)

    return jsonify({
        # "subjects_list": subjects_list,
        # "subjects_levels_list": subjects_levels_list,
        "roles_list": roles_list,
        # "professions_list": professions_list,
        # "payment_type_list": payment_type_list,
        # "education_languages_list": education_languages_list,
        # "course_types_list": course_types_list,
        # "years_list": years_list,
        # "months_list": months_list,
        # "days_list": days_list,
        # "accounting_periods_list": accounting_periods_list,
        # "locations_list": locations_list,
        # "rooms_list": rooms_list,
        # "room_images_list": room_images_list,
        # "week_list": week_list,

        # "users_list": users_list,

        # "staff_list": staff_list,

        # "students_list": students_list,

        # "attendance_history_students_list": attendance_history_students_list,

        # "attendance_history_teachers_list": attendance_history_teachers_list,

        # "attendance_list": attendance_list,

        # "attendance_days_list": attendance_days_list,

        # "student_payments_list": student_payments_list,

        # "deleted_student_payments_list": deleted_student_payments_list,
        # "student_charity_list": student_charity_list,
        # "student_history_groups_list": student_history_groups_list,

        # "student_excuses_list": student_excuses_list,
        # "contract_students_list": contract_students_list,
        # "deleted_students_list": deleted_students_list,
        # "registered_deleted_list": registered_deleted_list,

        # "book_payments_list": book_payments_list,
        # "deleted_book_payments_list": deleted_book_payments_list,

        # "teachers_list": teachers_list,
        # "deleted_teachers_list": deleted_teachers_list,
        # "teacher_salaries_list": teacher_salaries_list,
        # "teacher_salaries_day_list": teacher_salaries_day_list,
        # "deleted_teachers_list": deleted_teachers_list
        # "deleted_teacher_salaries_day_list": deleted_teacher_salaries_day_list,
        # "staff_salaries_list": staff_salaries_list,
        # "staff_salaries_day_list": staff_salaries_day_list,
        # "deleted_staff_salaries_day_list": deleted_staff_salaries_day_list,

        # "group_room_weeks_list": group_room_weeks_list,
        # "capital_expenditures_list": capital_expenditures_list,
        # "deleted_capital_expenditures_list": deleted_capital_expenditures_list,
        # "overheads_list": overheads_list,
        # "deleted_overheads_list": deleted_overheads_list,
        # "accounting_infos_list": accounting_infos_list,
        # "comments_list": comments_list,
        # "commentlikes_list": commentlikes_list,
        # "gallery_list": gallery_list
    })
