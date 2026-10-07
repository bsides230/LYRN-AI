import os
from pathlib import Path
from typing import Optional
from fastapi import Header, HTTPException

import core.state as state

async def verify_token(x_token: Optional[str] = Header(None, alias="X-Token"), token: Optional[str] = None):
    # Check for No Auth Flag
    if Path("global_flags/no_auth").exists():
        return "NO_AUTH"

    # Support both Header (preferred) and Query Param (SSE/EventSource)
    auth_token = x_token or token
    if not state.LYRN_TOKEN or not auth_token or auth_token != state.LYRN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return auth_token
