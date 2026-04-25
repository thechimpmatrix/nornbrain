# NORNBRAIN Test Harness: Design Specification

**Created:** 2026-04-02
**Campaign:** NORNBRAIN Test Harness
**Branch:** feature/test-harness
**Goal:** in-game testing controls + remote-access TCP API

---

## Architecture

Two layers sharing the same CAOS logic:

```
┌─────────────────────────────────┐
│  In-Game CAOS Control Panel     │  ← Player clicks buttons
│  (compound agent, family 3)     │
├─────────────────────────────────┤
│  Python Test Harness CLI        │  ← CC or user runs commands
│  tools/test_harness.py          │
├─────────────────────────────────┤
│  CAOS TCP (port 20001)          │  ← Shared transport
│  caos() helper function         │
└─────────────────────────────────┘
```

### File Structure

```
tools/test_harness.py         : Main CLI + Python API (ALL harness functions)
tools/test_harness_caos.py    : CAOS script generator for in-game panel agent
tools/test_harness_overlay.py : CAOS script generator for overlay agents
tests/test_harness_test.py    : Unit tests (mock TCP, verify CAOS output)
```

---

## Module 1: Core Infrastructure (tools/test_harness.py)

### CAOS TCP Helper

```python
import socket, json, sys, argparse

def caos(cmd: str, port: int = 20001) -> str:
    """Send CAOS command via TCP, return response string."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    s.connect(('127.0.0.1', port))
    s.sendall((cmd + '\nrscr\n').encode('latin-1'))
    data = b''
    while True:
        chunk = s.recv(65536)
        if not chunk:
            break
        data += chunk
    s.close()
    return data.decode('latin-1').strip()

def caos_json(cmd: str, port: int = 20001) -> dict:
    """Send CAOS, return parsed result as JSON-friendly dict."""
    raw = caos(cmd, port)
    return {"ok": True, "result": raw}
```

### CLI Interface

```
python tools/test_harness.py <command> [args] [--json] [--port 20001]
```

Every command prints human-readable output by default. `--json` flag outputs structured JSON for CC parsing.

---

## Module 2: Creature Management

### Commands

| Command | CAOS Logic | Notes |
|---------|-----------|-------|
| `spawn-eggs [n=2]` | Activate Norn Egg Layer (3 3 31) n times: `enum 3 3 31 mesg writ targ 1 0 0 next` with delay | MUST use egg layer per project rules |
| `hatch-all` | `enum 3 4 0 tick targ 9999 next`: force-tick all creature eggs | Skips incubation time |
| `spawn-and-hatch [n=2]` | Combined: spawn-eggs + wait + hatch-all | Convenience |
| `kill-grendels` | `enum 4 2 0 kill targ next` | Genus 2 only, verified |
| `kill-ettins` | `enum 4 3 0 kill targ next` | Genus 3 only |
| `kill-creature <id>` | Target by GAME var `lnn_norn_<id>` moniker, then `kill targ` | Uses auto-naming system |
| `teleport-to-hand [creature-id]` | `targ norn enum 4 1 0 ... mvto posx hand posy hand` or by ID | Moves norn to hand position |
| `teleport-all-norns <metaroom>` | Get metaroom centre coords, `enum 4 1 0 mvto X Y next` | Uses metaroom lookup table |
| `freeze <creature-id>` | `zomb targ 1` | Freezes creature movement |
| `unfreeze <creature-id>` | `zomb targ 0` | Unfreezes |
| `set-age <creature-id> <stage>` | `ages <stage>` on target creature | 0=baby..6=senile |
| `list-creatures` | Enumerate all family 4, report genus/species/position/name/drives | Returns JSON array |
| `auto-name-all` | Assign sequential IDs (NB-001, NB-002...) to all unnamed norns | Stores in GAME var `lnn_name_<moniker>` |
| `population` | Count by genus: norns, grendels, ettins | Quick headcount |

### Auto-Naming System

