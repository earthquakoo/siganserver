import re
from dotenv import load_dotenv
from datetime import datetime, timedelta

from slack_sdk.errors import SlackApiError

from sqlalchemy.orm import Session

import sys
sys.path.append('.')

import src.utils.global_utils as global_utils
import src.application.utils.utils as utils
import src.application.exceptions.exceptions as exceptions
import src.application.utils.blocks as blocks
import src.persistence.models as models
import src.persistence.repositories as repositories

load_dotenv('.env')


def create_alarm(db: Session, alarm: dict):
    alarm_datetime = alarm['alarm_date'] + " " + f"{alarm['alarm_time']}:00"
    post_time = datetime.strptime(alarm_datetime, '%Y/%m/%d %H:%M:%S')
    user_info = utils.get_user_info(db, alarm['team_id'])
    
    if alarm['slack_channel_name'] == "SiganBot":
        channel_id = user_info.channel_id
    else:
        channel_id = utils.get_channel_id_from_channel_name(db, alarm['slack_channel_name'], alarm['team_id'])
    
    if channel_id is None:
        raise exceptions.SlackChannelNotFound()
    
    client = utils.get_client(db, alarm['team_id'])
    
    try:
        response = client.chat_scheduleMessage(
            channel = channel_id,
            text = alarm['content'],
            blocks = blocks.alarm_blocks(alarm),
            post_at = int(post_time.timestamp()),
        )
    except SlackApiError as e:
        return {"success": False, "detail": e.response['error']}
    
    new_alarm = {
        "user_id": user_info.user_id,
        "content": alarm['content'],
        "alarm_date": alarm['alarm_date'],
        "alarm_time": alarm['alarm_time'],
        "interval": alarm['interval'],
        "scheduled_message_id": response['scheduled_message_id'],
        "slack_channel_name": alarm['slack_channel_name'],
        "slack_channel_id": channel_id,
        "confirm_alarm_date": alarm['confirm_alarm_date'],
    }
    
    if new_alarm['confirm_alarm_date']:
        new_alarm['sub_scheduled_message_id'] = create_confirm_alarm(db, new_alarm, alarm['team_id'])
    
    repositories.create_alarm(db, new_alarm)
    
    return {"success": True, "alarm": new_alarm}


def delete_alarm(db: Session, data: dict):
    alarm = db.query(models.Alarm).filter(models.Alarm.alarm_id==data['alarm_id']).first()
    
    user_id = alarm.user_id
    
    if datetime.strptime(alarm.alarm_date + " " + f"{alarm.alarm_time}:00", '%Y/%m/%d %H:%M:%S') < datetime.now():
        repositories.delete_alarm(db, alarm)
        return {"success": True, "user_id": user_id}
    
    post_at = utils.list_scheduled_messages(db, alarm.slack_channel_id, alarm.scheduled_message_id, data['team_id'])
    if post_at is None:
        if alarm.confirm_alarm_date:
            delete_confirm_alarm(db, alarm.alarm_id, data['team_id'])
        repositories.delete_alarm(db, alarm)
        return {"success": True, "user_id": user_id}
    
    alarm_date = datetime.fromtimestamp(post_at)
    if alarm_date - timedelta(minutes=5) < datetime.now():
        raise exceptions.AlarmConditionalFalse()
    
    client = utils.get_client(db, data['team_id'])
    
    try:
        client.chat_deleteScheduledMessage(
            channel=alarm.slack_channel_id,
            scheduled_message_id=alarm.scheduled_message_id
        )
    except SlackApiError as e:
        return {"success": False, "detail": e.response['error']}
    
    if alarm.confirm_alarm_date:
        delete_confirm_alarm(db, alarm.alarm_id, data['team_id'])
    
    repositories.delete_alarm(db, alarm)
    
    return {"success": True, "user_id": user_id}


def change_content(db: Session, data: dict):
    alarm = db.query(models.Alarm).filter(models.Alarm.alarm_id==data['alarm_id']).first()
    
    alarm_dict = global_utils.sql_obj_to_dict(alarm)
    
    alarm_dict['content'] = data['content']
    alarm_dict['team_id'] = data['team_id']

    try:
        deleted_alarm = delete_alarm(db, data)
        if deleted_alarm['success'] is False:
            return {"success": False, "detail": deleted_alarm['detail']}
        
        new_alarm = create_alarm(db, alarm_dict)
        if new_alarm['success'] is False:
            return {"success": False, "detail": new_alarm['detail']}
    except Exception as e:
        return {"success": False, "detail": e.error}
    
    repositories.change_content(db, new_alarm['alarm'], alarm)

    return {"success": True, "user_id": new_alarm['alarm']['user_id']}


