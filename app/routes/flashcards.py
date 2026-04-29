"""Flashcard CRUD and spaced-repetition review endpoints."""

from datetime import datetime, timezone, timedelta
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo import ReturnDocument

from app.database import get_collection
from app.middleware.auth import get_current_user
from app.models import BulkFlashcardsCreate, FlashcardCreate, ReviewSubmit

router = APIRouter()

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def _serialize(doc: dict) -> dict:
    """Convert MongoDB document to API-safe dict."""
    doc["id"]      = str(doc.pop("_id"))
    doc["user_id"] = str(doc.get("user_id", ""))
    if doc.get("source_note_id"):
        doc["source_note_id"] = str(doc["source_note_id"])
    return doc

def _serialize_demo(doc: dict) -> dict:
    """Convert demo dict to API-safe format without ObjectId conversion."""
    doc["id"] = doc.pop("_id")
    return doc


def _now() -> datetime:
    return datetime.now(timezone.utc)


# SM-2 quality codes
_QUALITY_MAP = {"again": 0, "hard": 2, "good": 3, "easy": 5}

# Default spaced-repetition state for a new card
_DEFAULT_SRS = {"ease_factor": 2.5, "interval": 1, "repetitions": 0}


def _sm2(
    ease_factor: float,
    interval: int,
    repetitions: int,
    quality: int,
) -> tuple[float, int, int, datetime]:
    """
    SuperMemo-2 algorithm.
    Returns (new_ease_factor, new_interval, new_repetitions, next_review_dt).
    """
    if quality < 3:
        # Failed — restart repetitions but keep ease factor
        repetitions = 0
        interval    = 1
    else:
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = round(interval * ease_factor)
        repetitions += 1

    ease_factor = max(
        1.3,
        ease_factor + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02),
    )

    next_review = _now() + timedelta(days=interval)
    return ease_factor, interval, repetitions, next_review


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────
@router.get("/")
async def list_cards(
    subject: Optional[str] = Query(None),
    due_only: bool          = Query(False),
    current_user: dict      = Depends(get_current_user),
):
    col = get_collection("flashcards")
    if col is None:
        return {"success": True, "total": 0, "data": []}

    filt: dict = {"user_id": ObjectId(current_user["id"])}

    if subject:
        filt["subject"] = {"$regex": subject, "$options": "i"}

    if due_only:
        filt["next_review"] = {"$lte": _now()}

    cards = [_serialize(doc) async for doc in col.find(filt).sort("next_review", 1)]
    return {"success": True, "total": len(cards), "data": cards}


@router.post("/", status_code=201)
async def create_card(
    body: FlashcardCreate,
    current_user: dict = Depends(get_current_user),
):
    col = get_collection("flashcards")
    now = _now()

    doc = body.model_dump()
    doc.update({
        "user_id":    current_user["id"] if col is None else ObjectId(current_user["id"]),
        "next_review": now,
        "last_result": None,
        "created_at":  now,
        **_DEFAULT_SRS,
    })

    if col is None:
        # Mock database insertion for demo mode
        doc["_id"] = f"card_{now.timestamp()}"
        return {"success": True, "data": _serialize_demo(doc)}

    res = await col.insert_one(doc)
    doc["_id"] = res.inserted_id
    return {"success": True, "data": _serialize(doc)}


@router.post("/bulk", status_code=201)
async def bulk_create(
    body: BulkFlashcardsCreate,
    current_user: dict = Depends(get_current_user),
):
    col = get_collection("flashcards")
    now = _now()
    uid = ObjectId(current_user["id"])

    docs = []
    for card in body.cards:
        d = card.model_dump()
        d.update({
            "user_id":     uid,
            "next_review": now,
            "last_result": None,
            "ai_generated": True,
            "created_at":  now,
            **_DEFAULT_SRS,
        })
        docs.append(d)

    if col is None:
        # Mock bulk insertion for demo mode
        for d in docs:
            d["_id"] = f"card_{now.timestamp()}_{id(d)}"
        return {"success": True, "created": len(docs), "data": [_serialize_demo(d) for d in docs]}

    result = await col.insert_many(docs)

    for d, oid in zip(docs, result.inserted_ids):
        d["_id"] = oid

    return {"success": True, "created": len(docs), "data": [_serialize(d) for d in docs]}


@router.post("/{card_id}/review")
async def submit_review(
    card_id: str,
    body: ReviewSubmit,
    current_user: dict = Depends(get_current_user),
):
    col = get_collection("flashcards")

    if col is None:
        # Mock review update for demo mode
        ef, iv, reps, nxt = _sm2(2.5, 1, 0, _QUALITY_MAP[body.result.value])
        mock_updated = {
            "_id": card_id,
            "user_id": current_user["id"],
            "ease_factor": ef,
            "interval": iv,
            "repetitions": reps,
            "next_review": nxt,
            "last_result": body.result.value,
        }
        return {"success": True, "data": _serialize_demo(mock_updated), "next_review": nxt.isoformat()}

    oid = ObjectId(card_id)
    card = await col.find_one({
        "_id":     oid,
        "user_id": ObjectId(current_user["id"]),
    })
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    quality = _QUALITY_MAP[body.result.value]
    ef, iv, reps, nxt = _sm2(
        card["ease_factor"],
        card["interval"],
        card["repetitions"],
        quality,
    )

    updated = await col.find_one_and_update(
        {"_id": oid},
        {"$set": {
            "ease_factor": ef,
            "interval":    iv,
            "repetitions": reps,
            "next_review": nxt,
            "last_result": body.result.value,
        }},
        return_document=ReturnDocument.AFTER,
    )

    return {
        "success":     True,
        "data":        _serialize(updated),
        "next_review": nxt.isoformat(),
    }


@router.delete("/{card_id}", status_code=200)
async def delete_card(
    card_id: str,
    current_user: dict = Depends(get_current_user),
):
    col = get_collection("flashcards")

    try:
        oid = ObjectId(card_id)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid card ID format")

    if col is None:
        # Mock deletion for demo mode
        return {"success": True, "message": "Card deleted"}

    result = await col.delete_one({
        "_id":     oid,
        "user_id": ObjectId(current_user["id"]),
    })

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Card not found")

    return {"success": True, "message": "Card deleted"}
