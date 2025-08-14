# LYRN-AI Project Architectural Rules

This file contains critical architectural rules that must be followed during development.

 - DO NOT BREAK 3 COLUMN LAYOUT!!

 - Always Version the LYRN_GUI from v*.* to v*.* , or v*.*.* example v6.1 to v6.2 and then save the old version to deprecated/Old/ in the directory

 - Always perform code anaysis and update feature_suggestion.md or tweaks, compare to future_features.md if available

 - Always update the build_notes.md file with detailed notes about the work done in the update. This should include a section on logging.
 
 - All python dependencies should be added to the `dependencies/requirements.txt` file.
 
 - This system was designed after 90s text based game parser scripts and the simplicity of those triggers. We bring that same energy to this system.
 
 - Remember in this design we are building cognition for AI. We are building this with simplicty in mind. For example, no crazy coding to complete a function that just requires a file to be watched and the text pulled from formatted blocks. The llm does most of the heavy lifting. This system just moves files and data around dumbly. The affordances are just going to be simple triggers using the similar logic.

---
## Parser Contract (v1.0)

### Global rules

- **Markers:** Every block begins with `###<BLOCK>_START###` and ends with `###_END###` (exact, uppercase).
- **Enable switch:** The first logical field in each block MAY be `ENABLED=true|false`. If `false`, parsers MUST ignore the remainder of that block until `###_END###`.
- **Key:Value lines:** Fields are `KEY: value` on single lines. Booleans are `true|false`. Integers are base‑10. Times are ISO‑8601 UTC (`YYYY‑MM‑DDTHH:MM:SSZ`).
- **Arrays:** When present inline, arrays MUST be JSON (e.g., `["alpha","beta"]`), not comma lists.
- **Heredoc values:** Use `<<EOF`; the value is the following lines until a lone `EOF` on its own line.
- **No tabs:** Parsers MUST treat TAB as invalid; use spaces only.
- **Whitespace:** Parsers MUST trim trailing spaces but preserve interior whitespace of heredocs.
- **Order:** Block order is stable but not required by parsers. Within a block, field order is not significant.