from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, BigInteger, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from backend.models.models import db


# ---------------------------------------------------------------------------
# TelegramGroup
# ---------------------------------------------------------------------------

class TelegramGroup(db.Model):
    """One row per unique Telegram group (chat)."""
    __tablename__ = "telegram_groups"

    id = Column(Integer, primary_key=True)
    telegram_group_id = Column(BigInteger, unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=True)   # when the Telegram group was created

    # relationships
    reports = relationship("ChatAnalysisReport", back_populates="group", lazy="select")
    members = relationship("TelegramGroupMember", back_populates="group", lazy="select")
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    location = relationship("Locations", backref="telegram_groups", foreign_keys=[location_id])

    def add(self):
        db.session.add(self)
        db.session.commit()

    def convert_json(self):
        return {
            "id": self.id,
            "telegram_group_id": self.telegram_group_id,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "location_id": self.location_id,
            "location": self.location.convert_json() if self.location else None,
        }

    def __repr__(self):
        return f"<TelegramGroup {self.name} ({self.telegram_group_id})>"


# ---------------------------------------------------------------------------
# TelegramGroupMember
# ---------------------------------------------------------------------------

class TelegramGroupMember(db.Model):
    """One row per unique Telegram user per group."""
    __tablename__ = "telegram_group_members"
    __table_args__ = (
        UniqueConstraint("telegram_user_id", "group_id", name="uq_member_group"),
    )

    id = Column(Integer, primary_key=True)

    # FK to the group this member belongs to
    group_id = Column(Integer, ForeignKey("telegram_groups.id"), nullable=False, index=True)
    group = relationship("TelegramGroup", back_populates="members")

    # Telegram user identifiers
    telegram_user_id = Column(BigInteger, nullable=False, index=True)
    username = Column(String(255), nullable=True)     # may be null (Telegram username is optional)
    first_name = Column(String(255), nullable=True)
    display_name = Column(String(255), nullable=True)

    # Lifecycle timestamps from the bot
    first_seen_at = Column(DateTime, nullable=True)
    joined_group_at = Column(DateTime, nullable=True)
    last_seen_at = Column(DateTime, nullable=True)

    # Running total messages (updated on each report)
    total_messages = Column(Integer, default=0)

    # DB timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationship to per-report stats
    report_stats = relationship("ReportMember", back_populates="member", lazy="select")

    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    location = relationship("Locations", backref="telegram_group_members", foreign_keys=[location_id])

    def add(self):
        db.session.add(self)
        db.session.commit()

    def convert_json(self):
        return {
            "id": self.id,
            "telegram_user_id": self.telegram_user_id,
            "username": self.username,
            "first_name": self.first_name,
            "display_name": self.display_name,
            "first_seen_at": self.first_seen_at.isoformat() if self.first_seen_at else None,
            "joined_group_at": self.joined_group_at.isoformat() if self.joined_group_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "total_messages": self.total_messages,
            "location_id": self.location_id,
            "location": self.location.convert_json() if self.location else None,
        }

    def __repr__(self):
        return f"<TelegramGroupMember {self.display_name} (uid={self.telegram_user_id})>"


# ---------------------------------------------------------------------------
# ReportMember  —  association between a report and a member
# ---------------------------------------------------------------------------

class ReportMember(db.Model):
    """Records how many messages a member sent in one specific daily report period."""
    __tablename__ = "report_members"
    __table_args__ = (
        UniqueConstraint("report_id", "member_id", name="uq_report_member"),
    )

    id = Column(Integer, primary_key=True)

    report_id = Column(Integer, ForeignKey("chat_analysis_reports.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("telegram_group_members.id"), nullable=False, index=True)

    # messages sent in THIS specific report's period
    daily_message_count = Column(Integer, default=0)

    report = relationship("ChatAnalysisReport", back_populates="member_stats")
    member = relationship("TelegramGroupMember", back_populates="report_stats")

    def convert_json(self):
        return {
            "member": self.member.convert_json() if self.member else {},
            "daily_message_count": self.daily_message_count,
        }


# ---------------------------------------------------------------------------
# ChatAnalysisReport
# ---------------------------------------------------------------------------

class ChatAnalysisReport(db.Model):
    """One row per daily analysis report received from the Telegram bot."""
    __tablename__ = "chat_analysis_reports"
    __table_args__ = (
        # One report per group per date — prevents duplicate deliveries from the bot
        UniqueConstraint("report_date", "group_id", name="uq_report_date_group"),
    )
    id = Column(Integer, primary_key=True)

    # --- Report meta ---
    report_id = Column(Integer, nullable=True)         # ID sent by the bot
    report_date = Column(String(20), nullable=True)    # "2026-02-26"
    sent_at = Column(DateTime, nullable=True)          # top-level sent_at timestamp

    # --- FK to the group ---
    group_id = Column(Integer, ForeignKey("telegram_groups.id"), nullable=True, index=True)
    group = relationship("TelegramGroup", back_populates="reports")

    # --- Group snapshot for this report day ---
    total_members_today = Column(Integer, default=0)   # group.total_members_today

    # --- Stats ---
    total_messages = Column(Integer, default=0)
    active_members = Column(Integer, default=0)
    messages_analyzed = Column(Integer, default=0)

    # --- Top-members ranking (JSON — ephemeral display data) ---
    top_members = Column(JSON, nullable=True)
    # e.g. [{"rank": 1, "display_name": "Alice", "message_count": 87}]

    # --- AI-generated text fields ---
    ai_analysis = Column(Text, nullable=True)
    report_text = Column(Text, nullable=True)

    # --- DB timestamps ---
    created_at = Column(DateTime, default=datetime.utcnow)

    # --- Relationship to per-member daily stats ---
    member_stats = relationship("ReportMember", back_populates="report", lazy="select")

    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)


    def add(self):
        db.session.add(self)
        db.session.commit()

    def convert_json(self, include_members=False):
        data = {
            "id": self.id,
            "report_id": self.report_id,
            "report_date": self.report_date,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "group": self.group.convert_json() if self.group else {},
            "total_members_today": self.total_members_today,
            "stats": {
                "total_messages": self.total_messages,
                "active_members": self.active_members,
                "messages_analyzed": self.messages_analyzed,
            },
            "top_members": self.top_members or [],
            "ai_analysis": self.ai_analysis,
            "report_text": self.report_text,
            "created_at": self.created_at.isoformat() if self.created_at else None, 
            "location_id": self.location_id,
            "location": self.location.convert_json() if self.location else None,
        }
        if include_members:
            data["member_stats"] = [rm.convert_json() for rm in self.member_stats]
        return data

    def __repr__(self):
        return f"<ChatAnalysisReport id={self.id} group_id={self.group_id} date={self.report_date}>"
