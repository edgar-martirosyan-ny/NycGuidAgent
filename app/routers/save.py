from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.schemas.destination import SaveRequest, SaveResponse
from app.services.destination_service import save_destination

router = APIRouter()


@router.post("/save", response_model=SaveResponse, status_code=201)
def save(request: SaveRequest, db: Session = Depends(get_db)):
    try:
        record = save_destination(request, db)
        return SaveResponse(id=record.id, message="Destination saved successfully")
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Destination already exists for this city")
