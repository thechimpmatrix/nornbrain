"""
NORNBRAIN Test Harness - tools/test_harness.py

Controls Creatures 3 (openc2e NB engine) via CAOS over TCP port 20001.

Rules:
- Spawn norns ONLY via Norn Egg Layer (3 3 31)
- Use lnn_ prefix for ALL GAME variables
- NEVER fire activate1 on unknown agents
- Verify genus before targeting: 1=norn, 2=grendel, 3=ettin
- Reward = CHEM 204, Punishment = CHEM 205
- CAOS commands terminated with rscr\n
"""

import socket
import json
import sys
import argparse
import time
import os
import tempfile

# ---------------------------------------------------------------------------
# Core Infrastructure
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

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

DRIVES = {
    0: "pain",
    1: "hunger_protein",
    2: "hunger_carb",
    3: "hunger_fat",
    4: "coldness",
    5: "hotness",
    6: "tiredness",
    7: "sleepiness",
    8: "loneliness",
    9: "crowdedness",
    10: "fear",
    11: "boredom",
    12: "anger",
    13: "sex_drive",
    14: "injury",
    15: "suffocation",
    16: "thirst",
    17: "stress",
    18: "backlash",
    19: "comfort",
}

FOOD_ITEMS = {
    "fruit":  (2, 8, 0),
    "cheese": (2, 11, 1),
    "carrot": (2, 11, 3),
    "plant":  (2, 4, 0),
    "seed":   (2, 3, 0),
}

GENUS_NAMES = {1: "norn", 2: "grendel", 3: "ettin"}

# Temp file for storing agent classifiers before clear
_AGENT_BACKUP_FILE = os.path.join(tempfile.gettempdir(), "nornbrain_agents_backup.json")


# ---------------------------------------------------------------------------
# Output Formatting
# ---------------------------------------------------------------------------

_json_mode = False
_port = 20001


