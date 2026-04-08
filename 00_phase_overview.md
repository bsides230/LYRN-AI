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
1. **Phase 1: Foundation (Models & Utils)**
   Extract shared dependencies first to ensure that higher-level services and routes can cleanly import them.
2. **Phase 2: Core Services**
   Untangle the complex state managers and controller classes.
3. **Phase 3: Domain Routers**
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