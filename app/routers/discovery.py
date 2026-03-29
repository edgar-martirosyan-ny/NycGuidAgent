from fastapi import APIRouter
from app.schemas.destination import DiscoverRequest, DiscoverResponse
from app.services.agent_discovery import run_discovery_agent

router = APIRouter()


@router.post("/discover", response_model=DiscoverResponse)
def discover(request: DiscoverRequest):
    destinations = run_discovery_agent(request)
    return DiscoverResponse(destinations=destinations)
