import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

_use_supabase = bool(SUPABASE_URL and SUPABASE_KEY)

# fallback in-memory store (used when Supabase not configured)
_fallback_users: dict = {}  # email -> { password_hash, name, ... }
_fallback_sessions: dict = {}  # token -> email
_fallback_profiles: dict = {}  # email -> profile dict


def _hash_password(pw: str) -> str:
    return hashlib.sha256((pw + "mf_salt_2024").encode()).hexdigest()


def _gen_token() -> str:
    return secrets.token_hex(32)


async def signup(email: str, password: str, name: str) -> dict:
    if _use_supabase:
        try:
            from supabase import create_client
            client = create_client(SUPABASE_URL, SUPABASE_KEY)
            resp = client.auth.sign_up({"email": email, "password": password})
            return {"ok": True, "user_id": resp.user.id, "email": email}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    else:
        email_l = email.lower().strip()
        if email_l in _fallback_users:
            return {"ok": False, "error": "Email already registered"}
        _fallback_users[email_l] = {
            "password_hash": _hash_password(password),
            "name": name,
            "created_at": datetime.utcnow().isoformat(),
        }
        _fallback_profiles[email_l] = {}
        return {"ok": True, "user_id": email_l, "email": email_l}


async def login(email: str, password: str) -> dict:
    if _use_supabase:
        try:
            from supabase import create_client
            client = create_client(SUPABASE_URL, SUPABASE_KEY)
            resp = client.auth.sign_in_with_password({"email": email, "password": password})
            session = resp.session
            return {"ok": True, "token": session.access_token, "email": email, "user_id": resp.user.id}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    else:
        email_l = email.lower().strip()
        user = _fallback_users.get(email_l)
        if not user or user["password_hash"] != _hash_password(password):
            return {"ok": False, "error": "Invalid email or password"}
        token = _gen_token()
        _fallback_sessions[token] = {
            "email": email_l,
            "created_at": datetime.utcnow().isoformat(),
        }
        return {"ok": True, "token": token, "email": email_l, "user_id": email_l}


async def logout(token: str) -> dict:
    if _use_supabase:
        try:
            from supabase import create_client
            client = create_client(SUPABASE_URL, SUPABASE_KEY)
            client.auth.sign_out()
        except Exception:
            pass
        return {"ok": True}
    else:
        _fallback_sessions.pop(token, None)
        return {"ok": True}


async def get_user_by_token(token: str) -> dict | None:
    if not token:
        return None
    if _use_supabase:
        try:
            from supabase import create_client
            client = create_client(SUPABASE_URL, SUPABASE_KEY)
            resp = client.auth.get_user(token)
            user = resp.user
            if user:
                return {"email": user.email, "user_id": user.id, "name": user.user_metadata.get("full_name", "")}
        except Exception:
            pass
        return None
    else:
        session = _fallback_sessions.get(token)
        if not session:
            return None
        email = session["email"]
        user = _fallback_users.get(email)
        if not user:
            return None
        return {"email": email, "user_id": email, "name": user.get("name", "")}


async def save_profile(email: str, profile_data: dict) -> dict:
    if _use_supabase:
        try:
            from supabase import create_client
            client = create_client(SUPABASE_URL, SUPABASE_KEY)
            client.table("profiles").upsert({
                "email": email,
                "profile": json.dumps(profile_data),
                "updated_at": datetime.utcnow().isoformat(),
            }).execute()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    else:
        _fallback_profiles[email] = dict(profile_data)
        return {"ok": True}


async def load_profile(email: str) -> dict | None:
    if _use_supabase:
        try:
            from supabase import create_client
            client = create_client(SUPABASE_URL, SUPABASE_KEY)
            resp = client.table("profiles").select("profile").eq("email", email).execute()
            if resp.data and len(resp.data) > 0:
                return json.loads(resp.data[0]["profile"])
        except Exception:
            pass
        return None
    else:
        return _fallback_profiles.get(email)


async def save_income_record(email: str, record: dict) -> dict:
    if _use_supabase:
        try:
            from supabase import create_client
            client = create_client(SUPABASE_URL, SUPABASE_KEY)
            client.table("income").insert({
                "email": email,
                "data": json.dumps(record),
                "created_at": datetime.utcnow().isoformat(),
            }).execute()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    else:
        key = f"income_{email}"
        records = _fallback_profiles.get(key, [])
        records.append(record)
        _fallback_profiles[key] = records
        return {"ok": True}


async def load_income_records(email: str) -> list:
    if _use_supabase:
        try:
            from supabase import create_client
            client = create_client(SUPABASE_URL, SUPABASE_KEY)
            resp = client.table("income").select("data").eq("email", email).order("created_at", desc=True).execute()
            if resp.data:
                return [json.loads(r["data"]) for r in resp.data]
        except Exception:
            pass
        return []
    else:
        key = f"income_{email}"
        return _fallback_profiles.get(key, [])
