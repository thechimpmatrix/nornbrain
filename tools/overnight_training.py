#!/usr/bin/env python3
"""NB Overnight Training Watchdog.

Keeps the CfC brain training all night:
- Starts openc2e with the configured brain module if not running
- Starts web monitor if not running (P1 law: monitor must run with every engine instance)
- Waits for world to load (900+ agents)
- Hatches norns if none exist, allows grendels/ettins to spawn naturally
- Respawns 2 norns if all die
- Pins camera to the first norn (genus 1)
- Restarts engine on crash
- Logs all events to overnight_training.log

Usage:
    python tools/overnight_training.py
"""

import os
import socket
import subprocess
import sys
import time
import datetime

# ── Paths ────────────────────────────────────────────────────────────

ENGINE_EXE = r"<PROJECT_ROOT>\openc2e\build64\RelWithDebInfo\openc2e.exe"
DATA_PATH = r"<PROJECT_ROOT>\creaturesexodusgame\Creatures Exodus\Creatures 3"
# Phase E.2 brain wrapper pending implementation; see
# docs/specs/2026-04-26-cfc-comb-replacement-design.md for the active design.
# When empty, the engine launches with the default SVRule brain.
BRAIN_MODULE = ""
MONITOR_SCRIPT = r"<PROJECT_ROOT>\openc2e\tools\web_monitor.py"
LOG_PATH = r"<PROJECT_ROOT>\tools\overnight_training.log"

CHECK_INTERVAL = 30  # seconds between checks
WORLD_LOAD_TIMEOUT = 60  # max seconds to wait for world to load
MIN_NORNS = 1  # respawn if fewer than this
MONITOR_PORT = 8088


