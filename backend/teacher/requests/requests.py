from flask import Blueprint, request, jsonify
from app import db
from backend.teacher.models import TeacherRequests, Teachers
from backend.models.models import Locations
from datetime import datetime

teacher_requests_bp = Blueprint("teacher_requests", __name__)


@teacher_requests_bp.route("/teacher-requests", methods=["GET"])
def get_teacher_requests():
    query = TeacherRequests.query

    teacher_id = request.args.get("teacher_id")
    location_id = request.args.get("location_id")
    status = request.args.get("status")
    if status:
        query = query.filter_by(status=status)
    if teacher_id:
        teacher = Teachers.query.filter_by(user_id=teacher_id).first()
        if not teacher:
            return jsonify({"error": "Teacher not found"}), 404
        query = query.filter_by(teacher_id=teacher.id)

    if location_id:
        query = query.filter_by(location_id=location_id)
    data = query.all()
    result = []
    for tr in data:
        result.append({
            "id": tr.id,
            "teacher_id": tr.teacher_id,
            "location_id": tr.location_id,
            "text": tr.text,
            "comment": tr.comment,
            "status": tr.status,
            "address": tr.address,
            "price": tr.price,
            "created_at": tr.created_at.strftime("%Y-%m-%d") if tr.created_at else None,
            "updated_at": tr.updated_at.strftime("%Y-%m-%d") if tr.updated_at else None
        })
    return jsonify(result), 200


@teacher_requests_bp.route("/teacher-requests", methods=["POST"])
def create_teacher_request():
    data = request.json
    teacher = Teachers.query.filter_by(user_id=data.get("teacher_id")).first()
    if not teacher:
        return jsonify({"error": "Teacher not found"}), 404

    teacher_request = TeacherRequests(
        teacher_id=teacher.id,
        location_id=data.get("location_id"),
        text=data.get("text"),
        comment=data.get("comment"),
        status='sent',
        address=data.get("address"),
        price=data.get("price"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.session.add(teacher_request)
    db.session.commit()

    return jsonify({
        "id": teacher_request.id,
        "teacher_id": teacher_request.teacher_id,
        "location_id": teacher_request.location_id,
        "text": teacher_request.text,
        "comment": teacher_request.comment,
        "status": teacher_request.status,
        "address": teacher_request.address,
        "price": teacher_request.price,
        "created_at": teacher_request.created_at.strftime("%Y-%m-%d"),
        "updated_at": teacher_request.updated_at.strftime("%Y-%m-%d")
    }), 201


@teacher_requests_bp.route("/teacher-requests/<int:request_id>", methods=["PUT", "PATCH"])
def update_teacher_request(request_id):
    tr = TeacherRequests.query.get_or_404(request_id)
    data = request.json

    for key, value in data.items():
        setattr(tr, key, value)
    tr.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "id": tr.id,
        "teacher_id": tr.teacher_id,
        "location_id": tr.location_id,
        "text": tr.text,
        "comment": tr.comment,
        "status": tr.status,
        "address": tr.address,
        "price": tr.price,
        "created_at": tr.created_at.strftime("%Y-%m-%d") if tr.created_at else None,
        "updated_at": tr.updated_at.strftime("%Y-%m-%d")
    }), 200


@teacher_requests_bp.route("/teacher-requests/<int:request_id>", methods=["DELETE"])
def delete_teacher_request(request_id):
    tr = TeacherRequests.query.get_or_404(request_id)
    db.session.delete(tr)
    db.session.commit()
    return jsonify({"message": "Deleted successfully"}), 200
