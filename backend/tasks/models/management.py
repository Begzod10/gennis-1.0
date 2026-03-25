"""
Read/write SQLAlchemy model mapped to the management app's mission table.
Only the columns needed for reverse sync are declared.
"""
import os
from sqlalchemy import create_engine, Column, BigInteger, String, Date, Boolean, Integer, Text, DateTime
from sqlalchemy.orm import DeclarativeBase, sessionmaker

MANAGEMENT_DB_URL = os.getenv("MANAGEMENT_DB_URL")


class ManagementBase(DeclarativeBase):
    pass


class ManagementMission(ManagementBase):
    __tablename__ = "mission"

    id = Column(BigInteger, primary_key=True)
    title = Column(String(255))
    description = Column(Text, nullable=True)
    category = Column(String(50))
    status = Column(String(30))
    deadline = Column(Date)
    finish_date = Column(Date, nullable=True)
    delay_days = Column(Integer, default=0)
    final_sc = Column(Integer, default=0)
    kpi_weight = Column(Integer, default=10)
    penalty_per_day = Column(Integer, default=2)
    early_bonus_per_day = Column(Integer, default=1)
    max_bonus = Column(Integer, default=3)
    max_penalty = Column(Integer, default=10)
    deleted = Column(Boolean, default=False)


class ManagementMissionComment(ManagementBase):
    __tablename__ = "mission_comment"

    id = Column(BigInteger, primary_key=True)
    mission_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=True)
    text = Column(Text, nullable=False)
    attachment = Column(String(500), nullable=True)
    creator_name = Column(String(255), nullable=True)
    deleted = Column(Boolean, default=False)


class ManagementMissionAttachment(ManagementBase):
    __tablename__ = "mission_attachment"

    id = Column(BigInteger, primary_key=True)
    mission_id = Column(BigInteger, nullable=False)
    file = Column(String(500), nullable=False)
    note = Column(String(255), nullable=True)
    creator_name = Column(String(255), nullable=True)
    deleted = Column(Boolean, default=False)


class ManagementMissionProof(ManagementBase):
    __tablename__ = "mission_proof"

    id = Column(BigInteger, primary_key=True)
    mission_id = Column(BigInteger, nullable=False)
    file = Column(String(500), nullable=False)
    comment = Column(String(255), nullable=True)
    creator_name = Column(String(255), nullable=True)
    deleted = Column(Boolean, default=False)


class ManagementMissionSubtask(ManagementBase):
    __tablename__ = "mission_subtask"

    id = Column(BigInteger, primary_key=True)
    mission_id = Column(BigInteger, nullable=False)
    title = Column(String(255), nullable=False)
    is_done = Column(Boolean, default=False)
    order = Column(Integer, default=0)
    deleted = Column(Boolean, default=False)


management_engine = create_engine(MANAGEMENT_DB_URL) if MANAGEMENT_DB_URL else None
ManagementSession = sessionmaker(bind=management_engine) if management_engine else None

_lazy_engine = None
_lazy_session_factory = None


def _get_management_session():
    global _lazy_engine, _lazy_session_factory
    # Try module-level session first (set at import time)
    if ManagementSession is not None:
        return ManagementSession()
    # Fallback: lazy init in case MANAGEMENT_DB_URL was loaded after import
    if _lazy_session_factory is None:
        url = os.getenv("MANAGEMENT_DB_URL")
        if not url:
            print("[management sync] MANAGEMENT_DB_URL is not set")
            return None
        _lazy_engine = create_engine(url)
        _lazy_session_factory = sessionmaker(bind=_lazy_engine)
    return _lazy_session_factory()


def sync_comment_to_management(mission_management_id, text, attachment_url, creator_name):
    """Create a comment in the management DB. Returns the new management comment id."""
    session = _get_management_session()
    if not session:
        return None
    try:
        c = ManagementMissionComment(
            mission_id=mission_management_id,
            text=text,
            attachment=attachment_url,
            creator_name=creator_name,
        )
        session.add(c)
        session.commit()
        return c.id
    except Exception as e:
        session.rollback()
        print(f"[management sync] comment failed: {e}")
        return None
    finally:
        session.close()


def sync_attachment_to_management(mission_management_id, file_url, note, creator_name):
    """Create an attachment in the management DB. Returns the new management attachment id."""
    session = _get_management_session()
    if not session:
        return None
    try:
        a = ManagementMissionAttachment(
            mission_id=mission_management_id,
            file=file_url,
            note=note,
            creator_name=creator_name,
        )
        session.add(a)
        session.commit()
        return a.id
    except Exception as e:
        session.rollback()
        print(f"[management sync] attachment failed: {e}")
        return None
    finally:
        session.close()


