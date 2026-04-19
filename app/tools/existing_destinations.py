import json
import logging
import httpx
from langchain_core.tools import tool
from app.config import settings

logger = logging.getLogger(__name__)


@tool
def get_existing_destinations(city_id: int) -> str:
    """Fetches destination names already saved in the database for a city.
    Call this FIRST before suggesting any destinations to avoid duplicates."""
    url = f"{settings.BACKEND_BASE_URL}/api/discover-destinations/city/{city_id}/names"
    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
        return json.dumps(response.json())
    except httpx.HTTPError as e:
        logger.error("Failed to fetch existing destinations: %s", e)
        return json.dumps([])
