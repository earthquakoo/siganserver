class AlarmNotFoundException(Exception):
    def __init__(self, alarm_id):
        self.error = f"Alarm id {alarm_id} is not found."
        
        
class AlarmConditionalFalse(Exception):
    def __init__(self):
        self.error = "If there is less than 5 minutes left for the alarm to go off, it cannot be changed or deleted."