def output_result(data, label: str = "result"):
    """Print data in human-readable or JSON format depending on _json_mode."""
    if _json_mode:
        if isinstance(data, str):
            print(json.dumps({label: data}))
        else:
            print(json.dumps(data, indent=2, default=str))
    else:
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, dict):
                    print(f"  {k}:")
                    for kk, vv in v.items():
                        print(f"    {kk}: {vv}")
                elif isinstance(v, list):
                    print(f"  {k}: [{', '.join(str(x) for x in v)}]")
                else:
                    print(f"  {k}: {v}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                print(f"[{i}]")
                if isinstance(item, dict):
                    for k, v in item.items():
                        print(f"  {k}: {v}")
                else:
                    print(f"  {item}")
        else:
            print(data)


# ---------------------------------------------------------------------------
# 3. Creature Management Functions
# ---------------------------------------------------------------------------

def spawn_eggs_caos_cmd(n: int = 2) -> list:
    """Return CAOS strings for spawning n eggs via Norn Egg Layer (3 3 31).
    Message 1001 = hatch button on the egg layer control panel.
    Uses mesg wrt+ (5 args: agent, msg_id, param1, param2, delay)."""
    cmds = []
    for _ in range(n):
        cmds.append("enum 3 3 31\nmesg wrt+ targ 1001 0 0 0\nnext")
    return cmds


def spawn_eggs(n: int = 2, port: int = None) -> dict:
    """Activate Norn Egg Layer n times to spawn n eggs."""
    p = port or _port
    cmds = spawn_eggs_caos_cmd(n)
    for cmd in cmds:
        caos(cmd, port=p)
        time.sleep(0.3)
    return {"spawned_eggs": n, "status": "ok"}


def hatch_all_caos_cmd() -> list:
    """Return CAOS strings for force-hatching all creature eggs.
    Egg species is 1 (3 4 1). Skip incubation: pose 3 then tick 1.
    Per cc-handbook.md verified recipe."""
    return ["enum 3 4 1\npose 3\ntick 1\nnext"]


def hatch_all(port: int = None) -> dict:
    """Force-tick all creature eggs to hatch them immediately."""
    p = port or _port
    for cmd in hatch_all_caos_cmd():
        caos(cmd, port=p)
    return {"status": "ok", "action": "hatch_all"}


def spawn_and_hatch_caos_cmd(n: int = 2) -> list:
    """Return CAOS strings for spawn_eggs + hatch_all."""
    cmds = spawn_eggs_caos_cmd(n)
    cmds.extend(hatch_all_caos_cmd())
    return cmds


def spawn_and_hatch(n: int = 2, port: int = None) -> dict:
    """Spawn n eggs via egg layer, wait 3s, then hatch all."""
    p = port or _port
    result = spawn_eggs(n, port=p)
    time.sleep(3)
    hatch_all(port=p)
    result["hatched"] = True
    return result


def kill_grendels_caos_cmd() -> list:
    """Return CAOS string to kill all grendels."""
    return ["enum 4 2 0\nkill targ\nnext"]


def kill_grendels(port: int = None) -> dict:
    """Kill all grendel creatures in the world."""
    p = port or _port
    for cmd in kill_grendels_caos_cmd():
        caos(cmd, port=p)
    return {"status": "ok", "action": "kill_grendels"}


def kill_ettins_caos_cmd() -> list:
    """Return CAOS string to kill all ettins."""
    return ["enum 4 3 0\nkill targ\nnext"]


def kill_ettins(port: int = None) -> dict:
    """Kill all ettin creatures in the world."""
    p = port or _port
    for cmd in kill_ettins_caos_cmd():
        caos(cmd, port=p)
    return {"status": "ok", "action": "kill_ettins"}


def teleport_to_hand_caos_cmd() -> list:
    """Return CAOS strings to teleport all norns to camera centre."""
    return [
        "outv cmrx",
        "outv cmry",
    ]


def teleport_to_hand(port: int = None) -> dict:
    """Teleport all norns to camera centre (openc2e: pntr not supported)."""
    p = port or _port
    x_str = caos("outv cmrx", port=p)
    y_str = caos("outv cmry", port=p)
    try:
        x = float(x_str)
        y = float(y_str)
    except ValueError:
        return {"status": "error", "reason": f"could not parse camera position: x={x_str!r} y={y_str!r}"}
    move_cmd = f"enum 4 1 0\nmvsf {x:.0f} {y:.0f}\nnext"
    caos(move_cmd, port=p)
    return {"status": "ok", "action": "teleport_to_camera_centre", "x": x, "y": y}


def teleport_all_norns_caos_cmd(metaroom_name: str) -> list:
    """Return CAOS string to teleport all norns to named metaroom."""
    if metaroom_name not in METAROOMS:
        raise ValueError(f"Unknown metaroom: {metaroom_name!r}. Valid: {list(METAROOMS.keys())}")
    _, x, y = METAROOMS[metaroom_name]
    return [f"enum 4 1 0\nmvto targ {x} {y}\nnext"]


def teleport_all_norns(metaroom_name: str, port: int = None) -> dict:
    """Teleport all norns to the named metaroom."""
    p = port or _port
    cmds = teleport_all_norns_caos_cmd(metaroom_name)
    for cmd in cmds:
        caos(cmd, port=p)
    _, x, y = METAROOMS[metaroom_name]
    return {"status": "ok", "action": "teleport_all_norns", "metaroom": metaroom_name, "x": x, "y": y}


def freeze_creature_caos_cmd(creature_id: str) -> list:
    """Return CAOS string to freeze (zombify) a creature by NB-ID."""
    var_name = f"lnn_name_{creature_id.replace('-', '_')}"
    return [
        f'sets va00 game "{var_name}"\n'
        f'enum 4 1 0\n'
        f'doif hist name targ 0 eq va00\n'
        f'zomb targ 1\n'
        f'stop\n'
        f'endi\n'
        f'next'
    ]


def freeze_creature(creature_id: str, port: int = None) -> dict:
    """Freeze (zombify) a creature so it cannot move."""
    p = port or _port
    # Look up moniker from lnn_name_<id> game var
    var_key = f"lnn_name_{creature_id.replace('-', '_')}"
    moniker = caos(f'outs game "{var_key}"', port=p).strip()
    if not moniker:
        # Try a direct enum matching hist name
        cmd = (
            f'sets va00 "{creature_id}"\n'
            f'enum 4 1 0\n'
            f'doif hist name targ 0 eq va00\n'
            f'zomb targ 1\n'
            f'stop\n'
            f'endi\n'
            f'next'
        )
        caos(cmd, port=p)
        return {"status": "ok", "creature_id": creature_id, "frozen": True}
    # Use moniker to target
    cmd = (
        f'sets va00 "{moniker}"\n'
        f'enum 4 1 0\n'
        f'doif hist name targ 0 eq va00\n'
        f'zomb targ 1\n'
        f'stop\n'
        f'endi\n'
        f'next'
    )
    caos(cmd, port=p)
    return {"status": "ok", "creature_id": creature_id, "moniker": moniker, "frozen": True}


def unfreeze_creature_caos_cmd(creature_id: str) -> list:
    """Return CAOS string to unfreeze (un-zombify) a creature by NB-ID."""
    return [
        f'sets va00 "{creature_id}"\n'
        f'enum 4 1 0\n'
        f'doif hist name targ 0 eq va00\n'
        f'zomb targ 0\n'
        f'stop\n'
        f'endi\n'
        f'next'
    ]


def unfreeze_creature(creature_id: str, port: int = None) -> dict:
    """Unfreeze (un-zombify) a creature so it can move again."""
    p = port or _port
    var_key = f"lnn_name_{creature_id.replace('-', '_')}"
    moniker = caos(f'outs game "{var_key}"', port=p).strip()
    if not moniker:
        cmd = (
            f'sets va00 "{creature_id}"\n'
            f'enum 4 1 0\n'
            f'doif hist name targ 0 eq va00\n'
            f'zomb targ 0\n'
            f'stop\n'
            f'endi\n'
            f'next'
        )
        caos(cmd, port=p)
        return {"status": "ok", "creature_id": creature_id, "frozen": False}
    cmd = (
        f'sets va00 "{moniker}"\n'
        f'enum 4 1 0\n'
        f'doif hist name targ 0 eq va00\n'
        f'zomb targ 0\n'
        f'stop\n'
        f'endi\n'
        f'next'
    )
    caos(cmd, port=p)
    return {"status": "ok", "creature_id": creature_id, "moniker": moniker, "frozen": False}


def set_age_caos_cmd(creature_id: str, stage: int) -> list:
    """Return CAOS string to set a creature's age stage."""
    return [
        f'sets va00 "{creature_id}"\n'
        f'enum 4 1 0\n'
        f'doif hist name targ 0 eq va00\n'
        f'ages {stage}\n'
        f'stop\n'
        f'endi\n'
        f'next'
    ]


def set_age(creature_id: str, stage: int, port: int = None) -> dict:
    """Set life stage for a creature (0=baby .. 6=senile)."""
    p = port or _port
    cmds = set_age_caos_cmd(creature_id, stage)
    for cmd in cmds:
        caos(cmd, port=p)
    return {"status": "ok", "creature_id": creature_id, "stage": stage}


def list_creatures_caos_cmd() -> list:
    """Return CAOS strings to enumerate creature data fields."""
    # Each field queried separately per creature; for bulk use we do a combined output
    return [
        "enum 4 1 0\nouts hist name targ 0\nouts \"|\"\noutv unid targ\nouts \"|\"\noutv gnus targ\nouts \"|\"\noutv posx targ\nouts \"|\"\noutv posy targ\nouts \"\\n\"\nnext"
    ]


def list_creatures(port: int = None) -> list:
    """
    Enumerate all family-4 creatures by genus.
    Returns list of dicts with: genus, genus_name, x, y.
    Queries each genus separately for reliable parsing.
    """
    p = port or _port
    creatures = []
    for genus in [1, 2, 3]:
        count = int(caos(f"outv totl 4 {genus} 0", port=p) or "0")
        if count == 0:
            continue
        # Get positions as semicolon-separated pairs
        raw = caos(
            f'enum 4 {genus} 0\n'
            f'outv posx\nouts ","\noutv posy\nouts ";"\n'
            f'next',
            port=p,
        )
        genus_name = GENUS_NAMES.get(genus, f"unknown({genus})")
        # Parse "x,y;x,y;" format
        for entry in raw.strip().split(";"):
            entry = entry.strip()
            if not entry:
                continue
            parts = entry.split(",")
            if len(parts) < 2:
                continue
            try:
                x = float(parts[0].strip())
                y = float(parts[1].strip())
            except (ValueError, IndexError):
                continue
            creatures.append({
                "genus": genus,
                "genus_name": genus_name,
                "x": x,
                "y": y,
            })
    return creatures


def auto_name_all_caos_cmd() -> list:
    """Return description of the CAOS logic used for auto-naming."""
    return [
        'setv va00 game "lnn_next_id"\n'
        'enum 4 0 0\n'
        '  <assign NB-XXX names to unnamed creatures>\n'
        'next'
    ]


def auto_name_all(port: int = None) -> dict:
    """
    Assign NB-XXX sequential IDs to all creatures. Stores the mapping
    in GAME vars with lnn_ prefix and also sets the creature's actual
    in-game name via hist name (readable by the engine and monitor).
    Uses UNID as the unique key per creature.
    """
    p = port or _port
    # Get current next_id counter
    next_id_str = caos('outv game "lnn_next_id"', port=p).strip()
    try:
        next_id = int(float(next_id_str)) if next_id_str else 0
    except ValueError:
        next_id = 0

    assignments = {}
    for genus in [1, 2, 3]:
        count_str = caos(f"outv totl 4 {genus} 0", port=p).strip()
        count = int(float(count_str)) if count_str else 0
        if count == 0:
            continue
        # Get UNIDs for this genus
        raw = caos(f'enum 4 {genus} 0\noutv unid\nouts ","\nnext', port=p).strip()
        for unid_str in raw.split(","):
            unid_str = unid_str.strip()
            if not unid_str:
                continue
            try:
                unid = int(float(unid_str))
            except ValueError:
                continue
            # Check if already named
            var_key = f"lnn_id_{unid}"
            existing = caos(f'outs game "{var_key}"', port=p).strip()
            if not existing:
                nb_id = f"NB-{next_id:03d}"
                caos(f'sets game "{var_key}" "{nb_id}"', port=p)
                # Set the actual in-game creature name via hist name
                # GTOS 0 gets the moniker from genome slot 0, then hist name sets the name
                caos(
                    f'enum 4 {genus} 0\n'
                    f'doif unid eq {unid}\n'
                    f'sets va00 gtos 0\n'
                    f'hist name va00 "{nb_id}"\n'
                    f'stop\n'
                    f'endi\n'
                    f'next',
                    port=p,
                )
                assignments[nb_id] = {"unid": unid, "genus": GENUS_NAMES.get(genus, str(genus))}
                next_id += 1

    # Save updated counter
    caos(f'setv game "lnn_next_id" {next_id}', port=p)

    return {"status": "ok", "assignments": assignments, "next_id": next_id}


def population_caos_cmd() -> list:
    """Return CAOS strings to count creatures by genus."""
    return [
        "outv totl 4 1 0",
        "outv totl 4 2 0",
        "outv totl 4 3 0",
    ]


def population(port: int = None) -> dict:
    """Count creatures by genus: norns, grendels, ettins."""
    p = port or _port
    norns_str = caos("outv totl 4 1 0", port=p)
    grendels_str = caos("outv totl 4 2 0", port=p)
    ettins_str = caos("outv totl 4 3 0", port=p)
    try:
        norns = int(float(norns_str))
    except ValueError:
        norns = -1
    try:
        grendels = int(float(grendels_str))
    except ValueError:
        grendels = -1
    try:
        ettins = int(float(ettins_str))
    except ValueError:
        ettins = -1
    total = max(0, norns) + max(0, grendels) + max(0, ettins)
    return {
        "norns": norns,
        "grendels": grendels,
        "ettins": ettins,
        "total_creatures": total,
    }


# ---------------------------------------------------------------------------
# 4. World State & Environment Functions
# ---------------------------------------------------------------------------

def save_world_caos_cmd() -> list:
    """Return CAOS string to save the world."""
    return ["save"]


def save_world(port: int = None) -> dict:
    """Save the current game world."""
    p = port or _port
    caos("save", port=p)
    return {"status": "ok", "action": "save_world"}


def teleport_camera_caos_cmd(metaroom_name: str) -> list:
    """Return CAOS string to move camera to named metaroom."""
    if metaroom_name not in METAROOMS:
        raise ValueError(f"Unknown metaroom: {metaroom_name!r}. Valid: {list(METAROOMS.keys())}")
    _, x, y = METAROOMS[metaroom_name]
    return [f"cmra {x} {y} 0"]


def teleport_camera(metaroom_name: str, port: int = None) -> dict:
    """Move camera to the named metaroom."""
    p = port or _port
    cmds = teleport_camera_caos_cmd(metaroom_name)
    for cmd in cmds:
        caos(cmd, port=p)
    _, x, y = METAROOMS[metaroom_name]
    return {"status": "ok", "action": "teleport_camera", "metaroom": metaroom_name, "x": x, "y": y}


def activate_all_gadgets_caos_cmd() -> list:
    """Return CAOS strings to activate machines and gadgets."""
    return [
        "enum 3 3 0\nmesg wrt+ targ 1 0 0 0\nnext",
        "enum 3 8 0\nmesg wrt+ targ 0 0 0 0\nnext",
    ]


def activate_all_gadgets(port: int = None) -> dict:
    """Activate all machines (family 3 genus 3) and gadgets (family 3 genus 8)."""
    p = port or _port
    for cmd in activate_all_gadgets_caos_cmd():
        caos(cmd, port=p)
    return {"status": "ok", "action": "activate_all_gadgets"}


def clear_non_creatures_caos_cmd() -> list:
    """Return description of clear_non_creatures logic."""
    return [
        "enum 0 0 0  # enumerate all non-creature, non-pointer agents\n"
        "  # store classifiers, then kill targ\n"
        "next"
    ]


def clear_non_creatures(port: int = None) -> dict:
    """
    Enumerate non-creature, non-pointer agents, record their classifiers to a
    temp file, then kill them. Returns count of agents killed.

    Skips: family 4 (creatures), family 2 genus 1 species 0 (pointer).
    Also skips family 0 agents (world meta-objects) and family 1 (C1/C2 compat).
    """
    p = port or _port
    # Collect agent data first
    cmd_collect = (
        'sets va99 ""\n'
        'enum 0 0 0\n'
        '  setv va10 fmly targ\n'
        '  setv va11 gnus targ\n'
        '  setv va12 spcs targ\n'
        '  doif va10 ne 4\n'
        '  doif va10 ne 2\n'  # skip pointer family-2-genus-1
        '  doif va10 gt 1\n'  # skip meta-objects family 0 and 1
        '    addv va99 va10\n'
        '    adds va99 " "\n'
        '    addv va99 va11\n'
        '    adds va99 " "\n'
        '    addv va99 va12\n'
        '    adds va99 "\\n"\n'
        '  endi\n'
        '  endi\n'
        '  endi\n'
        'next\n'
        'outs va99'
    )
    raw = caos(cmd_collect, port=p)
    agents = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) == 3:
            try:
                agents.append({
                    "family": int(float(parts[0])),
                    "genus": int(float(parts[1])),
                    "species": int(float(parts[2])),
                })
            except ValueError:
                continue

    # Save backup
    with open(_AGENT_BACKUP_FILE, "w") as f:
        json.dump(agents, f, indent=2)

    # Now kill them
    kill_cmd = (
        'enum 0 0 0\n'
        '  setv va10 fmly targ\n'
        '  doif va10 ne 4\n'
        '  doif va10 ne 2\n'
        '  doif va10 gt 1\n'
        '    kill targ\n'
        '  endi\n'
        '  endi\n'
        '  endi\n'
        'next'
    )
    caos(kill_cmd, port=p)
    return {
        "status": "ok",
        "action": "clear_non_creatures",
        "agents_killed": len(agents),
        "backup_file": _AGENT_BACKUP_FILE,
    }