def change_date(db: Session, data: dict):
    alarm = db.query(models.Alarm).filter(models.Alarm.alarm_id==data['alarm_id']).first()

    alarm_dict = global_utils.sql_obj_to_dict(alarm)
    
    if alarm.interval:
        raise exceptions.InvalidDateSetting()
    
    change_alarm_date = datetime.strptime(data['alarm_date'] + " " + f"{alarm_dict['alarm_time']}:00", '%Y/%m/%d %H:%M:%S')
    
    if change_alarm_date < datetime.now():
        raise exceptions.AlarmEarlierThanCurrentTime()
    
    if alarm.confirm_alarm_date:
        current_alarm_date = datetime.strptime(alarm_dict['alarm_date'] + " " + f"{alarm_dict['alarm_time']}:00", '%Y/%m/%d %H:%M:%S')
        diff_date = current_alarm_date - alarm.confirm_alarm_date
        alarm_dict['confirm_alarm_date'] = change_alarm_date - abs(diff_date)

    alarm_dict['alarm_date'] = data['alarm_date']
    alarm_dict['team_id'] = data['team_id']

    try:
        deleted_alarm = delete_alarm(db, data)
        if deleted_alarm['success'] is False:
            return {"success": False, "detail": deleted_alarm['detail']} 
        
        new_alarm = create_alarm(db, alarm_dict)
        if new_alarm['success'] is False:
            return {"success": False, "detail": new_alarm['detail']}       
    except Exception as e:
        return {"success": False, "detail": e.error}
    
    repositories.change_date(db, new_alarm['alarm'], alarm)

    return {"success": True, "user_id": new_alarm['alarm']['user_id']}


def change_time(db: Session, data: dict):
    alarm = db.query(models.Alarm).filter(models.Alarm.alarm_id==data['alarm_id']).first()

    alarm_dict = global_utils.sql_obj_to_dict(alarm)
    
    if alarm.interval:
        interval_list = alarm_dict['interval'].split(" ")
        if interval_list[0] == "every":
            interval_list = interval_list[1:]
            
        year, month, day = utils.get_date_from_shortcut(interval_list, data['alarm_time'])
        alarm_dict['alarm_date'] = f"{year}/{month}/{day}"
    
    change_alarm_date = datetime.strptime(alarm_dict['alarm_date'] + " " + f"{data['alarm_time']}:00", '%Y/%m/%d %H:%M:%S')
    
    if change_alarm_date < datetime.now():
        raise exceptions.AlarmEarlierThanCurrentTime()
    
    if alarm.confirm_alarm_date:
        current_alarm_date = datetime.strptime(alarm_dict['alarm_date'] + " " + f"{alarm_dict['alarm_time']}:00", '%Y/%m/%d %H:%M:%S')
        diff_date = current_alarm_date - alarm.confirm_alarm_date
        alarm_dict['confirm_alarm_date'] = change_alarm_date - abs(diff_date)
    
    alarm_dict['alarm_time'] = data['alarm_time']
    alarm_dict['team_id'] = data['team_id']
    
    try:
        deleted_alarm = delete_alarm(db, data)
        if deleted_alarm['success'] is False:
            return {"success": False, "detail": deleted_alarm['detail']} 
        
        new_alarm = create_alarm(db, alarm_dict)
        if new_alarm['success'] is False:
            return {"success": False, "detail": new_alarm['detail']}       
    except Exception as e:
        return {"success": False, "detail": e.error}
    
    repositories.change_time(db, new_alarm['alarm'], alarm)

    return {"success": True, "user_id": new_alarm['alarm']['user_id']}



