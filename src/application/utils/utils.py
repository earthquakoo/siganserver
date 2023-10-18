from datetime import datetime, timedelta

from sqlalchemy import and_
from sqlalchemy.orm import Session

from slack_sdk import WebClient

import src.utils.global_utils as global_utils
import src.persistence.models as models


def get_client(db: Session, team_id: str):
    user_info = db.query(models.User).filter(models.User.team_id==team_id).first()
    client = WebClient(token=user_info.access_token)
    return client


def get_user_id(db: Session, team_id: str):    
    user_info = db.query(models.User).filter(models.User.team_id==team_id).first()
    return user_info.user_id


def list_scheduled_messages(db: Session, channel_id: str, scheduled_message_id: str, team_id: str):
    client = get_client(db, team_id)
    response = client.chat_scheduledMessages_list(channel=channel_id)
    if response is None:
        return None
    
    for message in response['scheduled_messages']:
        if message['id'] == scheduled_message_id:
            return message['post_at']


def get_channel_id(db: Session, channel_name: str, team_id: str):
    client = get_client(db, team_id)
    channels = client.conversations_list(types="public_channel,private_channel")["channels"]
    for channel in channels:
        if channel["name"] == channel_name:
            return channel["id"]
    
    return None


def get_bot_channel(db: Session, channel_name: str):
    channel = db.query(models.User).filter(models.User.channel_name==channel_name).first()
    return channel.channel_id


def get_all_alarms(db: Session, user_id: str):
    alarm = db.query(models.Alarm).filter(models.Alarm.user_id==user_id).all()
    if alarm is None:
        return None
    alarm_dict_list = global_utils.sql_obj_list_to_dict_list(alarm)
    
    return alarm_dict_list


def get_conditional_alarm(db: Session, user_id: int, content: str, deadline: str, alarm_date: str, interval: str):
    if deadline == "None":
        deadline = None
    if interval == "None":
        interval = None
    alarm = db.query(models.Alarm).\
        filter(
            and_(
                models.Alarm.user_id==user_id,
                models.Alarm.content==content,
                models.Alarm.deadline==deadline,
                models.Alarm.alarm_date==alarm_date,
                models.Alarm.interval==interval,
                )
            ).first()
    
    return global_utils.sql_obj_to_dict(alarm)


def change_deadline_to_date(deadline: str):
    year, month, day = datetime.now().year, None, None
    date_list = list(map(int, deadline.split('/')))
    year, month, day = date_list

    return year, month, day


def get_date_from_shortcut(interval_day: list, time: str):
    alarm_date = f"{datetime.now().year}-{datetime.now().month}-{datetime.now().day} {time}:00"
    alarm_date = datetime.strptime(alarm_date, '%Y-%m-%d %H:%M:%S')

    if "everyday" in interval_day:
        if alarm_date < datetime.now():
            alarm_date += timedelta(days=1)
        return alarm_date.year, alarm_date.month, alarm_date.day
    
    weekday_mapping = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}  
    current_weekday_list = []
    
    current_weekday_num = datetime.now().weekday()
    
    for interval in interval_day:
        day_offset = weekday_mapping[interval] - current_weekday_num
        current_weekday_list.append(day_offset)
    
    current_weekday_list = sorted(current_weekday_list, key=lambda x: (abs(x), -x))
    
    if current_weekday_list[0] < 0:
        alarm_date += timedelta(days=current_weekday_list[-1]+7)
        return alarm_date.year, alarm_date.month, alarm_date.day
    
    for day_offset in current_weekday_list:        
        if alarm_date + timedelta(days=day_offset) > datetime.now():
            alarm_date += timedelta(days=day_offset)
            return alarm_date.year, alarm_date.month, alarm_date.day
        else:
            date_offset = alarm_date + timedelta(days=7+day_offset)
    
    return date_offset.year, date_offset.month, date_offset.day