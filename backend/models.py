from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)

    instagram_id = Column(String)
    rapid_key = Column(String)
    rapid_host = Column(String)

    smm_key = Column(String)

    interval_minutes = Column(Integer)

    followers_enabled = Column(Boolean)
    followers_service = Column(String)
    followers_pct = Column(Integer)

    likes_enabled = Column(Boolean)
    likes_service = Column(String)
    likes_pct = Column(Integer)

    views_enabled = Column(Boolean)
    views_service = Column(String)
    views_pct = Column(Integer)

    shares_enabled = Column(Boolean)
    shares_service = Column(String)
    shares_pct = Column(Integer)

    saves_enabled = Column(Boolean)
    saves_service = Column(String)
    saves_pct = Column(Integer)