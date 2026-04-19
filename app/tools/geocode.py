import json
import logging
import httpx
from langchain_core.tools import tool
from app.config import settings

logger = logging.getLogger(__name__)


@tool
def get_coordinates(destination_names: list[str]) -> str:
    """Get latitude and longitude for multiple destinations in one call.
    Pass all names at once, each concatenated with the city
    e.g. ['Central Park, New York', 'Brooklyn Bridge, New York']."""
    url = f"{settings.BACKEND_BASE_URL}/api/destinations/geocode"
    try:
        response = httpx.post(url, json=destination_names, timeout=10.0)
        response.raise_for_status()
        return json.dumps(response.json())
    except Exception as e:
        logger.error("Geocode API call failed: %s", e)
        return json.dumps([])
