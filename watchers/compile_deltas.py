"""
Compile Deltas Watcher / CLI Bridge for LYRN.
Compiles Layer 2 working memory into deltas/compiled_manifest.txt.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services import delta_service


def main():
    try:
        manifest = delta_service.compile_manifest()
        print(f"[CompileDeltas] Successfully compiled manifest ({len(manifest)} chars).")
        sys.exit(0)
    except Exception as e:
        print(f"[CompileDeltas] Error compiling delta manifest: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
