from sqlalchemy.orm import Session

import src.persistence.models as models


def create_alarm(db: Session, alarm: dict):
    new_alarm = models.Alarm(**alarm)
    
    db.add(new_alarm)
    db.commit()
    db.refresh(new_alarm)


def delete_alarm(db: Session, alarm_obj):

    db.delete(alarm_obj)
    db.commit()


def change_content(db: Session, change_alarm: dict, alarm_obj):
    
    setattr(alarm_obj, 'content', change_alarm['content'])
    setattr(alarm_obj, 'scheduled_message_id', change_alarm['scheduled_message_id'])
    db.commit()


def change_deadline(db: Session, change_alarm: dict, alarm_obj):
    
    setattr(alarm_obj, 'deadline', change_alarm['deadline'])
    setattr(alarm_obj, 'scheduled_message_id', change_alarm['scheduled_message_id'])
    db.commit()


def change_date(db: Session, change_alarm: dict, alarm_obj):
    
    setattr(alarm_obj, 'alarm_date',change_alarm['alarm_date'])
    setattr(alarm_obj, 'scheduled_message_id',change_alarm['scheduled_message_id'])
    db.commit()


def change_interval(db: Session, change_alarm: dict, alarm_obj):
    
    setattr(alarm_obj, 'interval', change_alarm['interval'])
    setattr(alarm_obj, 'scheduled_message_id', change_alarm['scheduled_message_id'])
    db.commit()


def repeat_schedule_message(db: Session, repeat_alarm: dict, alarm_obj):
    setattr(alarm_obj, 'alarm_date', repeat_alarm['alarm_date'])
    setattr(alarm_obj, 'scheduled_message_id', repeat_alarm['scheduled_message_id'])
    db.commit()


def bot_info_init(db: Session, bot_info: dict):
    bot_info_init = models.User(**bot_info)
    
    db.add(bot_info_init)
    db.commit()
    db.refresh(bot_info_init)