def restore_agents_caos_cmd() -> list:
    """Stub - full restoration from backup requires object re-creation."""
    return ["# restore_agents: reads backup file and re-injects agents (stub)"]


def restore_agents(port: int = None) -> dict:
    """
    Stub: Read the agent backup file and attempt to re-create agents.
    Full restoration is complex (requires knowing each agent's CAOS script).
    This stub reports what was backed up.
    """
    if not os.path.exists(_AGENT_BACKUP_FILE):
        return {"status": "error", "reason": "no backup file found", "path": _AGENT_BACKUP_FILE}
    with open(_AGENT_BACKUP_FILE) as f:
        agents = json.load(f)
    return {
        "status": "stub",
        "note": "Full agent restoration not implemented - backup data returned only.",
        "backup_file": _AGENT_BACKUP_FILE,
        "agent_count": len(agents),
        "agents": agents,
    }


def world_info_caos_cmd() -> list:
    """Return CAOS strings to query world info."""
    return [
        "outv totl 0 0 0",
        "outv totl 4 1 0",
        "outv totl 4 2 0",
        "outv totl 4 3 0",
        'outv game "Bioenergy"',
    ]


def world_info(port: int = None) -> dict:
    """Return dict with total agents, creature counts, and bioenergy."""
    p = port or _port
    total_str = caos("outv totl 0 0 0", port=p)
    norns_str = caos("outv totl 4 1 0", port=p)
    grendels_str = caos("outv totl 4 2 0", port=p)
    ettins_str = caos("outv totl 4 3 0", port=p)
    bioenergy_str = caos('outv game "Bioenergy"', port=p)

    def safe_int(s):
        try:
            return int(float(s))
        except (ValueError, TypeError):
            return -1

    def safe_float(s):
        try:
            return float(s)
        except (ValueError, TypeError):
            return -1.0

    return {
        "total_agents": safe_int(total_str),
        "norns": safe_int(norns_str),
        "grendels": safe_int(grendels_str),
        "ettins": safe_int(ettins_str),
        "bioenergy": safe_float(bioenergy_str),
    }


