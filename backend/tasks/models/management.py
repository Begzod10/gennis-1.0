"""
Read/write SQLAlchemy model mapped to the management app's mission table.
Only the columns needed for reverse sync are declared.
"""
import os
from sqlalchemy import create_engine, Column, BigInteger, String, Date, Boolean, Integer, Text
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


management_engine = create_engine(MANAGEMENT_DB_URL) if MANAGEMENT_DB_URL else None
ManagementSession = sessionmaker(bind=management_engine) if management_engine else None
