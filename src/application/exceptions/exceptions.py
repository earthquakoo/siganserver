from fastapi import status

class BaseCustomException(Exception):
    """Base class for custom exceptions"""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail

    def __str__(self):
        return self.detail


class SlackApiError(BaseCustomException):
    def __init__(self, error: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{error}"
        )
       
        
class AlarmConditionalFalse(BaseCustomException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="If there is less than 5 minutes left for the alarm to go off, it cannot be changed or deleted."
        )


class SlackChannelNotFound(BaseCustomException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Channel does not exist or cannot be found."
        )
        
        
class AlarmMaximumTimeLimit(BaseCustomException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can set up a reservation message in Slack for up to 4 months."
        )
        

class InvalidDateSetting(BaseCustomException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="If the interval is set, you can only enter the time."
        )


class InvalidIntervalSetting(BaseCustomException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot set an interval for an alarm with a date and time specified."
        )
        

class DeadlineEarlierThanAlarmSet(BaseCustomException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot set a deadline earlier than the current date."
        )


class DeadlineNotSet(BaseCustomException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alarm with no deadline set."
        )
        

class TeamIdNotMatch(BaseCustomException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team ID does not match."
        )