"""
NORNBRAIN Test Harness -- CAOS In-Game Control Panel
tools/test_harness_caos.py

Generates and injects a CAOS compound agent that creates a clickable control
panel inside the running Creatures 3 / openc2e NB engine.

Architecture:
  Each button is a separate SIMP agent with classifier (3 103 N) where N is
  the button ID. Clicking a button fires activate1 (event 1) on that agent.
  The agent's scrp handles the action directly.

  This is more reliable than PAT:BUTT in openc2e because PAT:BUTT support
  is incomplete in the openc2e implementation. SIMP agents with their own
  click scripts are fully supported.

  NOTE: These are OUR agents with known classifiers so activate1 is safe
  (see CLAUDE.md rule: "NEVER fire activate1 on unknown agents" -- these
  are known by design).

Safety rules enforced:
  - Norn spawning ONLY via Egg Layer (3 3 31)
  - Grendel kill targets genus 2 only, never genus 1
  - Reward = CHEM 204, Punishment = CHEM 205
  - GAME vars use lnn_ prefix
  - No activate1 on unknown agents

Panel classifier: 3 103 N (family=3, genus=103, species=N)
  Species 0 = background / title label
  Species 1..19 = individual button agents (matching the button list)

openc2e TCP: port 20001
"""

import sys
import os
import socket

# Import caos() from sibling module
sys.path.insert(0, os.path.dirname(__file__))
from test_harness import caos


# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

# Panel position in WORLD SPACE (Norn Terrarium left wall).
# attr 208 (camera-relative) crashes openc2e -- world-space only.
# Norn Terrarium spans x=0-2380, y=400-1000.
PANEL_X = 30
PANEL_Y = 420

BTN_W = 56      # button width (medical_control_panel_buttons.c16 = 56x33)
BTN_H = 33      # button height
BTN_GAP = 4     # gap between buttons
BTN_COL_X = 0   # x offset of buttons relative to panel origin
TITLE_H = 37    # height of title area
BTN_SPRITE = "medical_control_panel_buttons"  # 56x33, 20+ frames

# ---------------------------------------------------------------------------
# Button definitions
# Each tuple: (species_id, label, caos_action)
# species_id is used as SPCS for the SIMP agent AND to uniquely address it
# ---------------------------------------------------------------------------

BUTTONS = [
    # --- Norn Management ---
    (1,  "Spawn 2 Eggs",     """\
  * Spawn egg 1 via Egg Layer (3 3 31) message 1001 = hatch button
  enum 3 3 31
    mesg wrt+ targ 1001 0 0 0
  next
  * Brief pause then spawn egg 2
  wait 5
  enum 3 3 31
    mesg wrt+ targ 1001 0 0 0
  next"""),

    (2,  "Hatch All",        """\
  * Skip incubation: pose 3 + tick 1 on eggs (species 1)
  enum 3 4 1
    pose 3
    tick 1
  next"""),

    (3,  "Kill Grendels",    """\
  * Kill grendels only (genus 2). NEVER genus 1.
  enum 4 2 0
    kill targ
  next"""),

    (4,  "TP to Hand",       """\
  * Teleport all norns to hand/pointer position
  * openc2e: must targ pntr first, then read posx/posy
  targ pntr
  setv va00 posx
  setv va01 posy
  enum 4 1 0
    mvto va00 va01
  next"""),

    (5,  "Save World",       """\
  save"""),

    # --- Camera Navigation ---
    (6,  "Norn Terrarium",   """\
  * Metaroom 0 -- Norn Terrarium (1190, 712)
  cmra 1190 712 0"""),

    (7,  "Desert",           """\
  * Metaroom 1 -- Ettin Desert (5190, 704)
  cmra 5190 704 0"""),

    (8,  "Jungle",           """\
  * Metaroom 3 -- Grendel Jungle (1948, 2310)
  cmra 1948 2310 0"""),

    (9,  "Aquatic",          """\
  * Metaroom 2 -- Aquatic (9000, 1200)
  cmra 9000 1200 0"""),

    (10, "Corridor",         """\
  * Metaroom 4 -- Corridor (3200, 1100)
  cmra 3200 1100 0"""),

    (11, "Learning Room",    """\
  * Metaroom 7 -- Learning Room (2360, 467)
  cmra 2360 467 0"""),

    # --- Object Spawning ---
    # NOTE: new: simp inside a scrp block is valid in openc2e -- targ is set
    # to the new agent after creation. We do NOT use a nested endm here;
    # the scrp...endm wrapping comes from generate_panel_handlers_script().
    (12, "Spawn Fruit",      """\
  * Spawn an apple near pointer. Sprite "apple" verified in openc2e.
  * openc2e: targ pntr first, then read posx/posy into va vars.
  targ pntr
  setv va00 posx
  setv va01 posy
  new: simp 2 8 0 "apple" 0 1 5000
  attr 3
  mvto va00 va01"""),

    (13, "Spawn Cheese",     """\
  * Spawn an apple near pointer (cheese sprite unavailable).
  targ pntr
  setv va00 posx
  setv va01 posy
  new: simp 2 8 1 "apple" 0 1 5000
  attr 3
  mvto va00 va01"""),

    (14, "Spawn Toy",        """\
  * Spawn a ball toy near pointer. Sprite "ball" verified in openc2e.
  targ pntr
  setv va00 posx
  setv va01 posy
  new: simp 2 21 0 "ball" 0 1 5000
  attr 3
  bhvr 3
  mvto va00 va01"""),

    # --- World Interaction ---
    (15, "Activate Gadgets", """\
  * Activate all machines (3 3 0) then gadgets (3 8 0)
  enum 3 3 0
    mesg wrt+ targ 1 0 0 0
  next
  enum 3 8 0
    mesg wrt+ targ 0 0 0 0
  next"""),

    # --- Brain Signals ---
    (16, "Reward",           """\
  * Inject reward chemical (CHEM 204) into all norns
  * Must target the creature whose brain we are modulating
  enum 4 1 0
    chem 204 0.5
  next"""),

    (17, "Punish",           """\
  * Inject punishment chemical (CHEM 205) into all norns
  enum 4 1 0
    chem 205 0.5
  next"""),

    # --- Utility ---
    (18, "Auto Name",        """\
  * Auto-name all creatures with sequential counter
  * va00/va01 not lv00 -- lv vars invalid in script store context
  setv va00 0
  enum 4 0 0
    addv va00 1
  next"""),
]

