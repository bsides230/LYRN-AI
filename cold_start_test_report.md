# LYRN Cold Start Test Report

**Date:** 2026-03-19
**Model:** Qwen.Qwen3-0.6B.Q8_0.gguf (Q8_0, 805MB)
**Source:** https://huggingface.co/DevQuasar/Qwen.Qwen3-0.6B-GGUF/resolve/main/Qwen.Qwen3-0.6B.Q8_0.gguf
**Environment:** Linux x86_64, Python 3.11.14, CPU-only (no GPU)

---

## A. EXECUTIVE SUMMARY

| Step | Result |
|------|--------|
| Venv creation | PASS |
| Dependency install | PASS |
| Backend boot | PASS |
| UI accessible | PASS |
| Model download (UI) | PARTIAL - UI flow works, but backend aiohttp DNS fails in sandboxed env; curl workaround used |
| Model activation (UI) | PASS |
| Worker start (UI) | PASS |
| settings.json updated | PASS |
| Inference (job-based) | PASS - Full job pipeline executed |
| Response quality | POOR - Expected for 0.6B model |

**Overall Verdict: PASS (with documented environment limitation on model download)**

---

## B. WHAT WORKED

### 1. Fresh Venv + Dependency Install
- `python3 -m venv .test_venv` succeeded
- `pip install -r requirements.txt` installed all 41 packages including `llama-cpp-lyrn` (built from source via git)
- No dependency conflicts or build failures
- Total install time: ~2 minutes (including C++ compilation of llama.cpp)

### 2. Backend Boot
- `python3 start_lyrn.py` started successfully on port 8080 (read from `port.txt`)
- Loaded 5 job definitions: `chat_pair_summary`, `test_job_scripts`, `chat_to_job_example`, `chat_input_job`, `chat_response_job`
- Scheduler loop started automatically
- Required directories auto-created: `models/`, `global_flags/`, `chat/`, `jobs/`, `logs/`
- Warning about missing admin token (expected on fresh install)

### 3. UI Accessibility
- Dashboard served at `http://localhost:8080/`
- Module pages accessible at `/modules/<name>.html`
- All static files served correctly via FastAPI `StaticFiles` mount

### 4. Model Activation via UI (Playwright)
- ModelController UI loaded successfully
- Model dropdown populated with `Qwen.Qwen3-0.6B.Q8_0.gguf`
- Selected model, set parameters (n_ctx=2048, n_threads=4, n_gpu_layers=0, max_tokens=256)
- "Start System" button clicked
- Worker process spawned (PID 22435)
- `settings.json` updated with correct `model_path: models/Qwen.Qwen3-0.6B.Q8_0.gguf`
- Worker status polled as "RUNNING (IDLE)" via `/api/system/worker_status`

### 5. Job-Based Inference Flow (VERIFIED)
Full job pipeline traced successfully:

| Layer | Status | Evidence |
|-------|--------|----------|
| UI → API | PASS | POST /api/chat received "Hello world" |
| Job Creation | PASS | `chat_input_job` added to `automation/job_queue.json` |
| Dynamic Snapshot | PASS | `automation/dynamic_snapshots/jobs/chat_input_context.txt` created with `[Chat Input]:\nHello world` |
| Lock File | PASS | `global_flags/chat_processing.txt` created |
| Scheduler Pickup | PASS | `[Scheduler] Executing job: chat_input_job` logged |
| Script Execution | PASS | `route_chat.py` ran, queued `chat_response_job` |
| Second Job Pickup | PASS | `[Scheduler] Executing job: chat_response_job` logged |
| Watcher Spawn | PASS | `spawn_chat_watcher.py` launched background watcher |
| Trigger File | PASS | `chat_trigger.txt` written with path to `jobs/job_model_output.txt` |
| Worker Detection | PASS | `[Runner] Trigger detected: .../chat_trigger.txt` logged |
| Model Loading | PASS | Model loaded with mlock=True, mmap=False |
| Inference Execution | PASS | LLM status changed to "busy", generation ran |
| Output Written | PASS | Response written to `jobs/job_model_output.txt` |
| Chat History Saved | PASS | `chat/chat_20260319_174428_52.txt` created with user/model pair |
| Lock Cleared | PASS | `global_flags/chat_processing.txt` removed |
| API History | PASS | `/api/chat/history` returns correct user/assistant pair |
| Status API | PASS | `/api/chat/status` returns `{"processing": false}` |

**CRITICAL CHECK: Chat uses job system, NOT direct response.** The `/api/chat` endpoint returns `{"success": true, "message": "Chat job queued"}` immediately and does NOT return a direct LLM response. The full job pipeline is used. **This is NOT a bypass.**

---

## C. WHAT PARTIALLY WORKED

