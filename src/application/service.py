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
    post_time = datetime.strptime(alarm['alarm_date'], '%Y/%m/%d %H:%M:%S')
    
    if alarm['interval']:
        alarm['alarm_date'] = alarm['alarm_date'].split(" ")[1][:5]
    
    if alarm['slack_channel_name'] == "SiganBot":
        channel_id = utils.get_bot_channel(db, alarm['slack_channel_name'])
    else:
        channel_id = utils.get_channel_id(db, alarm['slack_channel_name'], alarm['team_id'])
    
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
        "user_id": utils.get_user_id(db, alarm['team_id']),
        "content": alarm['content'],
        "deadline": alarm['deadline'],
        "alarm_date": alarm['alarm_date'],
        "interval": alarm['interval'],
        "scheduled_message_id": response['scheduled_message_id'],
        "slack_channel_name": alarm['slack_channel_name'],
        "slack_channel_id": channel_id,
        "confirm_alarm_date": alarm['confirm_alarm_date'],
    }
    
    if new_alarm['confirm_alarm_date']:
        new_alarm['sub_scheduled_message_id'] = create_confirm_alarm(db, alarm)
    
    repositories.create_alarm(db, new_alarm)
    
    return {"success": True, "alarm": new_alarm}


def delete_alarm(db: Session, data: dict):
    alarm = db.query(models.Alarm).filter(models.Alarm.alarm_id==data['alarm_id']).first()
    
    user_id = alarm.user_id

    if alarm.deadline:
        year, month, day = utils.change_deadline_to_date(alarm.deadline)
        time = alarm.alarm_date
        if re.match("^([0-9]){4}/([0-9]){1,2}/([0-9]){1,2}|([0-9]){1,2}/([0-9]){1,2} [0-9]{2}:[0-9]{2}:[0-9]{2}$", time):
            time = alarm.alarm_date.split(" ")[1][:5]

        deadline = datetime.strptime(f"{year}/{month}/{day} {time}:00", '%Y/%m/%d %H:%M:%S')
        if deadline < datetime.now():
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
    
    if alarm.deadline:
        delete_confirm_alarm(db, alarm.alarm_id, data['team_id'])
    
    repositories.delete_alarm(db, alarm)
    
    return {"success": True, "user_id": user_id}


def change_content(db: Session, data: dict):
    alarm = db.query(models.Alarm).filter(models.Alarm.alarm_id==data['alarm_id']).first()
    
    alarm_dict = global_utils.sql_obj_to_dict(alarm)
    
    if re.match("^[0-9]{2}:[0-9]{2}$", alarm_dict['alarm_date']):
        interval_list = alarm_dict['interval'].split(" ")
        if interval_list[0] == "every":
            interval_list = interval_list[1:]
        
        year, month, day = utils.get_date_from_shortcut(interval_list, alarm_dict['alarm_date'])
        alarm_dict['alarm_date'] = f"{year}/{month}/{day} {alarm_dict['alarm_date']}:00"
    
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


def change_deadline(db: Session, data: dict):
    alarm = db.query(models.Alarm).filter(models.Alarm.alarm_id==data['alarm_id']).first()
    
    alarm_dict = global_utils.sql_obj_to_dict(alarm)
    
    if alarm_dict['deadline'] is None:
        raise exceptions.DeadlineNotSet()
    
    cur_deadline_year, cur_deadline_month, cur_deadline_day = utils.change_deadline_to_date(alarm_dict['deadline'])
    new_deadline_year, new_deadline_month, new_deadline_day = utils.change_deadline_to_date(data['deadline'])
    
    if re.match("^([0-9]){4}/([0-9]){1,2}/([0-9]){1,2}|([0-9]){1,2}/([0-9]){1,2} [0-9]{2}:[0-9]{2}:[0-9]{2}$", alarm_dict['alarm_date']):
        alarm_time = alarm_dict['alarm_date'].split(" ")[1][:5]
        cur_deadline_date = datetime.strptime(f"{cur_deadline_year}/{cur_deadline_month}/{cur_deadline_day} {alarm_time}:00", '%Y/%m/%d %H:%M:%S')
        new_deadline_date = datetime.strptime(f"{new_deadline_year}/{new_deadline_month}/{new_deadline_day} {alarm_time}:00", '%Y/%m/%d %H:%M:%S')
        cur_alarm_date = datetime.strptime(alarm_dict['alarm_date'], '%Y/%m/%d %H:%M:%S')

    elif re.match("^[0-9]{2}:[0-9]{2}$", alarm_dict['alarm_date']):
        interval_list = alarm_dict['interval'].split(" ")
        if interval_list[0] == "every":
            interval_list = interval_list[1:]
        
        year, month, day = utils.get_date_from_shortcut(interval_list, alarm_dict['alarm_date'])
        alarm_date = f"{year}/{month}/{day} {alarm_dict['alarm_date']}:00"
        
        cur_deadline_date = datetime.strptime(f"{cur_deadline_year}/{cur_deadline_month}/{cur_deadline_day} {alarm_dict['alarm_date']}:00", '%Y/%m/%d %H:%M:%S')
        new_deadline_date = datetime.strptime(f"{new_deadline_year}/{new_deadline_month}/{new_deadline_day} {alarm_dict['alarm_date']}:00", '%Y/%m/%d %H:%M:%S')
        cur_alarm_date = datetime.strptime(alarm_date, '%Y/%m/%d %H:%M:%S')
        
        alarm_dict['alarm_date'] = alarm_date
    
    if new_deadline_date < cur_alarm_date:
        raise exceptions.DeadlineEarlierThanAlarmSet()
    
    confirm_alarm_day = alarm_dict['confirm_alarm_date'] - cur_deadline_date
    alarm_dict['confirm_alarm_date'] = new_deadline_date + confirm_alarm_day
    alarm_dict['deadline'] = data['deadline']
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
    
    repositories.change_deadline(db, new_alarm['alarm'], alarm)

    return {"success": True, "user_id": new_alarm['alarm']['user_id']}


