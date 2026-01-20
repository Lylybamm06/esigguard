from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    fingerprint = Column(String, index=True, nullable=False)
    global_score = Column(Integer, nullable=False)
    classification = Column(String, nullable=False)
    modules = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)