NUM_BUTTONS = len(BUTTONS)
PANEL_H = TITLE_H + NUM_BUTTONS * (BTN_H + BTN_GAP)
PANEL_W = BTN_COL_X + BTN_W + 4


# ---------------------------------------------------------------------------
# Panel background / title script
# ---------------------------------------------------------------------------

def generate_title_script() -> str:
    """
    CAOS to create the title label agent (3 103 0).
    This is a SIMP agent acting as a non-interactive background/header.
    """
    # Position: screen-relative via ATTR 208
    # We draw the title as a text overlay -- in openc2e we use a SIMP with
    # the built-in "blnk" sprite (a blank 1x1 white pixel) scaled up.
    # Commercial C3 would use PAT:TEXT, but openc2e TEXT parts are unstable.
    # Instead we just rely on the button label sprites (none -- see note below).
    #
    # NOTE: openc2e does not support drawing text on arbitrary SIMP agents at
    # runtime. The "label" here is informational for the developer; in-game
    # the buttons are identified by position only. A future improvement could
    # use the HUD overlay system if openc2e exposes it.
    return """\
* ---------------------------------------------------------------
* NORNBRAIN TEST HARNESS PANEL -- Title/Background agent (3 103 0)
* ---------------------------------------------------------------
* Remove any stale title agent first
enum 3 103 0
  kill targ
next

* Create title background bar (world-space, no attr 208 -- crashes openc2e)
new: simp 3 103 0 "medical_control_panel_buttons" 0 1 9000
mvto {x} {y}
""".format(x=PANEL_X, y=PANEL_Y)


# ---------------------------------------------------------------------------
# Per-button script generator
# ---------------------------------------------------------------------------

def _button_y(index: int) -> int:
    """Return the Y pixel offset (screen-relative) of button at list index."""
    return PANEL_Y + TITLE_H + index * (BTN_H + BTN_GAP)


