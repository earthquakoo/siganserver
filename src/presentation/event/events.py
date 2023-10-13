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
    # print(event)
    try:
        client.views_publish(
            user_id=event["user"],
            view=blocks.app_home_opened_view_blocks()
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")



@app.event("message")
def handle_message_event(event):
    print(event)
    db = next(get_db())
    if event['type'] == "message" and "bot_profile" in event:
        if event['bot_profile']['name'] == "Sigan":
            alarm_date = event['blocks'][1]['fields'][2]['text'][21:]
            alarm_dict = service.get_conditional_alarm(db, event['text'], alarm_date)
            
            if alarm_dict['interval']:
                try:
                    service.repeat_schedule_message(db, alarm_dict)
                except Exception as e:
                    return {"success": False, "error": e.error}

    if "subtype" in event:
        if event['subtype'] == "message_changed" and event['message']['bot_profile']['name'] == "Sigan":
            if event['message']['text'] == 'Alarm has been deleted.':
                content = event['previous_message']['blocks'][1]['fields'][0]['text'][11:]
                alarm_date = event['previous_message']['blocks'][1]['fields'][2]['text'][21:]
                interval = event['previous_message']['blocks'][1]['fields'][3]['text'][12:]
                service.delete_button_click_response(db, alarm_date, content)
    

events_router = APIRouter(
    prefix="",
    tags=["events"]
)


@events_router.post("/slack/click-button")
async def post_message(request: Request):
    form_data = await request.form()
    payload = json.loads(form_data.get("payload"))
    db = next(get_db())
    # print(payload)
    service.click_button_response(db, payload)

    return "OK"


@events_router.post("/slack/events")
async def endpoint(req: Request):
    return await app_handler.handle(req)