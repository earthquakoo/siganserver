from fastapi import APIRouter, status, Depends, status
from sqlalchemy.orm import Session

import sys
sys.path.append('.')

from src.infrastructure.database import get_db
import src.application.exceptions.exceptions as exceptions
import src.persistence.models as models
import src.presentation.server.schemas as schemas
import src.application.service as service
import src.application.utils.utils as utils

router = APIRouter(
    prefix="/slack",
    tags=["slack"]  
)


@router.post('/', status_code=status.HTTP_201_CREATED, response_model=schemas.AlarmResponse)
def create_alarm(data: schemas.AlarmCreateIn, db: Session = Depends(get_db)):
    resp = service.create_alarm(db, data.model_dump())
    if resp['success'] is False:
        raise exceptions.SlackApiError(error=resp['detail'])
    return schemas.AlarmResponse(user_id=resp['alarm']['user_id'])
    

@router.post('/delete', status_code=status.HTTP_200_OK, response_model=schemas.AlarmResponse)
def delete_alarm(data: dict, db: Session = Depends(get_db)):

    resp = service.delete_alarm(db, data)
    if resp['success'] is False:
        raise exceptions.SlackApiError(error=resp['detail'])
    return schemas.AlarmResponse(user_id=resp['user_id'])

    
@router.get('/', status_code=status.HTTP_200_OK, response_model=schemas.AlarmShowResponse)
def get_alarm(data: schemas.AlarmGetIn, db: Session = Depends(get_db)):
    data = data.model_dump()

    if data['team_id'] is not None:
        data['user_id'] = utils.get_user_id(db, data['team_id'])

    alarm = utils.get_all_alarms(db, data['user_id'])
    return schemas.AlarmShowResponse(alarm=alarm)
    
    
@router.patch('/change_content', status_code=status.HTTP_200_OK, response_model=schemas.AlarmResponse)
def change_content(data: schemas.ChangeContentIn, db: Session = Depends(get_db)):

    resp = service.change_content(db, data.model_dump())
    if resp['success'] is False:
        raise exceptions.SlackApiError(error=resp['detail'])
    return schemas.AlarmResponse(user_id=resp['user_id'])
    
    
@router.patch('/change_deadline', status_code=status.HTTP_200_OK, response_model=schemas.AlarmResponse)
def change_deadline(data: schemas.ChangeDeadlineIn, db: Session = Depends(get_db)):
    
    resp = service.change_deadline(db, data.model_dump())
    if resp['success'] is False:
        raise exceptions.SlackApiError(error=resp['detail'])
    return schemas.AlarmResponse(user_id=resp['user_id'])


@router.patch('/change_date', status_code=status.HTTP_200_OK, response_model=schemas.AlarmResponse)
def change_date(data: schemas.ChangeDateIn, db: Session = Depends(get_db)):
    
    resp = service.change_date(db, data.model_dump())
    if resp['success'] is False:
        raise exceptions.SlackApiError(error=resp['detail'])
    return schemas.AlarmResponse(user_id=resp['user_id'])

    
@router.patch('/change_interval', status_code=status.HTTP_200_OK,response_model=schemas.AlarmResponse)
def change_interval(data: schemas.ChangeIntervalIn, db: Session = Depends(get_db)):

    resp = service.change_interval(db, data.model_dump())
    if resp['success'] is False:
        raise exceptions.SlackApiError(error=resp['detail'])
    return schemas.AlarmResponse(user_id=resp['user_id'])


@router.post('/register', status_code=status.HTTP_200_OK, response_model=schemas.RegisterResponse)
def register(data: dict, db: Session = Depends(get_db)):

    user_info = db.query(models.User).filter(models.User.team_id==data['team_id']).first()
    if not user_info:
        raise exceptions.TeamIdNotMatch()
    service.register_success_alarm(db, data['team_id'])
    return schemas.RegisterResponse(team_id=user_info.team_id)