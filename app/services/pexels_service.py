import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

FALLBACK_IMAGE = "https://placehold.co/600x400?text=No+Image"


def fetch_image_url(destination_name: str) -> str:
    """Fetch a photo URL from Pexels for the given destination name."""
    logger.info("Pexels: fetching image for '%s'", destination_name)
    try:
        with httpx.Client(timeout=5) as http:
            response = http.get(
                settings.PEXELS_URL,
                params={"query": destination_name, "per_page": 1},
                headers={"Authorization": settings.PEXELS_TOKEN},
            )
            response.raise_for_status()
            data = response.json()
            photos = data.get("photos", [])
            if photos:
                url = photos[0]["src"]["original"]
                logger.info("Pexels: found image for '%s': %s", destination_name, url)
                return url
            logger.warning("Pexels: no photos returned for '%s'", destination_name)
    except Exception as e:
        logger.warning("Pexels: request failed for '%s': %s", destination_name, str(e))

    return FALLBACK_IMAGE
