import json
import logging
import re
import anthropic
from fastapi import HTTPException
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import settings
from app.models.destination import DetailItem

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a professional travel writer and tourism guide.

Return ONLY a valid JSON object with no prose, no markdown fences, no extra text.

The JSON object must have these exact fields:
- name (string — the exact destination name)
- short_description (string — 2 sentences introducing the destination as a tourism guide)
- long_description (string — 3 to 4 paragraphs written as a tourism app audio script, vivid and engaging)
- interesting_facts (array of exactly 10 strings — unique, specific, and engaging facts about the destination)"""

_model = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    api_key=settings.ANTHROPIC_API_KEY,
    max_tokens=2048,
)

_chain = (
    ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT),
        ("human", "Give me the full tourism guide details for '{destination_name}' in {city}."),
    ])
    | _model
    | StrOutputParser()
)


def generate_destination_details(city: str, destination_name: str) -> DetailItem:
    logger.info("=== Detail Agent START === destination: '%s' | city: '%s'", destination_name, city)

    try:
        text = _chain.invoke({"destination_name": destination_name, "city": city})
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
        logger.exception("Unexpected error in detail agent")
        raise HTTPException(status_code=500, detail=f"Unexpected error fetching destination detail: {str(e)}")

    logger.info("LLM raw response (first 300 chars): %s", text[:300])
    detail = _parse_detail(text)
    logger.info("=== Detail Agent END === returned detail for '%s'", detail.name)
    return detail


def _parse_detail(text: str) -> DetailItem:
    text = text.strip()

    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start:end + 1]

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.error("Failed to parse detail JSON. Raw: %s", text[:500])
        raise HTTPException(status_code=502, detail="AI returned malformed JSON for destination detail. Please try again.")

    try:
        return DetailItem(**data)
    except Exception as e:
        logger.error("DetailItem validation failed: %s", e)
        raise HTTPException(status_code=502, detail=f"AI response had unexpected structure: {str(e)}")
