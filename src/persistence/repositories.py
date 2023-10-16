from sqlalchemy.orm import Session

import src.persistence.models as models


def delete_alarm(db: Session, alarm_obj):

    db.delete(alarm_obj)
    db.commit()
    
    return {"success": True}


def repeat_schedule_message(db: Session, repeat_alarm: dict, alarm_obj):
    
    setattr(alarm_obj, 'alarm_date', repeat_alarm['alarm_date'])
    setattr(alarm_obj, 'scheduled_message_id', repeat_alarm['scheduled_message_id'])
    db.commit()
    
    return {"success": True}


def bot_info_init(db: Session, bot_info: dict):
    
    bot_info_init = models.User(**bot_info)
    
    db.add(bot_info_init)
    db.commit()
    db.refresh(bot_info_init)