```python
def auto_name_all():
    """Assign NB-XXX IDs to all creatures, store in GAME vars."""
    # Get current highest ID
    next_id = int(caos('outv game "lnn_next_id"') or '1')
    # Enumerate all creatures
    creatures = enumerate_creatures()
    for c in creatures:
        existing = caos(f'outs game "lnn_name_{c["moniker"]}"')
        if not existing or existing == '':
            name = f'NB-{next_id:03d}'
            caos(f'setv game "lnn_next_id" {next_id + 1}')
            caos(f'sets game "lnn_name_{c["moniker"]}" "{name}"')
            next_id += 1
    return list_creatures()
```

---

## Module 3: World State & Environment

### Commands

| Command | CAOS Logic | Notes |
|---------|-----------|-------|
| `save-world` | `save` | Save world state without exiting: verify openc2e supports this |
| `teleport-camera <metaroom-name>` | `cmra X Y 0` where X,Y from lookup table | Named presets below |
| `activate-all-gadgets` | `enum 3 3 0 mesg writ targ 1 0 0 next` then `enum 3 8 0 mesg writ targ 0 0 0 next` | Fire activate on all machinery + gadgets |
| `clear-non-creatures` | Enumerate non-family-4, store classifiers+positions, then kill | Saves state for restore |
| `restore-agents` | Re-inject from saved state | Limited: can only restore what was catalogued |
| `world-info` | Report: agent count, creature count, bioenergy, tick count | Quick world status |

### Metaroom Lookup Table

```python
METAROOMS = {
    "norn-terrarium": (0, 1190, 712),
    "ettin-desert":   (1, 5190, 704),
    "aquatic":        (2, 9000, 1200),
    "grendel-jungle": (3, 1948, 2310),
    "corridor":       (4, 3200, 1100),
    "pinball":        (5, 6000, 2000),
    "space":          (6, 9000, 500),
    "learning-room":  (7, 2360, 467),
    "crypt":          (8, 3200, 2500),
}
```

---

## Module 4: Agent Spawning

### Commands

| Command | CAOS Logic | Notes |
|---------|-----------|-------|
| `spawn-food [type] [n=1]` | Activate food dispensers/makers to produce food naturally | Prefers ecosystem spawning |
| `spawn-food-direct <classifier> [x] [y]` | `new: simp F G S ...` at position | WARNING: drains bioenergy |
| `spawn-toy [x] [y]` | Create toy agent at position | Uses known toy classifiers |
| `spawn-potion <type> [x] [y]` | Create potion agent | 12 potion types from game-files-analysis |
| `list-food` | Count all food agents by type | Enumerate 2 6-11 0 * |
| `list-toys` | Count all toy agents | Enumerate 2 21 0 * |

### Food Types (safe to spawn directly for testing)

```python
FOOD_ITEMS = {
    "fruit":   {"family": 2, "genus": 8, "species": 0},
    "cheese":  {"family": 2, "genus": 11, "species": 1},
    "carrot":  {"family": 2, "genus": 11, "species": 3},  # Note: injects chem 75 (alcohol)
    "plant":   {"family": 2, "genus": 4, "species": 0},
    "seed":    {"family": 2, "genus": 3, "species": 0},
}
```

---

## Module 5: Biochemistry & RL Controls

### Commands

| Command | CAOS Logic | Notes |
|---------|-----------|-------|
| `inject-chem <creature-id> <chem#> <amount>` | `targ <creature> chem <N> <amount>` | Any chemical 0-255 |
| `inject-reward [creature-id] [amount=0.5]` | `chem 204 <amount>` | Reward = CHEM 204 |
| `inject-punishment [creature-id] [amount=0.5]` | `chem 205 <amount>` | Punishment = CHEM 205 |
| `read-drives [creature-id]` | `driv 0` through `driv 19` | Returns all 20 drive levels |
| `read-chems [creature-id] <chem-list>` | `chem N` for each | Reads specific chemicals |
| `fire-stimulus <creature-id> <stim#> [intensity=1]` | `stim writ targ <N> <I>` | Fire arbitrary stimulus |
| `set-drive <creature-id> <drive#> <level>` | Inject opposing chemicals to shift drive | Indirect: drives aren't directly writable |
| `creature-status [creature-id]` | Combined: drives, key chems, age, position, name | Full creature snapshot |
| `tick-count` | `outv totl 0 0 0` + `outv game "engine_tick_count"` | World tick counter |

