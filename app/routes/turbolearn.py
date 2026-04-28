# app/routes/turbolearn.py  — Advanced TurboLearn AI
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
import json

router = APIRouter()

# ──────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────
class GenerateQuizRequest(BaseModel):
    content: str
    num_questions: int = 5
    difficulty: str = "medium"          # easy | medium | hard | mixed
    question_types: str = "mcq"         # mcq | true_false | short_answer
    subject: Optional[str] = None
    focus_area: Optional[str] = None    # e.g. "formulas only"

class TextToNotesRequest(BaseModel):
    content: str
    subject: Optional[str] = None
    style: str = "comprehensive"        # comprehensive | concise | bullet

class YouTubeRequest(BaseModel):
    url: str
    depth: str = "full"                 # full | summary

class ExplainConceptRequest(BaseModel):
    concept: str
    level: str = "undergraduate"        # beginner | high_school | undergraduate | advanced
    subject: Optional[str] = None

class StudyPatternRequest(BaseModel):
    study_hours: List[float]
    completion_rates: List[float]
    subjects: List[str]

class StudyPatternResponse(BaseModel):
    optimal_study_hours: List[int]
    predicted_productivity: float
    recommended_break_interval: int

class DifficultyRequest(BaseModel):
    title: str
    subject: Optional[str] = None
    tags: List[str] = []
    estimated_minutes: Optional[int] = None

class DifficultyResponse(BaseModel):
    difficulty_score: float
    difficulty_label: str
    suggested_minutes: int

async def get_current_user():
    return {"id": "test_user", "email": "test@example.com"}

# ──────────────────────────────────────────────
# Lazy imports (avoid circular at module level)
# ──────────────────────────────────────────────
def _ai():
    from app.routes.ai import _complete, clean_json
    return _complete, clean_json

# ──────────────────────────────────────────────
# ML heuristic endpoints (unchanged)
# ──────────────────────────────────────────────
@router.post("/study-pattern", response_model=StudyPatternResponse)
async def predict_study_pattern(body: StudyPatternRequest, current_user: dict = Depends(get_current_user)):
    avg = sum(body.completion_rates) / len(body.completion_rates)
    return StudyPatternResponse(
        optimal_study_hours=[20, 21, 22],
        predicted_productivity=round(min(avg * 1.1, 1.0), 2),
        recommended_break_interval=25
    )

@router.post("/difficulty", response_model=DifficultyResponse)
async def predict_difficulty(body: DifficultyRequest, current_user: dict = Depends(get_current_user)):
    text = (body.title + " " + " ".join(body.tags)).lower()
    hard = {"exam", "final", "project", "thesis", "dissertation", "research"}
    med  = {"quiz", "assignment", "report", "homework", "test"}
    if any(k in text for k in hard):   diff, score, mins = "hard",   0.8, 120
    elif any(k in text for k in med):  diff, score, mins = "medium", 0.5, 60
    else:                               diff, score, mins = "easy",   0.2, 30
    return DifficultyResponse(difficulty_score=score, difficulty_label=diff,
                               suggested_minutes=body.estimated_minutes or mins)

@router.get("/status")
async def ml_status(current_user: dict = Depends(get_current_user)):
    return {
        "success": True,
        "ml_models": {
            "study_optimizer":      {"state": "active",  "mode": "heuristic"},
            "difficulty_predictor": {"state": "active",  "mode": "heuristic"},
            "turbolearn_ai":        {"state": "active",  "mode": "featherless-llm"},
            "retention_model":      {"state": "pending", "note": "Run python train_models.py"}
        }
    }

