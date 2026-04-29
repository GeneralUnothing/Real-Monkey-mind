from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid
import json

from app.models import FriendRequest, StudyGroup, ChatMessage, GroupMember, FriendRequestStatus
from app.routes.ai import _complete

router = APIRouter()

# ── IN-MEMORY DATABASES (For Demo Mode) ────────────────────────────────────────
_users = {
    # email -> user dict. Automatically populated on first access.
    "demo@monkeymind.ai": {"id": "demo_id", "name": "Demo User", "email": "demo@monkeymind.ai"}
}
_friend_requests = []
_friends = {} # user_id -> List[dict]
_groups = []
_messages = []

# Mock auth dependency
async def get_current_user_mock(email: str = "demo@monkeymind.ai"):
    # In a real app this uses the token. Here we accept a query param or default.
    return _users.get(email, {"id": f"u_{uuid.uuid4().hex[:8]}", "name": email.split("@")[0], "email": email})

# ── 1. FRIENDS ─────────────────────────────────────────────────────────────────
class FriendRequestPayload(BaseModel):
    receiver_email: str
    sender_email: str

@router.post("/friends/request")
async def send_friend_request(payload: FriendRequestPayload):
    sender_email = payload.sender_email.lower()
    receiver_email = payload.receiver_email.lower()

    # Auto-register users if not exist
    if sender_email not in _users:
        _users[sender_email] = {"id": f"u_{uuid.uuid4().hex[:8]}", "name": payload.sender_email.split("@")[0], "email": sender_email}
    if receiver_email not in _users:
        _users[receiver_email] = {"id": f"u_{uuid.uuid4().hex[:8]}", "name": payload.receiver_email.split("@")[0], "email": receiver_email}
    
    sender = _users[sender_email]
    receiver = _users[receiver_email]

    req = FriendRequest(
        id=str(uuid.uuid4()),
        sender_id=sender["id"],
        sender_name=sender["name"],
        receiver_id=receiver["id"],
    )
    _friend_requests.append(req)
    return {"success": True, "data": req}

@router.get("/friends/requests")
async def get_requests(email: str):
    email = email.lower()
    if email not in _users: return {"requests": []}
    uid = _users[email]["id"]
    reqs = [r for r in _friend_requests if r.receiver_id == uid and r.status == FriendRequestStatus.pending]
    return {"requests": reqs}

@router.post("/friends/accept/{req_id}")
async def accept_request(req_id: str):
    for r in _friend_requests:
        if r.id == req_id:
            r.status = FriendRequestStatus.accepted
            # Add to friends list bidirectionally
            if r.sender_id not in _friends: _friends[r.sender_id] = []
            if r.receiver_id not in _friends: _friends[r.receiver_id] = []
            
            _friends[r.sender_id].append({"id": r.receiver_id, "name": "Friend"}) # Will resolve real name in GET
            _friends[r.receiver_id].append({"id": r.sender_id, "name": r.sender_name})
            return {"success": True}
    raise HTTPException(status_code=404, detail="Request not found")

@router.get("/friends")
async def list_friends(email: str):
    email = email.lower()
    if email not in _users: return {"friends": []}
    uid = _users[email]["id"]
    friend_ids = [f["id"] for f in _friends.get(uid, [])]
    
    # Resolve full names from _users
    result = []
    for f_id in friend_ids:
        for u in _users.values():
            if u["id"] == f_id:
                result.append({"id": u["id"], "name": u["name"], "email": u["email"]})
                break
    return {"friends": result}

# ── 2. STUDY GROUPS ────────────────────────────────────────────────────────────
class CreateGroupPayload(BaseModel):
    name: str
    creator_email: str

@router.post("/groups")
async def create_group(payload: CreateGroupPayload):
    if payload.creator_email not in _users:
        _users[payload.creator_email] = {"id": f"u_{uuid.uuid4().hex[:8]}", "name": payload.creator_email.split("@")[0], "email": payload.creator_email}
    creator = _users[payload.creator_email]
    
    g = StudyGroup(
        id=f"g_{uuid.uuid4().hex[:8]}",
        name=payload.name,
        members=[GroupMember(user_id=creator["id"], name=creator["name"])]
    )
    _groups.append(g)
    return {"success": True, "data": g}

class InviteGroupPayload(BaseModel):
    group_id: str
    friend_id: str

@router.post("/groups/invite")
async def invite_to_group(payload: InviteGroupPayload):
    for g in _groups:
        if g.id == payload.group_id:
            # Find friend details
            friend_name = "User"
            for u in _users.values():
                if u["id"] == payload.friend_id: friend_name = u["name"]
            
            # Add if not already there
            if not any(m.user_id == payload.friend_id for m in g.members):
                g.members.append(GroupMember(user_id=payload.friend_id, name=friend_name))
            return {"success": True, "group": g}
    raise HTTPException(status_code=404, detail="Group not found")

