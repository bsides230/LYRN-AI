# 03 Phase Three: Extract FastAPI Routes

## Objective
To group the sprawling API endpoints currently sitting in `start_lyrn.py` into cohesive, domain-specific `APIRouter` modules. This step cleans up the main file dramatically and makes individual API domains easier to maintain and extend. It will also facilitate the creation of the API Manifest CSV.

## Target Components
Create a `routers/` directory and distribute the `@app.` endpoints into the following potential routers:
- **`routers/logs_router.py`**: Endpoints starting with `/api/logs`
- **`routers/chat_router.py`**: Endpoints starting with `/api/chat`
- **`routers/models_router.py`**: Endpoints starting with `/api/models`
- **`routers/config_router.py`**: Endpoints starting with `/api/config`
- **`routers/system_router.py`**: Endpoints starting with `/api/system` and `/api/auth/status`
- **`routers/claude_router.py`**: Endpoints starting with `/api/claude`
- **`routers/automation_router.py`**: Endpoints starting with `/api/automation`
- **`routers/fs_router.py`**: Endpoints starting with `/api/fs`
- **`routers/snapshot_router.py`**: Endpoints starting with `/api/snapshot`
- **`routers/terminal_router.py`**: The websocket endpoint for `/api/terminal`

## Recommended Extraction Order
1. Create the `routers/` directory.
2. Initialize an `APIRouter` in each domain file.
3. Migrate the route functions from `start_lyrn.py` into the respective router file, updating `@app.get(...)` to `@router.get(...)`.
4. Ensure dependencies (e.g., `Depends(verify_token)`) and services (e.g., `logger`, `claude_run_manager`) are correctly imported or injected into the route handlers.
5. In `start_lyrn.py`, import each router and use `app.include_router(...)` to mount them to the FastAPI application.
6. Generate the API Manifest CSV by scripting or manually recording all routes across these newly formed routers.

## Dependency Concerns & Risks
- **Dependency Injection**: Route functions currently have implicit access to globals in `start_lyrn.py` (e.g., `settings_manager`, `automation_controller`, `chat_manager`). These will either need to be imported from a centralized `core/registry.py` module, or passed in via FastAPI's `Depends` system.
- **`verify_token` Dependency**: The `verify_token` function must be extracted to a shared location (e.g., `core/security.py`) so all routers can import it cleanly.

## Completion Checklist
- [ ] `routers/` directory created.
- [ ] All `@app.` endpoints successfully migrated to `APIRouter` instances.
- [ ] All required services and dependencies successfully imported into routers.
- [ ] Routers successfully mounted to the main `app` in `start_lyrn.py`.
- [ ] API Manifest CSV generated outlining the complete API structure.

## Build Notes
*(To be filled by the executor during implementation)*
-
-