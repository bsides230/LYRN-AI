from fastapi import APIRouter, HTTPException, Query, Body, Request
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from core.security import verify_token
from services.verbatim_memory import (
    create_or_load_conversation,
    save_chat_pair,
    update_summary,
    update_chat_pair,
    delete_chat_pair,
    delete_block,
    delete_conversation,
    clear_conversation,
    get_convo_list,
    get_blocks,
    get_block,
    get_chat_pair
)

router = APIRouter(prefix="/api/memory/verbatim", tags=["verbatim"])

# Pydantic models for incoming requests
class ChatPairCreate(BaseModel):
    input_text: str
    output_text: str

class SummaryUpdate(BaseModel):
    summary_text: str

class ChatPairUpdate(BaseModel):
    input_text: str
    output_text: str

# 1. CONVERSATION VIEW endpoints

@router.get("/convos")
async def list_conversations(request: Request):
    await verify_token(request)
    convos = get_convo_list()
    return {"status": "success", "data": convos}

@router.post("/convos/{convo_id}")
async def load_conversation(convo_id: str, request: Request):
    await verify_token(request)
    meta = create_or_load_conversation(convo_id)
    return {"status": "success", "data": meta}

@router.delete("/convos/{convo_id}")
async def hard_delete_conversation(convo_id: str, request: Request, confirm: bool = Query(False)):
    await verify_token(request)
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation required to delete conversation")
    success = delete_conversation(convo_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success", "message": f"Conversation {convo_id} deleted."}

@router.post("/convos/{convo_id}/clear")
async def clear_all_blocks(convo_id: str, request: Request, confirm: bool = Query(False)):
    await verify_token(request)
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation required to clear conversation")
    success = clear_conversation(convo_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success", "message": f"Conversation {convo_id} cleared."}

# 2. BLOCK VIEW endpoints

@router.get("/convos/{convo_id}/blocks")
async def list_blocks(convo_id: str, request: Request):
    await verify_token(request)
    blocks = get_blocks(convo_id)
    return {"status": "success", "data": blocks}

@router.delete("/convos/{convo_id}/blocks/{block_id}")
async def remove_block(convo_id: str, block_id: int, request: Request, confirm: bool = Query(False)):
    await verify_token(request)
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation required to delete block")
    success = delete_block(convo_id, block_id)
    if not success:
        raise HTTPException(status_code=404, detail="Block not found")
    return {"status": "success", "message": f"Block {block_id} deleted."}

# 3. CHAT PAIR VIEW endpoints

@router.get("/convos/{convo_id}/blocks/{block_id}")
async def view_block(convo_id: str, block_id: int, request: Request):
    await verify_token(request)
    rows = get_block(convo_id, block_id)
    return {"status": "success", "data": rows}

@router.post("/convos/{convo_id}/pairs")
async def add_chat_pair(convo_id: str, data: ChatPairCreate, request: Request):
    await verify_token(request)
    pair_id = save_chat_pair(convo_id, data.input_text, data.output_text)
    return {"status": "success", "data": {"pair_id": pair_id}}

@router.get("/convos/{convo_id}/blocks/{block_id}/pairs/{row_id}")
async def view_chat_pair(convo_id: str, block_id: int, row_id: int, request: Request):
    await verify_token(request)
    pair = get_chat_pair(convo_id, block_id, row_id)
    if not pair:
        raise HTTPException(status_code=404, detail="Chat pair not found")
    return {"status": "success", "data": pair}

@router.put("/convos/{convo_id}/blocks/{block_id}/pairs/{row_id}")
async def edit_chat_pair(convo_id: str, block_id: int, row_id: int, data: ChatPairUpdate, request: Request):
    await verify_token(request)
    success = update_chat_pair(convo_id, block_id, row_id, data.input_text, data.output_text)
    if not success:
        raise HTTPException(status_code=404, detail="Chat pair not found")
    return {"status": "success", "message": "Chat pair updated"}

@router.patch("/convos/{convo_id}/blocks/{block_id}/pairs/{row_id}/summary")
async def edit_summary(convo_id: str, block_id: int, row_id: int, data: SummaryUpdate, request: Request):
    await verify_token(request)
    success = update_summary(convo_id, block_id, row_id, data.summary_text)
    if not success:
        raise HTTPException(status_code=404, detail="Chat pair not found")
    return {"status": "success", "message": "Summary updated"}

@router.delete("/convos/{convo_id}/blocks/{block_id}/pairs/{row_id}")
async def remove_chat_pair(convo_id: str, block_id: int, row_id: int, request: Request, confirm: bool = Query(False)):
    await verify_token(request)
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation required to delete chat pair")
    success = delete_chat_pair(convo_id, block_id, row_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat pair not found")
    return {"status": "success", "message": "Chat pair deleted"}