@router.get("/groups")
async def list_groups(email: str):
    email = email.lower()
    if email not in _users: return {"groups": []}
    uid = _users[email]["id"]
    my_groups = [g for g in _groups if any(m.user_id == uid for m in g.members)]
    return {"groups": my_groups}

# ── 3. MESSAGING & AI INTEGRATION ──────────────────────────────────────────────
class SendMessagePayload(BaseModel):
    sender_email: str
    content: str
    group_id: Optional[str] = None
    receiver_id: Optional[str] = None

async def process_monky_ai(msg: ChatMessage, context_messages: List[ChatMessage]):
    # AI logic runs in background
    system_prompt = (
        "You are @monky, MonkeyMind AI. You are in a study group chat or DM with students. "
        "Keep responses brief, punchy, technically accurate, and a bit snarky/monkey-like. "
        "Explain topics clearly or generate quizzes if asked."
    )
    
    # Format context
    history = []
    for m in context_messages[-10:]: # last 10
        role = "assistant" if m.is_ai else "user"
        prefix = "" if m.is_ai else f"[{m.sender_name}]: "
        history.append({"role": role, "content": prefix + m.content})
        
    try:
        reply_content = await _complete(
            messages=[{"role": "system", "content": system_prompt}] + history,
            temperature=0.7, max_tokens=400
        )
        
        ai_msg = ChatMessage(
            id=str(uuid.uuid4()),
            group_id=msg.group_id,
            receiver_id=msg.receiver_id if msg.receiver_id else msg.sender_id, # If DM, reply to the thread
            sender_id="ai_monky",
            sender_name="MonkeyMind AI",
            content=reply_content,
            is_ai=True
        )
        # If it was a DM, make sure both sides can see it. We'll set receiver to sender if it's a DM, 
        # but wait, DM threads are fetched by combining sender/receiver. 
        # Let's assign receiver_id to the OTHER person in the DM if possible, or just the thread owner.
        if msg.receiver_id:
            # AI sends message TO the person who didn't trigger it? No, just attach it to the same thread.
            ai_msg.receiver_id = msg.receiver_id
            ai_msg.sender_id = msg.sender_id # Keep thread same, but mark is_ai = True
            
        _messages.append(ai_msg)
    except Exception as e:
        print("AI Error:", e)

@router.post("/messages")
async def send_message(payload: SendMessagePayload, background_tasks: BackgroundTasks):
    if payload.sender_email not in _users:
        _users[payload.sender_email] = {"id": f"u_{uuid.uuid4().hex[:8]}", "name": payload.sender_email.split("@")[0], "email": payload.sender_email}
    sender = _users[payload.sender_email]
    
    msg = ChatMessage(
        id=str(uuid.uuid4()),
        group_id=payload.group_id,
        receiver_id=payload.receiver_id,
        sender_id=sender["id"],
        sender_name=sender["name"],
        content=payload.content
    )
    _messages.append(msg)
    
    # Check for AI trigger
    if "@monky" in payload.content.lower():
        # Get context
        context = []
        if payload.group_id:
            context = [m for m in _messages if m.group_id == payload.group_id]
        elif payload.receiver_id:
            context = [m for m in _messages if not m.group_id and 
                       ((m.sender_id == sender["id"] and m.receiver_id == payload.receiver_id) or 
                        (m.sender_id == payload.receiver_id and m.receiver_id == sender["id"]))]
        
        background_tasks.add_task(process_monky_ai, msg, context)
        
    return {"success": True, "data": msg}

@router.get("/messages/group/{group_id}")
async def get_group_messages(group_id: str):
    msgs = [m for m in _messages if m.group_id == group_id]
    return {"messages": sorted(msgs, key=lambda x: x.timestamp)}

@router.get("/messages/dm/{friend_id}")
async def get_dm_messages(friend_id: str, email: str):
    email = email.lower()
    if email not in _users: return {"messages": []}
    my_id = _users[email]["id"]
    
    msgs = [m for m in _messages if not m.group_id and 
            ((m.sender_id == my_id and m.receiver_id == friend_id) or 
             (m.sender_id == friend_id and m.receiver_id == my_id) or
             # Also include AI messages in this thread
             (m.is_ai and m.sender_id == my_id and m.receiver_id == friend_id) or
             (m.is_ai and m.sender_id == friend_id and m.receiver_id == my_id))]
             
    return {"messages": sorted(msgs, key=lambda x: x.timestamp)}
