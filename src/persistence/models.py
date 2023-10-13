from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import TIMESTAMP, Boolean, DateTime

import sys
sys.path.append('.')

from src.infrastructure.database import Base


class User(Base):
    __tablename__ = "user"
    
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    slack_id = Column(String(100), nullable=False)
    channel_id = Column(String(100), nullable=False)
    channel_name = Column(String(100), nullable=False)
    access_token = Column(String(100), nullable=True)
    user_token = Column(String(100), nullable=True)


class Alarm(Base):
    __tablename__ = "alarm"
    
    alarm_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.user_id"), nullable=False)
    content = Column(String(300), nullable=False)
    deadline = Column(String(100), nullable=True)
    alarm_date = Column(String(100), nullable=False)
    interval = Column(String(100), nullable=True)
    scheduled_message_id = Column(String(100), nullable=True)
    slack_channel_name = Column(String(100), nullable=True)
    slack_channel_id = Column(String(100), nullable=True)
    confirm_alarm_date = Column(String(100), nullable=True)
    sub_scheduled_message_id = Column(String(100), nullable=True)
    
    
class Token(Base):
    __tablename__ = "token"
    
    id = Column(Integer, primary_key=True)
    access_token = Column(String(100), nullable=True)
    user_token = Column(String(100), nullable=True)