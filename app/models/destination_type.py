from sqlalchemy import Column, Integer, String
from app.database import Base


class DestinationType(Base):
    __tablename__ = "destination_type"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
