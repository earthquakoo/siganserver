import sys
sys.path.append('.')

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.presentation.event.events import events_router as slack_events
from src.presentation.server.router import router as server_router
from src.presentation.auth.oauth import oauth_router
from src.infrastructure.database import Base, engine
from src.application.exceptions.handler import exception_handler
import src.application.exceptions.exceptions as exceptions
Base.metadata.create_all(bind=engine)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(server_router)
app.include_router(slack_events)
app.include_router(oauth_router)
app.add_exception_handler(exceptions.BaseCustomException, exception_handler)

@app.get("/")
def root():
    return {"message": "hello to the root"}

