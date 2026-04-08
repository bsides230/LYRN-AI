# 04 Phase Four: Reduce `start_lyrn.py` to Composition Layer

## Objective
To finalize the refactoring by reducing `start_lyrn.py` to its essential role: bootstrapping the application, configuring global state/lifespan, and composing the extracted modules. After this phase, `start_lyrn.py` should be clean, readable, and focused entirely on wiring the application together.

## Target Components
1. **`start_lyrn.py`**: The main entry point.
2. **`core/state.py` or `core/globals.py`**: A centralized location for true global state that must be shared across the application, if not already addressed.
3. **`core/lifecycle.py`**: The app lifespan management.

## Recommended Process
1. Consolidate any remaining global variables (`main_loop`, `LYRN_TOKEN`, `extended_llm_stats`, `active_downloads`, `terminal_sessions_lock`) into a clearly defined `core` module if they cannot be neatly encapsulated by a service class.
2. Ensure the `lifespan` context manager (`@asynccontextmanager def lifespan(app: FastAPI)`) is well-structured, optionally extracting it to `core/lifecycle.py` and importing it back into `start_lyrn.py`.
3. Review `start_lyrn.py` to ensure it only contains:
   - Imports of routers, core middleware (CORS), and global state/lifecycle functions.
   - The `FastAPI` instance creation.
   - Middleware mounting (`app.add_middleware(...)`).
   - Router inclusion (`app.include_router(...)`).
   - Static file mounting (`app.mount(...)`).
   - The `if __name__ == "__main__": uvicorn.run(...)` block.
4. Verify the system works entirely end-to-end.

## Dependency Concerns & Risks
- **Initialization Order**: Pay close attention to the order in which modules are imported and initialized. Ensure that state is instantiated before the routes that depend on them are mounted, especially within the `lifespan` events.
- **Background Tasks & Loops**: Ensure that assigning `main_loop = asyncio.get_running_loop()` during the lifespan setup still propagates correctly to any services that rely on it.
- **Port Conflicts/Cleanup**: Ensure that standard port-checking and cleanup logic at startup (e.g., checking port availability) remains intact.

## Completion Checklist
- [X] All remaining global state gracefully centralized.
- [X] Lifespan and middleware logic cleanly structured.
- [X] `start_lyrn.py` refactored into a concise composition layer.
- [X] The full application boots cleanly without implicit initialization order bugs.
- [X] Final testing of key flows (chat generation, background worker jobs, snapshot saves, terminal usage).

## Build Notes
- Extracted the application lifespan context manager and scheduler loop background task into a new `core/lifecycle.py` file.
- Refactored `start_lyrn.py` to be exclusively a composition layer coordinating routers, static files, and initializations.
- Adjusted the sleep interval on the `scheduler_loop` to 0.5s per memory instructions regarding background automated latency intervals.
- Tested the refactored monolithic bootstrap and verified the backend runs without any new exceptions and hosts statically generated files.