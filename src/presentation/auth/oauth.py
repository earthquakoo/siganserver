import sys
sys.path.append('.')

import os, logging
from dotenv import load_dotenv

from fastapi import Request, APIRouter

from slack_bolt import App, BoltResponse
from slack_bolt.adapter.fastapi import SlackRequestHandler
from slack_bolt.oauth.callback_options import CallbackOptions, SuccessArgs, FailureArgs
from slack_bolt.oauth.oauth_settings import OAuthSettings
from slack_sdk.oauth.installation_store import FileInstallationStore
from slack_sdk.oauth.state_store import FileOAuthStateStore
from slack_sdk.errors import SlackApiError

from src.infrastructure.database import get_db
import src.application.service as service

load_dotenv('.env')


# logging.basicConfig(level=logging.DEBUG)


def success_callback(args: SuccessArgs) -> BoltResponse:
    
    installation = args.installation
    client = args.request.context.client
    print(installation.bot_token)
    print(installation.user_token)

    try:
        response = client.chat_postMessage(
            token=installation.bot_token,
            channel=installation.user_id, 
            text="Thanks for installing sigan app!"
        )
    except SlackApiError as e:
        return e.response['error']
    
    user_info = {
        "slack_id": installation.user_id,
        "channel_id": response['channel'],
        "channel_name": "SiganBot",
        }
    db = next(get_db())
    service.bot_info_init(db, user_info)
        
    return BoltResponse(status=200, body="Thanks!")


def failure_callback(args: FailureArgs) -> BoltResponse:
    return BoltResponse(status=args.suggested_status_code, body=args.reason)
 

app = App(
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    installation_store=FileInstallationStore(),
    ignoring_self_events_enabled=False,
    oauth_settings=OAuthSettings(
        client_id=os.environ.get("SLACK_CLIENT_ID"),
        client_secret=os.environ.get("SLACK_CLIENT_SECRET"),
        scopes=["chat:write", "channels:read", "channels:history", "groups:read", "im:history", "im:read", "mpim:read"],
        user_scopes=["identity.basic"],
        redirect_uri=None,
        install_path="/slack/install",
        redirect_uri_path="/slack/oauth_redirect",
        state_store=FileOAuthStateStore(expiration_seconds=600),
        callback_options=CallbackOptions(success=success_callback, failure=failure_callback),
    ),
)

app_handler = SlackRequestHandler(app)


oauth_router = APIRouter(
    prefix="",
    tags=["oauth"]
)


@oauth_router.get("/slack/install")
async def install(request: Request):
    return await app_handler.handle(request)


@oauth_router.get("/slack/oauth_redirect")
async def oauth_redirect(request: Request):
    return await app_handler.handle(request)