from datetime import datetime, timedelta


def sql_obj_to_dict(sql_obj):
    d = dict()
    for col in sql_obj.__table__.columns:
        d[col.name] = getattr(sql_obj, col.name)
    return d


def sql_obj_list_to_dict_list(sql_obj_list):
    return [sql_obj_to_dict(sql_obj) for sql_obj in sql_obj_list]


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