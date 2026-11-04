# LYRN v6 — Living Yield Relational Network

**Local-First Cognitive Operating System | Plain-Text Stateful Memory | Deterministic Job Loops**

LYRN is a local-first cognitive architecture designed to run entirely on commodity hardware (`llama.cpp` / GGUF) without cloud APIs, vector databases, or external embedding pipelines. Every memory record, working-memory delta, mind-state snapshot (`.sns`), and autonomous task chain is stored as human-readable, auditable plain text.

---

## Upcoming Showcase: **Capsule Man** (Demo Coming Soon)

**One local LLM. One sealed 9×9 habitat (`Seed_Capsule_Alpha`). Zero cloud dependencies.**

**Capsule Man** places a single local language model inside a deterministic `9×9` tile habitat (`A1`–`I9`) equipped with:
- **`[A1–B2]` 3D Printer & Fabricator:** Synthesizes replacement mechanical parts, tools, utility belts, and custom habitat garments from raw feedstock.
- **`[A2–B3]` Recharge Station & Personal Locker `[C2]`:** Manages chassis power reserves and stores personal attire and modular tool belts.
- **`[D1–F1]` & `[A4–A6]` Viewport Windows & Observation Bench `[E2]`:** Exterior collector and environmental monitoring.
- **`[D8–F9]` Hydroponic Grow Tray:** Living botanical bay where the agent monitors cultivar growth, moisture, and nutrient telemetry across ticks.
- **`[I1–I3]` Study Desk, Manual Shelf `[I5–I6]` & Tool Cabinet `[H8–I9]`:** Persistent plain-text observation logs, technical manuals, and preventative maintenance tools.

Instead of scripted behavior trees or artificial hunger bars, the agent contends with **simulated mechanical wear**, power budgets, and empirical botanical care—advancing a deterministic turn-by-turn tick clock with live hardware telemetry (`CPU`, `VRAM`, `KV Cache Reused`, and `tok/s`) visible at all times.

---

## What's New in LYRN v6

### 1. Modern Dimensional Dark UI (`LYRN_v6/`)
The v6 Desktop Dashboard and all 7 core studio modules feature a redesigned **Modern Dimensional Dark** interface (`themes/cyber-dark.css`) with tactile surface elevation, top-edge specular bevels, recessed code/prompt editors, and high-contrast slate typography:
- **`JobLoopInterface.html` (Job Loop Studio):** Visual builder, CSV table editor, and live execution console for affordance-driven job chains (`runtime/jobs/categories/*.csv`).
- **`DeltaManager.html` (Delta Working Memory Manager):** Volatility-ordered working memory manager (`deltas/`) with live block reordering and compilation.
- **`Snapshot Builder.html` (Mind-State Snapshot Architect):** Modular `.sns` snapshot editor for configuring static cognitive scaffolds.
- **`ModelController.html`:** GGUF runtime configuration (`n_ctx`, `n_gpu_layers`, `n_threads`, `n_batch`) and live streaming inference profiler.
- **`ModelManager.html`:** Local GGUF model inspector and downloader.
- **`ServerStatus.html`:** Real-time CPU, RAM, GPU, and VRAM hardware telemetry.
- **`LogViewer.html`:** Live SSE session log streamer.

### 2. Core Architectural Tenets
1. **100% Local & Offline Determinism:** No Chroma, Pinecone, FAISS, LangChain, or cloud wrappers. All state lives on disk in deterministic plain text, JSON, and CSV files.
2. **KV Cache Prefix Preservation:** Static mind-state snapshots remain pinned at the prompt prefix so `llama.cpp` achieves instant prefix cache reuse across autonomous ticks.
3. **Affordance-Driven Job Loops:** Tasks execute as atomic, inspectable steps that transition cleanly via structured affordance tokens.

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```
*(Ensure `llama-cpp-python` is compiled with your preferred hardware acceleration backend—CUDA, Metal, Vulkan, or AVX2 CPU).*

### 2. Launch the LYRN v6 Server & Dashboard
```bash
python start_lyrn.py
```
Then open **`http://localhost:8080`** in your browser to access the LYRN v6 Desktop Dashboard, or use the CLI control harness:
```bash
python lyrn_ctl.py --status
```

---

## Documentation & Whitepapers (`lyrn_docs/`)

- [`Stateful Cognition Paper.md`](lyrn_docs/Stateful%20Cognition%20Paper.md)
- [`LYRN_Whitepaper.txt`](lyrn_docs/LYRN_Whitepaper.txt)
- [`LYRN_Job_Loop_Injection_System.txt`](lyrn_docs/LYRN_Job_Loop_Injection_System.txt)
- [`Long-Term Relational Memory Through Topic Indexing.txt`](lyrn_docs/Long-Term%20Relational%20Memory%20Through%20Topic%20Indexing.txt)
- [`Organizing Symbolic Thought Through Reflection.txt`](lyrn_docs/Organizing%20Symbolic%20Thought%20Through%20Reflection.txt)
- [`Solving Episodic Memory Through Hierarchical Indexing and Relational Cognition.txt`](lyrn_docs/Solving%20Episodic%20Memory%20Through%20Hierarchical%20Indexing%20and%20Relational%20Cognition.txt)
