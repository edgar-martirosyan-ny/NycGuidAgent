from fastapi import APIRouter
from app.models.destination import DetailRequest, DetailItem, TourGuideRequest, TourGuideResponse
from app.agents.initial_destination_detail import generate_destination_details
from app.agents.description_regeneration import regenerate_description
from fastapi import APIRouter
from app.models.destination import DiscoverRequest, DiscoverResponse
from app.agents.discovery_agent import discover_destinations

router = APIRouter()


@router.post("/detail", response_model=DetailItem)
def detail(request: DetailRequest):
    return generate_destination_details(request.city, request.destination_name)


@router.post("/tour-guide", response_model=TourGuideResponse)
def tour_guide(request: TourGuideRequest):
    return regenerate_description(request.city, request.destination_name, request.selected_facts)

@router.post("/discover", response_model=DiscoverResponse)
def discover(request: DiscoverRequest):
    destinations = discover_destinations(request)
    return DiscoverResponse(destinations=destinations)
