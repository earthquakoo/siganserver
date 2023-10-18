import sys
sys.path.append('.')

import os, logging
from fastapi import Request, APIRouter

from slack_bolt import App, BoltResponse
from slack_bolt.adapter.fastapi import SlackRequestHandler
from slack_bolt.oauth.callback_options import CallbackOptions, SuccessArgs, FailureArgs
from slack_bolt.oauth.oauth_settings import OAuthSettings
from slack_sdk.oauth.installation_store import FileInstallationStore
from slack_sdk.oauth.state_store import FileOAuthStateStore
from slack_sdk.errors import SlackApiError

from src.infrastructure.database import get_db
import src.persistence.repositories as repositories

oauth_router = APIRouter(
    prefix="",
    tags=["oauth"]
)


# logging.basicConfig(level=logging.DEBUG)


def success_callback(args: SuccessArgs) -> BoltResponse:
    user_id = args.installation.user_id
    bot_token = args.installation.bot_token
    team_id = args.installation.team_id
    client = args.request.context.client

    try:
        response = client.chat_postMessage(
            token=bot_token,
            channel=user_id,
            text=f"Thanks for installing sigan app!\nYour team id is as follows.```{team_id}```\nComplete the register by entering the command in the Sigan CLI APP and entering the corresponding team id.```sigan register```",
            mrkdwn=True,
        )
    except SlackApiError as e:
        return e.response['error']
    
    user_info = {
        "team_id": team_id,
        "channel_id": response['channel'],
        "channel_name": "SiganBot",
        "access_token": bot_token,
        }
    db = next(get_db())
    repositories.bot_info_init(db, user_info)
    
    return args.default.success(args)


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
        user_scopes=[""],
        redirect_uri=None,
        install_path="/slack/install",
        redirect_uri_path="/slack/oauth_redirect",
        state_store=FileOAuthStateStore(expiration_seconds=600),
        callback_options=CallbackOptions(success=success_callback, failure=failure_callback),
    ),
)

app_handler = SlackRequestHandler(app)


@oauth_router.get("/slack/install")
async def install(request: Request):
    return await app_handler.handle(request)


@oauth_router.get("/slack/oauth_redirect")
async def oauth_redirect(request: Request):
    return await app_handler.handle(request)