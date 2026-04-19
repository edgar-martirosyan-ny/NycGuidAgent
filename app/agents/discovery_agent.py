import json
import logging
import re
import anthropic
from fastapi import HTTPException
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

from app.config import settings
from app.models.destination import DiscoveryItem, DiscoverRequest
from app.tools.existing_destinations import get_existing_destinations
from app.tools.geocode import get_coordinates
from app.services.pexels_service import fetch_image_url

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a tourism expert AI assistant.
You will be given city names and asked to find tourist destinations in those cities.
You need to find the next most popular/interesting destinations not already in the database.
Rank destinations by popularity from 1 to 10.

When asked to find destinations in a city:
1. Call `get_existing_destinations` with the city_id to get destinations already saved.
2. Decide on exactly 5 NEW destinations NOT in that list.
3. Call `get_coordinates` ONCE with all 5 names concatenated with the city (e.g. "Central Park, New York") to get coordinates in a single call.
4. Never repeat destinations from the user's "already seen" list.
5. Return ONLY a valid JSON array — no prose, no markdown fences.

Each item must have exactly these fields:
- name (string)
- short_description (string, 2 sentences)
- wikipedia_url (string — full Wikipedia URL, e.g. https://en.wikipedia.org/wiki/Statue_of_Liberty)
- latitude (string — from get_coordinates result)
- longitude (string — from get_coordinates result)
- interesting_facts (array of 3 strings)
- priority (integer 1–10)
"""

_model = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    api_key=settings.ANTHROPIC_API_KEY,
    max_tokens=4096,
)

_agent = create_react_agent(
    model=_model,
    tools=[get_existing_destinations, get_coordinates],
    prompt=_SYSTEM_PROMPT,
)


def discover_destinations(request: DiscoverRequest) -> list[DiscoveryItem]:
    user_message = f"Find me tourist destinations in {request.city_name} (city_id: {request.city_id})."

    if request.previous_results:
        seen_names = [d.name for d in request.previous_results]
        user_message += f" I have already seen these, do not repeat them: {json.dumps(seen_names)}."

    logger.info("=== Discovery Agent START === city: %s (id=%d)", request.city_name, request.city_id)

    try:
        result = _agent.invoke({"messages": [("human", user_message)]})
        text = result["messages"][-1].content
    except anthropic.AuthenticationError:
        logger.error("Anthropic authentication failed — check ANTHROPIC_API_KEY")
        raise HTTPException(status_code=401, detail="Invalid Anthropic API key.")
    except anthropic.RateLimitError:
        logger.warning("Anthropic rate limit reached")
        raise HTTPException(status_code=429, detail="Anthropic API rate limit reached. Please try again.")
    except anthropic.APIConnectionError:
        logger.error("Cannot connect to Anthropic API")
        raise HTTPException(status_code=503, detail="Could not connect to the AI service.")
    except anthropic.APIStatusError as e:
        logger.error("Anthropic API error %d: %s", e.status_code, e.message)
        raise HTTPException(status_code=502, detail=f"AI service error: {e.message}")
    except Exception as e:
        logger.exception("Unexpected error in discovery agent")
        raise HTTPException(status_code=500, detail=f"Unexpected error during destination discovery: {str(e)}")

    logger.info("LLM final response (first 300 chars): %s", text[:300])
    destinations = _parse_destinations(text)

    logger.info("--- Pexels image fetch ---")
    enriched = [
        dest.model_copy(update={"image_url": fetch_image_url(dest.name)})
        for dest in destinations
    ]

    logger.info("=== Discovery Agent END | returned %d destination(s) ===", len(enriched))
    return enriched


def _parse_destinations(text: str) -> list[DiscoveryItem]:
    text = text.strip()

    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    else:
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            text = text[start:end + 1]

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.error("Failed to parse destinations JSON. Raw: %s", text[:500])
        raise HTTPException(status_code=502, detail="AI returned malformed JSON for destinations. Please try again.")

    try:
        return [DiscoveryItem(**item) for item in data]
    except Exception as e:
        logger.error("DiscoveryItem validation failed: %s", e)
        raise HTTPException(status_code=502, detail=f"AI response had unexpected structure: {str(e)}")
