from datetime import datetime, date
from marshmallow import Schema, fields, post_load
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, SQLAlchemySchema
from backend.tasks.models.models import Mission, MissionSubtask, MissionAttachment, MissionComment, MissionProof, Tag, \
    db
from backend.models.models import Users
from backend.tasks.missions.marshmallow import UserShortSchema, CommentSchema, ProofSchema, AttachmentSchema


class MobileMissionListSchema(SQLAlchemySchema):
    class Meta:
        model = Mission

    id = fields.Int()
    title = fields.Str()
    category = fields.Str()
    status = fields.Str()
    deadline_datetime = fields.DateTime(format="%Y-%m-%d %H:%M")

    deadline_color = fields.Method("get_color")

    def get_color(self, obj):
        if not obj.deadline_datetime:
            return "grey"
        days = (obj.deadline_datetime.date() - date.today()).days
        if days <= 1:
            return "red"
        elif days <= 4:
            return "yellow"
        return "green"


class MobileMissionDetailSchema(SQLAlchemyAutoSchema):
    deadline_datetime = fields.DateTime(format="%Y-%m-%d %H:%M")
    created_at = fields.DateTime(format="%Y-%m-%d %H:%M")

    creator = fields.Nested(UserShortSchema)
    comments = fields.Nested(CommentSchema, many=True)
    proofs = fields.Nested(ProofSchema, many=True)
    attachments = fields.Nested(AttachmentSchema, many=True)

    class Meta:
        model = Mission
        include_relationships = True
