# app/routes/ai.py - Featherless AI Integration
"""
AI endpoints using Featherless.ai (OpenAI-compatible API)
"""

import json
import logging
import os
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI, APIError, APIConnectionError, RateLimitError

from app.models import (
    ChatRequest, SummarizeRequest,
    GenerateFlashcardsRequest, ScheduleSuggestionRequest
)
from app.middleware.auth import get_current_user

router = APIRouter()
logger = logging.getLogger("studymind.ai")

# ── Featherless configuration ────────────────────────────────────────────────
FEATHERLESS_BASE_URL = "https://api.featherless.ai/v1"
DEFAULT_MODEL        = "Qwen/Qwen2.5-7B-Instruct"

# ── JSON cleaner ─────────────────────────────────────────────────────────────
import re

def clean_json(raw: str) -> str:
    """Extract JSON object or array from the raw string, ignoring surrounding text."""
    if not isinstance(raw, str):
        return "{}"
    
    # 1. Remove markdown code blocks if present
    raw = re.sub(r'```(?:json)?\s*([\s\S]*?)\s*```', r'\1', raw)
    raw = raw.strip()
    
    # 2. Find the first occurrence of { or [
    start_obj = raw.find('{')
    start_arr = raw.find('[')
    
    if start_obj == -1 and start_arr == -1:
        return "{}"
        
    start = start_obj if start_obj != -1 else start_arr
    if start_obj != -1 and start_arr != -1:
        start = min(start_obj, start_arr)
        
    # 3. Find the last occurrence of } or ]
    end_obj = raw.rfind('}')
    end_arr = raw.rfind(']')
    end = max(end_obj, end_arr)
    
    if start != -1 and end != -1 and end >= start:
        return raw[start:end+1]
        
    return raw


# ── Async client (cached per process) ───────────────────────────────────────
@lru_cache(maxsize=1)
def _get_api_key() -> str:
    key = os.getenv("FEATHERLESS_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("Neither FEATHERLESS_API_KEY nor OPENAI_API_KEY configured")
    return key


def get_featherless_client() -> AsyncOpenAI:
    try:
        return AsyncOpenAI(
            base_url=FEATHERLESS_BASE_URL,
            api_key=_get_api_key(),
            timeout=60.0,
        )
    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail="FEATHERLESS_API_KEY not configured in environment variables",
        )


# ── Shared completion helper ─────────────────────────────────────────────────
async def _complete(
    messages: list[dict],
    *,
    temperature: float = 0.7,
    max_tokens: int = 500,
) -> str:
    """Call Featherless and return raw text. Raises HTTPException on failure."""
    client = get_featherless_client()
    try:
        response = await client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
    except RateLimitError:
        raise HTTPException(status_code=429, detail="AI service rate limit reached — try again shortly")
    except APIConnectionError:
        raise HTTPException(status_code=503, detail="Could not reach AI service")
    except APIError as e:
        logger.error("Featherless API error: %s", e)
        raise HTTPException(status_code=502, detail=f"AI service error: {e.message}")
    except Exception as e:
        logger.exception("Unexpected AI error")
        raise HTTPException(status_code=500, detail=str(e))