### Drive Index (for reference)

```python
DRIVES = {
    0: "pain", 1: "hunger_protein", 2: "hunger_carb", 3: "hunger_fat",
    4: "coldness", 5: "hotness", 6: "tiredness", 7: "sleepiness",
    8: "loneliness", 9: "crowdedness", 10: "fear", 11: "boredom",
    12: "anger", 13: "sex_drive", 14: "injury", 15: "suffocation",
    16: "thirst", 17: "stress", 18: "backlash", 19: "comfort",
}
```

---

## Module 6: In-Game Overlay Agents

These are CAOS compound agents injected into the game that display information.

### Norn ID Label (floating above each creature)

```caos
* Create a floating label agent that follows a creature
new: comp 3 100 0 "blnk" 1 1 1
* Timer script updates position to follow creature
* Uses PAT: TEXT to display norn name
```

### Drive Bar Display

A compound agent showing the selected creature's top 5 drives as coloured bars, positioned at top-right of screen. Updated every 10 ticks via timer script.

### World Info Overlay

Fixed-position compound agent showing:
- World tick count
- Creature population (N/G/E counts)  
- Current metaroom name
- Bioenergy level

---

## Module 7: In-Game Control Panel

A CAOS compound agent with buttons. Positioned at screen edge, always visible.

### Panel Layout

```
┌──────────────────────────┐
│  NORNBRAIN TEST HARNESS  │
├──────────────────────────┤
│ [Spawn 2 Eggs] [Hatch]   │
│ [Kill Grendels] [TP Hand] │
│ [Save World]              │
├──────────────────────────┤
│ TELEPORT:                 │
│ [Norn T] [Desert] [Jungle]│
│ [Aqua] [Corridor] [Learn] │
├──────────────────────────┤
│ SPAWN:                    │
│ [Fruit] [Cheese] [Toy]   │
├──────────────────────────┤
│ [Activate All Gadgets]    │
│ [Reward] [Punish]         │
│ [Clear Agents] [Restore]  │
└──────────────────────────┘
```

Each button fires a CAOS script via `mesg writ` to the panel agent's own script handlers (events 1000+). The panel agent's scripts contain the same CAOS logic as the Python harness.

### Panel Injection

```python
def inject_panel():
    """Inject the in-game control panel as a CAOS compound agent."""
    caos(panel_creation_script)
    caos(panel_button_scripts)
    caos(panel_timer_script)
```

---

## Module 8: Tests

### test_harness_test.py

```python
# Test categories:
# 1. CAOS generation tests (no TCP needed): verify correct CAOS strings produced
# 2. CLI argument parsing tests
# 3. Integration tests (need running engine): marked with @pytest.mark.integration
# 4. Metaroom lookup table completeness
# 5. Classifier table accuracy vs game-files-analysis.md
```

---

## Implementation Priority (for autobuild)

**Stage 1 (core: must work):**
- tools/test_harness.py with caos() helper, CLI framework, and ALL creature management + world state commands
- tests/test_harness_test.py with CAOS generation tests

**Stage 2 (spawning + biochem):**
- Agent spawning commands
- Biochemistry & RL control commands
- Extended tests

**Stage 3 (overlays + panel):**
- In-game overlay CAOS scripts
- In-game control panel CAOS agent
- tools/test_harness_overlay.py
- tools/test_harness_caos.py

**Stage 4 (polish + integration):**
- Batch command support
- JSON output mode for all commands
- Desktop shortcut for harness
- Full integration test with engine

---

## CAOS Safety Rules (from project CLAUDE.md)

- NEVER fire activate1 on unknown agents (many self-destruct)
- ALWAYS verify genus before targeting creatures (1=norn, 2=grendel, 3=ettin)
- Use `lnn_` prefix for all GAME variables
- Spawn norns ONLY via Norn Egg Layer (3 3 31)
- Terminate all CAOS with `rscr\n`
- Do NOT consume bioenergy from bridge/harness unless explicitly testing
