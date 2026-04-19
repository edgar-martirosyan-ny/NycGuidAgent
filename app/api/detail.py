from fastapi import APIRouter
from app.schemas.destination import DetailRequest, DetailItem, TourGuideRequest, TourGuideResponse
from app.services.agent_detail import run_detail_agent, run_tour_guide_agent

router = APIRouter()


@router.post("/detail", response_model=DetailItem)
def detail(request: DetailRequest):
    return run_detail_agent(request.city, request.destination_name)


@router.post("/tour-guide", response_model=TourGuideResponse)
def tour_guide(request: TourGuideRequest):
    return run_tour_guide_agent(request.city, request.destination_name, request.selected_facts)
