#!/usr/bin/env python3
"""
LYRN Control and Test Harness Entrypoint.
Usage:
    python lyrn_ctl.py --status
    python lyrn_ctl.py --start-server
    python lyrn_ctl.py --start-worker
    python lyrn_ctl.py --stop-worker
    python lyrn_ctl.py --bench --prompt "Explain episodic memory in AI."
    python lyrn_ctl.py --inject-job General respond_to_input
    python lyrn_ctl.py --deltas-compile
    python lyrn_ctl.py --full-test
"""

import sys
from pathlib import Path

# Ensure LYRN REF root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.cli import main

if __name__ == "__main__":
    main()
