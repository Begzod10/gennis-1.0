from datetime import datetime
from marshmallow import Schema, fields, post_load
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from backend.tasks.models.models import Mission, MissionSubtask, MissionAttachment, MissionComment, MissionProof, Tag, \
    db
from backend.models.models import Users


class TagSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Tag
        load_instance = True
        include_relationships = True
        sqla_session = db.session


from marshmallow import Schema, fields


class MissionCreateSchema(Schema):
    title = fields.Str(required=True)
    description = fields.Str(load_default=None)
    category = fields.Str(load_default=None)
    status = fields.Str(load_default=None)

    tags = fields.List(fields.Int(), load_default=[])

    creator_id = fields.Int(required=True)
    executor_ids = fields.List(fields.Int(), load_default=[])
    reviewer_id = fields.Int(load_default=None)

    location_id = fields.Int(load_default=None)

    start_datetime = fields.DateTime(load_default=None)
    deadline_datetime = fields.DateTime(required=True)

    # Recurring fields
    is_recurring = fields.Bool(load_default=False)
    recurring_type = fields.Str(load_default=None)
    repeat_every = fields.Int(load_default=1)

    # KPI / Penalty defaults
    kpi_weight = fields.Int(load_default=10)
    penalty_per_day = fields.Int(load_default=2)
    early_bonus_per_day = fields.Int(load_default=1)
    max_bonus = fields.Int(load_default=3)
    max_penalty = fields.Int(load_default=10)


class SubtaskSchema(SQLAlchemyAutoSchema):
    created_at = fields.DateTime(format="%Y-%m-%d %H:%M")

    class Meta:
        model = MissionSubtask
        include_fk = True
        load_instance = True
        sqla_session = db.session


class AttachmentSchema(SQLAlchemyAutoSchema):
    uploaded_at = fields.DateTime(format="%Y-%m-%d %H:%M")

    class Meta:
        model = MissionAttachment
        include_fk = True
        load_instance = True
        sqla_session = db.session


class UserShortSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Users
        include_fk = True
        load_instance = True
        sqla_session = db.session
        fields = ("id", "name", "surname")


class CommentSchema(SQLAlchemyAutoSchema):
    created_at = fields.DateTime(format="%Y-%m-%d %H:%M")
    user = fields.Nested(UserShortSchema)

    class Meta:
        model = MissionComment
        include_fk = True
        load_instance = True
        sqla_session = db.session


class ProofSchema(SQLAlchemyAutoSchema):
    created_at = fields.DateTime(format="%Y-%m-%d %H:%M")

    class Meta:
        model = MissionProof
        include_fk = True
        load_instance = True
        sqla_session = db.session


class MissionDetailSchema(SQLAlchemyAutoSchema):
    start_datetime = fields.DateTime(format="%Y-%m-%d %H:%M")
    deadline_datetime = fields.DateTime(format="%Y-%m-%d %H:%M")
    finish_datetime = fields.DateTime(format="%Y-%m-%d %H:%M")
    created_at = fields.DateTime(format="%Y-%m-%d %H:%M")
    updated_at = fields.DateTime(format="%Y-%m-%d %H:%M")
    creator = fields.Nested(UserShortSchema)
    executor = fields.Nested(UserShortSchema)
    reviewer = fields.Nested(UserShortSchema, allow_none=True)

    tags = fields.Nested(TagSchema, many=True)
    comments = fields.Nested(CommentSchema, many=True)
    subtasks = fields.Nested(SubtaskSchema, many=True)
    proofs = fields.Nested(ProofSchema, many=True)
    attachments = fields.Nested(AttachmentSchema, many=True)

    final_score = fields.Method("get_final_score")
    days_left = fields.Method("get_days_left")
    status_color = fields.Method("get_color")

    class Meta:
        model = Mission
        include_fk = True
        load_instance = True
        sqla_session = db.session
        include_relationships = True

    def get_final_score(self, obj):
        return obj.compute_final_score()

    def get_days_left(self, obj):
        from datetime import datetime, date
        if not obj.deadline_datetime:
            return None
        return (obj.deadline_datetime.date() - date.today()).days

    def get_color(self, obj):
        return obj.status_color()
