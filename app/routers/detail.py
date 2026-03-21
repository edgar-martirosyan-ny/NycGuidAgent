from fastapi import APIRouter
from app.schemas.destination import DetailRequest, DetailItem
from app.services.agent_detail import run_detail_agent

router = APIRouter()


@router.post("/detail", response_model=DetailItem)
def detail(request: DetailRequest):
    return run_detail_agent(request.city, request.destination_name)