def change_interval(db: Session, data: dict):
    alarm = db.query(models.Alarm).filter(models.Alarm.alarm_id==data['alarm_id']).first()
      
    alarm_dict = global_utils.sql_obj_to_dict(alarm)
    
    if not alarm.interval:
        raise exceptions.InvalidIntervalSetting()
    
    interval_list = data['interval'].split(" ")
    if interval_list[0] == "every":
        interval_list = interval_list[1:]
    
    year, month, day = utils.get_date_from_shortcut(interval_list, alarm_dict['alarm_time'])
    
    alarm_dict['alarm_date'] = f"{year}/{month}/{day}"
    alarm_dict['interval'] = data['interval']
    alarm_dict['team_id'] = data['team_id']
    
    try:
        deleted_alarm = delete_alarm(db, data)
        if deleted_alarm['success'] is False:
            return {"success": False, "detail": deleted_alarm['detail']} 
        
        new_alarm = create_alarm(db, alarm_dict)
        if new_alarm['success'] is False:
            return {"success": False, "detail": new_alarm['detail']}       
    except Exception as e:
        return {"success": False, "detail": e.error}
    
    repositories.change_interval(db, new_alarm['alarm'], alarm)

    return {"success": True, "user_id": new_alarm['alarm']['user_id']}


def create_confirm_alarm(db: Session, alarm: dict, team_id: str):
    post_time = alarm['confirm_alarm_date']
    
    client = utils.get_client(db, team_id)
    
    response = client.chat_scheduleMessage(
        channel = alarm['slack_channel_id'],
        text = alarm['content'],
        blocks = blocks.confirm_alarm_blocks(alarm),
        post_at = int(post_time.timestamp()),
    )
    return response['scheduled_message_id']


def delete_confirm_alarm(db: Session, alarm_id: int, team_id: str):
    alarm = db.query(models.Alarm).filter(models.Alarm.alarm_id==alarm_id).first()
    
    client = utils.get_client(db, team_id)

    client.chat_deleteScheduledMessage(
        channel=alarm.slack_channel_id,
        scheduled_message_id=alarm.sub_scheduled_message_id
    )


def repeat_schedule_message(db: Session, repeat_alarm: dict, team_id: str):
    alarm = db.query(models.Alarm).filter(models.Alarm.alarm_id==repeat_alarm['alarm_id']).first()
    
    interval_list = alarm.interval.split(" ")
    if interval_list[0] == "every":
        interval_list = interval_list[1:]
        
    year, month, day = utils.get_date_from_shortcut(interval_list, alarm.alarm_time)
    alarm_date = f"{year}/{month}/{day} {alarm.alarm_time}:00"
    new_alarm_date = datetime.strptime(alarm_date, '%Y/%m/%d %H:%M:%S')
    
    client = utils.get_client(db, team_id)
    
    try:
        schedule_message = client.chat_scheduleMessage(
            channel = repeat_alarm['slack_channel_id'],
            text = repeat_alarm['content'],
            blocks = blocks.alarm_blocks(repeat_alarm),
            post_at = int(new_alarm_date.timestamp()),
        )
    except SlackApiError as e:
        return {"success": False, "detail": e.response['error']}
    
    repeat_alarm['alarm_date'] = f"{year}/{month}/{day}"
    repeat_alarm['scheduled_message_id'] = schedule_message['scheduled_message_id']
    
    repositories.repeat_schedule_message(db, repeat_alarm, alarm)

    return {"success": True, "alarm_dict": repeat_alarm, "alarm_obj": alarm}
    

def click_button_response(db: Session, data: dict, team_id: str):
    client = utils.get_client(db, team_id)
    
    if data['actions'][0]['text']['text'] == "Delete":
        client.chat_update(
            channel=data['container']['channel_id'],
            text="Alarm has been deleted.",
            ts=data['container']['message_ts'],
            blocks=blocks.click_delete_button_blocks(data['message']['text']),
            )
        return {"success": True}
        
    elif data['actions'][0]['text']['text'] == "Check":
        client.chat_update(
            channel=data['container']['channel_id'],
            text="Checked the alarm.",
            ts=data['container']['message_ts'],
            blocks=blocks.click_check_button_blocks(data['message']['text']),
            )
        return {"success": True}
    
    
def register_success_alarm(db: Session, team_id: str):
    client = utils.get_client(db, team_id)
    user_info = utils.get_user_info(db, team_id)
    client.chat_postMessage(
        channel=user_info.channel_id,
        text="Registration is complete. Feel free to use the sigan app!",
    )