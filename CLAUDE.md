# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NycGuidAgent is an AI-powered tourism content generation agent. It uses Anthropic's Claude LLM to suggest travel destinations for a given city, avoid duplicates by querying existing destinations from a MySQL database on Amazon RDS, and return structured JSON for display in an Angular UI.

## Architecture

```
Angular UI (webapp/)
     │
     ▼
Python Agent Backend (FastAPI or Flask)
     │
     ├── Anthropic Claude API  ← AI agent for destination discovery & detail generation
     │
     └── MySQL (Amazon RDS)    ← stores saved destinations per city
```

### Two Agents

**Agent 1 – Destination Discovery**
- Accepts city name from UI
- Fetches already-saved destinations for that city from RDS (to exclude them from LLM results)
- Calls Claude with a tool that provides the existing destinations as context
- Returns structured JSON list of new destinations
- Supports "load more": re-triggers with prior LLM response included as context

**Agent 2 – Destination Detail**
- Triggered when user clicks a specific destination
- Returns detailed structured JSON for that single destination

### Destination JSON Schemas

**Discovery response (list item):**
```json
{
  "name": "string",
  "short_description": "string",
  "wikipedia_url": "string",
  "image_url": "string",
  "latitude": "float",
  "longitude": "float",
  "interesting_facts": ["string"],
  "priority": "int (1–10, popularity rank)"
}
```

**Detail response (single destination):**
```json
{
  "name": "string",
  "latitude": "float",
  "longitude": "float",
  "short_description": "string",
  "long_description": "string"
}
```

## Key Workflows

1. User enters city name → clicks "Find Destinations"
2. Backend queries RDS for existing destinations for that city
3. Agent 1 calls Claude, excluding existing destinations
4. UI displays results; user can click "Load More" (repeats step 3–4 with prior results as context)
5. User clicks a destination → Agent 2 fetches detailed info
6. User clicks "Save" → destination detail stored in RDS

## Environment

- **Python version:** 3.13
- **Virtual environment:** `.venv/` (excluded from source control)
- **Frontend:** Angular (`../webapp/` directory)
- **Database:** MySQL on Amazon RDS
- **LLM:** Anthropic Claude via `anthropic` Python SDK

## Setup

```bash
# Activate virtual environment
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies (once requirements.txt exists)
pip install -r requirements.txt

# Run backend (once entry point is defined)
python main.py
```

## External APIs

### Pexels Image API

Used in `app/services/pexels_service.py` to enrich each discovery result with a photo.

**Environment variables (`.env`):**
| Variable | Description |
|---|---|
| `PEXELS_URL` | Base endpoint — `https://api.pexels.com/v1/search` |
| `PEXELS_TOKEN` | API key — passed as `Authorization: <token>` header (no `Bearer` prefix) |

**Request:**
```
GET https://api.pexels.com/v1/search
Headers:
  Authorization: <PEXELS_TOKEN>
Query params:
  query=<destination name>
  per_page=1
```

**Response shape (relevant fields only):**
```json
{
  "photos": [
    {
      "src": {
        "original": "https://images.pexels.com/photos/...",
        "large2x": "...",
        "large": "...",
        "medium": "...",
        "small": "...",
        "portrait": "...",
        "landscape": "...",
        "tiny": "..."
      }
    }
  ]
}
```

The service reads `photos[0]["src"]["original"]`. If the request fails or returns no photos, it falls back to `https://placehold.co/600x400?text=No+Image`.

**Note:** The `Authorization` header value is the raw token — Pexels does **not** use a `Bearer` prefix.

## Branches

- `master` — stable / production
- `develop` — active development; branch off here for new features
