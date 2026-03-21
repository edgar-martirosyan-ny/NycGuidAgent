from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.destination import Destination
from app.models.destination_type import DestinationType
from app.schemas.destination import SaveRequest


def get_existing_by_city(city: str, db: Session) -> list[str]:
    """Return list of destination titles already saved for a city."""
    rows = db.execute(
        select(Destination.title).where(
            Destination.city == city.lower()
        )
    ).scalars().all()
    return list(rows)


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
