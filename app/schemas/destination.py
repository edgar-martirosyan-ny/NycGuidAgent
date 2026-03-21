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


class DestinationTypeSchema(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


# --- Request bodies ---

class DiscoverRequest(BaseModel):
    city: str
    previous_results: list[DiscoveryItem] | None = None


class DetailRequest(BaseModel):
    city: str
    destination_name: str


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
