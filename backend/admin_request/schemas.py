from marshmallow import fields, Schema
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from backend.models.models import AdminRequest, RequestComment, db

class RequestCommentSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = RequestComment
        load_instance = True
        sqla_session = db.session
        include_fk = True

    user_name = fields.Method("get_user_name", dump_only=True)

    def get_user_name(self, obj):
        if obj.user_info:
            return f"{obj.user_info.name} {obj.user_info.surname}"
        return None

class AdminRequestSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = AdminRequest
        load_instance = True
        sqla_session = db.session
        include_fk = True

    branch_name = fields.Method("get_branch_name", dump_only=True)
    user_name = fields.Method("get_user_name", dump_only=True)
    comments = fields.Nested(RequestCommentSchema, many=True, dump_only=True)

    def get_branch_name(self, obj):
        return obj.location.name if obj.location else None

    def get_user_name(self, obj):
        if obj.user:
            return f"{obj.user.name} {obj.user.surname}"
        return None