# ---------------------------------------------------------------------------
# 5. Agent Spawning Functions
# ---------------------------------------------------------------------------

def spawn_food_caos_cmd(food_type: str = "fruit", x: float = None, y: float = None) -> list:
    """Return CAOS string to create a food agent."""
    if food_type not in FOOD_ITEMS:
        raise ValueError(f"Unknown food type: {food_type!r}. Valid: {list(FOOD_ITEMS.keys())}")
    fam, gen, spc = FOOD_ITEMS[food_type]
    if x is None or y is None:
        return [f"new: simp {fam} {gen} {spc} \"\" 1 0 0\nmvto targ posx pntr posy pntr"]
    return [f"new: simp {fam} {gen} {spc} \"\" 1 0 0\nmvto targ {x:.1f} {y:.1f}"]


def spawn_food(food_type: str = "fruit", x: float = None, y: float = None, port: int = None) -> dict:
    """Create a food agent at given position (or hand position if x/y not given)."""
    p = port or _port
    if x is None or y is None:
        x_str = caos("outv posx pntr", port=p).strip()
        y_str = caos("outv posy pntr", port=p).strip()
        try:
            x = float(x_str)
            y = float(y_str)
        except ValueError:
            x, y = 1190.0, 712.0
    fam, gen, spc = FOOD_ITEMS[food_type]
    cmd = f'new: simp {fam} {gen} {spc} "" 1 0 0\nmvto targ {x:.1f} {y:.1f}'
    caos(cmd, port=p)
    return {"status": "ok", "food_type": food_type, "x": x, "y": y, "classifier": f"{fam}/{gen}/{spc}"}


def spawn_toy_caos_cmd(x: float = None, y: float = None) -> list:
    """Return CAOS string to create a toy agent (2 21 0)."""
    if x is None or y is None:
        return ['new: simp 2 21 0 "" 1 0 0\nmvto targ posx pntr posy pntr']
    return [f'new: simp 2 21 0 "" 1 0 0\nmvto targ {x:.1f} {y:.1f}']


def spawn_toy(x: float = None, y: float = None, port: int = None) -> dict:
    """Create a toy agent at given position (or hand position if x/y not given)."""
    p = port or _port
    if x is None or y is None:
        x_str = caos("outv posx pntr", port=p).strip()
        y_str = caos("outv posy pntr", port=p).strip()
        try:
            x = float(x_str)
            y = float(y_str)
        except ValueError:
            x, y = 1190.0, 712.0
    cmd = f'new: simp 2 21 0 "" 1 0 0\nmvto targ {x:.1f} {y:.1f}'
    caos(cmd, port=p)
    return {"status": "ok", "toy": "2/21/0", "x": x, "y": y}


def list_food_caos_cmd() -> list:
    """Return CAOS strings to count food by type."""
    cmds = []
    for fname, (fam, gen, spc) in FOOD_ITEMS.items():
        cmds.append(f"outv totl {fam} {gen} {spc}")
    return cmds


def list_food(port: int = None) -> dict:
    """Count food agents by type."""
    p = port or _port
    counts = {}
    for fname, (fam, gen, spc) in FOOD_ITEMS.items():
        raw = caos(f"outv totl {fam} {gen} {spc}", port=p).strip()
        try:
            counts[fname] = int(float(raw))
        except ValueError:
            counts[fname] = -1
    return counts


def list_toys_caos_cmd() -> list:
    """Return CAOS string to count toys."""
    return ["outv totl 2 21 0"]


def list_toys(port: int = None) -> dict:
    """Count toy agents in the world."""
    p = port or _port
    raw = caos("outv totl 2 21 0", port=p).strip()
    try:
        count = int(float(raw))
    except ValueError:
        count = -1
    return {"toys": count, "classifier": "2/21/0"}


# ---------------------------------------------------------------------------
# 6. Biochemistry & RL Functions
# ---------------------------------------------------------------------------

def inject_chem_caos_cmd(creature_id: str, chem_num: int, amount: float) -> list:
    """Return CAOS string to inject a chemical into a named creature."""
    return [
        f'sets va00 "{creature_id}"\n'
        f'enum 4 0 0\n'
        f'doif hist name targ 0 eq va00\n'
        f'chem {chem_num} {amount:.4f}\n'
        f'stop\n'
        f'endi\n'
        f'next'
    ]


def inject_chem(creature_id: str, chem_num: int, amount: float, port: int = None) -> dict:
    """Inject a chemical into the creature with the given name/ID."""
    p = port or _port
    cmds = inject_chem_caos_cmd(creature_id, chem_num, amount)
    for cmd in cmds:
        caos(cmd, port=p)
    return {
        "status": "ok",
        "creature_id": creature_id,
        "chem": chem_num,
        "amount": amount,
    }


def _target_first_norn_cmd(inner_caos: str) -> str:
    """Wrap inner CAOS to target the first norn found."""
    return (
        f'enum 4 1 0\n'
        f'{inner_caos}\n'
        f'stop\n'
        f'next'
    )


def inject_reward_caos_cmd(creature_id: str = None, amount: float = 0.5) -> list:
    """Return CAOS string to inject reward chemical (204) into a creature."""
    if creature_id:
        return [
            f'sets va00 "{creature_id}"\n'
            f'enum 4 0 0\n'
            f'doif hist name targ 0 eq va00\n'
            f'chem 204 {amount:.4f}\n'
            f'stop\n'
            f'endi\n'
            f'next'
        ]
    return [_target_first_norn_cmd(f"chem 204 {amount:.4f}")]


def inject_reward(creature_id: str = None, amount: float = 0.5, port: int = None) -> dict:
    """Inject reward chemical (CHEM 204) into creature. Targets first norn if no ID given."""
    p = port or _port
    cmds = inject_reward_caos_cmd(creature_id, amount)
    for cmd in cmds:
        caos(cmd, port=p)
    return {
        "status": "ok",
        "creature_id": creature_id or "first_norn",
        "chem": 204,
        "amount": amount,
        "action": "reward",
    }