def sync_proof_to_management(mission_management_id, file_url, comment, creator_name):
    """Create a proof in the management DB. Returns the new management proof id."""
    session = _get_management_session()
    if not session:
        return None
    try:
        p = ManagementMissionProof(
            mission_id=mission_management_id,
            file=file_url,
            comment=comment,
            creator_name=creator_name,
        )
        session.add(p)
        session.commit()
        return p.id
    except Exception as e:
        session.rollback()
        print(f"[management sync] proof failed: {e}")
        return None
    finally:
        session.close()


def sync_subtask_to_management(mission_management_id, title, is_done, order):
    """Create a subtask in the management DB. Returns the new management subtask id."""
    session = _get_management_session()
    if not session:
        return None
    try:
        st = ManagementMissionSubtask(
            mission_id=mission_management_id,
            title=title,
            is_done=is_done,
            order=order,
        )
        session.add(st)
        session.commit()
        return st.id
    except Exception as e:
        session.rollback()
        print(f"[management sync] subtask failed: {e}")
        return None
    finally:
        session.close()


def sync_comment_update_to_management(management_id, text=None, attachment=None):
    session = _get_management_session()
    if not session:
        return
    try:
        c = session.query(ManagementMissionComment).filter(ManagementMissionComment.id == management_id).first()
        if not c:
            return
        if text is not None:
            c.text = text
        if attachment is not None:
            c.attachment = attachment
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"[management sync] comment update failed: {e}")
    finally:
        session.close()


def sync_comment_delete_to_management(management_id):
    session = _get_management_session()
    if not session:
        return
    try:
        c = session.query(ManagementMissionComment).filter(ManagementMissionComment.id == management_id).first()
        if c:
            c.deleted = True
            session.commit()
    except Exception as e:
        session.rollback()
        print(f"[management sync] comment delete failed: {e}")
    finally:
        session.close()


def sync_attachment_update_to_management(management_id, file=None, note=None):
    session = _get_management_session()
    if not session:
        return
    try:
        a = session.query(ManagementMissionAttachment).filter(ManagementMissionAttachment.id == management_id).first()
        if not a:
            return
        if file is not None:
            a.file = file
        if note is not None:
            a.note = note
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"[management sync] attachment update failed: {e}")
    finally:
        session.close()


def sync_attachment_delete_to_management(management_id):
    session = _get_management_session()
    if not session:
        return
    try:
        a = session.query(ManagementMissionAttachment).filter(ManagementMissionAttachment.id == management_id).first()
        if a:
            a.deleted = True
            session.commit()
    except Exception as e:
        session.rollback()
        print(f"[management sync] attachment delete failed: {e}")
    finally:
        session.close()


def sync_proof_update_to_management(management_id, file=None, comment=None):
    session = _get_management_session()
    if not session:
        return
    try:
        p = session.query(ManagementMissionProof).filter(ManagementMissionProof.id == management_id).first()
        if not p:
            return
        if file is not None:
            p.file = file
        if comment is not None:
            p.comment = comment
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"[management sync] proof update failed: {e}")
    finally:
        session.close()


def sync_proof_delete_to_management(management_id):
    session = _get_management_session()
    if not session:
        return
    try:
        p = session.query(ManagementMissionProof).filter(ManagementMissionProof.id == management_id).first()
        if p:
            p.deleted = True
            session.commit()
    except Exception as e:
        session.rollback()
        print(f"[management sync] proof delete failed: {e}")
    finally:
        session.close()


def sync_subtask_delete_to_management(management_id):
    """Soft-delete a subtask in the management DB by its management_id."""
    session = _get_management_session()
    if not session:
        return
    try:
        st = session.query(ManagementMissionSubtask).filter(
            ManagementMissionSubtask.id == management_id
        ).first()
        if st:
            st.deleted = True
            session.commit()
    except Exception as e:
        session.rollback()
        print(f"[management sync] subtask delete failed: {e}")
    finally:
        session.close()


def sync_subtask_update_to_management(management_id, title=None, is_done=None):
    """Update a subtask in the management DB by its management_id."""
    session = _get_management_session()
    if not session:
        return
    try:
        st = session.query(ManagementMissionSubtask).filter(
            ManagementMissionSubtask.id == management_id
        ).first()
        if not st:
            return
        if title is not None:
            st.title = title
        if is_done is not None:
            st.is_done = is_done
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"[management sync] subtask update failed: {e}")
    finally:
        session.close()
