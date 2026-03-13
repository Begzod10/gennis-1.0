from flask import request, Blueprint, jsonify

from backend.models.models import Report, db

report_bp = Blueprint("reports", __name__)

@report_bp.route("/reports", methods=["POST"])
def create_report():
    data = request.json

    report = Report(
        name=data.get("name"),
        category=data.get("category"),
        program_type=data.get("program_type"),
        text=data.get("text"),
    )

    db.session.add(report)
    db.session.commit()

    return jsonify({
        "message": "created",
        "data": {
            "id": report.id,
            "name": report.name,
            "category": report.category,
            "program_type": report.program_type,
            "text": report.text
        }
    }), 201


@report_bp.route("/reports", methods=["GET"])
def get_reports():
    reports = Report.query.all()

    result = []
    for r in reports:
        result.append({
            "id": r.id,
            "name": r.name,
            "category": r.category,
            "program_type": r.program_type,
            "text": r.text
        })

    return jsonify({
        "message": "success",
        "data": result
    })

@report_bp.route("/reports/<int:id>", methods=["GET"])
def get_report(id):
    r = Report.query.get_or_404(id)

    return jsonify({
        "message": "success",
        "data": {
            "id": r.id,
            "name": r.name,
            "category": r.category,
            "program_type": r.program_type,
            "text": r.text
        }
    })

@report_bp.route("/reports/<int:id>", methods=["PUT"])
def update_report(id):
    r = Report.query.get_or_404(id)
    data = request.json

    r.name = data.get("name", r.name)
    r.category = data.get("category", r.category)
    r.program_type = data.get("program_type", r.program_type)
    r.text = data.get("text", r.text)

    db.session.commit()

    return jsonify({
        "message": "updated",
        "data": {
            "id": r.id,
            "name": r.name,
            "category": r.category,
            "program_type": r.program_type,
            "text": r.text
        }
    })

@report_bp.route("/reports/<int:id>", methods=["DELETE"])
def delete_report(id):
    r = Report.query.get_or_404(id)

    db.session.delete(r)
    db.session.commit()

    return jsonify({
        "message": "deleted",
        "data": {
            "id": r.id
        }
    })