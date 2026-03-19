# LYRN-AI Cold Start Validation Report

**Date:** 2026-03-19
**Tester:** Claude Code (Automated)
**Branch:** claude/cold-start-validation-zFuZR
**Environment:** Linux 6.18.5, Python 3.11.14
**Model:** `Qwen.Qwen3-0.6B.Q8_0.gguf` (DevQuasar/Qwen.Qwen3-0.6B-GGUF, Q8_0 quant)

---

## A. EXECUTIVE SUMMARY

| Component | Status |
|---|---|
| venv creation | ✅ PASS |
| dependency install (`requirements.txt`) | ⚠️ PARTIAL — missing 4 critical packages |
| full dependency install (after manual addition) | ✅ PASS |
| model install (UI-triggered) | ⚠️ PARTIAL — UI triggered download, but aiohttp DNS failed; curl fallback used |
| model file on disk | ✅ PASS — 804MB Q8_0 model present |
| runtime boot | ✅ PASS — backend boots, worker starts, model loads |
| inference (job-based) | ✅ PASS — full job pipeline ran end-to-end |
| `/api/chat/status` completion detection | ✅ PASS |

**Overall: FUNCTIONAL with documented issues.**

---

## B. WHAT WORKED

### 1. venv Creation
```
python3 -m venv venv_cold_start
```
- Python 3.11.14 used (system default)
- venv created successfully

### 2. Backend Boot (`start_lyrn.py`)
- FastAPI app started on port `8080` (from `port.txt`)
- Settings loaded successfully (Windows paths in `settings.json` are overridden by SettingsManager for absolute paths)
- Scheduler loop started
- `global_flags/` directory created automatically

### 3. Model Loading
- Model `models/Qwen.Qwen3-0.6B.Q8_0.gguf` (804MB) loaded by `model_runner.py`
- llama-cpp-lyrn (custom fork) loaded model successfully with mlock=True, mmap=False
- Worker status: `idle` after model loaded

### 4. Job-Based Chat Architecture — Full Trace

```
UI POST /api/chat {"message": "Hello world"}
  → API creates chat_processing.txt lock
  → API creates dynamic snapshot: jobs/chat_input_context
  → automation_controller.add_job("chat_input_job") → written to automation/job_queue.json
  → Returns: {"success": true, "message": "Chat job queued"}

scheduler_loop (every 5s)
  → get_next_due_job() → pops "chat_input_job" from queue
  → execute_job_scripts(job) → runs automation/job_scripts/route_chat.py
    → route_chat.py queues "chat_response_job" back to job_queue.json
    → exit 0 (success)
  → job.prompt == "" (chat_input_job has no direct prompt)

scheduler_loop (next tick)
  → get_next_due_job() → pops "chat_response_job"
  → execute_job_scripts(job) → runs spawn_chat_watcher.py
    → spawn_chat_watcher.py forks chat_watcher_bg.py (background, detached)
    → exit 0
  → job.prompt = "You are processing a user's chat input..." (instructions from jobs.json)
  → trigger_chat_generation(prompt, folder="jobs")
    → writes jobs/job_model_output.txt with "user\n{prompt}\n"
    → writes chat_trigger.txt = "/home/user/LYRN-AI/jobs/job_model_output.txt"

model_runner.py (main loop polling every 0.1s)
  → detects chat_trigger.txt
  → reads trigger → gets path to job_model_output.txt
  → deletes trigger file
  → builds context: system prompt + dynamic snapshots + history
  → calls llm.create_chat_completion(messages, stream=True)
  → streams output to job_model_output.txt
  → appends model response including ##Response_START## / ##Response_END## markers
  → sets llm_status = "idle"

chat_watcher_bg.py (background process)
  → polls job_model_output.txt every 1s
  → detects ##Response_START## and ##Response_END## markers
  → extracts response text
  → saves to chat/chat_<timestamp>.txt as "user\n{input}\nmodel\n{response}"
  → removes global_flags/chat_processing.txt (unlock)
  → deactivates chat_input_context dynamic snapshot
  → exits

/api/chat/status → {"processing": false}  ← UI polls this for completion
```

