from fastapi import APIRouter
from app.models.destination import (
    DetailRequest, DetailItem, TourGuideRequest, TourGuideResponse,
    DiscoverRequest, DiscoverResponse, RegenerateRequest, RegenerateResponse,
)
from app.agents.initial_destination_detail import generate_destination_details
from app.agents.description_regeneration import regenerate_description
from app.agents.description_regeneration_with_instructions_agent import regenerate_text
from app.agents.discovery_agent import discover_destinations

router = APIRouter()


@router.post("/detail", response_model=DetailItem)
def detail(request: DetailRequest):
    return generate_destination_details(request.city, request.destination_name)


@router.post("/regenerate", response_model=TourGuideResponse)
def tour_guide(request: TourGuideRequest):
    return regenerate_description(request.city, request.destination_name, request.selected_facts)


@router.post("/discover", response_model=DiscoverResponse)
def discover(request: DiscoverRequest):
    destinations = discover_destinations(request)
    return DiscoverResponse(destinations=destinations)


@router.post("/regenerate-with-instructions", response_model=RegenerateResponse)
def regenerate(request: RegenerateRequest):
    text = regenerate_text(
        city=request.city,
        destination_name=request.destination_name,
        current_text=request.current_text,
        text_type=request.text_type,
        annotations=[a.model_dump() for a in request.annotations],
        target_length=request.target_length,
    )
    return RegenerateResponse(text=text)
