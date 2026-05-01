from flask import request, jsonify
from flask_restful import Resource
from backend.models.models import db, AdminRequest, RequestComment
from .schemas import AdminRequestSchema, RequestCommentSchema
from flask_jwt_extended import jwt_required, get_jwt_identity

class AdminRequestListResource(Resource):
    @jwt_required()
    def get(self):
        branch_id = request.args.get('branch')
        user_id = request.args.get('user')
        
        query = AdminRequest.query
        if branch_id:
            query = query.filter_by(branch_id=branch_id)
        if user_id:
            query = query.filter_by(user_id=user_id)
            
        requests = query.order_by(AdminRequest.created_at.desc()).all()
        schema = AdminRequestSchema(many=True)
        return schema.dump(requests), 200

    @jwt_required()
    def post(self):
        data = request.get_json()
        schema = AdminRequestSchema()
        try:
            admin_request = schema.load(data)
            db.session.add(admin_request)
            db.session.commit()
            return schema.dump(admin_request), 201
        except Exception as e:
            db.session.rollback()
            return {"msg": str(e)}, 400

class AdminRequestResource(Resource):
    @jwt_required()
    def get(self, request_id):
        admin_request = AdminRequest.query.get_or_404(request_id)
        schema = AdminRequestSchema()
        return schema.dump(admin_request), 200

    @jwt_required()
    def put(self, request_id):
        admin_request = AdminRequest.query.get_or_404(request_id)
        data = request.get_json()
        schema = AdminRequestSchema(partial=True)
        try:
            updated_request = schema.load(data, instance=admin_request)
            db.session.commit()
            return schema.dump(updated_request), 200
        except Exception as e:
            db.session.rollback()
            return {"msg": str(e)}, 400

    @jwt_required()
    def delete(self, request_id):
        admin_request = AdminRequest.query.get_or_404(request_id)
        db.session.delete(admin_request)
        db.session.commit()
        return {"msg": "Deleted successfully"}, 200

class RequestCommentListResource(Resource):
    @jwt_required()
    def get(self):
        req_id = request.args.get('request')
        user_id = request.args.get('user')
        
        query = RequestComment.query
        if req_id:
            query = query.filter_by(request_id=req_id)
        if user_id:
            query = query.filter_by(user_id=user_id)
            
        comments = query.order_by(RequestComment.created_at.asc()).all()
        schema = RequestCommentSchema(many=True)
        return schema.dump(comments), 200

    @jwt_required()
    def post(self):
        data = request.get_json()
        schema = RequestCommentSchema()
        try:
            comment = schema.load(data)
            db.session.add(comment)
            db.session.commit()
            return schema.dump(comment), 201
        except Exception as e:
            db.session.rollback()
            return {"msg": str(e)}, 400

def register_admin_request_views(api, app):
    api.add_resource(AdminRequestListResource, '/api/admin-requests/')
    api.add_resource(AdminRequestResource, '/api/admin-requests/<int:request_id>/')
    api.add_resource(RequestCommentListResource, '/api/request-comments/')
