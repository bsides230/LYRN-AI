"""
Command-Line Interface for the LYRN Control and Test Harness.
Allows full control of server, worker, model inference benchmarking,
deltas, and jobs via HTTP API endpoints.
"""

import sys
import argparse
from pathlib import Path

# Force UTF-8 encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from .lyrn_client import LyrnClient
from .lyrn_harness import LyrnTestHarness


def main():
    parser = argparse.ArgumentParser(description="LYRN Control & Test Harness CLI")
    parser.add_argument("--url", default=None, help="Base URL of LYRN server (defaults to port.txt or http://localhost:8080)")
    parser.add_argument("--token", default=None, help="Admin token (defaults to admin_token.txt)")

    # Actions
    parser.add_argument("--status", action="store_true", help="Print server health, hardware, and worker status")
    parser.add_argument("--start-server", action="store_true", help="Start the LYRN backend server")
    parser.add_argument("--stop-server", action="store_true", help="Stop the LYRN backend server")
    parser.add_argument("--start-worker", action="store_true", help="Start the headless model runner process")
    parser.add_argument("--stop-worker", action="store_true", help="Stop the headless model runner process")
    parser.add_argument("--clear-stats", action="store_true", help="Clear LLM metrics and stats")

    # Benchmark
    parser.add_argument("--bench", action="store_true", help="Run real-time inference speed benchmark")
    parser.add_argument("--prompt", default="Explain what an episodic memory system does in an AI architecture in 2 sentences.", help="Prompt for benchmark")

    # Deltas
    parser.add_argument("--deltas-list", action="store_true", help="List registered delta working memory blocks")
    parser.add_argument("--deltas-compile", action="store_true", help="Compile deltas/compiled_manifest.txt via API")

    # Jobs
    parser.add_argument("--jobs-list", action="store_true", help="List registered job categories and jobs")
    parser.add_argument("--inject-job", nargs=2, metavar=("CATEGORY", "JOB_NAME"), help="Inject and execute a job (e.g. TopicIndex extract_kws)")

    # Full Verification
    parser.add_argument("--full-test", action="store_true", help="Run full end-to-end automated verification suite")

    args = parser.parse_args()

    client = LyrnClient(base_url=args.url, token=args.token)
    harness = LyrnTestHarness(client)

    # 1. Full Test Suite
    if args.full_test:
        report = harness.run_full_suite(benchmark_prompt=args.prompt)
        sys.exit(0 if report.all_passed else 1)

    # 2. Status
    if args.status:
        if not client.is_server_alive(timeout=1.0):
            print("=" * 60)
            print("LYRN SYSTEM STATUS")
            print("=" * 60)
            print(f"Server URL:     {client.base_url}")
            print(f"Status:         OFFLINE (Server not running)")
            print(f"Action:         Run 'python lyrn_ctl.py --start-server' to launch.")
            print("=" * 60)
            return

        try:
            health = client.get_health()
            auth = client.verify_token()
            print("=" * 60)
            print("LYRN SYSTEM STATUS")
            print("=" * 60)
            print(f"Server URL:     {client.base_url}")
            print(f"Auth Valid:     {auth}")
            print(f"CPU Util:       {health.get('cpu')}%")
            ram = health.get("ram", {})
            print(f"RAM:            {ram.get('used_gb', 0):.2f} / {ram.get('total_gb', 0):.2f} GB ({ram.get('percent')}%)")
            gpu = health.get("gpu", {})
            print(f"GPU Available:  {gpu.get('available', False)}")
            worker = health.get("worker", {})
            print(f"Worker Running: {worker.get('running')} (PID: {worker.get('pid')})")
            print(f"LLM Status:     {worker.get('llm_status')}")
            llm_stats = health.get("llm_stats", {})
            print(f"Active Model:   {llm_stats.get('model_name', 'None')}")
            if "eval_speed" in llm_stats:
                print(f"Last Eval Speed:{llm_stats.get('eval_speed', 0):.2f} tokens/sec")
            print("=" * 60)
        except Exception as e:
            print(f"Error querying status: {e}")
            sys.exit(1)
        return

    # 3. Server Control
    if args.start_server:
        try:
            client.start_server(wait=True)
            print(f"Server successfully running at {client.base_url}")
        except Exception as e:
            print(f"Failed to start server: {e}")
            sys.exit(1)
        return

    if args.stop_server:
        stopped = client.stop_server()
        print(f"Server stopped: {stopped}")
        return

    # 4. Worker Control
    if args.start_worker:
        try:
            print("Starting model worker (loading model into memory)...")
            res = client.start_worker(wait_ready=True)
            print(f"Worker started successfully: {res}")
        except Exception as e:
            print(f"Failed to start worker: {e}")
            sys.exit(1)
        return

    if args.stop_worker:
        try:
            res = client.stop_worker()
            print(f"Worker stopped: {res}")
        except Exception as e:
            print(f"Failed to stop worker: {e}")
            sys.exit(1)
        return

    if args.clear_stats:
        try:
            res = client.clear_stats()
            print(f"Stats cleared: {res}")
        except Exception as e:
            print(f"Failed to clear stats: {e}")
            sys.exit(1)
        return

    # 5. Benchmark
    if args.bench:
        try:
            # Ensure server and worker
            client.start_server(wait=True)
            w_status = client.get_worker_status()
            if not w_status.get("running") or w_status.get("llm_status") != "idle":
                print("Starting worker for benchmark...")
                client.start_worker(wait_ready=True)

            print(f"Executing inference benchmark with prompt: \"{args.prompt}\"")
            print("Streaming output: ", end="", flush=True)

            def on_token(t: str):
                sys.stdout.write(t)
                sys.stdout.flush()

            res = client.stream_benchmark(prompt=args.prompt, on_token=on_token)
            print("\n" + "=" * 60)
            print(f"Benchmark State:    {res.state}")
            print(f"Duration:           {res.duration_seconds:.2f}s")
            print(f"Prompt Tokens:      {res.prompt_tokens} ({res.prompt_speed:.2f} t/s)")
            print(f"Generation Tokens:  {res.eval_tokens} ({res.eval_speed:.2f} t/s)")
            print(f"Total Tokens:       {res.total_tokens}")
            print(f"KV Cache Hits:      {res.kv_cache_reused}")
            print("=" * 60)
        except Exception as e:
            print(f"Benchmark failed: {e}")
            sys.exit(1)
        return

    # 6. Deltas
    if args.deltas_list:
        try:
            blocks = client.get_delta_blocks()
            print(f"Found {len(blocks)} Delta Blocks:")
            for b in blocks:
                en = "[ENABLED] " if b.get("enabled", True) else "[DISABLED]"
                print(f"  {en} {b.get('id'):<20} | {b.get('file'):<30} | {b.get('description')}")
        except Exception as e:
            print(f"Failed to list deltas: {e}")
            sys.exit(1)
        return

    if args.deltas_compile:
        try:
            client.start_server(wait=True)
            res = client.compile_deltas()
            print(f"Compiled Delta Manifest: {res.get('manifest_size')} characters saved to {res.get('manifest_path')}")
        except Exception as e:
            print(f"Failed to compile deltas: {e}")
            sys.exit(1)
        return

    # 7. Jobs
    if args.jobs_list:
        try:
            client.start_server(wait=True)
            categories = client.get_job_categories()
            print(f"Registered Job Categories ({len(categories)}):")
            for cat in categories:
                print(f"\n[{cat}]")
                jobs = client.get_jobs(cat)
                for j in jobs:
                    en = "[+]" if j.get("enabled") else "[-]"
                    print(f"  {en} {j.get('job_name'):<22} | Trigger: {j.get('trigger_name'):<20} | Max Retries: {j.get('max_retries')}")
        except Exception as e:
            print(f"Failed to list jobs: {e}")
            sys.exit(1)
        return

    if args.inject_job:
        cat, job_name = args.inject_job
        try:
            client.start_server(wait=True)
            w_status = client.get_worker_status()
            if not w_status.get("running"):
                client.start_worker(wait_ready=True)

            print(f"Injecting job: {cat}/{job_name}...")
            result = client.inject_and_await_job(cat, job_name)
            print(f"Job completed in {result['duration']:.2f}s!")
            print(f"Output File: {result['output_file']}")
            print("-" * 60)
            print(result["content"])
            print("-" * 60)
        except Exception as e:
            print(f"Job injection failed: {e}")
            sys.exit(1)
        return

    # No argument provided -> print help
    parser.print_help()


if __name__ == "__main__":
    main()