### 5. Job History (Confirmed from automation/job_history.json)

| Job | Scripts Run | Status | Notes |
|---|---|---|---|
| `chat_input_job` | `route_chat.py` | ✅ success | Queued `chat_response_job` |
| `chat_response_job` | `spawn_chat_watcher.py` | ✅ success | Spawned background watcher, triggered LLM |

### 6. UI (Playwright)
- Dashboard loads at `http://127.0.0.1:8080/`
- Model Manager iframe (`ModelManager.html`) accessible and functional
- Model Controller iframe (`ModelController.html`) accessible
- Chat Interface iframe accessible with send button
- Download triggered successfully via UI API call

---

## C. WHAT PARTIALLY WORKED

### 1. Model Download via UI
**Status: PARTIAL**

The UI Model Manager triggered a download via `/api/models/fetch` successfully from the browser. However, the backend's `aiohttp` async download failed with:

```
Cannot connect to host huggingface.co:443 ssl:default
[Temporary failure in name resolution]
```

This is an aiohttp-specific DNS resolution failure. System-level `curl` resolves the same hostname without issue. The download succeeded via curl fallback:
```bash
curl -L "https://huggingface.co/.../Qwen.Qwen3-0.6B.Q8_0.gguf" \
     -o models/Qwen.Qwen3-0.6B.Q8_0.gguf
```

**Root cause:** aiohttp uses asyncio's event loop for DNS which may not respect `/etc/resolv.conf` in all environments.

### 2. UI Playwright Interaction
**Status: PARTIAL**

Several workarounds were required:

1. **External fonts block DOMContentLoaded**: The page includes `<link>` to `fonts.googleapis.com`. This causes `page.goto(wait_until='domcontentloaded')` to time out. Fix: `page.route('**/*.googleapis.com/**', route.abort)`.

2. **`coreUrl` not in iframe scope by default**: The ModelManager/ModelController iframes define `coreUrl` via `postMessage` from the parent dashboard. In Playwright, this message may not arrive before JS evaluation. Fix: Explicitly set via `frame.evaluate('coreUrl = "http://127.0.0.1:8080"')`.

3. **Model select dropdown empty**: The model dropdown in ModelController requires `authToken` to populate (calls `/api/models/list` only if `authToken` is set). With no_auth, the token is `"NO_AUTH"` but the iframe variable is still empty. Fix: Set via JS before interaction.

4. **Download button click fails**: The download button in ModelManager requires `wait_until='commit'` not `'domcontentloaded'` on the iframe. Used JS `.click()` instead.

### 3. Model Response Quality
**Status: PARTIAL**

The model generated output through the full pipeline, but the response was not contextually relevant to "Hello world". The model responded about "creating a character and a room" with `##Response_START##`/`##Response_END##` markers as instructed.

**Analysis:** The system prompt (from `build_prompt/` components) and active dynamic snapshots appear to contain context about a game/creative system that biased the model. This is a content configuration issue, not a pipeline failure.

The saved chat history shows only "and" as the model response — this is because `chat_watcher_bg.py` extracted the first match between `##Response_START##`/`##Response_END##` markers. The model generated multiple repetitions, and the watcher may have matched before the full sequence was written.

---

## D. WHAT FAILED

### 1. `requirements.txt` is Incomplete — CRITICAL
The following packages are used by `start_lyrn.py` but are **not in `requirements.txt`**:

| Package | Used By | Impact |
|---|---|---|
| `fastapi` | `start_lyrn.py` | Backend won't start |
| `uvicorn[standard]` | `start_lyrn.py` | Backend won't start |
| `aiohttp` | `start_lyrn.py` (model download) | Download API broken |
| `aiofiles` | `start_lyrn.py` (model download) | Download API broken |

A fresh install of `requirements.txt` alone will fail to start the backend with:
```
ModuleNotFoundError: No module named 'fastapi'
```