### 1. Model Download via UI
- **UI flow itself works correctly:** Playwright successfully loaded ModelManager, filled URL field, clicked Download, and the UI showed "Download started: Qwen.Qwen3-0.6B.Q8_0.gguf"
- **Backend download failed:** The `aiohttp` HTTP client inside `_download_model_task()` could not resolve DNS for `huggingface.co` in this sandboxed environment
- **Error:** `Cannot connect to host huggingface.co:443 ssl:default [Timeout while contacting DNS servers]`
- **Root cause:** Environment network sandbox routes HTTP through a proxy that `curl` can use but Python's `aiohttp` cannot (no proxy configuration in the download code)
- **Workaround:** Downloaded model via `curl -L -o models/Qwen.Qwen3-0.6B.Q8_0.gguf <url>` (805MB, ~5 seconds)

### 2. Response Quality
- The 0.6B model generated a response but the content was incoherent ("and" for "Hello world")
- The model did not follow the `##Response_START##` / `##Response_END##` marker instructions in the `chat_response_job` prompt
- The watcher (`chat_watcher_bg.py`) still extracted and saved a response
- This is expected behavior for a 0.6B parameter model - not a code bug

### 3. Playwright Google Fonts Blocking
- All UI HTML pages include `<link>` to Google Fonts (`fonts.googleapis.com`)
- In sandboxed environments, these requests hang and cause Playwright page loads to timeout with default `wait_until="load"`
- **Workaround:** Blocked font requests via `page.route()` and used `wait_until="domcontentloaded"`
- The UI renders and functions correctly without the external fonts

---

## D. WHAT FAILED

### 1. Model Download via Backend HTTP Client
- **Impact:** MEDIUM - The download feature is broken in environments without direct DNS resolution
- **Error path:** `start_lyrn.py:_download_model_task()` → `aiohttp.ClientSession().get(url)` → DNS timeout
- **The UI correctly showed the error status**

---

## E. MANUAL INTERVENTIONS

| # | Intervention | Reason |
|---|-------------|--------|
| 1 | Created `global_flags/no_auth` file | Backend started without admin token; all API endpoints returned 401. The `no_auth` flag bypasses token verification. |
| 2 | Downloaded model via `curl` | Backend's aiohttp client couldn't resolve DNS in sandboxed environment |
| 3 | Blocked Google Fonts in Playwright | External font requests caused page load timeouts |
| 4 | Set `authToken` via `page.evaluate()` | ModelController/ModelManager UI requires auth token in localStorage; set programmatically |

---

## F. REQUIRED FIXES

### CRITICAL
*None* - The core architecture works correctly.

### IMPORTANT

1. **Fresh install auth UX** - On first boot with no `admin_token.txt`, the system is effectively locked out. The UI modules check `if(!authToken) return;` and silently fail. A new user has no way to interact without knowing to create `admin_token.txt` or `global_flags/no_auth`.
   - **Suggestion:** Auto-generate a token on first boot and print it to console, or default to no-auth mode when no token exists.

2. **Model download proxy support** - The `_download_model_task()` function uses `aiohttp` without proxy configuration. In environments behind HTTP proxies, downloads will fail.
   - **Suggestion:** Read `HTTP_PROXY`/`HTTPS_PROXY` env vars and pass to `aiohttp.ClientSession()`.

3. **Response marker reliability** - The `chat_response_job` requires the LLM to output `##Response_START##` / `##Response_END##` markers. Small models (0.6B) do not follow this instruction. If markers are not found, the watcher times out (30 minutes) and the chat appears stuck.
   - **Suggestion:** Add a fallback that extracts the full model output after a reasonable timeout (e.g., 60 seconds) if markers are not found.

4. **Double inference on chat_input_job** - The `chat_input_job` has both `scripts` (route_chat.py) AND `instructions` ("You are processing a new chat input."). The scheduler runs the script AND triggers chat generation. This causes two inference runs per chat message: one for `chat_input_job`'s vague instructions, and one for `chat_response_job`'s actual prompt. The first inference is wasted work.
   - **Suggestion:** Remove the `instructions` field from `chat_input_job` in `jobs.json`, or make the scheduler skip chat generation when scripts are present and sufficient.

### OPTIONAL

1. **Google Fonts dependency** - All module HTML files depend on Google Fonts CDN. In offline or restricted environments, page loads hang. Consider bundling fonts locally or using `font-display: swap`.

2. **Stale download status** - Download error status persists in `active_downloads` dict for 10 minutes. No way to clear/retry from UI without waiting.

---

## G. FINAL VERDICT

**PASS** - The LYRN system can be installed and run from scratch in a fresh venv. The job-based chat architecture works as designed: UI → API → job queue → scheduler → trigger file → model_runner worker → output → chat history → frontend.

The system correctly uses the job pipeline for chat (not a direct response bypass). The full two-stage job flow (`chat_input_job` → `route_chat.py` → `chat_response_job` → `spawn_chat_watcher.py` → inference → watcher extraction) executes end-to-end.

**Key concerns:**
- Fresh install auth UX is hostile (silent failures, no guidance)
- Double inference per chat message wastes compute
- Small models can't follow marker instructions, causing poor UX

---

## Chat Summary

- **Overall verdict:** PASS
- **Biggest blocker:** Fresh install authentication - without knowing to create `global_flags/no_auth` or `admin_token.txt`, a new user is completely locked out with no error messages
- **Manual intervention required:** Yes - auth bypass (`no_auth` flag), model download (curl fallback due to DNS), Playwright font blocking
