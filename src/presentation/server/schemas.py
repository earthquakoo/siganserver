from typing import Union
from pydantic import BaseModel
from datetime import datetime

import sys
sys.path.append('.')

class AlarmCreateIn(BaseModel):
    team_id: str
    content: str
    alarm_date: str
    alarm_time: str
    interval: Union[str, None] = None
    confirm_alarm_date: Union[datetime, None] = None
    slack_channel_name: str


class AlarmGetIn(BaseModel):
    user_id: Union[int, None] = None
    team_id: Union[str, None] = None


class AlarmDeleteIne(BaseModel):
    alarm_id: int
    team_id: str


class ChangeContentIn(BaseModel):
    alarm_id: int
    content: str
    team_id: str
    

class ChangeDateIn(BaseModel):
    alarm_id: int
    alarm_date: str
    team_id: str


class ChangeTimeIn(BaseModel):
    alarm_id: int
    alarm_time: str
    team_id: str


class ChangeIntervalIn(BaseModel):
    alarm_id: int
    interval: str
    team_id: str


class AlarmResponse(BaseModel):
    user_id: int


class RegisterResponse(BaseModel):
    team_id: str

    
class AlarmShowResponse(BaseModel):
    alarm: Union[list, None] = None