from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.sql.sqltypes import TIMESTAMP, Boolean, DateTime

import sys
sys.path.append('.')

from src.infrastructure.database import Base

class Alarm(Base):
    __tablename__ = "alarm"
    
    alarm_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_info.user_id"), nullable=False)
    content = Column(String(300), nullable=False)
    deadline = Column(String(100), nullable=True)
    alarm_date = Column(String(100), nullable=False)
    interval = Column(String(100), nullable=True)
    scheduled_message_id = Column(String(100), nullable=True)
    slack_channel_name = Column(String(100), nullable=True)
    slack_channel_id = Column(String(100), nullable=True)
    confirm_alarm_date = Column(String(100), nullable=True)
    sub_scheduled_message_id = Column(String(100), nullable=True)


class UserInfo(Base):
    __tablename__ = "user_info"
    
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(String(100), nullable=True)
    channel_name = Column(String(100), nullable=True)
    access_token = Column(String(100), nullable=True)