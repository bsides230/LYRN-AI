import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DELTAS_LIVE_DIR = os.path.join(PROJECT_ROOT, "deltas", "live")
MANIFEST_OUT = os.path.join(PROJECT_ROOT, "deltas", "compiled_manifest.txt")

def main():
    if not os.path.exists(DELTAS_LIVE_DIR):
        print(f"[DeltaCompiler] Directory not found: {DELTAS_LIVE_DIR}")
        return

    delta_files = [f for f in os.listdir(DELTAS_LIVE_DIR) if f.endswith('.txt')]
    delta_files.sort()  # Ensures DEL01 is at the top, then DEL02, etc.

    compiled_content = "##DELTA:START##\n"

    for filename in delta_files:
        filepath = os.path.join(DELTAS_LIVE_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    compiled_content += content + "\n"
        except Exception as e:
            print(f"[DeltaCompiler] Error reading {filepath}: {e}")

    compiled_content += "##DELTA:END##\n"

    # Make sure output dir exists
    os.makedirs(os.path.dirname(MANIFEST_OUT), exist_ok=True)

    try:
        with open(MANIFEST_OUT, 'w', encoding='utf-8') as f:
            f.write(compiled_content)
        print(f"[DeltaCompiler] Manifest compiled to {MANIFEST_OUT}")
    except Exception as e:
        print(f"[DeltaCompiler] Error writing manifest: {e}")

if __name__ == "__main__":
    main()
