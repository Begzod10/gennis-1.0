import logging
from datetime import datetime
from typing import Optional

from flask import Blueprint, request, jsonify

from backend.models.models import db
from .models import ChatAnalysisReport, TelegramGroup, TelegramGroupMember, ReportMember

logger = logging.getLogger(__name__)

chat_analyzer_bp = Blueprint("chat_analyzer", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    """Safely parse an ISO-8601 datetime string (with optional Z suffix)."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        logger.warning(f"Could not parse datetime string: {value!r}")
        return None


def _upsert_group(group_data: dict) -> TelegramGroup:
    """
    Find-or-create a TelegramGroup by telegram_group_id.
    Always updates name/created_at with the latest values from the bot.
    """
    tg_id = group_data.get("id")
    group = TelegramGroup.query.filter_by(telegram_group_id=tg_id).first()

    if group is None:
        group = TelegramGroup(telegram_group_id=tg_id)
        db.session.add(group)

    group.name = group_data.get("name", group.name)
    group.created_at = _parse_dt(group_data.get("created_at")) or group.created_at
    return group


def _upsert_member(member_data: dict, group: TelegramGroup) -> TelegramGroupMember:
    """
    Find-or-create a TelegramGroupMember by (telegram_user_id, group_id).
    Always refreshes all fields with the latest snapshot from the bot.
    """
    tg_user_id = member_data.get("id")
    member = (
        TelegramGroupMember.query
        .filter_by(telegram_user_id=tg_user_id, group_id=group.id)
        .first()
    )

    if member is None:
        member = TelegramGroupMember(
            telegram_user_id=tg_user_id,
            group=group,
        )
        db.session.add(member)

    # Always refresh with latest snapshot
    member.username = member_data.get("username")          # may be None
    member.first_name = member_data.get("first_name", member.first_name)
    member.display_name = member_data.get("display_name", member.display_name)
    member.first_seen_at = _parse_dt(member_data.get("first_seen_at")) or member.first_seen_at
    member.joined_group_at = _parse_dt(member_data.get("joined_group_at")) or member.joined_group_at
    member.last_seen_at = _parse_dt(member_data.get("last_seen_at")) or member.last_seen_at
    member.total_messages = member_data.get("total_messages", member.total_messages)
    return member


def _upsert_report(report_item: dict, group: TelegramGroup,
                   sent_at: Optional[datetime]) -> ChatAnalysisReport:
    """
    Find-or-create a ChatAnalysisReport identified by (report_date, group_id).
    If it already exists the stats / AI text are updated in-place — no duplicate row.
    """
    report_date = report_item.get("report_date")
    report = (
        ChatAnalysisReport.query
        .filter_by(report_date=report_date, group_id=group.id)
        .first()
    )

    stats = report_item.get("stats", {})

    if report is None:
        report = ChatAnalysisReport(
            report_date=report_date,
            group=group,
        )
        db.session.add(report)

    # Always overwrite with freshest data from the bot
    report.report_id = report_item.get("report_id", report.report_id)
    report.sent_at = sent_at or report.sent_at
    report.total_members_today = report_item.get("group", {}).get("total_members_today", report.total_members_today)
    report.total_messages = stats.get("total_messages", report.total_messages)
    report.active_members = stats.get("active_members", report.active_members)
    report.messages_analyzed = stats.get("messages_analyzed", report.messages_analyzed)
    report.top_members = report_item.get("top_members", report.top_members)
    report.ai_analysis = report_item.get("ai_analysis", report.ai_analysis)
    report.report_text = report_item.get("report_text", report.report_text)
    return report


def _upsert_report_member(report: ChatAnalysisReport,
                           member: TelegramGroupMember,
                           daily_count: int) -> ReportMember:
    """
    Find-or-create a ReportMember row for (report, member).
    Updates the daily message count if the row already exists.
    """
    rm = (
        ReportMember.query
        .filter_by(report_id=report.id, member_id=member.id)
        .first()
    )

    if rm is None:
        rm = ReportMember(report=report, member=member)
        db.session.add(rm)

    rm.daily_message_count = daily_count
    return rm


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@chat_analyzer_bp.route("/reports/", methods=["POST"])
def receive_reports():
    """
    Receive a daily-report payload from the Telegram bot.

    All operations are idempotent — re-sending the same payload updates
    existing rows rather than creating duplicates:

        TelegramGroup      → upserted by telegram_group_id
        TelegramGroupMember → upserted by (telegram_user_id, group_id)
        ChatAnalysisReport  → upserted by (report_date, group_id)
        ReportMember        → upserted by (report_id, member_id)
    """
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"success": False, "msg": "No JSON payload received"}), 400

    reports_data = data.get("reports")
    if not reports_data or not isinstance(reports_data, list):
        return jsonify({"success": False, "msg": "'reports' field is missing or not a list"}), 400

    sent_at = _parse_dt(data.get("sent_at"))
    result_ids = []

    try:
        for report_item in reports_data:

            # 1. Upsert group
            group = _upsert_group(report_item.get("group", {}))
            db.session.flush()

            # 2. Upsert report (no duplicate for same group+date)
            report = _upsert_report(report_item, group, sent_at)
            db.session.flush()

            # 3. Upsert each member + their ReportMember row
            for member_data in report_item.get("group_members", []):
                member = _upsert_member(member_data, group)
                db.session.flush()

                _upsert_report_member(
                    report=report,
                    member=member,
                    daily_count=member_data.get("total_messages", 0),
                )

            result_ids.append(report.id)

        db.session.commit()
        logger.info(f"Processed {len(result_ids)} report(s) (upserted). IDs: {result_ids}")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing reports: {e}")
        return jsonify({"success": False, "msg": str(e)}), 500

    return jsonify({
        "success": True,
        "msg": f"{len(result_ids)} report(s) processed (upserted)",
        "report_ids": result_ids,
    }), 201


@chat_analyzer_bp.route("/reports/", methods=["GET"])
def list_reports():
    """Return all saved reports (latest first)."""
    reports = (
        ChatAnalysisReport.query
        .order_by(ChatAnalysisReport.id.desc())
        .all()
    )
    return jsonify({
        "success": True,
        "count": len(reports),
        "reports": [r.convert_json() for r in reports],
    }), 200


@chat_analyzer_bp.route("/reports/<int:report_id>/", methods=["GET"])
def get_report(report_id):
    """Return a single report including per-member daily stats."""
    record = ChatAnalysisReport.query.get(report_id)
    if not record:
        return jsonify({"success": False, "msg": "Report not found"}), 404
    return jsonify({"success": True, "report": record.convert_json(include_members=True)}), 200


@chat_analyzer_bp.route("/groups/", methods=["GET"])
def list_groups():
    """Return all known Telegram groups."""
    groups = TelegramGroup.query.order_by(TelegramGroup.id).all()
    return jsonify({
        "success": True,
        "count": len(groups),
        "groups": [g.convert_json() for g in groups],
    }), 200


@chat_analyzer_bp.route("/groups/<int:group_id>/members/", methods=["GET"])
def list_group_members(group_id):
    """Return all known members of a group (by DB id)."""
    group = TelegramGroup.query.get(group_id)
    if not group:
        return jsonify({"success": False, "msg": "Group not found"}), 404
    return jsonify({
        "success": True,
        "group": group.convert_json(),
        "count": len(group.members),
        "members": [m.convert_json() for m in group.members],
    }), 200

# /api/chat-analyzer/reports/