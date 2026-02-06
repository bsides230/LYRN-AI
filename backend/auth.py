import os
import secrets
import time
from pathlib import Path
from typing import Optional, Dict
from fastapi import Header, HTTPException, Depends

# Global Token
ADMIN_TOKEN: Optional[str] = None

# Short-lived session keys: {key: expiry_timestamp}
SESSION_KEYS: Dict[str, float] = {}

def load_token():
    global ADMIN_TOKEN
    # 1. Try admin_token.txt in CWD
    token_file = Path("admin_token.txt")
    if token_file.exists():
        try:
            ADMIN_TOKEN = token_file.read_text(encoding="utf-8").strip()
            print("[Auth] Loaded admin token from admin_token.txt")
            return
        except Exception as e:
            print(f"[Auth] Failed to read admin_token.txt: {e}")

    # 2. Try Env Var
    ADMIN_TOKEN = os.environ.get("LYRN_MODEL_TOKEN") or os.environ.get("REMODASH_TOKEN")
    if ADMIN_TOKEN:
        print("[Auth] Loaded admin token from Environment Variable")
    else:
        print("[Auth] Warning: No admin token found.")

async def verify_token(x_token: Optional[str] = Header(None, alias="X-Token"), token: Optional[str] = None, key: Optional[str] = None):
    # Check for No Auth Flag in global_flags/no_auth
    if Path("global_flags/no_auth").exists():
        return "NO_AUTH"

    # 1. Check Session Key (Preferred for WS/SSE)
    if key:
        expiry = SESSION_KEYS.get(key)
        if expiry and time.time() < expiry:
            return "SESSION_KEY_VALID"

    # 2. Check Standard Token
    auth_token = x_token or token
    if not ADMIN_TOKEN or not auth_token or auth_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return auth_token

def create_session_key(duration=60):
    key = secrets.token_urlsafe(32)
    SESSION_KEYS[key] = time.time() + duration

    # Cleanup
    expired = [k for k, exp in SESSION_KEYS.items() if time.time() > exp]
    for k in expired:
        del SESSION_KEYS[k]

    return key
