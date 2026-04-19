import logging
import anthropic
from fastapi import HTTPException
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import settings

logger = logging.getLogger(__name__)

_LENGTH_HINTS = {
    "short": {
        "short": "1 to 2 concise sentences",
        "long": "1 to 2 short paragraphs",
    },
    "medium": {
        "short": "2 to 3 sentences",
        "long": "3 to 4 paragraphs",
    },
    "long": {
        "short": "4 to 5 detailed sentences",
        "long": "5 to 6 rich paragraphs",
    },
}

_SYSTEM_PROMPT = """You are an expert travel writer, tourism guide editor, and audio narration script reviser.

The user will provide:
- an existing destination script
- a list of targeted annotation instructions
- each annotation references a specific excerpt and explains what should change

Your task is to rewrite the FULL script while applying ALL annotations accurately.

Core objectives:
- preserve the original meaning, factual accuracy, and overall flow unless an annotation requests change
- improve clarity, engagement, rhythm, and listenability
- keep the script suitable for a tourism app audio guide
- maintain a natural spoken tone designed for text-to-speech narration
- smoothly blend edits into the full script so no section feels patched in
- preserve facts not mentioned in annotations
- do not remove useful details unless requested
- do not invent new facts unless explicitly requested

When applying annotations:
- if asked to make text more vivid, add sensory or descriptive language
- if asked to shorten, tighten wording without losing meaning
- if asked to expand, add useful context while staying concise
- if asked to change tone, make it consistent across the entire script
- if asked to improve transitions, make the narration flow naturally
- if multiple annotations overlap, resolve them intelligently into one polished result

Writing standards:
- avoid robotic or repetitive phrasing
- begin with an engaging hook, never with “Welcome to…”
- avoid bullet points, headings, or labels
- keep sentences varied and easy to hear aloud
- preserve immersion and storytelling quality
- never begin abruptly or end awkwardly

Length requirement:
- write exactly {length_hint}

Output rules:
- return ONLY the rewritten script
- no JSON
- no markdown
- no commentary
- no explanation"""

_model = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    api_key=settings.ANTHROPIC_API_KEY,
    max_tokens=2048,
)


def regenerate_text(
    city: str,
    destination_name: str,
    current_text: str,
    text_type: str,
    annotations: list[dict],
    target_length: str = "medium",
) -> str:
    logger.info(
        "=== Text Regen START === dest: '%s' | type: %s | length: %s | annotations: %d",
        destination_name, text_type, target_length, len(annotations),
    )

    length_hint = _LENGTH_HINTS.get(target_length, _LENGTH_HINTS["medium"]).get(text_type, "3 to 4 paragraphs")

    system = _SYSTEM_PROMPT.format(length_hint=length_hint)

    annotation_lines = ""
    if annotations:
        parts = []
        for a in annotations:
            tone_note = f" [tone: {a['tone']}]" if a.get("tone") and a["tone"] != "neutral" else ""
            parts.append(f'• Excerpt: "{a["selected_text"]}"\n  Instruction: {a["comment"]}{tone_note}')
        annotation_lines = "\n\n".join(parts)
    else:
        annotation_lines = "(No specific annotations — just rewrite at the requested length.)"

    human_message = (
        f"Destination: {destination_name} ({city})\n\n"
        f"Current text:\n{current_text}\n\n"
        f"Annotation instructions:\n{annotation_lines}"
    )

    chain = (
        ChatPromptTemplate.from_messages([
            ("system", system),
            ("human", "{user_message}"),
        ])
        | _model
        | StrOutputParser()
    )

    try:
        result = chain.invoke({"user_message": human_message})
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid Anthropic API key.")
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="Anthropic API rate limit reached. Please try again.")
    except anthropic.APIConnectionError:
        raise HTTPException(status_code=503, detail="Could not connect to the AI service.")
    except anthropic.APIStatusError as e:
        raise HTTPException(status_code=502, detail=f"AI service error: {e.message}")
    except Exception as e:
        logger.exception("Unexpected error in text regeneration agent")
        raise HTTPException(status_code=500, detail=f"Unexpected error regenerating text: {str(e)}")

    logger.info("=== Text Regen END ===")
    return result.strip()