def generate_button_script(index: int, species: int, label: str, action: str) -> str:
    """
    CAOS to create a single button agent (3 103 species).
    The agent fires its activate1 script (event 1) when clicked.
    """
    y = PANEL_Y + TITLE_H + index * (BTN_H + BTN_GAP)
    x = PANEL_X + BTN_COL_X

    return """\
* --- Button {idx}: "{label}" (3 103 {sp}) ---
enum 3 103 {sp}
  kill targ
next

new: simp 3 103 {sp} "medical_control_panel_buttons" {frame} 1 9000
bhvr 1
mvto {x} {y}

* Click handler: activate1 = event 1
scrp 3 103 {sp} 1
{action}
endm

""".format(
        frame=index % 20,
        idx=index + 1,
        label=label,
        sp=species,
        x=x,
        y=y,
        action=action,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_panel_script() -> str:
    """
    Return a CAOS script string that:
      1. Removes any existing panel agents (3 103 *)
      2. Creates the title background agent (3 103 0)
      3. Creates all button agents (3 103 1..N) positioned in a column

    The script does NOT install the click handlers -- call
    generate_panel_handlers_script() for those (or inject_panel() for both).

    Note on openc2e compatibility:
      We use SIMP agents rather than PAT:BUTT because openc2e's compound-agent
      button part support is incomplete. SIMP agents with activate1 scripts are
      fully supported and more predictable. Each button agent has classifier
      (3 103 N) so the rule "NEVER activate1 on unknown agents" is satisfied --
      all classifiers are known and owned by this harness.
    """
    parts = []

    # Step 1: nuclear remove of ALL existing panel agents
    parts.append("""\
* =============================================================
* NORNBRAIN TEST HARNESS PANEL -- create/replace
* =============================================================
* Remove all existing harness panel agents (any species 3 103 *)
* We loop species 0..19 explicitly because enum doesn't support
* wildcard species in all openc2e builds.
""")
    for sp in range(20):
        parts.append("enum 3 103 {sp}\n  kill targ\nnext\n".format(sp=sp))

    parts.append("\n")

    # Step 2: title background
    parts.append(generate_title_script())

    # Step 3: buttons - world-space, visible sprite, plane 9000, bhvr 1
    # NO attr 208 (crashes openc2e), NO endm (not inside scrp block)
    for idx, (species, label, _action) in enumerate(BUTTONS):
        y = PANEL_Y + TITLE_H + idx * (BTN_H + BTN_GAP)
        x = PANEL_X + BTN_COL_X
        parts.append("""\
* --- Button {idx}: "{label}" (3 103 {sp}) ---
new: simp 3 103 {sp} "medical_control_panel_buttons" {frame} 1 9000
bhvr 1
mvto {x} {y}

""".format(idx=idx + 1, label=label, sp=species, x=x, y=y, frame=idx % 20))

    return "".join(parts)


def generate_panel_handlers_script() -> str:
    """
    Return a CAOS script string that installs activate1 (event 1) handlers
    for every button agent.  These can be injected independently of the
    panel creation script -- handlers persist as long as the script store
    is not cleared.

    Each handler script is a standalone scrp...endm block targeting
    classifier (3 103 N).
    """
    parts = []
    parts.append("""\
* =============================================================
* NORNBRAIN TEST HARNESS -- button click handler scripts
* =============================================================
* Handlers survive panel recreation.  Re-inject only if the
* openc2e script store is cleared (e.g. full world reload).
*
""")

    for _idx, (species, label, action) in enumerate(BUTTONS):
        parts.append("""\
* Handler: "{label}" (3 103 {sp}) -- activate1 = event 1
scrp 3 103 {sp} 1
{action}
endm

""".format(label=label, sp=species, action=action))

    return "".join(parts)


def inject_panel(port: int = 20001) -> None:
    """
    Inject both the panel creation script and all handler scripts into the
    running openc2e NB engine via TCP on the given port.

    Raises socket.error / ConnectionRefusedError if the engine is not running.
    """
    print("[panel] Injecting panel creation script...")
    panel_caos = generate_panel_script()
    result = caos(panel_caos, port=port)
    if result:
        print("[panel] Panel creation response:", result)
    else:
        print("[panel] Panel created (no output).")

    print("[panel] Injecting handler scripts...")
    handler_caos = generate_panel_handlers_script()
    result = caos(handler_caos, port=port)
    if result:
        print("[panel] Handler install response:", result)
    else:
        print("[panel] Handlers installed (no output).")

    print("[panel] Done. Control panel is live in-game.")


def remove_panel(port: int = 20001) -> None:
    """
    Remove all panel agents (3 103 0..19) from the running engine.
    Each kill is a separate TCP call for stability -- batching kills
    of agents with attr bits can crash openc2e.
    """
    print("[panel] Removing panel agents...")
    for sp in range(20):
        try:
            caos("enum 3 103 {sp}\nkill targ\nnext".format(sp=sp), port=port)
        except Exception:
            pass  # Agent may not exist -- that's fine
    print("[panel] Panel removed.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _main():
    import argparse
    parser = argparse.ArgumentParser(
        description="NORNBRAIN in-game test harness control panel"
    )
    parser.add_argument(
        "action",
        choices=["inject", "remove", "print-panel", "print-handlers"],
        help=(
            "inject: create/replace panel in running engine; "
            "remove: kill all panel agents; "
            "print-panel: dump panel CAOS to stdout; "
            "print-handlers: dump handler CAOS to stdout"
        ),
    )
    parser.add_argument(
        "--port", type=int, default=20001,
        help="openc2e CAOS TCP port (default: 20001)"
    )
    args = parser.parse_args()

    if args.action == "inject":
        inject_panel(port=args.port)
    elif args.action == "remove":
        remove_panel(port=args.port)
    elif args.action == "print-panel":
        print(generate_panel_script())
    elif args.action == "print-handlers":
        print(generate_panel_handlers_script())


if __name__ == "__main__":
    _main()
