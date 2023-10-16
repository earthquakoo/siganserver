import json
from dotenv import load_dotenv

from slack_bolt.adapter.fastapi import SlackRequestHandler
from fastapi import APIRouter, Request

import sys
sys.path.append('.')

from src.infrastructure.database import get_db
from src.presentation.auth.oauth import app
import src.application.blocks as blocks
import src.application.service as service


load_dotenv('.env')


app_handler = SlackRequestHandler(app)


@app.event("url_verification")
def url_verification():
    # Verifies ownership of an Events API Request URL
    return None


@app.event("app_home_opened")
def update_home_tab(client, event, logger):
    print(event)
    try:
        client.views_publish(
            user_id=event["user"],
            view=blocks.app_home_opened_view_blocks()
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")
{'bot_id': 'B061SRP5KH6', 'type': 'message', 'text': 'repeat test', 'user': 'U060X715WES', 'ts': '1697436780.346609', 'app_id': 'A05UTUY85AT', 'blocks': [{'type': 'header', 'block_id': 'XldJk', 'text': {'type': 'plain_text', 'text': 'The alarm has arrived!', 'emoji': True}}, {'type': 'section', 'block_id': 'ed6/y', 'fields': [{'type': 'mrkdwn', 'text': '*Content:*\nrepeat test', 'verbatim': False}, {'type': 'mrkdwn', 'text': '*Deadline:*\n2023/11/16', 'verbatim': False}, {'type': 'mrkdwn', 'text': '*Notification Time:*\n15:13', 'verbatim': False}, {'type': 'mrkdwn', 'text': '*Interval:*\nevery mon', 'verbatim': False}]}, {'type': 'section', 'block_id': '3D3xp', 'text': {'type': 'plain_text', 'text': 'Are you sure you want to delete the alarm?', 'emoji': True}}, {'type': 'actions', 'block_id': 'tHE8Z', 'elements': [{'type': 'button', 'action_id': 'f4ocJ', 'text': {'type': 'plain_text', 'text': 'Check', 'emoji': True}, 'style': 'primary', 'value': 'click_me_123'}, {'type': 'button', 'action_id': 'ssas9', 'text': {'type': 'plain_text', 'text': 'Delete', 'emoji': True}, 'style': 'danger', 'value': 'click_me_123'}]}], 'team': 'T060U561J3G', 'bot_profile': {'id': 'B061SRP5KH6', 'deleted': False, 'name': 'testapp', 'updated': 1697436005, 'app_id': 'A05UTUY85AT', 'icons': {'image_36': 'https://a.slack-edge.com/80588/img/plugins/app/bot_36.png', 'image_48': 'https://a.slack-edge.com/80588/img/plugins/app/bot_48.png', 'image_72': 'https://a.slack-edge.com/80588/img/plugins/app/service_72.png'}, 'team_id': 'T060U561J3G'}, 'channel': 'D060PA4PNQ7', 'event_ts': '1697436780.346609', 'channel_type': 'im'}

@app.event("message")
def handle_message_event(event):
    print(event)
    db = next(get_db())    
    if event['type'] == "message" and "bot_profile" in event:
        if event['bot_profile']['name'] == "Sigan":
            if event['blocks'][0]['type'] == 'header':
                deadline = event['blocks'][1]['fields'][1]['text'][12:]
                alarm_date = event['blocks'][1]['fields'][2]['text'][21:]
                interval = event['blocks'][1]['fields'][3]['text'][12:]
                print(deadline, alarm_date, interval)
                user_id = service.get_user_id(db, event['team'])
                alarm_dict = service.get_conditional_alarm(db, user_id, event['text'], deadline, alarm_date, interval)
                
                if alarm_dict['interval'] is not None:
                    try:
                        service.repeat_schedule_message(db, alarm_dict)
                    except Exception as e:
                        return {"success": False, "error": e.error}

    if "subtype" in event:
        if event['subtype'] == "message_changed" and event['message']['bot_profile']['name'] == "Sigan":
            if event['message']['text'] == 'Alarm has been deleted.':
                content = event['previous_message']['blocks'][1]['fields'][0]['text'][11:]
                deadline = event['previous_message']['blocks'][1]['fields'][1]['text'][12:]
                alarm_date = event['previous_message']['blocks'][1]['fields'][2]['text'][21:]
                interval = event['previous_message']['blocks'][1]['fields'][3]['text'][12:]
                user_id = service.get_user_id(db, event['message']['team'])
                alarm_dict = service.get_conditional_alarm(db, user_id, content, deadline, alarm_date, interval)
                service.delete_alarm(db, alarm_dict['alarm_id'])
    

events_router = APIRouter(
    prefix="",
    tags=["events"]
)


@events_router.post("/slack/click-button")
async def post_message(request: Request):
    form_data = await request.form()
    payload = json.loads(form_data.get("payload"))
    db = next(get_db())
    print(payload)
    user_id = service.get_user_id(db, payload['team']['id'])
    service.click_button_response(db, payload, user_id)

    return "OK"


@events_router.post("/slack/events")
async def endpoint(req: Request):
    return await app_handler.handle(req)