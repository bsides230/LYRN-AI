# Job Loop Injection System

This document outlines the foundation layer for job loops in LYRN (e.g., keyword extraction, index scan, affordance loops).

## System Purpose

The Job Loop Injection System is a simple, "dumb", file-based layer designed to execute automated jobs. It aligns perfectly with the existing LYRN file-based trigger system, providing a clean execution rail for all future loops without redesigning the model runner, chat flows, or snapshots.

## Storage Structure

Jobs are categorized and stored in simple CSV files. Each category is represented by its own CSV file.

**Location:**
`runtime/jobs/categories/{category}.csv`

**Example CSV Structure:**
- `runtime/jobs/categories/keyword.csv`
- `runtime/jobs/categories/index_scan.csv`

**CSV Schema:**
- `job_id`: Stable unique identifier (UUID).
- `job_name`: Unique name within the category.
- `trigger_name`: A tiny minimal input string (e.g., "run") associated with the job (though the actual execution trigger is hardcoded as `##JOB_START##`).
- `instruction_layer`: The multiline heavy-lifting logic and prompt instructions.
- `affordances`: A pipe-separated string (`|`) of allowed next steps (e.g., `Category/JobName`).
- `scripts`: A pipe-separated string (`|`) of Python scripts to launch concurrently.
- `max_retries`: Integer indicating maximum allowed parsing failures.
- `retry_error_message`: Custom error message injected on final failure.
- `enabled`: Boolean to quickly toggle job execution.
- `created_at`: Creation timestamp.
- `updated_at`: Last updated timestamp.
- `notes`: Optional user notes.

## Standard Job Output Format

Jobs in LYRN eschew rigid JSON structures in favor of simple, text-based marker extraction. To successfully navigate to the next job in the loop, the model **must** emit an affordance marker in its text output matching this shape:

```text
##AF: Category/JobName ##
```

- The system extracts this block using a Regex `r"##AF:\s*(.*?)\s*##"`.
- The parsed `Category/JobName` string must be present in the job's allowed `affordances` list.

## Job Injection Flow

1. The external script or API selects a job by its `category` and `job_name`.
2. The system loads the corresponding CSV and finds the matching job (ensuring it is `enabled`).
3. The `instruction_layer` and `affordances` are formatted with markers and written to `global_flags/job_context.txt`.
4. The system executes any associated `scripts` in the background and waits for them to signal completion.
5. A standard chat file is created using the existing LYRN mechanism containing the universal trigger `##JOB_START##` as the user input. This gives the snapshot a reliable target to begin execution.
6. The `chat_trigger.txt` file is written to kick off the existing LYRN `model_runner`.
7. The job execution is logged to `runtime/jobs/job_runs.jsonl`.

## Model Runner Injection Point

The instruction layer is injected into the model runner's prompt sequence explicitly **after the delta layer** and **before the final trigger input**.

```
Snapshot -> Repo Context -> History -> Deltas -> [ JOB INSTRUCTIONS ] -> New Input (Trigger)
```

The system safely reads and deletes `global_flags/job_context.txt` once it is loaded into the prompt to ensure it fires exactly once per run.

## Output Parsing and Validation

We supply a simple "dumb" script to validate job output against the standard schema. It does not decide logic or meaning, only structural correctness.

**Parser Usage:**
```bash
python scripts/parse_job_response.py --category "keyword" --job-name "extract_keywords" --response-file "path/to/raw_output.txt"
```

**Retry Rules:**
If the output fails validation:
- If `retry_count < max_retries`, the parser returns `status: retry`.
- If `retry_count >= max_retries`, the parser returns `status: failed` with the configured `retry_error_message` and forces the affordance to `flag_error`.

## Usage

**Via Script:**
```bash
python scripts/inject_job.py --category "keyword" --job-name "extract_keywords"
```

**Via UI:**
Use the **Job Manager** in the LYRN Dashboard to graphically create, view, edit, run, and delete jobs. The UI includes a top toolbar for quick navigation, category/job selection, loading, saving, and an editable affordance list.

## Why No Loop Builder?

This system explicitly avoids hardcoded chains, drag-and-drop workflow editors, or a separate loop builder.

A "loop" is not a fixed sequence. Instead, it emerges dynamically: the output of one job yields a list of `available_affordances`, and future systems (or agents) use those affordances to choose the next logical job or step. Each job describes its own execution scope and what can happen next.

## Limitations

- This system contains **no intelligence** or orchestration logic. It only provides a mechanism for storing jobs, validating output, and injecting them into the existing runner.
- Advanced features like chaining, reflection loops, or conditional logic are **not** implemented here.
