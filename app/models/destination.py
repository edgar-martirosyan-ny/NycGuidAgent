from sqlalchemy import Column, Integer, String, Text
from app.database import Base


class Destination(Base):
    __tablename__ = "destination"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(256), nullable=False)
    longitude = Column(String(256), nullable=False)
    latitude = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    full_description = Column(Text, nullable=True)
    destination_type_id = Column(Integer, nullable=False)
    destination_rank = Column(Integer, nullable=True)
    destination_main_image_id = Column(Integer, nullable=True)
    city = Column(String(100), nullable=True)
