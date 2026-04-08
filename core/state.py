import asyncio
from typing import Optional, Dict, Any

# Global reference to the main event loop
main_loop: Optional[asyncio.AbstractEventLoop] = None
LYRN_TOKEN: Optional[str] = None

# Global LLM Stats (populated from log parsing)
extended_llm_stats = {
    "kv_cache_reused": 0,
    "prompt_tokens": 0,
    "prompt_speed": 0.0,
    "eval_tokens": 0,
    "eval_speed": 0.0,
    "total_tokens": 0,
    "load_time": 0.0,
    "total_time": 0.0,
    "tokenization_time_ms": 0.0,
    "generation_time_ms": 0.0
}

# Global Active Downloads
active_downloads: Dict[str, Dict[str, Any]] = {} # filename -> { status, bytes, total, pct, error, timestamp }
