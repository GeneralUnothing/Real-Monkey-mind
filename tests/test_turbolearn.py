"""
Tests for TurboLearn endpoints.

Run:
    pytest tests/test_turbolearn.py -v --anyio-mode=asyncio
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# ── Patch DB connections before importing the app ─────────────────────────────
with patch("app.database.connect_db", new_callable=AsyncMock), \
     patch("app.database.close_db",   new_callable=AsyncMock):
    from main import app

# ─────────────────────────────────────────────
# Fixtures & constants
# ─────────────────────────────────────────────
FAKE_USER = {"id": "6" * 24, "email": "test@test.com", "role": "student"}
AUTH_HEADER = {"Authorization": "Bearer fake.jwt.token"}

_NOTES_PAYLOAD = {
    "title": "Test Notes",
    "summary": "A brief summary.",
    "sections": [{"heading": "Intro", "content": "...", "key_points": ["Point 1"]}],
    "key_terms": [{"term": "ML", "definition": "Machine Learning"}],
    "exam_tips": ["Review key terms"],
    "estimated_read_minutes": 3,
}

_QUIZ_PAYLOAD = {
    "quiz_title": "Test Quiz",
    "questions": [
        {
            "id": 1,
            "type": "mcq",
            "question": "What is 2+2?",
            "options": ["A. 3", "B. 4", "C. 5", "D. 6"],
            "correct_answer": "B",
            "explanation": "Basic arithmetic.",
            "difficulty": "easy",
            "topic": "Math",
        }
    ],
    "total_marks": 1,
    "estimated_minutes": 5,
}

_GRADE_PAYLOAD = {
    "is_correct": True,
    "score": 1.0,
    "feedback": "Correct!",
    "correct_answer": "B",
    "improvement_tip": "Keep it up.",
}


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


def _mock_completion(payload: dict | str) -> MagicMock:
    """Build a mock that mimics AsyncOpenAI chat completions response."""
    content = payload if isinstance(payload, str) else json.dumps(payload)
    choice  = MagicMock()
    choice.message.content = content
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _patch_openai(payload: dict | str):
    """Context manager: patch AsyncOpenAI inside turbolearn with a fake response."""
    instance = AsyncMock()
    instance.chat.completions.create = AsyncMock(return_value=_mock_completion(payload))
    mock_cls = MagicMock(return_value=instance)
    return patch("app.routes.turbolearn.AsyncOpenAI", mock_cls)


# ─────────────────────────────────────────────
# Quiz generator
# ─────────────────────────────────────────────
@pytest.mark.anyio
async def test_generate_quiz_success(client):
    with patch("app.middleware.auth.decode_token", return_value=FAKE_USER), \
         _patch_openai(_QUIZ_PAYLOAD):

        r = await client.post(
            "/api/v1/turbolearn/generate-quiz",
            data={
                "content":        "Machine learning is a subset of AI...",
                "num_questions":  "3",
                "difficulty":     "easy",
                "question_types": "mcq",
                "subject":        "AI",
            },
            headers=AUTH_HEADER,
        )

    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "questions" in body["data"]
    assert len(body["data"]["questions"]) >= 1


@pytest.mark.anyio
async def test_generate_quiz_invalid_type(client):
    with patch("app.middleware.auth.decode_token", return_value=FAKE_USER):
        r = await client.post(
            "/api/v1/turbolearn/generate-quiz",
            data={
                "content":        "Some content",
                "num_questions":  "5",
                "difficulty":     "easy",
                "question_types": "invalid_type",
            },
            headers=AUTH_HEADER,
        )
    assert r.status_code == 400


@pytest.mark.anyio
async def test_generate_quiz_num_questions_below_min(client):
    """num_questions below the minimum of 3 should fail validation (422)."""
    with patch("app.middleware.auth.decode_token", return_value=FAKE_USER):
        r = await client.post(
            "/api/v1/turbolearn/generate-quiz",
            data={
                "content":        "Some content",
                "num_questions":  "1",
                "difficulty":     "easy",
                "question_types": "mcq",
            },
            headers=AUTH_HEADER,
        )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_generate_quiz_num_questions_above_max(client):
    """num_questions above 30 should fail validation (422)."""
    with patch("app.middleware.auth.decode_token", return_value=FAKE_USER):
        r = await client.post(
            "/api/v1/turbolearn/generate-quiz",
            data={
                "content":        "Some content",
                "num_questions":  "50",
                "difficulty":     "easy",
                "question_types": "mcq",
            },
            headers=AUTH_HEADER,
        )
    assert r.status_code == 422


# ─────────────────────────────────────────────
# Grade answer
# ─────────────────────────────────────────────
@pytest.mark.anyio
async def test_grade_answer_success(client):
    with patch("app.middleware.auth.decode_token", return_value=FAKE_USER), \
         _patch_openai(_GRADE_PAYLOAD):

        r = await client.post(
            "/api/v1/turbolearn/grade-answer",
            data={
                "question":       "What is 2+2?",
                "question_type":  "mcq",
                "student_answer": "B",
                "correct_answer": "B",
            },
            headers=AUTH_HEADER,
        )

    assert r.status_code == 200
    data = r.json()["data"]
    assert "is_correct"       in data
    assert "score"            in data
    assert "feedback"         in data
    assert "improvement_tip"  in data


@pytest.mark.anyio
async def test_grade_answer_invalid_type(client):
    with patch("app.middleware.auth.decode_token", return_value=FAKE_USER):
        r = await client.post(
            "/api/v1/turbolearn/grade-answer",
            data={
                "question":       "What is 2+2?",
                "question_type":  "essay",          # invalid
                "student_answer": "4",
                "correct_answer": "4",
            },
            headers=AUTH_HEADER,
        )
    assert r.status_code == 422


# ─────────────────────────────────────────────
# PDF to notes
# ─────────────────────────────────────────────
@pytest.mark.anyio
async def test_pdf_wrong_format_rejected(client):
    with patch("app.middleware.auth.decode_token", return_value=FAKE_USER):
        r = await client.post(
            "/api/v1/turbolearn/pdf-to-notes",
            files={"file": ("lecture.docx", b"fake content", "application/octet-stream")},
            headers=AUTH_HEADER,
        )
    assert r.status_code == 400


@pytest.mark.anyio
async def test_pdf_to_notes_success(client):
    fake_text = "This is a lecture about neural networks and deep learning."

    mock_page = MagicMock()
    mock_page.get_text.return_value = fake_text

    mock_doc = MagicMock()
    mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
    mock_doc.__len__  = MagicMock(return_value=1)

    with patch("app.middleware.auth.decode_token", return_value=FAKE_USER), \
         _patch_openai(_NOTES_PAYLOAD), \
         patch("fitz.open", return_value=mock_doc):

        r = await client.post(
            "/api/v1/turbolearn/pdf-to-notes",
            files={"file": ("lecture.pdf", b"%PDF-fake", "application/pdf")},
            headers=AUTH_HEADER,
        )

    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "title" in body["data"]
    assert body["data"]["source"]["type"] == "pdf_upload"


# ─────────────────────────────────────────────
# Audio to notes
# ─────────────────────────────────────────────
@pytest.mark.anyio
async def test_audio_wrong_format_rejected(client):
    with patch("app.middleware.auth.decode_token", return_value=FAKE_USER):
        r = await client.post(
            "/api/v1/turbolearn/audio-to-notes",
            files={"file": ("lecture.exe", b"fake", "application/octet-stream")},
            headers=AUTH_HEADER,
        )
    assert r.status_code == 400


# ─────────────────────────────────────────────
# YouTube to notes
# ─────────────────────────────────────────────
@pytest.mark.anyio
async def test_youtube_invalid_url(client):
    """Unavailable video should return 400, not 500."""
    with patch("app.middleware.auth.decode_token", return_value=FAKE_USER), \
         patch("yt_dlp.YoutubeDL") as mock_ydl:

        mock_ydl.return_value.__enter__.return_value.extract_info.side_effect = \
            Exception("Video unavailable")

        r = await client.post(
            "/api/v1/turbolearn/youtube-to-notes",
            data={"url": "https://youtube.com/watch?v=INVALID"},
            headers=AUTH_HEADER,
        )
    assert r.status_code == 400


# ─────────────────────────────────────────────
# Auth guard
# ─────────────────────────────────────────────
@pytest.mark.anyio
async def test_turbolearn_requires_auth(client):
    """All endpoints must reject unauthenticated requests."""
    r = await client.post(
        "/api/v1/turbolearn/generate-quiz",
        data={
            "content":        "test",
            "num_questions":  "5",
            "difficulty":     "easy",
            "question_types": "mcq",
        },
        # No Authorization header
    )
    assert r.status_code in (401, 403)
