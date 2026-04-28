from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os, shutil, psutil, json
from typing import List, Optional
from datetime import datetime
import subprocess

router = APIRouter()

ADMIN_USER = "Nameless_General"
ADMIN_PASS = "()@10987654321"
SITE_CONFIG_PATH = "site_config.json"

def _load_config():
    if os.path.exists(SITE_CONFIG_PATH):
        with open(SITE_CONFIG_PATH, "r") as f:
            return json.load(f)
    return {
        "site_title": "MonkeyMind AI",
        "tagline": "Your intelligent study companion",
        "logo_emoji": "🐒",
        "accent_color": "#00f2ff",
        "bg_color": "#060608",
        "hero_text": "Study Smarter, Not Harder",
        "hero_subtext": "AI-powered flashcards, notes, and study groups — all in one place.",
        "announcement": "",
        "announcement_enabled": False,
        "announcement_color": "#ff9800",
        "features_section": [
            {"icon": "🧠", "title": "AI Study Assistant", "desc": "Ask @monky anything, anytime"},
            {"icon": "📚", "title": "Smart Flashcards", "desc": "Spaced repetition that actually works"},
            {"icon": "👥", "title": "Study Groups", "desc": "Collaborate and learn together"}
        ],
        "footer_text": "© 2026 MonkeyMind AI. Built for students, by students.",
        "show_streak": True,
        "show_gpa": True
    }

