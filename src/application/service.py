import re, logging
from dotenv import load_dotenv
from datetime import datetime, timedelta

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from sqlalchemy import and_
from sqlalchemy.orm import Session

import sys
sys.path.append('.')

import src.application.utils as utils
import src.application.exceptions as exceptions
import src.application.blocks as blocks
import src.persistence.models as models
import src.persistence.repositories as repositories


load_dotenv('.env')

logger = logging.getLogger(__name__)


def repeat_schedule_message(db: Session, repeat_alarm: dict):
    alarm = db.query(models.Alarm).filter(models.Alarm.alarm_id==repeat_alarm['alarm_id']).first()
    if not alarm:
        raise exceptions.AlarmNotFoundException(alarm_id=repeat_alarm['alarm_id'])
    
    interval_list = alarm.interval.split(" ")
    if interval_list[0] == "every":
        interval_list = interval_list[1:]
        
    year, month, day = utils.get_date_from_shortcut(interval_list, alarm.alarm_date)
    alarm_date = f"{year}-{month}-{day} {alarm.alarm_date}:00"
    new_alarm_date = datetime.strptime(alarm_date, '%Y-%m-%d %H:%M:%S')
    
    if repeat_alarm['deadline']:
        deadline_year, deadline_month, deadline_day = utils.change_deadline_to_date(repeat_alarm['deadline'])
        deadline_date = datetime.strptime(f"{deadline_year}-{deadline_month}-{deadline_day} {alarm.alarm_date}:00", '%Y-%m-%d %H:%M:%S')

        if deadline_date < new_alarm_date:
            return None
    
    client = get_client(db)
    
    try:
        schedule_message = client.chat_scheduleMessage(
            channel = repeat_alarm['slack_channel_id'],
            text = repeat_alarm['content'],
            blocks = blocks.alarm_blocks(repeat_alarm),
            post_at = int(new_alarm_date.timestamp()),
        )
    except SlackApiError as e:
        return {"success": False, "error": e.response['error']}
    
    repeat_alarm['scheduled_message_id'] = schedule_message['scheduled_message_id']
    
    repositories.repeat_schedule_message(db, repeat_alarm, alarm)

    return {"success": True, "alarm_dict": repeat_alarm, "alarm_obj": alarm}


def delete_alarm(db: Session, alarm_id: int):
    alarm = db.query(models.Alarm).filter(models.Alarm.alarm_id==alarm_id).first()
    if not alarm:
        raise exceptions.AlarmNotFoundException(alarm_id=alarm_id)
    
    alarm_dict = utils.sql_obj_to_dict(alarm)
    
    if alarm_dict['deadline']:
        year, month, day = utils.change_deadline_to_date(alarm_dict['deadline'])
        time = alarm_dict['alarm_date']
        if re.match("^([0-9]){4}-([0-9]){1,2}-([0-9]){1,2}|([0-9]){1,2}-([0-9]){1,2} [0-9]{2}:[0-9]{2}:[0-9]{2}$", time):
            time = alarm_dict['alarm_date'].split(" ")[1][:5]

        deadline = datetime.strptime(f"{year}-{month}-{day} {time}:00", '%Y-%m-%d %H:%M:%S')
        if deadline < datetime.now():
            repositories.delete_alarm(db, alarm)
            return {"success": True, "delete_alarm": alarm_dict}
    
    post_at = list_scheduled_messages(db, alarm_dict['slack_channel_id'], alarm_dict['scheduled_message_id'])
    if post_at is None:
        if alarm_dict['confirm_alarm_date']:
            delete_confirm_alarm(db, alarm_id)
            
        repositories.delete_alarm(db, alarm)
        return {"success": True, "delete_alarm": alarm_dict}
    
    alarm_date = datetime.fromtimestamp(post_at)
    if alarm_date - timedelta(minutes=5) < datetime.now():
        raise exceptions.AlarmConditionalFalse()
    
    client = get_client(db)
    
    try:
        client.chat_deleteScheduledMessage(
            channel=alarm_dict['slack_channel_id'],
            scheduled_message_id=alarm_dict['scheduled_message_id']
        )
    except SlackApiError as e:
        return {"success": False, "error": e.response['error']}
    
    if alarm_dict['deadline']:
        delete_confirm_alarm(db, alarm_id)
    
    repositories.delete_alarm(db, alarm)
    
    return {"success": True}


def get_client(db: Session):
    token = db.query(models.Token).first()
    client = WebClient(token=token.access_token)
    return client


def get_user_id(db: Session):
    client = get_client(db)
    token = db.query(models.Token).first()
    response = client.users_identity(token=token.user_token)
    
    user_info = db.query(models.User).filter(models.User.slack_id==response['user']['id']).first()
    
    return user_info.user_id


def list_scheduled_messages(db: Session, channel_id: str, scheduled_message_id: str):
    client = get_client(db)
    response = client.chat_scheduledMessages_list(channel=channel_id)
    if response is None:
        return None
    
    for message in response['scheduled_messages']:
        if message['id'] == scheduled_message_id:
            return message['post_at']


def get_conditional_alarm(db: Session, content: str, alarm_date: str):
    alarm = db.query(models.Alarm).\
        filter(
            and_(
                models.Alarm.content==content,
                models.Alarm.alarm_date==alarm_date,
                )
            ).first()
    
    return utils.sql_obj_to_dict(alarm)
    

def click_button_response(db: Session, data: dict):
    client = get_client(db)
    
    if data['actions'][0]['text']['text'] == "Delete":
        try:
            response = client.chat_update(
                channel=data['container']['channel_id'],
                text="Alarm has been deleted.",
                ts=data['container']['message_ts'],
                blocks=blocks.click_delete_button_blocks(data['message']['text']),
            )
            return {"success": True}
        except SlackApiError as e:
            return {"success": False, "error": e.response["error"]}
        
    elif data['actions'][0]['text']['text'] == "Check":
        try:
            response = client.chat_update(
                channel=data['container']['channel_id'],
                text="Checked the alarm.",
                ts=data['container']['message_ts'],
                blocks=blocks.click_check_button_blocks(data['message']['text']),
            )
            return {"success": True}
        except SlackApiError as e:
            return {"success": False, "error": e.response["error"]}


def delete_button_click_response(db: Session, alarm_date: str, content: str):
    alarm = db.query(models.Alarm).\
        filter(
            and_(
                models.Alarm.content==content,
                models.Alarm.alarm_date==alarm_date,
                )
            ).all()
    
    user_id = get_user_id(db)
    
    alarm_list = utils.sql_obj_list_to_dict_list(alarm)
    for alarm_obj in alarm_list:
        if alarm_obj['content'] == content and alarm_obj['user_id']==user_id:
            delete_alarm(db, alarm_obj['alarm_id'])


def delete_confirm_alarm(db: Session, alarm_id: int):
    alarm = db.query(models.Alarm).filter(models.Alarm.alarm_id==alarm_id).first()
    if not alarm:
        raise exceptions.AlarmNotFoundException(alarm_id=alarm_id)
    
    client = get_client(db)

    client.chat_deleteScheduledMessage(
        channel=alarm.slack_channel_id,
        scheduled_message_id=alarm.sub_scheduled_message_id
    )
   

def bot_info_init(db: Session, bot_info: dict):
    
    bot_info_init = models.User(**bot_info)
    
    db.add(bot_info_init)
    db.commit()
    db.refresh(bot_info_init)