# 00 Phase Overview: Decoupling `start_lyrn.py`

## Objective
The current `start_lyrn.py` is a monolithic file of approximately 2500 lines. It contains FastAPI startup logic, Pydantic data models, complex service classes (`DiskJournalLogger`, `ClaudeRunManager`, etc.), application state variables, and dozens of API route definitions. This structure hinders extensibility and increases the risk of merge conflicts or unintended side effects during active development.

The goal of this 4-phase decoupling task is to safely split `start_lyrn.py` into a clean, modular architecture. After completion, `start_lyrn.py` will serve solely as a bootstrap/composition layer, wiring together explicitly decoupled components.

## Architectural Strategy
The target directory structure will follow a standard separation of concerns:
- **`core/`**: App bootstrap, shared globals, lifecycle mechanics, constants, and dependency injection items (e.g., `main_loop`, `LYRN_TOKEN`).
- **`models/`**: Pydantic schemas and generic data classes.
- **`utils/`**: Small, pure, reusable helper functions.
- **`services/`**: Core orchestration classes and controllers (`DiskJournalLogger`, `ProxyController`, etc.).
- **`routers/`**: FastAPI `APIRouter` definitions, grouping endpoints by domain (e.g., `logs`, `chat`, `automation`).

### The API Manifest CSV
As part of standardizing the API system, an API manifest CSV will be generated to document all available endpoints, modules, dashboards, and settings. This CSV will act as the source of truth for the system API, making future integrations predictable.

## The 4-Phase Plan
1. **[X] Phase 1: Foundation (Models & Utils)**
   Extract shared dependencies first to ensure that higher-level services and routes can cleanly import them.
2. **[X] Phase 2: Core Services**
   Untangle the complex state managers and controller classes.
3. **[X] Phase 3: Domain Routers**
   Extract the FastAPI endpoints into dedicated router modules.
4. **Phase 4: Composition & Finalization**
   Reduce `start_lyrn.py` to a clear entry point that coordinates the app lifespan, mounts routers, and manages centralized state.

## Centralized State & High-Risk Areas
During this refactoring, certain elements must *remain centralized* and be treated with care. Do not force them into isolated modules if they represent true global state:
- **Global Variables**: `main_loop`, `LYRN_TOKEN`, `extended_llm_stats`, `active_downloads`. These should likely move to a `core/state.py` or `core/globals.py` registry.
- **App Lifecycle**: The `@asynccontextmanager def lifespan(app: FastAPI)` function manages critical startup/shutdown wiring and should stay in the main entry point or a dedicated `core/lifecycle.py`.
- **Websocket / Terminal Locks**: `terminal_sessions_lock` and the active sessions dict must remain shared across requests.
- **Background Tasks**: Thread-based logs or spawned background workers.

By keeping the extraction phased, we ensure the system remains stable and verifiable at every step.

## Build Notes
### Phase 1
- **What was moved:** Extracted Pydantic models to `models/schemas.py` and `_get_file_explanation` to `utils/helpers.py`.
- **Issues encountered:** None.
- **Risks or follow-ups:** Pydantic imports needed to be maintained correctly. No cyclic dependencies introduced since these are leaf nodes.

### Phase 2
- **What was moved:** Extracted global state to `core/state.py`. Extracted `DiskJournalLogger` to `services/logger.py`. Extracted `ProxyController` and `ClaudeRunManager` to `services/claude.py`. Extracted `WorkerController` to `services/worker.py`. Extracted Terminal session classes to `services/terminal.py`.
- **Issues encountered:** Encountered circular dependency concerns but circumvented them by creating `core/state.py` for global variables (`main_loop`, `LYRN_TOKEN`, `extended_llm_stats`, `active_downloads`) which services and `start_lyrn.py` both reference.
- **Risks or follow-ups:** `start_lyrn.py` still has remaining route code to be extracted, but the orchestration logic has been effectively decoupled.

### Phase 3
- **What was moved:** Extracted all API endpoints from `start_lyrn.py` into dedicated domain routers in the `routers/` directory (`logs_router`, `chat_router`, `models_router`, `config_router`, `system_router`, `claude_router`, `automation_router`, `fs_router`, `snapshot_router`, and `terminal_router`). Shared logic like `verify_token` was moved to `core/security.py`, and global instances were centralized in `core/registry.py`. `trigger_chat_generation` moved to `utils/helpers.py`.
- **Issues encountered:** Encountered dependency injection issues, which required establishing `core/registry.py` and `core/security.py` to maintain imports without cyclic references. The manifest script failed due to missing `psutil` in standard envs, so it wasn't retained.
- **Risks or follow-ups:** Phase 4 remains to finalize `start_lyrn.py` as a composition layer.