def inject_punishment_caos_cmd(creature_id: str = None, amount: float = 0.5) -> list:
    """Return CAOS string to inject punishment chemical (205) into a creature."""
    if creature_id:
        return [
            f'sets va00 "{creature_id}"\n'
            f'enum 4 0 0\n'
            f'doif hist name targ 0 eq va00\n'
            f'chem 205 {amount:.4f}\n'
            f'stop\n'
            f'endi\n'
            f'next'
        ]
    return [_target_first_norn_cmd(f"chem 205 {amount:.4f}")]


def inject_punishment(creature_id: str = None, amount: float = 0.5, port: int = None) -> dict:
    """Inject punishment chemical (CHEM 205) into creature. Targets first norn if no ID given."""
    p = port or _port
    cmds = inject_punishment_caos_cmd(creature_id, amount)
    for cmd in cmds:
        caos(cmd, port=p)
    return {
        "status": "ok",
        "creature_id": creature_id or "first_norn",
        "chem": 205,
        "amount": amount,
        "action": "punishment",
    }


def read_drives_caos_cmd(creature_id: str = None) -> list:
    """Return CAOS strings to read all 20 drive values from a creature.
    Uses 'driv N' command (0-19) inside an enum on the target creature."""
    drive_reads = "\n".join(f"outv driv {i}\nouts \",\"" for i in range(20))
    if creature_id:
        return [f'enum 4 0 0\n{drive_reads}\nstop\nnext']
    return [f'enum 4 1 0\n{drive_reads}\nstop\nnext']


def read_drives(creature_id: str = None, port: int = None) -> dict:
    """Read all 20 drive values from a creature. Returns dict drive_name -> value."""
    p = port or _port
    # Query each drive individually for reliability
    result = {}
    for i in range(20):
        drive_name = DRIVES.get(i, f"drive_{i}")
        raw = caos(f"enum 4 1 0\noutv driv {i}\nstop\nnext", port=p).strip()
        try:
            result[drive_name] = float(raw)
        except ValueError:
            result[drive_name] = None
    return result


def read_chems_caos_cmd(creature_id: str = None, chem_list: list = None) -> list:
    """Return CAOS strings to read specific chemicals from a creature."""
    if chem_list is None:
        chem_list = [118, 119, 120, 121, 204, 205]  # default: drives + reward/punishment
    chem_reads = "\n".join(
        f'addv va97 chem targ {c}\nadds va97 "\\n"'
        for c in chem_list
    )
    if creature_id:
        return [
            f'sets va00 "{creature_id}"\n'
            f'sets va97 ""\n'
            f'enum 4 0 0\n'
            f'doif hist name targ 0 eq va00\n'
            f'{chem_reads}\n'
            f'stop\n'
            f'endi\n'
            f'next\n'
            f'outs va97'
        ]
    return [
        f'sets va97 ""\n'
        f'enum 4 1 0\n'
        f'{chem_reads}\n'
        f'stop\n'
        f'next\n'
        f'outs va97'
    ]


def read_chems(creature_id: str = None, chem_list: list = None, port: int = None) -> dict:
    """
    Read specific chemicals from a creature.
    Default chem_list: [118, 119, 120, 121, 204, 205].
    Returns dict chem_num -> value.
    """
    p = port or _port
    if chem_list is None:
        chem_list = [118, 119, 120, 121, 204, 205]
    cmds = read_chems_caos_cmd(creature_id, chem_list)
    raw = caos(cmds[0], port=p).strip()
    result = {}
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    for i, line in enumerate(lines):
        if i < len(chem_list):
            try:
                result[chem_list[i]] = float(line)
            except ValueError:
                result[chem_list[i]] = None
    return result


def fire_stimulus_caos_cmd(creature_id: str, stim_num: int, intensity: int = 1) -> list:
    """Return CAOS string to fire a stimulus at a creature."""
    return [
        f'sets va00 "{creature_id}"\n'
        f'enum 4 0 0\n'
        f'doif hist name targ 0 eq va00\n'
        f'stim writ targ {stim_num} {intensity}\n'
        f'stop\n'
        f'endi\n'
        f'next'
    ]


def fire_stimulus(creature_id: str, stim_num: int, intensity: int = 1, port: int = None) -> dict:
    """Fire a stimulus at a specific creature."""
    p = port or _port
    cmds = fire_stimulus_caos_cmd(creature_id, stim_num, intensity)
    for cmd in cmds:
        caos(cmd, port=p)
    return {
        "status": "ok",
        "creature_id": creature_id,
        "stim_num": stim_num,
        "intensity": intensity,
    }


def creature_status_caos_cmd(creature_id: str = None) -> list:
    """Return CAOS strings to get combined creature status."""
    return read_drives_caos_cmd(creature_id) + read_chems_caos_cmd(creature_id)


def creature_status(creature_id: str = None, port: int = None) -> dict:
    """
    Get combined status for a creature: drives + key chemicals + position + name.
    Targets first norn if no ID given.
    """
    p = port or _port

    # Get creature list to find position and name
    creatures = list_creatures(port=p)
    target = None
    if creature_id:
        for c in creatures:
            if c["name"] == creature_id or str(c["unid"]) == str(creature_id):
                target = c
                break
    elif creatures:
        # First norn
        for c in creatures:
            if c["genus"] == 1:
                target = c
                break
        if target is None and creatures:
            target = creatures[0]

    drives = read_drives(creature_id, port=p)
    chems = read_chems(creature_id, port=p)

    status = {
        "creature_id": creature_id or "first_norn",
        "name": target.get("name", "unnamed") if target else "unknown",
        "genus": target["genus_name"] if target else "unknown",
        "x": target["x"] if target else None,
        "y": target["y"] if target else None,
        "drives": drives,
        "chemicals": chems,
    }
    return status


def tick_count(port: int = None) -> dict:
    """Get total agent count as a world activity indicator."""
    p = port or _port
    raw = caos("outv totl 0 0 0", port=p).strip()
    try:
        count = int(float(raw))
    except ValueError:
        count = -1
    return {"total_agents": count}


# ---------------------------------------------------------------------------
# 7. Batch Command Runner
# ---------------------------------------------------------------------------

_SUBCOMMAND_MAP = {}  # filled after CLI setup


def run_batch(batch_str: str, port: int = None, json_output: bool = False) -> list:
    """
    Run a semicolon-separated batch of CLI-style commands.
    Each command is parsed as a subcommand name + args, executed sequentially.
    Returns list of results.
    """
    results = []
    commands = [c.strip() for c in batch_str.split(";") if c.strip()]
    for cmd_str in commands:
        parts = cmd_str.split()
        subcmd = parts[0]
        rest = parts[1:]
        if subcmd not in _SUBCOMMAND_MAP:
            results.append({"command": cmd_str, "status": "error", "reason": f"unknown subcommand: {subcmd}"})
            continue
        try:
            result = _SUBCOMMAND_MAP[subcmd](rest, port=port)
            results.append({"command": cmd_str, "result": result})
        except Exception as e:
            results.append({"command": cmd_str, "status": "error", "reason": str(e)})
    return results


