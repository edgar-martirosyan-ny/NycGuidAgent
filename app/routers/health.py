from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter()


@router.get("/welcome-message", response_class=PlainTextResponse)
def welcome_message():
    return "NycGuidAgent is running"
