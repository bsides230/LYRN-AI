# LYRN-AI Project Architectural Rules

This file contains critical architectural rules that must be followed during development.

 - DO NOT BREAK 3 COLUMN LAYOUT!!

 - Always Version the LYRN_GUI from v*.* to v*.*  example v6.1 to v6.2 and then save the old version to deprecated/Old/ in the directory

 - Always perform code anaysis and update feature_suggestion.md or tweaks, compare to future_features.md if available

 - Always update the build_notes.md file with detailed notes about the work done in the update. This should include a section on logging.
 
 - All python dependencies should be added to the `dependencies/requirements.txt` file.

 - Remember in this design we are building cognition for AI. We are building this with simplicty in mind. For example, no crazy coding to complete a function that just requires a file to be watched and the text pulled from formatted blocks. The llm does most of the heavy lifting. This system just moves files and data around dumbly. The affordances are just going to be simple triggers using the similar logic.

---

## The Delta System: Architecture and Purpose

The "delta" system is a core architectural component for providing the LLM with a stream of self-awareness and enabling state changes without compromising performance.

### Core Concepts

1.  **What Deltas Are**: Deltas are small, individual text files, where each file represents a single, atomic change to the system's state. This can be anything from a change in the AI's personality settings to a new system hardware reading (e.g., CPU temperature).

2.  **Delta Injection**: For every reasoning cycle (whether triggered by user chat, a heartbeat, or an automated job), the collection of new delta files should be read. Their contents, which are formatted strings, must be injected "as-is" into the LLM's context.

3.  **Injection Point**: The block of delta strings must be injected immediately after the primary input (user chat, job instruction, etc.) and right before any system flags are appended.

4.  **The "Why" - KV Cache Efficiency**: This architecture is critical for performance. The main system prompt is large and expensive to process. By injecting state changes as small, separate delta strings, we provide the LLM with new information without altering the base prompt. This keeps the KV cache for the base prompt valid, saving thousands of tokens from being re-tokenized and re-processed on every minor change. It is a foundational principle for achieving peak efficiency.

5.  **Purpose**: The primary goal is to feed the LLM a continuous stream of events and state changes, allowing it to self-monitor, reason about its own state, and make informed decisions.