# ──────────────────────────────────────────────
# 1. ADVANCED QUIZ GENERATOR
# ──────────────────────────────────────────────
@router.post("/generate-quiz")
async def generate_quiz(body: GenerateQuizRequest, current_user: dict = Depends(get_current_user)):
    if not 3 <= body.num_questions <= 30:
        raise HTTPException(422, "num_questions must be 3–30")
    if body.question_types not in ("mcq", "true_false", "short_answer"):
        raise HTTPException(400, "Invalid question_types")

    _complete, clean_json = _ai()

    focus = f" Focus specifically on: {body.focus_area}." if body.focus_area else ""
    subj  = f"Subject: {body.subject}." if body.subject else ""

    system = (
        "You are a strict JSON data generator. Generate an academic quiz. "
        "Keep explanations under 15 words to maximize speed."
    )
    user = (
        f"{subj} Generate {body.num_questions} {body.difficulty} "
        f"{body.question_types} questions based on this content:{focus}\n\n"
        f"CONTENT:\n{body.content}\n\n"
        "OUTPUT ONLY STRICT JSON in this exact format:\n"
        '{"quiz_title":"...","difficulty":"...","questions":['
        '{"id":1,"type":"mcq","question":"...","hint":"...","options":["...","...","...","..."],'
        '"correct_answer":"A","explanation":"...","topic":"...","difficulty":"..."}]}'
    )

    raw = await _complete(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.1, max_tokens=1500
    )
    try:
        data = json.loads(clean_json(raw))
        if "questions" not in data:
            raise ValueError
    except Exception:
        data = {"quiz_title": "Quiz", "questions": []}

    return {"success": True, "data": data}


# ──────────────────────────────────────────────
# 2. ADVANCED TEXT → NOTES
# ──────────────────────────────────────────────
@router.post("/text-to-notes")
async def text_to_notes(body: TextToNotesRequest, current_user: dict = Depends(get_current_user)):
    _complete, clean_json = _ai()

    subj = f"Subject: {body.subject}." if body.subject else ""
    style_hint = {
        "comprehensive": "Create very detailed, well-structured notes with examples.",
        "concise":       "Create concise, scannable notes. Keep each point brief.",
        "bullet":        "Use bullet points exclusively. No long paragraphs.",
    }.get(body.style, "Create detailed notes.")

    system = (
        "You are a master academic note-taker. You transform raw text into beautiful, "
        "structured, exam-ready study notes."
    )
    user = (
        f"{subj} {style_hint}\n\nSOURCE TEXT:\n{body.content[:4000]}\n\n"
        "RETURN ONLY valid JSON:\n"
        '{"title":"...","subject":"...","summary":"...","sections":['
        '{"heading":"...","content":"...","key_points":["..."],"examples":["..."]}],'
        '"key_terms":[{"term":"...","definition":"..."}],'
        '"exam_tips":["..."],'
        '"common_mistakes":["..."],'
        '"difficulty":"easy|medium|hard"}'
    )

    raw = await _complete(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.3, max_tokens=2500
    )
    try:
        data = json.loads(clean_json(raw))
    except Exception:
        data = {"title": "Notes", "summary": raw, "sections": [], "key_terms": [], "exam_tips": []}

    return {"success": True, "data": data, "source": {"type": "text"}}