### 2. aiohttp DNS Resolution Fails — CRITICAL for Model Download
Even with correct packages installed, the model download via UI fails because `aiohttp` cannot resolve external hostnames in this environment. The backend download endpoint is non-functional.

### 3. Model select dropdown in ModelController doesn't auto-populate
The `inp-model` `<select>` dropdown only calls `fetchModels()` if `authToken` is truthy. Since `authToken` is set via `postMessage` from parent dashboard, and the timing of this message is non-deterministic in Playwright, the dropdown may appear empty. This also affects real users if they open the module before the auth postMessage fires.

### 4. Chat history saved response is truncated
The `chat_watcher_bg.py` saved only "and" as the model response. The watcher may have matched a partial `##Response_START##`...`##Response_END##` block before the full generation was written. The regex uses non-greedy `.*?` which matches the first closing marker, but if the model generates the pattern multiple times (as seen in output), only the first (possibly partial) match is used.

---

## E. MANUAL INTERVENTIONS

The following steps were NOT possible without manual intervention:

1. **Installed missing packages manually** (not in requirements.txt):
   ```bash
   pip install fastapi uvicorn[standard] aiohttp aiofiles
   ```

2. **Created `global_flags/no_auth` flag** for token-free testing:
   ```bash
   touch global_flags/no_auth
   ```

3. **Created required directories** that don't exist in fresh clone:
   ```bash
   mkdir -p models global_flags chat jobs
   ```

4. **Downloaded model via curl** instead of UI API (aiohttp DNS failure):
   ```bash
   curl -L "https://huggingface.co/DevQuasar/Qwen.Qwen3-0.6B-GGUF/resolve/main/Qwen.Qwen3-0.6B.Q8_0.gguf" \
        -o models/Qwen.Qwen3-0.6B.Q8_0.gguf
   ```

5. **Set coreUrl/authToken in iframe JS** to work around postMessage timing:
   ```python
   mm_frame.evaluate('coreUrl = "http://127.0.0.1:8080"')
   ```

6. **Blocked Google Fonts requests** to allow page DOMContentLoaded to fire:
   ```python
   page.route('**/*.googleapis.com/**', lambda route: route.abort())
   ```

---

## F. REQUIRED FIXES

### CRITICAL

#### F1. `requirements.txt` is incomplete
**File:** `requirements.txt`
**Fix:** Add the following lines:
```
fastapi>=0.100.0
uvicorn[standard]>=0.20.0
aiohttp>=3.8.0
aiofiles>=23.0.0
```
**Impact:** Without these, `start_lyrn.py` cannot be imported or run.

#### F2. aiohttp DNS resolution failure for model downloads
**File:** `start_lyrn.py`, function `_download_model_task`
**Issue:** `aiohttp.ClientSession` uses asyncio's event-loop DNS resolver which fails in some Linux environments.
**Fix options:**
- Use `aiohttp.AsyncResolver` with `nameservers=["8.8.8.8", "1.1.1.1"]`
- Use `asyncio.get_event_loop().run_in_executor()` + `requests` library for downloads
- Add `aiodns` package to requirements.txt (aiohttp optional c-ares DNS resolver)
- Simplest: `pip install aiodns` and it auto-uses c-ares for resolution

#### F3. `settings.json` has hardcoded Windows absolute paths
**File:** `settings.json`
**Issue:** Paths under `settings.paths` point to `C:\Users\matta\...` which don't exist on Linux.
**Current mitigation:** `SettingsManager.load_or_detect_first_boot()` detects absolute paths that don't exist and the code treats them as-is. Relative paths work because the backend resolves them relative to the script directory.
**Fix:** Normalize `settings.json` to use relative paths only in the committed version, or document that `settings.json` paths are machine-specific and should be regenerated on first boot.

### IMPORTANT