# ---------------------------------------------------------------------------
# 8. CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="test_harness",
        description="NORNBRAIN Test Harness - control Creatures 3 via CAOS over TCP",
    )
    parser.add_argument("--port", type=int, default=20001, help="CAOS TCP port (default: 20001)")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output JSON instead of human-readable text")

    sub = parser.add_subparsers(dest="subcmd", required=True, title="subcommands")

    # spawn-eggs
    p_spawn = sub.add_parser("spawn-eggs", help="Activate Norn Egg Layer n times")
    p_spawn.add_argument("--n", type=int, default=2, help="Number of eggs to spawn (default: 2)")

    # hatch-all
    sub.add_parser("hatch-all", help="Force-hatch all creature eggs")

    # spawn-and-hatch
    p_sah = sub.add_parser("spawn-and-hatch", help="Spawn eggs then hatch them")
    p_sah.add_argument("--n", type=int, default=2, help="Number of eggs (default: 2)")

    # kill-grendels
    sub.add_parser("kill-grendels", help="Kill all grendel creatures")

    # kill-ettins
    sub.add_parser("kill-ettins", help="Kill all ettin creatures")

    # teleport-to-hand
    sub.add_parser("teleport-to-hand", help="Teleport all norns to the pointer position")

    # teleport-all-norns
    p_tan = sub.add_parser("teleport-all-norns", help="Teleport all norns to named metaroom")
    p_tan.add_argument("metaroom", choices=list(METAROOMS.keys()), help="Target metaroom name")

    # freeze-creature
    p_freeze = sub.add_parser("freeze-creature", help="Freeze (zombify) a creature")
    p_freeze.add_argument("creature_id", help="Creature name or NB-XXX ID")

    # unfreeze-creature
    p_unfreeze = sub.add_parser("unfreeze-creature", help="Unfreeze a creature")
    p_unfreeze.add_argument("creature_id", help="Creature name or NB-XXX ID")

    # set-age
    p_age = sub.add_parser("set-age", help="Set a creature's life stage")
    p_age.add_argument("creature_id", help="Creature name or NB-XXX ID")
    p_age.add_argument("stage", type=int, help="Age stage 0=baby .. 6=senile")

    # list-creatures
    sub.add_parser("list-creatures", help="List all creatures in the world")

    # auto-name-all
    sub.add_parser("auto-name-all", help="Assign NB-XXX names to unnamed creatures")

    # population
    sub.add_parser("population", help="Count creatures by genus")

    # save-world
    sub.add_parser("save-world", help="Save the game world")

    # teleport-camera
    p_cam = sub.add_parser("teleport-camera", help="Move camera to named metaroom")
    p_cam.add_argument("metaroom", choices=list(METAROOMS.keys()), help="Target metaroom name")

    # activate-all-gadgets
    sub.add_parser("activate-all-gadgets", help="Activate all machines and gadgets")

    # clear-non-creatures
    sub.add_parser("clear-non-creatures", help="Kill all non-creature agents (saves backup)")

    # restore-agents
    sub.add_parser("restore-agents", help="Show backed-up agent data (stub)")

    # world-info
    sub.add_parser("world-info", help="Get world state summary")

    # spawn-food
    p_food = sub.add_parser("spawn-food", help="Spawn a food agent")
    p_food.add_argument("--type", dest="food_type", default="fruit", choices=list(FOOD_ITEMS.keys()), help="Food type (default: fruit)")
    p_food.add_argument("--x", type=float, default=None, help="X position (default: hand position)")
    p_food.add_argument("--y", type=float, default=None, help="Y position (default: hand position)")

    # spawn-toy
    p_toy = sub.add_parser("spawn-toy", help="Spawn a toy agent")
    p_toy.add_argument("--x", type=float, default=None, help="X position (default: hand position)")
    p_toy.add_argument("--y", type=float, default=None, help="Y position (default: hand position)")

    # list-food
    sub.add_parser("list-food", help="Count food agents by type")

    # list-toys
    sub.add_parser("list-toys", help="Count toy agents")

    # inject-chem
    p_ic = sub.add_parser("inject-chem", help="Inject a chemical into a creature")
    p_ic.add_argument("creature_id", help="Creature name or NB-XXX ID")
    p_ic.add_argument("chem_num", type=int, help="Chemical number (0-255)")
    p_ic.add_argument("--amount", type=float, default=0.5, help="Amount (default: 0.5)")

    # inject-reward
    p_ir = sub.add_parser("inject-reward", help="Inject reward chemical (CHEM 204)")
    p_ir.add_argument("creature_id", nargs="?", default=None, help="Creature name (default: first norn)")
    p_ir.add_argument("--amount", type=float, default=0.5, help="Amount (default: 0.5)")

    # inject-punishment
    p_ip = sub.add_parser("inject-punishment", help="Inject punishment chemical (CHEM 205)")
    p_ip.add_argument("creature_id", nargs="?", default=None, help="Creature name (default: first norn)")
    p_ip.add_argument("--amount", type=float, default=0.5, help="Amount (default: 0.5)")

    # read-drives
    p_rd = sub.add_parser("read-drives", help="Read all 20 drive values from a creature")
    p_rd.add_argument("creature_id", nargs="?", default=None, help="Creature name (default: first norn)")

    # read-chems
    p_rc = sub.add_parser("read-chems", help="Read specific chemicals from a creature")
    p_rc.add_argument("creature_id", nargs="?", default=None, help="Creature name (default: first norn)")
    p_rc.add_argument("--chems", type=str, default=None, help="Comma-separated chem numbers (default: 118,119,120,121,204,205)")

    # fire-stimulus
    p_fs = sub.add_parser("fire-stimulus", help="Fire a stimulus at a creature")
    p_fs.add_argument("creature_id", help="Creature name or NB-XXX ID")
    p_fs.add_argument("stim_num", type=int, help="Stimulus number")
    p_fs.add_argument("--intensity", type=int, default=1, help="Stimulus intensity (default: 1)")

    # creature-status
    p_cs = sub.add_parser("creature-status", help="Get full creature status (drives + chems + position)")
    p_cs.add_argument("creature_id", nargs="?", default=None, help="Creature name (default: first norn)")

    # tick-count
    sub.add_parser("tick-count", help="Get total agent count")

    # caos-cmd
    p_caos_cmd = sub.add_parser("caos-cmd", help="Show CAOS commands for a function without executing (for testing)")
    p_caos_cmd.add_argument("function_name", help="Function name (e.g., spawn-eggs, teleport-camera)")
    p_caos_cmd.add_argument("args", nargs="*", help="Arguments for the function")

    # batch
    p_batch = sub.add_parser("batch", help="Run semicolon-separated commands sequentially")
    p_batch.add_argument("commands", help='Semicolon-separated commands, e.g. "spawn-eggs 2; hatch-all; teleport-camera norn-terrarium"')

    # --- Quick reference ---
    sub.add_parser("commands", help="Print quick-reference card of all commands grouped by category")

    # --- Overlay & Panel subcommands ---
    sub.add_parser("inject-overlays", help="Inject all in-game overlay agents (labels, drives, world info)")
    sub.add_parser("remove-overlays", help="Remove all in-game overlay agents")
    sub.add_parser("inject-labels", help="Inject norn ID label overlays only")
    sub.add_parser("inject-drive-bars", help="Inject drive bar overlay only")
    sub.add_parser("inject-world-info", help="Inject world info overlay only")
    sub.add_parser("inject-panel", help="Inject in-game control panel with buttons")
    sub.add_parser("remove-panel", help="Remove in-game control panel")

    # --- Prep world for testing ---
    sub.add_parser("prep-world", help="Full world prep: activate gadgets, spawn eggs, hatch, auto-name, inject overlays+panel")

    return parser


