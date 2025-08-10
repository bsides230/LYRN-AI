"""
This module contains the canonical template for the Heartbeat Cycle output
and helper functions to generate the Heartbeat job prompt.

The Heartbeat is the LLM's "internal dialog" pass, used for summarizing,
self-correction, and triggering automated actions.
"""

# The canonical, copy-pasteable template the Heartbeat emits each pass.
# Imported from cognition_upgrade_v1.2.md on 2025-08-09.
# Note: The 'Parser Contract' version of the template is more up-to-date and specific.
# This template is a general guide for the LLM.
HEARTBEAT_TEMPLATE_V1 = """
###HB_META_START###
ENABLED=true
SCHEMA: "hb/v1"
VERSION: "1.0.0"
HB_ID: "hb_YYYY-MM-DDTHH-MM-SSZ_xxxx"
CHAT_PAIR_ID: "cp_YYYY-MM-DDTHH-MM-SSZ"
TIMESTAMP_UTC: "YYYY-MM-DDTHH:MM:SSZ"
PROCESSING_MODE: "thinking"
REASONING_FLAG: "none"
###_END###

###HB_SUM_START###
ENABLED=true
TEXT: <<EOF
<1-3 sentence summary of the user's request and the assistant's response.>
EOF
###_END###

###HB_KEYS_START###
ENABLED=true
KEYWORDS: ["<json_list_of_keywords>"]
TOPICS: ["<json_list_of_topics>"]
ENTITIES: [["<entity_name>", "<entity_type>"]]
###_END###

###HB_INSIGHTS_START###
ENABLED=true
NOTES: <<EOF
- <Key insight, inference, or observation 1>
- <Key insight, inference, or observation 2>
EOF
###_END###

###HB_MEMORY_START###
ENABLED=true
# Format: DELTA|<scope>|<target>|<op>|<path>|<value_mode>|<value or EOF>
# Example: DELTA|conversation|conversation_summary|append|summary_points|RAW|- User was pleased with the outcome.
###_END###

###HB_ACTIONS_START###
ENABLED=true
# Format: AFFORD|<name>|<args_json> or JOB|<name>|<args_json>
# Example: JOB|summary_job|{"source": "cp_YYYY-MM-DDTHH-MM-SSZ"}
###_END###

###HB_FOLLOWUPS_START###
ENABLED=true
# Format: ASK|<question_id>|<prompt> or CORRECT|<field>|<correction_text>
###_END###

###HB_SEARCH_START###
ENABLED=false
# Format: SEARCH|<query>|<hints_json>
###_END###

###HB_FLAGS_START###
ENABLED=true
NEXT_ACTION: "idle"
SAFE_AFTER_DELETE_SIGNAL: false
###_END###
"""

def get_heartbeat_job_prompt(user_input: str, assistant_output: str) -> str:
    """
    Constructs the prompt for the Heartbeat job.
    The prompt instructs the LLM to analyze the recent chat pair and fill out
    the canonical Heartbeat template.
    """

    chat_pair_content = f"USER INPUT:\n{user_input}\n\nASSISTANT OUTPUT:\n{assistant_output}"

    prompt = "###JOB_START: HEARTBEAT###\n"
    prompt += "You are the System Heartbeat. Your role is to perform a meta-analysis of the recent conversation turn. Do NOT respond to the user. Your output MUST be the completed Heartbeat Template, filled with your analysis of the provided chat pair.\n\n"
    prompt += "Analyze the user input and assistant output. Your tasks are:\n"
    prompt += "1. Summarize the turn in HB_SUM.\n"
    prompt += "2. Extract keywords, topics, and entities in HB_KEYS.\n"
    prompt += "3. Note any non-obvious insights or inferences in HB_INSIGHTS.\n"
    prompt += "4. Generate memory deltas in HB_MEMORY to update system knowledge (e.g., user preferences, facts, conversation summary).\n"
    prompt += "5. Trigger system actions or jobs in HB_ACTIONS if needed (e.g., to file a note, to start a longer background task).\n\n"
    prompt += "Fill out the template below with your analysis. If a section is not applicable, leave it empty but enabled.\n"
    prompt += "\n--- CHAT PAIR TO ANALYZE ---\n"
    prompt += chat_pair_content
    prompt += "\n--- END OF CHAT PAIR ---\n"
    prompt += "\n--- HEARTBEAT TEMPLATE (FILL THIS OUT) ---\n"
    prompt += HEARTBEAT_TEMPLATE_V1
    prompt += "###_END###\n"

    return prompt
