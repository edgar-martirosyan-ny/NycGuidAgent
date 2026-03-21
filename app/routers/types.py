from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.destination import DestinationTypeSchema
from app.services.destination_service import get_all_types

router = APIRouter()


@router.get("/types", response_model=list[DestinationTypeSchema])
def list_types(db: Session = Depends(get_db)):
    return get_all_types(db)
