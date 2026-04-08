# 02 Phase Two: Extract Core Services and Controllers

## Objective
To isolate the heavy lifting and orchestration logic from the API routing layer. This phase involves taking the large classes in `start_lyrn.py` that manage the system's background processes, terminal interactions, and interactions with external CLI tools, and moving them into a dedicated `services/` directory.

## Target Components
1. **Core Services (`services/`)**:
   - `DiskJournalLogger`: Handles log session management, file writing, and chunking.
   - `ProxyController`: Manages the local Anthropic proxy wrapper lifecycle.
   - `ClaudeRunManager`: Orchestrates interactions with the Claude Code CLI and stores run outputs.
   - `WorkerController`: Manages background workers.
2. **Terminal Session Management**:
   - `WebTerminalSession` and `LocalPTYSession`: Classes related to handling the terminal PTY integration.

## Recommended Extraction Order
1. Create the `services/` directory.
2. Extract `DiskJournalLogger` into `services/logger.py`.
3. Extract `WorkerController` into `services/worker.py`.
4. Extract `ProxyController` and `ClaudeRunManager` into `services/claude.py` (or individual files if they remain large).
5. Extract `WebTerminalSession` and `LocalPTYSession` into `services/terminal.py`.
6. Instantiate these classes inside `start_lyrn.py` and ensure they are passed as dependencies to the remaining route functions, or placed in a centralized service registry within `core/`.

## Dependency Concerns & Risks
- **Concurrency Locks**: Pay close attention to asyncio locks (e.g., inside `DiskJournalLogger` or `LocalPTYSession`). They must remain tied to the same event loop context.
- **Global State Coupling**: If any of these classes rely heavily on global state (like `main_loop`), you must ensure they accept these via dependency injection upon initialization or import them explicitly from a new `core/state.py` module.
- **Process Management**: `ProxyController` and `WorkerController` interact with system processes. Ensure pathing to the proxy and worker scripts remains accurate relative to their new location in `services/`.

## Completion Checklist
- [ ] `services/` directory created.
- [ ] `DiskJournalLogger` extracted and wired up.
- [ ] `WorkerController` extracted and wired up.
- [ ] `ProxyController` and `ClaudeRunManager` extracted.
- [ ] Terminal session classes extracted.
- [ ] Application starts and background workers/proxy behave correctly.

## Build Notes
*(To be filled by the executor during implementation)*
-
-