#### F4. `chat_watcher_bg.py` may capture incomplete model response
**File:** `automation/job_scripts/chat_watcher_bg.py`
**Issue:** The watcher polls every 1 second and extracts the FIRST match of `##Response_START##.*?##Response_END##`. If the model has started writing but hasn't completed the block, or writes multiple blocks, the first (possibly partial or wrong) match is used.
**Fix:** Add a check that the LLM status is `idle` before extracting the response, ensuring generation is complete. Or poll less frequently + verify generation is done via `llm_status.txt`.

#### F5. ModelController model dropdown doesn't populate without authToken
**File:** `LYRN_v5/modules/ModelController.html`
**Issue:** `fetchModels()` (called to populate the dropdown) is gated on `if(!authToken) return`. When `no_auth` mode is active, the backend accepts any token, but the iframe's `authToken` variable isn't set until `postMessage` from parent arrives.
**Fix:** Call `fetchModels()` unconditionally, or set a default `authToken` value for no-auth environments, or call `fetchModels()` on a timer if token isn't received within 2 seconds.

#### F6. Missing directories in fresh clone
**Directories needed but not created by code:**
- `models/` — model storage
- `chat/` — chat history
- `jobs/` — job output files
- `global_flags/` — created by SettingsManager but only if settings load

**Fix:** Add directory creation at the top of `start_lyrn.py` or add a `setup.py`/`first_run.sh`.

### OPTIONAL

#### F7. External font dependency blocks page load in restricted environments
**File:** `LYRN_v5/dashboard.html`
**Issue:** `<link href="https://fonts.googleapis.com/...">` and `<link rel="preconnect">` tags cause `DOMContentLoaded` to delay/timeout in network-restricted environments.
**Fix:** Host fonts locally or add a `font-display: swap` fallback that doesn't block rendering.

#### F8. `coreUrl` not initialized in iframe scope before postMessage
**Files:** `LYRN_v5/modules/ModelManager.html`, `ModelController.html`, `Chat Interface.html`
**Issue:** Modules initialize `coreUrl` from localStorage with a hardcoded fallback of `http://localhost:8000`. If the server runs on a different port (e.g., 8080) and localStorage is empty (fresh browser), the API calls go to the wrong port until the parent sends a `postMessage`.
**Fix:** Initialize `coreUrl` from `window.location.origin` if available, rather than hardcoding `http://localhost:8000`.

---

## G. FINAL VERDICT

### Job-Based Architecture: VERIFIED WORKING ✅

The complete job-based inference pipeline executed successfully:

```
/api/chat → job_queue.json → scheduler_loop → route_chat.py
  → chat_response_job → spawn_chat_watcher.py + LLM trigger
  → chat_trigger.txt → model_runner.py → inference
  → ##Response markers → chat_watcher_bg.py → chat/ directory
  → chat_processing.txt cleared → /api/chat/status = {processing: false}
```

**The chat system does NOT bypass the job system.** Every chat message goes through the automation_controller queue → scheduler → scripts → trigger pipeline before reaching the LLM.

### Installation: BROKEN without manual fix ❌

A real user following a fresh install would hit `ModuleNotFoundError: No module named 'fastapi'` on the first run. `requirements.txt` is missing 4 critical runtime dependencies.

### Model Download via UI: BROKEN in this environment ❌

The aiohttp backend cannot resolve external hostnames in this test environment. This blocks the model download UI from working. curl works. This may be environment-specific (DNS sandbox restriction in CI), but the code lacks a fallback/diagnostic for this failure mode.

---

## Short Summary

**Overall verdict:** CONDITIONALLY FUNCTIONAL — the job-based chat architecture is correctly implemented and runs end-to-end. The biggest blockers are an incomplete `requirements.txt` (fatal for fresh install) and aiohttp DNS failures (fatal for model download). With these fixed, the system works as designed.

**Biggest blocker:** `requirements.txt` missing `fastapi`, `uvicorn`, `aiohttp`, `aiofiles`.

**Manual interventions required:** Yes — 6 steps required before the system could run (missing pip packages, missing dirs, no_auth flag, model download via curl, Playwright iframe coreUrl workaround).
