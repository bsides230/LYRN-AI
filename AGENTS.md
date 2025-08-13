# LYRN-AI Project Architectural Rules

This file contains critical architectural rules that must be followed during development.

 - DO NOT BREAK 3 COLUMN LAYOUT!!

 - Always Version the LYRN_GUI from v*.* to v*.*  example v6.1 to v6.2 and then save the old version to deprecated/Old/ in the directory

 - Always perform code anaysis and update feature_suggestion.md or tweaks, compare to future_features.md if available

 - Always update the build_notes.md file with detailed notes about the work done in the update. This should include a section on logging.
 
 - All python dependencies should be added to the `dependencies/requirements.txt` file.

 - Remember in this design we are building cognition for AI. We are building this with simplicty in mind. For example, no crazy coding to complete a function that just requires a file to be watched and the text pulled from formatted blocks. The llm does most of the heavy lifting. This system just moves files and data around dumbly. The affordances are just going to be simple triggers using the similar logic.

---
