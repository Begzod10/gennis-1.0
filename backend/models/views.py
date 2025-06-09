from app import db, admin
from flask_admin.contrib.sqla import ModelView
from backend.models.models import Users, Roles, Subjects, EducationLanguage, Locations, PaymentTypes, Professions, \
    Students


class UserAdmin(ModelView):
    column_list = ['id', 'username', 'role_id', 'location_id', 'born_day', 'born_month', 'born_year',
                   'director', 'user_id', 'name', 'surname', 'password', 'father_name']
    form_columns = ['username', 'role_id', 'location_id', 'name', 'surname', 'password', 'father_name',
                    'director', 'user_id', 'born_day', 'born_month', 'born_year']


class StudentAdmin(ModelView):
    column_list = ['id', 'subject']
    form_columns = ['subject']


class RoleAdmin(ModelView):
    column_list = ['id', 'type_role', 'role']
    form_columns = ['type_role', 'role']


class SubjectAdmin(ModelView):
    column_list = ['id', 'name', 'ball_number', 'old_id']
    form_columns = ['name', 'ball_number', 'old_id']


class EducationLanguageAdmin(ModelView):
    column_list = ['id', 'name', 'old_id']
    form_columns = ['name', 'old_id']


class LocationAdmin(ModelView):
    column_list = ['id', 'name', 'old_id']
    form_columns = ['name', 'old_id']


class PaymentTypeAdmin(ModelView):
    column_list = ['id', 'name', 'old_id']
    form_columns = ['name', 'old_id']


class ProfessionAdmin(ModelView):
    column_list = ['id', 'name']
    form_columns = ['name']


admin.add_view(UserAdmin(Users, db.session))
admin.add_view(SubjectAdmin(Students, db.session))
admin.add_view(RoleAdmin(Roles, db.session))
admin.add_view(SubjectAdmin(Subjects, db.session))
admin.add_view(EducationLanguageAdmin(EducationLanguage, db.session))
admin.add_view(LocationAdmin(Locations, db.session))
admin.add_view(PaymentTypeAdmin(PaymentTypes, db.session))
admin.add_view(ProfessionAdmin(Professions, db.session))