def _dispatch_args(args, port: int) -> object:
    """Dispatch parsed args to the appropriate function and return result."""
    sc = args.subcmd

    if sc == "spawn-eggs":
        return spawn_eggs(n=args.n, port=port)
    elif sc == "hatch-all":
        return hatch_all(port=port)
    elif sc == "spawn-and-hatch":
        return spawn_and_hatch(n=args.n, port=port)
    elif sc == "kill-grendels":
        return kill_grendels(port=port)
    elif sc == "kill-ettins":
        return kill_ettins(port=port)
    elif sc == "teleport-to-hand":
        return teleport_to_hand(port=port)
    elif sc == "teleport-all-norns":
        return teleport_all_norns(args.metaroom, port=port)
    elif sc == "freeze-creature":
        return freeze_creature(args.creature_id, port=port)
    elif sc == "unfreeze-creature":
        return unfreeze_creature(args.creature_id, port=port)
    elif sc == "set-age":
        return set_age(args.creature_id, args.stage, port=port)
    elif sc == "list-creatures":
        return list_creatures(port=port)
    elif sc == "auto-name-all":
        return auto_name_all(port=port)
    elif sc == "population":
        return population(port=port)
    elif sc == "save-world":
        return save_world(port=port)
    elif sc == "teleport-camera":
        return teleport_camera(args.metaroom, port=port)
    elif sc == "activate-all-gadgets":
        return activate_all_gadgets(port=port)
    elif sc == "clear-non-creatures":
        return clear_non_creatures(port=port)
    elif sc == "restore-agents":
        return restore_agents(port=port)
    elif sc == "world-info":
        return world_info(port=port)
    elif sc == "spawn-food":
        return spawn_food(food_type=args.food_type, x=args.x, y=args.y, port=port)
    elif sc == "spawn-toy":
        return spawn_toy(x=args.x, y=args.y, port=port)
    elif sc == "list-food":
        return list_food(port=port)
    elif sc == "list-toys":
        return list_toys(port=port)
    elif sc == "inject-chem":
        return inject_chem(args.creature_id, args.chem_num, args.amount, port=port)
    elif sc == "inject-reward":
        return inject_reward(args.creature_id, args.amount, port=port)
    elif sc == "inject-punishment":
        return inject_punishment(args.creature_id, args.amount, port=port)
    elif sc == "read-drives":
        return read_drives(args.creature_id, port=port)
    elif sc == "read-chems":
        chem_list = None
        if args.chems:
            chem_list = [int(c.strip()) for c in args.chems.split(",") if c.strip()]
        return read_chems(args.creature_id, chem_list=chem_list, port=port)
    elif sc == "fire-stimulus":
        return fire_stimulus(args.creature_id, args.stim_num, args.intensity, port=port)
    elif sc == "creature-status":
        return creature_status(args.creature_id, port=port)
    elif sc == "tick-count":
        return tick_count(port=port)
    elif sc == "caos-cmd":
        return _dispatch_caos_cmd(args.function_name, args.args)
    elif sc == "batch":
        return run_batch(args.commands, port=port, json_output=args.json_output)
    elif sc == "commands":
        return _print_command_reference()
    elif sc in ("inject-overlays", "remove-overlays", "inject-labels",
                "inject-drive-bars", "inject-world-info", "inject-panel",
                "remove-panel", "prep-world"):
        return _dispatch_overlay_panel(sc, port=port)
    else:
        return {"status": "error", "reason": f"unknown subcommand: {sc}"}


def _dispatch_caos_cmd(function_name: str, fn_args: list) -> dict:
    """Return the CAOS strings for a function without executing."""
    fn_map = {
        "spawn-eggs":          lambda a: spawn_eggs_caos_cmd(int(a[0]) if a else 2),
        "hatch-all":           lambda a: hatch_all_caos_cmd(),
        "spawn-and-hatch":     lambda a: spawn_and_hatch_caos_cmd(int(a[0]) if a else 2),
        "kill-grendels":       lambda a: kill_grendels_caos_cmd(),
        "kill-ettins":         lambda a: kill_ettins_caos_cmd(),
        "teleport-to-hand":    lambda a: teleport_to_hand_caos_cmd(),
        "teleport-all-norns":  lambda a: teleport_all_norns_caos_cmd(a[0]) if a else ["<requires metaroom arg>"],
        "freeze-creature":     lambda a: freeze_creature_caos_cmd(a[0]) if a else ["<requires creature_id>"],
        "unfreeze-creature":   lambda a: unfreeze_creature_caos_cmd(a[0]) if a else ["<requires creature_id>"],
        "set-age":             lambda a: set_age_caos_cmd(a[0], int(a[1])) if len(a) >= 2 else ["<requires creature_id stage>"],
        "list-creatures":      lambda a: list_creatures_caos_cmd(),
        "auto-name-all":       lambda a: auto_name_all_caos_cmd(),
        "population":          lambda a: population_caos_cmd(),
        "save-world":          lambda a: save_world_caos_cmd(),
        "teleport-camera":     lambda a: teleport_camera_caos_cmd(a[0]) if a else ["<requires metaroom arg>"],
        "activate-all-gadgets": lambda a: activate_all_gadgets_caos_cmd(),
        "clear-non-creatures": lambda a: clear_non_creatures_caos_cmd(),
        "restore-agents":      lambda a: restore_agents_caos_cmd(),
        "world-info":          lambda a: world_info_caos_cmd(),
        "spawn-food":          lambda a: spawn_food_caos_cmd(a[0] if a else "fruit"),
        "spawn-toy":           lambda a: spawn_toy_caos_cmd(),
        "list-food":           lambda a: list_food_caos_cmd(),
        "list-toys":           lambda a: list_toys_caos_cmd(),
        "inject-chem":         lambda a: inject_chem_caos_cmd(a[0], int(a[1]), float(a[2])) if len(a) >= 3 else ["<requires creature_id chem_num amount>"],
        "inject-reward":       lambda a: inject_reward_caos_cmd(a[0] if a else None, float(a[1]) if len(a) > 1 else 0.5),
        "inject-punishment":   lambda a: inject_punishment_caos_cmd(a[0] if a else None, float(a[1]) if len(a) > 1 else 0.5),
        "read-drives":         lambda a: read_drives_caos_cmd(a[0] if a else None),
        "read-chems":          lambda a: read_chems_caos_cmd(a[0] if a else None),
        "fire-stimulus":       lambda a: fire_stimulus_caos_cmd(a[0], int(a[1]), int(a[2]) if len(a) > 2 else 1) if len(a) >= 2 else ["<requires creature_id stim_num>"],
        "creature-status":     lambda a: creature_status_caos_cmd(a[0] if a else None),
        "tick-count":          lambda a: ["outv totl 0 0 0"],
    }
    if function_name not in fn_map:
        return {"status": "error", "reason": f"unknown function: {function_name}. Valid: {sorted(fn_map.keys())}"}
    try:
        cmds = fn_map[function_name](fn_args)
        return {"function": function_name, "caos_commands": cmds}
    except Exception as e:
        return {"status": "error", "function": function_name, "reason": str(e)}


