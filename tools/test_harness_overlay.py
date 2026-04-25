"""
NORNBRAIN Test Harness -- In-Game Overlay Agents
tools/test_harness_overlay.py

STATUS: SIMPLIFIED -- compound text overlays disabled.
  openc2e has bugs with attr 208, frat 1, pat: text, and reps that
  crash or hang the engine. The overlay functions now create simple
  SIMP marker agents (visible dots) instead of text HUDs.

  Full text overlays should be implemented in the Python-side monitor
  (runtime/norn_monitor.py) where rendering is reliable.

Classifiers used:
  3 100 0 -- Norn position markers (one per norn)
  3 101 0 -- DISABLED (drive bars need text rendering)
  3 102 0 -- DISABLED (world info needs text rendering)

openc2e crash triggers to NEVER use:
  - attr with bits 6+7 (64+128 = 192, 208, etc.)
  - frat 1
  - reps command
  - new: simp without plane parameter
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from test_harness import caos


def generate_norn_labels_script() -> str:
    """Create a visible marker (small sprite) above each norn.
    No text -- just a visual indicator of norn position.
    Uses SIMP agents with 'button' sprite (30x30)."""
    return """\
* Remove existing labels
enum 3 100 0
  kill targ
next

* Create one marker per norn
enum 4 1 0
  setv va00 unid
  setv va01 posx
  setv va02 posy
  subv va02 40
  new: simp 3 100 0 "button" 1 1 8000
  setv ov00 va00
  mvto va01 va02
  tick 10
next

* Timer: follow norn
scrp 3 100 0 9
  seta va00 agnt ov00
  doif va00 eq null
    kill ownr
    stop
  endi
  setv va01 posx va00
  setv va02 posy va00
  subv va02 40
  mvto va01 va02
endm
"""


def generate_drive_bars_script() -> str:
    """DISABLED -- returns a no-op comment.
    openc2e cannot reliably render text overlays (attr 208 + pat: text crash).
    Use the Python monitor (norn_monitor.py) or CLI read-drives instead."""
    return "* Drive bar overlay disabled -- use CLI read-drives or Python monitor\n"


def generate_world_info_script() -> str:
    """DISABLED -- returns a no-op comment.
    openc2e cannot reliably render text overlays.
    Use CLI world-info or Python monitor instead."""
    return "* World info overlay disabled -- use CLI world-info or Python monitor\n"


def generate_remove_overlays_script() -> str:
    """Remove all overlay agents. No reps (crashes openc2e)."""
    return """\
enum 3 100 0
  kill targ
next
enum 3 101 0
  kill targ
next
enum 3 102 0
  kill targ
next
"""


def inject_all_overlays(port: int = 20001) -> None:
    """Inject working overlays (labels only -- drive/world disabled)."""
    print("[overlay] Injecting norn position markers...", end=" ", flush=True)
    try:
        result = caos(generate_norn_labels_script(), port=port)
        print(f"OK" if "EXCEPTION" not in result else f"WARN: {result[:60]}")
    except Exception as exc:
        print(f"ERROR: {exc}")
    print("[overlay] Drive bars: DISABLED (use CLI read-drives)")
    print("[overlay] World info: DISABLED (use CLI world-info)")


def remove_all_overlays(port: int = 20001) -> None:
    """Remove all overlay agents."""
    try:
        caos(generate_remove_overlays_script(), port=port)
        print("[overlay] Removed.")
    except Exception as exc:
        print(f"[overlay] Remove error: {exc}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="NORNBRAIN in-game overlay injector")
    parser.add_argument("action", choices=["inject", "remove", "print"],
                        help="inject/remove/print overlays")
    parser.add_argument("--port", type=int, default=20001)
    args = parser.parse_args()
    if args.action == "inject":
        inject_all_overlays(port=args.port)
    elif args.action == "remove":
        remove_all_overlays(port=args.port)
    elif args.action == "print":
        print(generate_norn_labels_script())
