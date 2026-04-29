"""
Pydantic v2 schemas for all domain objects.
Each section maps to a MongoDB collection.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator
from enum import Enum


# ── Shared ─────────────────────────────────────────────────────────────────────
class PyObjectId(str):
    """Serialisable MongoDB ObjectId."""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        return str(v)


class BaseResponse(BaseModel):
    success: bool = True
    message: str = "OK"


# ── User ───────────────────────────────────────────────────────────────────────
class SubjectProgress(BaseModel):
    name: str
    progress: float = Field(0.0, ge=0, le=100)

class UserPreferences(BaseModel):
    study_reminders: bool = True
    theme: str = "light"
    daily_goal_hours: float = 4.0

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str = "student"
    gpa: Optional[float] = None
    streak: int = 0
    subjects: List[SubjectProgress] = []
    preferences: UserPreferences = UserPreferences()
    created_at: Optional[datetime] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    gpa: Optional[float] = Field(None, ge=0.0, le=4.0)
    subjects: Optional[List[SubjectProgress]] = None
    preferences: Optional[UserPreferences] = None


# ── Task ───────────────────────────────────────────────────────────────────────
class Priority(str, Enum):
    low    = "low"
    medium = "medium"
    high   = "high"

class TaskStatus(str, Enum):
    pending     = "pending"
    in_progress = "in_progress"
    done        = "done"

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    subject: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Priority = Priority.medium
    tags: List[str] = []
    estimated_minutes: Optional[int] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    subject: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[Priority] = None
    status: Optional[TaskStatus] = None
    tags: Optional[List[str]] = None
    estimated_minutes: Optional[int] = None

class TaskOut(TaskCreate):
    id: str
    user_id: str
    status: TaskStatus = TaskStatus.pending
    ai_suggested: bool = False
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    # ── ML: predicted difficulty score (0-1) populated by ML service ─────────
    difficulty_score: Optional[float] = None
    # ─────────────────────────────────────────────────────────────────────────


# ── Schedule ───────────────────────────────────────────────────────────────────
class EventType(str, Enum):
    cls    = "class"
    study  = "study"
    exam   = "exam"
    other  = "other"

class ScheduleCreate(BaseModel):
    title: str = Field(..., min_length=1)
    subject: Optional[str] = None
    type: EventType = EventType.study
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    recurring: bool = False
    color: str = "#7F77DD"
    ai_scheduled: bool = False
    notes: Optional[str] = None

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, v, info):
        if info.data.get("start_time") and v <= info.data["start_time"]:
            raise ValueError("end_time must be after start_time")
        return v

class ScheduleOut(ScheduleCreate):
    id: str
    user_id: str
    created_at: Optional[datetime] = None


# ── Flashcard ──────────────────────────────────────────────────────────────────
class ReviewResult(str, Enum):
    again = "again"
    hard  = "hard"
    good  = "good"
    easy  = "easy"

class FlashcardCreate(BaseModel):
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    subject: Optional[str] = None
    tags: List[str] = []
    ai_generated: bool = False
    source_note_id: Optional[str] = None
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "question": "What is the powerhouse of the cell?",
                    "answer": "Mitochondria",
                    "subject": "Biology",
                    "tags": ["biology", "cell"]
                }
            ]
        }
    }

class FlashcardOut(FlashcardCreate):
    id: str
    user_id: str
    ease_factor: float = 2.5
    interval: int = 1          # days until next review
    repetitions: int = 0
    next_review: Optional[datetime] = None
    last_result: Optional[str] = None
    created_at: Optional[datetime] = None
    # ── ML: predicted retention probability ──────────────────────────────────
    retention_probability: Optional[float] = None
    # ─────────────────────────────────────────────────────────────────────────

class ReviewSubmit(BaseModel):
    result: ReviewResult

class BulkFlashcardsCreate(BaseModel):
    cards: List[FlashcardCreate]


# ── Note ───────────────────────────────────────────────────────────────────────
class NoteCreate(BaseModel):
    title: str = "Untitled Note"
    content: str = Field(..., min_length=1)
    subject: Optional[str] = None
    tags: List[str] = []
    is_pinned: bool = False

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    subject: Optional[str] = None
    tags: Optional[List[str]] = None
    is_pinned: Optional[bool] = None
    ai_summary: Optional[str] = None
    key_points: Optional[List[str]] = None

class NoteOut(NoteCreate):
    id: str
    user_id: str
    word_count: int = 0
    ai_summary: Optional[str] = None
    key_points: List[str] = []
    # ── ML: topic cluster label ───────────────────────────────────────────────
    topic_cluster: Optional[str] = None
    # ─────────────────────────────────────────────────────────────────────────
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ── AI payloads ────────────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    subject: Optional[str] = None
    history: List[ChatMessage] = []
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "What is photosynthesis?",
                    "subject": "Biology",
                    "history": []
                }
            ]
        }
    }

class SummarizeRequest(BaseModel):
    content: str = Field(..., min_length=10)
    subject: Optional[str] = None
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "content": "Photosynthesis is the process by which plants use sunlight, water and CO2 to produce oxygen and energy in the form of sugar.",
                    "subject": "Biology"
                }
            ]
        }
    }

class GenerateFlashcardsRequest(BaseModel):
    content: str = Field(..., min_length=10)
    subject: Optional[str] = None
    count: int = Field(8, ge=1, le=20)
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "content": "Photosynthesis is the process by which plants use sunlight, water and CO2 to produce oxygen and energy in the form of sugar.",
                    "count": 5
                }
            ]
        }
    }

class ScheduleSuggestionRequest(BaseModel):
    tasks: List[Any] = []
    existing_events: List[Any] = []
    preferences: dict = {}
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tasks": [],
                    "existing_events": [],
                    "preferences": {}
                }
            ]
        }
    }


# ── ML payloads ────────────────────────────────────────────────────────────────
class StudyPatternRequest(BaseModel):
    """Input features for the study pattern / optimal time predictor."""
    study_hours: List[float]          # hours studied each day (last 14 days)
    completion_rates: List[float]     # task completion rate per day (0–1)
    subjects: List[str]               # subjects studied each day

class StudyPatternResponse(BaseModel):
    optimal_study_hours: List[int]    # e.g. [20, 21, 22] → 8–10 PM
    predicted_productivity: float     # 0–1 score
    recommended_break_interval: int   # minutes

class DifficultyPredictRequest(BaseModel):
    """Features for task difficulty scorer."""
    title: str
    subject: Optional[str] = None
    estimated_minutes: Optional[int] = None
    tags: List[str] = []

class DifficultyPredictResponse(BaseModel):
    difficulty_score: float           # 0–1
    difficulty_label: str             # "easy" | "medium" | "hard"
    suggested_minutes: int

class RetentionPredictRequest(BaseModel):
    """Features for flashcard retention predictor (forgetting curve)."""
    ease_factor: float
    interval: int
    repetitions: int
    last_result: Optional[str]

class RetentionPredictResponse(BaseModel):
    retention_probability: float      # 0–1
    should_review_now: bool
    next_review_days: int

# ── Social ─────────────────────────────────────────────────────────────────────
class FriendRequestStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"

class FriendRequest(BaseModel):
    id: str
    sender_id: str
    sender_name: str
    receiver_id: str
    status: FriendRequestStatus = FriendRequestStatus.pending
    created_at: datetime = Field(default_factory=datetime.utcnow)

class GroupMember(BaseModel):
    user_id: str
    name: str

class StudyGroup(BaseModel):
    id: str
    name: str
    members: List[GroupMember] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ChatMessage(BaseModel):
    id: str
    group_id: Optional[str] = None
    receiver_id: Optional[str] = None # For DMs
    sender_id: str
    sender_name: str
    content: str
    is_ai: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)