def change_date(db: Session, data: dict):
    alarm = db.query(models.Alarm).filter(models.Alarm.alarm_id==data['alarm_id']).first()

    alarm_dict = global_utils.sql_obj_to_dict(alarm)
    
    if alarm_dict['interval']:
        if not re.match("^[0-9]{2}:[0-9]{2}$", data['alarm_date']):
            raise exceptions.InvalidDateSetting()

        interval_list = alarm_dict['interval'].split(" ")
        if interval_list[0] == "every":
            interval_list = interval_list[1:]
            
        year, month, day = utils.get_date_from_shortcut(interval_list, data['alarm_date'])
        alarm_date = f"{year}/{month}/{day} {data['alarm_date']}:00"
    else:
        # 시간만 변경하고자 하는 경우
        if re.match("^[0-9]{2}:[0-9]{2}$", data['alarm_date']):
            current_date = alarm_dict['alarm_date'].split(" ")[0]
            alarm_date = f"{current_date} {data['alarm_date']}:00"
        # 날짜만 변경하고자 하는 경우
        elif re.match("^([0-9]){4}/([0-9]){1,2}/([0-9]){1,2}$", data['alarm_date']):
            alarm_time = alarm_dict['alarm_date'].split(" ")[1]
            alarm_date = f"{data['alarm_date']} {alarm_time}"
        # 날짜와 시간 모두 변경하고자 하는 경우
        elif re.match("^([0-9]){4}/([0-9]){1,2}/([0-9]){1,2} [0-9]{2}:[0-9]{2}:[0-9]{2}$", data['alarm_date']):
            alarm_date = data['alarm_date']

    alarm_time = alarm_date.split(" ")[1]
    deadline = f"{alarm_dict['deadline']} {alarm_time}"
    if datetime.strptime(deadline, '%Y/%m/%d %H:%M:%S') < datetime.strptime(alarm_date, '%Y/%m/%d %H:%M:%S'):
        raise exceptions.DeadlineEarlierThanAlarmSet()

    alarm_dict['alarm_date'] = alarm_date
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


def change_interval(db: Session, data: dict):
    alarm = db.query(models.Alarm).filter(models.Alarm.alarm_id==data['alarm_id']).first()
      
    alarm_dict = global_utils.sql_obj_to_dict(alarm)
    
    if re.match("^([0-9]){4}/([0-9]){1,2}/([0-9]){1,2} [0-9]{2}:[0-9]{2}:[0-9]{2}$", alarm_dict['alarm_date']):
        raise exceptions.InvalidIntervalSetting()
    
    interval_list = data['interval'].split(" ")
    if interval_list[0] == "every":
        interval_list = interval_list[1:]
    
    year, month, day = utils.get_date_from_shortcut(interval_list, alarm_dict['alarm_date'])
    alarm_date = f"{year}/{month}/{day} {alarm_dict['alarm_date']}:00"
    
    alarm_dict['alarm_date'] = alarm_date
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


def match_team_id(db: Session, team_id: str):
    user_info = db.query(models.User).filter(models.User.team_id==team_id).first()
    
    if not user_info:
        raise exceptions.TeamIdNotMatch()
    
    return user_info.team_id


def create_confirm_alarm(db: Session, alarm: dict):
    post_time = alarm['confirm_alarm_date']
    if alarm['slack_channel_name'] == "SiganBot":
        channel_id = utils.get_bot_channel(db, alarm['slack_channel_name'])
    else:
        channel_id = utils.get_channel_id(db, alarm['slack_channel_name'])
    
    client = utils.get_client(db, alarm['team_id'])
    
    response = client.chat_scheduleMessage(
        channel = channel_id,
        text = alarm['content'],
        blocks = blocks.alarm_blocks(alarm),
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
        
    year, month, day = utils.get_date_from_shortcut(interval_list, alarm.alarm_date)
    alarm_date = f"{year}/{month}/{day} {alarm.alarm_date}:00"
    new_alarm_date = datetime.strptime(alarm_date, '%Y/%m/%d %H:%M:%S')
    
    if repeat_alarm['deadline']:
        deadline_year, deadline_month, deadline_day = utils.change_deadline_to_date(repeat_alarm['deadline'])
        deadline_date = datetime.strptime(f"{deadline_year}/{deadline_month}/{deadline_day} {alarm.alarm_date}:00", '%Y/%m/%d %H:%M:%S')

        if deadline_date < new_alarm_date:
            return None
    
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
    slack_channel_name = "SiganBot"
    channel_id = utils.get_bot_channel(db, slack_channel_name)
    client.chat_postMessage(
        channel=channel_id,
        text="Registration is complete. Feel free to use the sigan app!",
    )