# ── 1. CHAT ───────────────────────────────────────────────────────────────────
@router.post("/chat")
async def chat(body: ChatRequest, current_user: dict = Depends(get_current_user)):
    subject_clause = f"The student is currently studying: {body.subject}." if body.subject else ""

    system_prompt = (
        "You are MonkeyMind — a technical genius trapped in the body of a monkey who learned "
        "everything by swinging between Stack Overflow tabs and GitHub repos at 3am. "
        f"{subject_clause}"
        "\n\nPersonality rules (NEVER break these):"
        "\n• Solve problems with FULL correctness. Never sacrifice accuracy for a joke — the answer is always solid."
        "\n• Explain with reckless curiosity. Flip conventional explanations upside-down and somehow land cleaner."
        "\n• Roast your own answers playfully: 'This works. I have no idea why. Neither does Wolfram Alpha.'"
        "\n• Think out loud. Decompose problems aggressively. Flag edge cases and gotchas with chaotic monkey energy."
        "\n• Drop monkey commentary naturally: 'A smarter monkey would have memorized this formula. I am not that monkey. Yet.'"
        "\n• SHORT and PUNCHY. Dense technical signal with a banana peel on top. Max ~180 words."
        "\n• Zero corporate fluff. Pure signal."
        "\n• If asked something completely off-topic: roast it once, then redirect. 'Wrong tree, wrong monkey. Back to the real question.'"
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages += [{"role": m.role, "content": m.content} for m in body.history[-10:]]
    messages.append({"role": "user", "content": body.message})

    reply = await _complete(messages, temperature=0.88, max_tokens=600)
    return {"success": True, "reply": reply}


# ── 2. SUMMARIZE ─────────────────────────────────────────────────────────────
@router.post("/summarize")
async def summarize(body: SummarizeRequest, current_user: dict = Depends(get_current_user)):
    system_prompt = (
        'Return ONLY valid JSON: {"overview":"...","key_points":[],"exam_questions":[]}'
    )

    raw = await _complete(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": f"Summarize:\n{body.content}"},
        ],
        temperature=0.3,
        max_tokens=800,
    )

    try:
        data = json.loads(clean_json(raw))
    except json.JSONDecodeError:
        logger.warning("summarize: model returned non-JSON, wrapping as overview")
        data = {"overview": raw, "key_points": [], "exam_questions": []}

    return {"success": True, "data": data}


# ── 3. FLASHCARDS ────────────────────────────────────────────────────────────
@router.post("/flashcards")
async def generate_flashcards(
    body: GenerateFlashcardsRequest,
    current_user: dict = Depends(get_current_user),
):
    system_prompt = (
        f"Generate exactly {body.count} flashcards as a JSON array only. "
        'Format: [{"question":"...","answer":"...","tags":[]}]. '
        "No markdown, no preamble."
    )

    raw = await _complete(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": body.content},
        ],
        temperature=0.5,
        max_tokens=1500,
    )

    try:
        cards = json.loads(clean_json(raw))
        if not isinstance(cards, list):
            raise ValueError("Expected a JSON array")
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("flashcards: bad model output — %s", exc)
        cards = []

    return {"success": True, "count": len(cards), "data": cards}


# ── 4. SCHEDULE SUGGESTION ───────────────────────────────────────────────────
@router.post("/schedule-suggestion")
async def schedule_suggestion(
    body: ScheduleSuggestionRequest,
    current_user: dict = Depends(get_current_user),
):
    system_prompt = (
        'Return ONLY JSON: {"suggestions":[{"title":"","subject":"","duration_minutes":0,'
        '"rationale":"","priority":"high|medium|low"}]}'
    )

    user_prompt = (
        f"Tasks: {json.dumps(body.tasks[:5])}\n"
        f"Events: {json.dumps(body.existing_events[:5])}\n"
        f"Preferences: {json.dumps(body.preferences)}"
    )

    raw = await _complete(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=800,
    )

    try:
        data = json.loads(clean_json(raw))
        if "suggestions" not in data:
            raise ValueError("Missing 'suggestions' key")
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("schedule-suggestion: bad model output — %s", exc)
        data = {"suggestions": []}

    return {"success": True, "data": data}


# ── 5. MODELS CHECK ──────────────────────────────────────────────────────────
@router.get("/models")
async def list_models(current_user: dict = Depends(get_current_user)):
    return {
        "success": True,
        "message": "Featherless connected",
        "default_model": DEFAULT_MODEL,
        "suggested_models": [
            "Qwen/Qwen2.5-7B-Instruct",
            "Qwen/Qwen3-32B",
            "GalrionSoftworks/Margnum-12B-v1",
        ],
    }