def _print_command_reference() -> dict:
    """Print a grouped quick-reference card of all harness commands."""
    card = """
+----------------------------------------------------------+
|            NORNBRAIN TEST HARNESS -- COMMANDS             |
+----------------------------------------------------------+
| CREATURE MANAGEMENT                                      |
|   spawn-eggs [--n 2]       Spawn eggs via Egg Layer      |
|   hatch-all                Force-hatch all eggs           |
|   spawn-and-hatch [--n 2]  Spawn + wait + hatch          |
|   kill-grendels            Kill all grendels (genus 2)    |
|   kill-ettins              Kill all ettins (genus 3)      |
|   teleport-to-hand         Move all norns to pointer      |
|   teleport-all-norns <mr>  Move norns to metaroom         |
|   freeze-creature <id>     Freeze (zombie) a creature     |
|   unfreeze-creature <id>   Unfreeze a creature            |
|   set-age <id> <0-6>       Set life stage                 |
|   list-creatures           List all creatures              |
|   auto-name-all            Assign NB-XXX names            |
|   population               Count by genus                  |
+----------------------------------------------------------+
| WORLD & ENVIRONMENT                                      |
|   save-world               Save without exiting           |
|   teleport-camera <mr>     Camera to metaroom             |
|   activate-all-gadgets     Activate machines + gadgets     |
|   clear-non-creatures      Remove non-creature agents      |
|   restore-agents           Restore cleared agents (stub)   |
|   world-info               Agent counts + bioenergy        |
+----------------------------------------------------------+
| AGENT SPAWNING                                           |
|   spawn-food [--type X]    Spawn food at hand position     |
|   spawn-toy                Spawn toy at hand position      |
|   list-food                Count food by type              |
|   list-toys                Count toys                      |
+----------------------------------------------------------+
| BIOCHEMISTRY & RL                                        |
|   inject-chem <id> <#> [a] Inject chemical 0-255          |
|   inject-reward [id] [a]   CHEM 204 (default 0.5)         |
|   inject-punishment [id]   CHEM 205 (default 0.5)         |
|   read-drives [id]         Read all 20 drives              |
|   read-chems [id] [--chems] Read specific chemicals        |
|   fire-stimulus <id> <#>   Fire stimulus at creature       |
|   creature-status [id]     Full snapshot (drives+chems)    |
|   tick-count               Total agent count               |
+----------------------------------------------------------+
| IN-GAME OVERLAYS & PANEL                                 |
|   inject-overlays          All overlays (labels+drives+info)|
|   remove-overlays          Remove all overlays             |
|   inject-labels            Norn ID labels only             |
|   inject-drive-bars        Drive bar display only          |
|   inject-world-info        World info overlay only         |
|   inject-panel             In-game control panel           |
|   remove-panel             Remove control panel            |
+----------------------------------------------------------+
| AUTOMATION                                               |
|   prep-world               Full setup (gadgets+eggs+name+  |
|                            overlays+panel)                 |
|   batch "cmd1; cmd2; ..."  Run commands sequentially       |
|   caos-cmd <fn> [args]     Show CAOS without executing     |
|   commands                 This help card                  |
+----------------------------------------------------------+
| METAROOMS: norn-terrarium, ettin-desert, aquatic,        |
|   grendel-jungle, corridor, pinball, space,              |
|   learning-room, crypt                                   |
+----------------------------------------------------------+
| FLAGS: --json (JSON output)  --port N (default 20001)    |
+----------------------------------------------------------+
"""
    print(card)
    return {"status": "ok", "action": "printed command reference"}


def _dispatch_overlay_panel(sc: str, port: int) -> dict:
    """Dispatch overlay and panel subcommands."""
    from test_harness_overlay import (
        generate_norn_labels_script, generate_drive_bars_script,
        generate_world_info_script, generate_remove_overlays_script,
    )
    from test_harness_caos import (
        generate_panel_script, generate_panel_handlers_script,
    )

    if sc == "inject-overlays":
        for script_fn in [generate_norn_labels_script, generate_drive_bars_script, generate_world_info_script]:
            caos(script_fn(), port=port)
        return {"status": "ok", "action": "injected all overlays"}
    elif sc == "remove-overlays":
        caos(generate_remove_overlays_script(), port=port)
        return {"status": "ok", "action": "removed all overlays"}
    elif sc == "inject-labels":
        caos(generate_norn_labels_script(), port=port)
        return {"status": "ok", "action": "injected norn labels"}
    elif sc == "inject-drive-bars":
        caos(generate_drive_bars_script(), port=port)
        return {"status": "ok", "action": "injected drive bars"}
    elif sc == "inject-world-info":
        caos(generate_world_info_script(), port=port)
        return {"status": "ok", "action": "injected world info overlay"}
    elif sc == "inject-panel":
        caos(generate_panel_script(), port=port)
        caos(generate_panel_handlers_script(), port=port)
        return {"status": "ok", "action": "injected control panel"}
    elif sc == "remove-panel":
        # Kill all panel agents (3 103 0 through 3 103 19)
        for sp in range(20):
            caos(f"enum 3 103 {sp} kill targ next", port=port)
        return {"status": "ok", "action": "removed control panel"}
    elif sc == "prep-world":
        results = []
        # Step 1: Activate all gadgets
        results.append(activate_all_gadgets(port=port))
        # Step 2: Spawn 2 eggs
        results.append(spawn_eggs(n=2, port=port))
        # Step 3: Wait and hatch
        time.sleep(3)
        results.append(hatch_all(port=port))
        # Step 4: Auto-name
        time.sleep(2)
        results.append(auto_name_all(port=port))
        # Step 5: Inject overlays
        for script_fn in [generate_norn_labels_script, generate_drive_bars_script, generate_world_info_script]:
            caos(script_fn(), port=port)
        # Step 6: Inject panel
        caos(generate_panel_script(), port=port)
        caos(generate_panel_handlers_script(), port=port)
        return {"status": "ok", "action": "world prepped for testing", "steps": results}
    return {"status": "error", "reason": f"unknown overlay/panel command: {sc}"}


def main():
    global _json_mode, _port

    parser = build_parser()
    args = parser.parse_args()

    _json_mode = args.json_output
    _port = args.port

    try:
        result = _dispatch_args(args, port=args.port)
        output_result(result)
    except ConnectionRefusedError:
        err = {"status": "error", "reason": f"Cannot connect to engine on port {args.port}. Is openc2e running?"}
        output_result(err)
        sys.exit(1)
    except Exception as e:
        err = {"status": "error", "reason": str(e)}
        output_result(err)
        sys.exit(1)


if __name__ == "__main__":
    main()
