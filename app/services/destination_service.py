from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.destination import Destination
from app.models.destination_type import DestinationType
from app.schemas.destination import SaveRequest


def save_destination(request: SaveRequest, db: Session) -> Destination:
    dest = request.destination
    record = Destination(
        title=dest.name,
        latitude=dest.latitude,
        longitude=dest.longitude,
        description=dest.short_description,
        full_description=dest.long_description,
        destination_type_id=request.destination_type_id,
        city=request.city.lower(),
        destination_rank=None,
        destination_main_image_id=None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_all_types(db: Session) -> list[DestinationType]:
    return db.execute(select(DestinationType)).scalars().all()