# ──────────────────────────────────────────────
# 3. ADVANCED YOUTUBE → NOTES
# ──────────────────────────────────────────────
@router.post("/youtube-to-notes")
async def youtube_to_notes(body: YouTubeRequest, current_user: dict = Depends(get_current_user)):
    import yt_dlp
    _complete, clean_json = _ai()

    try:
        ydl_opts = {
            "quiet": True, 
            "simulate": True, 
            "noplaylist": True,
            "extractor_args": {"youtube": {"player_client": ["android"]}}
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info   = ydl.extract_info(body.url, download=False)
            title  = info.get("title", "YouTube Video")
            desc   = info.get("description", "")[:2000]
            ch     = info.get("channel", "")
            dur    = info.get("duration_string", "")
            tags   = ", ".join(info.get("tags", [])[:10])
    except Exception:
        raise HTTPException(400, "Video unavailable or URL invalid")

    depth_hint = (
        "Generate VERY COMPREHENSIVE study notes with all sections filled in detail."
        if body.depth == "full" else
        "Generate a concise summary with key points only."
    )

    system = (
        "You are an expert academic summarizer specializing in turning video content "
        "into high-quality, structured, exam-ready study notes."
    )
    user = (
        f"VIDEO: {title}\nChannel: {ch}\nDuration: {dur}\nTags: {tags}\n"
        f"Description: {desc}\n\n{depth_hint}\n\n"
        "RETURN ONLY valid JSON:\n"
        '{"title":"...","channel":"...","duration":"...","summary":"...","sections":['
        '{"heading":"...","content":"...","key_points":["..."],"examples":["..."]}],'
        '"key_terms":[{"term":"...","definition":"..."}],'
        '"exam_tips":["..."],'
        '"common_mistakes":["..."],'
        '"related_topics":["..."],'
        '"estimated_read_minutes":5}'
    )

    raw = await _complete(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.3, max_tokens=2500
    )
    try:
        data = json.loads(clean_json(raw))
    except Exception:
        data = {"title": title, "summary": raw, "sections": [], "key_terms": [], "exam_tips": []}

    return {"success": True, "data": data, "source": {"type": "youtube", "url": body.url}}


# ──────────────────────────────────────────────
# 4. NOTE TO FLASHCARDS (NEW)
# ──────────────────────────────────────────────
class NoteFlashcardRequest(BaseModel):
    text: str
    title: str = "Extracted Flashcards"

@router.post("/note-to-flashcards")
async def note_to_flashcards(body: NoteFlashcardRequest, current_user: dict = Depends(get_current_user)):
    _complete, clean_json = _ai()

    system = (
        "You are an expert study assistant. The user will provide a set of study notes. "
        "Extract the most important concepts, definitions, and facts, and convert them "
        "into a set of highly effective study flashcards (Question and Answer format)."
    )
    user = (
        f"Title: {body.title}\n\n"
        f"Notes:\n{body.text}\n\n"
        "Generate 5 to 10 high-yield flashcards from these notes.\n"
        "RETURN ONLY a valid JSON list of objects. Each object must have a 'question' and 'answer' key.\n"
        'Example: [{"question": "What is mitochondria?", "answer": "The powerhouse of the cell."}]'
    )

    raw = await _complete(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.3, max_tokens=1500
    )
    try:
        cards = json.loads(clean_json(raw))
        if not isinstance(cards, list):
            cards = [{"question": "Failed to parse", "answer": "AI did not return a list."}]
    except Exception:
        cards = [{"question": "Error", "answer": "Could not extract flashcards from note."}]

    return {"success": True, "cards": cards}


# ──────────────────────────────────────────────
# 5. EXPLAIN CONCEPT (NEW)
# ──────────────────────────────────────────────
@router.post("/explain")
async def explain_concept(body: ExplainConceptRequest, current_user: dict = Depends(get_current_user)):
    _complete, clean_json = _ai()

    subj = f" in the context of {body.subject}" if body.subject else ""
    level_map = {
        "beginner":      "Explain as if to a 10-year-old with no background knowledge.",
        "high_school":   "Explain at a high school level with clear examples.",
        "undergraduate": "Explain at a university undergraduate level with technical accuracy.",
        "advanced":      "Explain at a graduate/research level with full technical depth.",
    }
    level_hint = level_map.get(body.level, level_map["undergraduate"])

    system = "You are a brilliant professor who can explain any concept with perfect clarity."
    user = (
        f"Explain '{body.concept}'{subj}. {level_hint}\n\n"
        "RETURN ONLY valid JSON:\n"
        '{"concept":"...","level":"...","simple_explanation":"...","detailed_explanation":"...",'
        '"analogy":"...","key_points":["..."],"common_misconceptions":["..."],'
        '"real_world_examples":["..."],"related_concepts":["..."]}'
    )

    raw = await _complete(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.5, max_tokens=1500
    )
    try:
        data = json.loads(clean_json(raw))
    except Exception:
        data = {"concept": body.concept, "simple_explanation": raw}

    return {"success": True, "data": data}
