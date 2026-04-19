import json
import logging
import re
import anthropic
from fastapi import HTTPException
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import settings
from app.models.destination import TourGuideResponse

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a professional travel writer and tourism guide.

The user will provide a destination and a list of specific interesting facts they want to focus on.
Write a vivid, engaging tour guide narrative (3 to 4 paragraphs) that weaves those specific facts into the story.
Return ONLY a valid JSON object with a single field:
- tour_guide (string — the generated narrative, written as a tourism app audio script)"""

_model = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    api_key=settings.ANTHROPIC_API_KEY,
    max_tokens=2048,
)

_chain = (
    ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT),
        ("human", "{user_message}"),
    ])
    | _model
    | StrOutputParser()
)


def regenerate_description(city: str, destination_name: str, selected_facts: list[str]) -> TourGuideResponse:
    logger.info("=== Tour Guide Agent START === destination: '%s' | city: '%s' | facts: %d",
                destination_name, city, len(selected_facts))

    facts_text = "\n".join(f"- {f}" for f in selected_facts)
    user_message = (
        f"Write a tour guide for '{destination_name}' in {city} "
        f"focused on these specific facts:\n{facts_text}"
    )

    try:
        text = _chain.invoke({"user_message": user_message})
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid Anthropic API key.")
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="Anthropic API rate limit reached. Please try again.")
    except anthropic.APIConnectionError:
        raise HTTPException(status_code=503, detail="Could not connect to the AI service.")
    except anthropic.APIStatusError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {e.message}")
    except Exception as e:
        logger.exception("Unexpected error in tour guide agent")
        raise HTTPException(status_code=500, detail=f"Unexpected error generating tour guide: {str(e)}")

    logger.info("Tour Guide LLM response (first 300 chars): %s", text[:300])

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
        result = TourGuideResponse(tour_guide=data["tour_guide"])
        logger.info("=== Tour Guide Agent END ===")
        return result
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("Failed to parse tour guide response: %s", e)
        raise HTTPException(status_code=502, detail="AI returned malformed tour guide response. Please try again.")
