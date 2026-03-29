from pydantic import BaseModel


class DiscoveryItem(BaseModel):
    name: str
    short_description: str
    wikipedia_url: str
    image_url: str = ""
    latitude: str
    longitude: str
    interesting_facts: list[str]
    priority: int


class DetailItem(BaseModel):
    name: str
    latitude: str
    longitude: str
    short_description: str
    long_description: str
    interesting_facts: list[str]


class DestinationTypeSchema(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


# --- Request bodies ---

class DiscoverRequest(BaseModel):
    city_id: int
    city_name: str
    previous_results: list[DiscoveryItem] | None = None


class DetailRequest(BaseModel):
    city: str
    destination_name: str


class TourGuideRequest(BaseModel):
    city: str
    destination_name: str
    selected_facts: list[str]


class TourGuideResponse(BaseModel):
    tour_guide: str


class SaveDestinationBody(BaseModel):
    name: str
    latitude: str
    longitude: str
    short_description: str
    long_description: str


class SaveRequest(BaseModel):
    city: str
    destination_type_id: int
    destination: SaveDestinationBody


# --- Response bodies ---

class DiscoverResponse(BaseModel):
    destinations: list[DiscoveryItem]


class SaveResponse(BaseModel):
    id: int
    message: str
