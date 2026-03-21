from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.destination import DiscoverRequest, DiscoverResponse
from app.services.agent_discovery import run_discovery_agent

router = APIRouter()


@router.post("/discover", response_model=DiscoverResponse)
def discover(request: DiscoverRequest, db: Session = Depends(get_db)):
    destinations = run_discovery_agent(request, db)
    return DiscoverResponse(destinations=destinations)
