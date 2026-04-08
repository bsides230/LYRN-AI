# 01 Phase One: Extract Shared Models, Schemas, and Utils

## Objective
To establish a clear dependency foundation by extracting all "leaf" nodes in the dependency tree. This includes pure utility functions, Pydantic models (schemas), and basic configuration constants. By moving these out first, Phase 2 and Phase 3 will have clean, standardized imports to rely on, eliminating circular dependencies.

## Target Components
1. **Pydantic Models (`models/`)**:
   - `FileTreeSelectionModel`
   - `FileTreeProfileModel`
   - `InjectArtifactModel`
   - `PresetModel`
   - `ActiveConfigModel`
   - `ChatRequest`
   - `JobDefinitionModel`
   - `JobScheduleModel`
   - `CycleModel`
   - `ModelFetchRequest`
   - `SnapshotSaveModel`
   - `SnapshotLoadModel`
2. **Utilities (`utils/`)**:
   - Any standalone helper functions that do not rely on app state, such as `_get_file_explanation(filepath: Path) -> str`.
3. **Core Constants (`core/config.py` or similar)**:
   - Identify static constants (if any) that are safe to extract.

## Recommended Extraction Order
1. Create the new directories: `models/` and `utils/`.
2. Move the Pydantic classes from `start_lyrn.py` into a new file, e.g., `models/schemas.py` or split them by domain (e.g., `models/chat.py`, `models/fs.py`).
3. Move pure helper functions into `utils/helpers.py`.
4. Update imports in `start_lyrn.py` to point to the new module locations.
5. Verify application startup.

## Dependency Concerns & Risks
- **No Circular Imports**: Ensure that `models/` and `utils/` do not import anything from `start_lyrn.py` or any future `services/` or `routers/`.
- **Validation Continuity**: Make sure Pydantic schemas retain their strict type definitions and that nested structures (like `Dict[str, Any]` in FileTree) are correctly imported.
- **Do NOT Move State**: Do not move global state variables (e.g., `active_downloads`, `extended_llm_stats`) into `models` or `utils`. They belong in `core/` during Phase 4.

## Completion Checklist
- [x] `models/` directory created.
- [x] All Pydantic classes extracted and imported correctly into `start_lyrn.py`.
- [x] `utils/` directory created and standalone helpers moved.
- [x] Application starts successfully without import errors.
- [x] Unit tests (if any apply to schemas) pass.

## Build Notes
- Extracted Pydantic models to `models/schemas.py`.
- Extracted `_get_file_explanation` to `utils/helpers.py`.
- Updated imports in `start_lyrn.py` and successfully tested the application start up.