def log(msg: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def is_monitor_running() -> bool:
    """Check if web monitor HTTP server is accepting connections on MONITOR_PORT."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        result = s.connect_ex(("127.0.0.1", MONITOR_PORT))
        s.close()
        return result == 0
    except Exception:
        return False


def ensure_monitor():
    """Start web monitor if it is not running. Kills any stale port-holders first."""
    if is_monitor_running():
        return
    # Kill anything squatting on MONITOR_PORT or WS port 8081
    for port in (MONITOR_PORT, 8081):
        try:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if f":{port} " in line and "LISTENING" in line:
                    parts = line.split()
                    pid = int(parts[-1])
                    subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                                   capture_output=True, timeout=5)
                    log(f"Killed stale monitor process (PID {pid}) on port {port}")
        except Exception:
            pass
    time.sleep(1)
    log("Starting web monitor...")
    subprocess.Popen(
        ["pythonw", MONITOR_SCRIPT],
        cwd=os.path.dirname(ENGINE_EXE),
    )
    # Wait up to 8s for it to come up
    for _ in range(8):
        time.sleep(1)
        if is_monitor_running():
            log("Web monitor started - http://localhost:8088/")
            return
    log("WARNING: Web monitor did not start within 8s")


def caos(cmd: str, port: int = 20001, timeout: float = 10.0) -> str | None:
    """Send CAOS via TCP. Returns response string or None on failure."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(("127.0.0.1", port))
        s.sendall((cmd + "\nrscr\n").encode("latin-1"))
        data = b""
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            data += chunk
        s.close()
        return data.decode("latin-1").strip()
    except Exception:
        return None


def is_engine_running() -> bool:
    """Check if openc2e process is alive."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq openc2e.exe"],
            capture_output=True, text=True, timeout=5
        )
        return "openc2e.exe" in result.stdout
    except Exception:
        return False


def start_engine():
    """Start openc2e with the configured brain module, or the SVRule default if BRAIN_MODULE is empty."""
    cmd = [ENGINE_EXE,
           "--data-path", DATA_PATH,
           "--gamename", "Creatures 3"]
    if BRAIN_MODULE:
        log(f"Starting openc2e with brain module {BRAIN_MODULE}...")
        cmd += ["--brain-module", BRAIN_MODULE]
    else:
        log("Starting openc2e with default SVRule brain (BRAIN_MODULE empty)...")
    subprocess.Popen(cmd, cwd=os.path.dirname(ENGINE_EXE))
    log("Engine process started, waiting for world to load...")


def wait_for_world() -> bool:
    """Wait for the world to fully load (900+ agents). Returns True if loaded."""
    start = time.time()
    while time.time() - start < WORLD_LOAD_TIMEOUT:
        resp = caos("outv totl 0 0 0")
        if resp is not None:
            try:
                count = int(float(resp))
                if count > 100:
                    log(f"World loaded: {count} agents")
                    return True
            except ValueError:
                pass
        time.sleep(3)
    log("WARNING: World load timeout")
    return False


def count_creatures() -> tuple[int, int, int]:
    """Returns (norns, grendels, ettins) count."""
    norns = grendels = ettins = 0
    try:
        r = caos("outv totl 4 1 0")
        if r:
            norns = int(float(r))
    except Exception:
        pass
    try:
        r = caos("outv totl 4 2 0")
        if r:
            grendels = int(float(r))
    except Exception:
        pass
    try:
        r = caos("outv totl 4 3 0")
        if r:
            ettins = int(float(r))
    except Exception:
        pass
    return norns, grendels, ettins


def hatch_norns(count: int = 2):
    """Hatch count norns using the standard recipe."""
    genomes = ["norn.bondi.48", "norn.astro.48", "norn.fallow.48", "norn.siamese.48"]
    for i in range(count):
        genome = genomes[i % len(genomes)]
        log(f"Hatching norn #{i+1} with genome {genome}...")
        result = caos(
            f'new: simp 1 1 252 "blnk" 1 0 0\n'
            f'gene load targ 1 "{genome}"\n'
            f'new: crea 4 targ 1 0 0\n'
            f'born\n'
            f'enum 1 1 252 kill targ next'
        )
        if result is not None:
            log(f"  Hatch result: OK")
        else:
            log(f"  Hatch result: FAILED (no response)")
        time.sleep(1)

    # Move norns to terrarium and fix physics
    caos("enum 4 1 0 mvsf 3583 604 next")
    caos("enum 4 1 0 attr 198 accg 10 aero 10 next")
    time.sleep(0.5)

    # Verify
    norns, _, _ = count_creatures()
    log(f"  Norns after hatch: {norns}")


def pin_camera_to_norn():
    """Lock camera to the first norn (genus 1)."""
    caos("enum 4 1 0 trck targ 50 50 2 0 next")


def ensure_ecosystem():
    """Check creature population, respawn if needed."""
    norns, grendels, ettins = count_creatures()
    log(f"Population: norns={norns} grendels={grendels} ettins={ettins}")

    if norns < MIN_NORNS:
        log(f"Norns below minimum ({norns} < {MIN_NORNS}), hatching 2...")
        hatch_norns(2)
        pin_camera_to_norn()

    # Let grendels and ettins spawn naturally - don't disable their spawners
    # The ecosystem needs predators for the norn to learn fear responses


def main():
    log("=" * 60)
    log("NB OVERNIGHT TRAINING WATCHDOG STARTED")
    log(f"Engine: {ENGINE_EXE}")
    log(f"Brain: {BRAIN_MODULE if BRAIN_MODULE else 'SVRule (default)'}")
    log(f"Monitor: http://localhost:{MONITOR_PORT}/")
    log(f"Check interval: {CHECK_INTERVAL}s")
    log("=" * 60)

    # P1 law: monitor must be running
    ensure_monitor()

    crashes = 0

    while True:
        try:
            # P1 law: ensure monitor is up on every iteration
            ensure_monitor()

            # Check if engine is running
            if not is_engine_running():
                crashes += 1
                if crashes > 1:
                    log(f"ENGINE CRASH DETECTED (crash #{crashes})")
                start_engine()
                if not wait_for_world():
                    log("World failed to load, retrying in 30s...")
                    time.sleep(30)
                    continue

                # Fresh start: hatch norns and pin camera
                time.sleep(5)  # Let world settle
                hatch_norns(2)
                pin_camera_to_norn()
                log("Engine running, creatures hatched, camera pinned")
            else:
                # Engine is running - check world state
                resp = caos("outv totl 0 0 0")
                if resp is None:
                    log("WARNING: TCP connection failed (engine may be loading)")
                    time.sleep(10)
                    continue

                try:
                    agent_count = int(float(resp))
                except ValueError:
                    agent_count = 0

                if agent_count < 50:
                    log(f"WARNING: Only {agent_count} agents - world may not be loaded")
                    time.sleep(10)
                    continue

                # World is running - check creatures
                ensure_ecosystem()

                # Re-pin camera every check (in case creature died and was replaced)
                pin_camera_to_norn()

        except KeyboardInterrupt:
            log("WATCHDOG STOPPED (Ctrl+C)")
            break
        except Exception as e:
            log(f"WATCHDOG ERROR: {e}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