def _save_config(cfg: dict):
    with open(SITE_CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

class AdminLogin(BaseModel):
    username: str
    password: str

class FileEdit(BaseModel):
    path: str
    content: str

class SiteConfig(BaseModel):
    site_title: str
    tagline: str
    logo_emoji: str
    accent_color: str
    bg_color: str
    hero_text: str
    hero_subtext: str
    announcement: str
    announcement_enabled: bool
    announcement_color: str
    footer_text: str
    show_streak: bool
    show_gpa: bool

class BanPayload(BaseModel):
    user_id: str

class KickPayload(BaseModel):
    user_id: str
    group_id: Optional[str] = None

class DeleteGroupPayload(BaseModel):
    group_id: str

class AnnouncementPayload(BaseModel):
    message: str
    color: str = "#ff9800"
    enabled: bool = True

_banned_users: set = set()

@router.post("/login")
async def login(data: AdminLogin):
    if data.username == ADMIN_USER and data.password == ADMIN_PASS:
        return {"success": True, "token": "dev_root_access_granted"}
    raise HTTPException(status_code=401, detail="Unauthorized")

@router.get("/site-config")
async def get_site_config():
    return _load_config()

@router.post("/site-config")
async def update_site_config(cfg: SiteConfig):
    existing = _load_config()
    existing.update(cfg.dict())
    _save_config(existing)
    return {"success": True, "config": existing}

@router.post("/announcement")
async def set_announcement(payload: AnnouncementPayload):
    cfg = _load_config()
    cfg["announcement"] = payload.message
    cfg["announcement_color"] = payload.color
    cfg["announcement_enabled"] = payload.enabled
    _save_config(cfg)
    return {"success": True}

@router.get("/stats")
async def get_stats():
    try:
        return {
            "cpu": psutil.cpu_percent(),
            "memory": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage('.').percent,
            "uptime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except:
        return {"cpu": 0, "memory": 0, "disk": 0, "uptime": "Unknown"}

class TerminalCommand(BaseModel):
    command: str

@router.post("/terminal")
async def run_terminal(data: TerminalCommand):
    try:
        # Run command securely
        result = subprocess.run(
            data.command, 
            shell=True, 
            cwd=".", 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        output = result.stdout if result.stdout else ""
        error = result.stderr if result.stderr else ""
        return {"output": output + error, "exit_code": result.returncode}
    except subprocess.TimeoutExpired:
        return {"output": "Command timed out after 10 seconds", "exit_code": -1}
    except Exception as e:
        return {"output": str(e), "exit_code": -1}

@router.get("/files")
async def list_files(path: str = "."):
    try:
        target_path = os.path.abspath(path)
        if not os.path.exists(target_path):
            target_path = "."
        items = []
        for item in os.listdir(target_path):
            full_path = os.path.join(target_path, item)
            try:
                is_dir = os.path.isdir(full_path)
                items.append({"name": item, "path": full_path, "isDir": is_dir,
                               "size": 0 if is_dir else os.path.getsize(full_path)})
            except:
                continue
        return {"items": items, "current_path": target_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/file/content")
async def get_file_content(path: str):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return {"content": f.read()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/file/save")
async def save_file(data: FileEdit):
    try:
        if os.path.exists(data.path):
            shutil.copy2(data.path, data.path + ".bak")
        with open(data.path, "w", encoding="utf-8") as f:
            f.write(data.content)
        return {"success": True, "message": "File saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _get_social():
    try:
        import app.routes.social as s
        return s._users, s._friends, s._groups, s._messages
    except:
        return {}, {}, [], []

@router.get("/users")
async def list_users():
    users, friends, groups, messages = _get_social()
    result = []
    for email, u in users.items():
        friend_count = len(friends.get(u["id"], []))
        group_count = sum(1 for g in groups if any(m.user_id == u["id"] for m in g.members))
        msg_count = sum(1 for m in messages if m.sender_id == u["id"] and not m.is_ai)
        user_groups = [{"id": g.id, "name": g.name} for g in groups if any(m.user_id == u["id"] for m in g.members)]
        result.append({
            "id": u["id"],
            "name": u["name"],
            "email": email,
            "friend_count": friend_count,
            "group_count": group_count,
            "message_count": msg_count,
            "groups": user_groups,
            "banned": u["id"] in _banned_users,
            "joined": u.get("joined", "Demo session")
        })
    return {"users": result, "total": len(result)}

@router.get("/users/{user_id}/details")
async def get_user_details(user_id: str):
    users, friends, groups, messages = _get_social_store()
    
    target_user = None
    for email, u in users.items():
        if u["id"] == user_id:
            target_user = u
            break
            
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user_friends = friends.get(user_id, [])
    user_groups = [{"id": g.id, "name": g.name} for g in groups if any(m.user_id == user_id for m in g.members)]
    
    return {
        "info": target_user,
        "friends": user_friends,
        "groups": user_groups,
        "banned": user_id in _banned_users
    }

@router.post("/users/ban")
async def ban_user(payload: BanPayload):
    _banned_users.add(payload.user_id)
    return {"success": True, "message": f"User {payload.user_id} banned"}

@router.post("/users/unban")
async def unban_user(payload: BanPayload):
    _banned_users.discard(payload.user_id)
    return {"success": True, "message": f"User {payload.user_id} unbanned"}

@router.post("/users/kick")
async def kick_user(payload: KickPayload):
    import app.routes.social as social
    kicked = []
    if payload.group_id:
        for g in social._groups:
            if g.id == payload.group_id:
                before = len(g.members)
                g.members = [m for m in g.members if m.user_id != payload.user_id]
                if len(g.members) < before:
                    kicked.append(g.name)
    else:
        for g in social._groups:
            before = len(g.members)
            g.members = [m for m in g.members if m.user_id != payload.user_id]
            if len(g.members) < before:
                kicked.append(g.name)
        if payload.user_id in social._friends:
            social._friends[payload.user_id] = []
        for uid in list(social._friends.keys()):
            social._friends[uid] = [f for f in social._friends[uid] if f["id"] != payload.user_id]
        kicked.append("all friendships removed")
    return {"success": True, "kicked_from": kicked}

@router.get("/groups")
async def admin_list_groups():
    users, friends, groups, messages = _get_social()
    result = []
    for g in groups:
        msg_count = sum(1 for m in messages if m.group_id == g.id)
        result.append({
            "id": g.id,
            "name": g.name,
            "member_count": len(g.members),
            "members": [{"id": m.user_id, "name": m.name} for m in g.members],
            "message_count": msg_count,
            "created_at": g.created_at.isoformat()
        })
    return {"groups": result}

@router.post("/groups/delete")
async def delete_group(payload: DeleteGroupPayload):
    import app.routes.social as social
    before = len(social._groups)
    social._groups = [g for g in social._groups if g.id != payload.group_id]
    if len(social._groups) < before:
        return {"success": True, "message": "Group deleted"}
    raise HTTPException(status_code=404, detail="Group not found")
