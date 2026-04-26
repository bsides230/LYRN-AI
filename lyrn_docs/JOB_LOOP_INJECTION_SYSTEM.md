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
- `trigger_name`: A tiny minimal input string (e.g., "run") to fire the model.
- `instruction_layer`: The multiline heavy-lifting logic and prompt instructions.
- `enabled`: Boolean to quickly toggle job execution.
- `created_at`: Creation timestamp.
- `updated_at`: Last updated timestamp.
- `notes`: Optional user notes.

## Job Injection Flow

1. The external script or API selects a job by its `category` and `job_name`.
2. The system loads the corresponding CSV and finds the matching job (ensuring it is `enabled`).
3. The `instruction_layer` is extracted and written to `global_flags/job_context.txt`.
4. A standard chat file is created using the existing LYRN mechanism containing only the minimal `trigger_name` as the user input.
5. The `chat_trigger.txt` file is written to kick off the existing LYRN `model_runner`.
6. The job execution is logged to `runtime/jobs/job_runs.jsonl`.

## Model Runner Injection Point

The instruction layer is injected into the model runner's prompt sequence explicitly **after the delta layer** and **before the final trigger input**.

```
Snapshot -> Repo Context -> History -> Deltas -> [ JOB INSTRUCTIONS ] -> New Input (Trigger)
```

The system safely reads and deletes `global_flags/job_context.txt` once it is loaded into the prompt to ensure it fires exactly once per run.

## Usage

**Via Script:**
```bash
python scripts/inject_job.py --category "keyword" --job-name "extract_keywords"
```

**Via UI:**
Use the **Job Manager** in the LYRN Dashboard to graphically create, view, edit, and run jobs.

## Limitations

- This system contains **no intelligence** or orchestration logic. It only provides a mechanism for storing jobs and injecting them into the existing runner.
- Advanced features like chaining, reflection loops, or conditional logic are **not** implemented here.
- Deletion is not implemented directly via the UI; jobs should be disabled via the `enabled` toggle or manually deleted from the CSV file.
