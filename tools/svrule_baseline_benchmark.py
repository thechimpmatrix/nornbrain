#!/usr/bin/env python3
"""SVRule Baseline Benchmark - capture behavioural metrics from the native C3 brain.

Runs against openc2e in SVRule mode (no --brain-module) and records:
  - Action distribution (decision neuron argmax over time)
  - Attention distribution (attention neuron argmax over time)
  - Drive trajectories (20 drives sampled every interval)
  - Reward/punishment/adrenaline chemicals
  - Position and alive/asleep state

Outputs a JSON file compatible with the CfC evaluation framework so we can
do apples-to-apples comparison in Phase D.

Usage:
    # Engine must be running in SVRule mode (no --brain-module)
    python tools/svrule_baseline_benchmark.py                    # 5 min, 2s interval
    python tools/svrule_baseline_benchmark.py --duration 600     # 10 min
    python tools/svrule_baseline_benchmark.py --interval 1       # 1s sampling
    python tools/svrule_baseline_benchmark.py --no-spawn         # use existing norn
"""

import argparse
import json
import math
import os
import socket
import sys
import time
from collections import Counter
from datetime import datetime

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.normpath(os.path.join(_THIS_DIR, ".."))

# Import test harness for CAOS infrastructure
sys.path.insert(0, _THIS_DIR)
from test_harness import caos, DRIVES, METAROOMS

# ── Constants ─────────────────────────────────────────────────────────

ACTION_NAMES = {
    0: "look", 1: "push", 2: "pull", 3: "deactivate", 4: "approach",
    5: "retreat", 6: "get", 7: "drop", 8: "express", 9: "rest",
    10: "left", 11: "right", 12: "eat", 13: "hit",
}

CATEGORY_NAMES = {
    0: "self", 1: "hand", 2: "door", 3: "seed", 4: "plant", 5: "weed",
    6: "leaf", 7: "flower", 8: "fruit", 9: "manky", 10: "detritus",
    11: "food", 12: "button", 13: "bug", 14: "pest", 15: "critter",
    16: "beast", 17: "nest", 18: "animal_egg", 19: "weather", 20: "bad",
    21: "toy", 22: "incubator", 23: "dispenser", 24: "tool", 25: "potion",
    26: "elevator", 27: "teleporter", 28: "machinery", 29: "creature_egg",
    30: "norn_home", 31: "grendel_home", 32: "ettin_home", 33: "gadget",
    34: "something", 35: "vehicle", 36: "norn", 37: "grendel", 38: "ettin",
    39: "something2",
}

DRIVE_NAMES = {
    0: "pain", 1: "hunger_prot", 2: "hunger_carb", 3: "hunger_fat",
    4: "cold", 5: "hot", 6: "tired", 7: "sleepy", 8: "lonely",
    9: "crowded", 10: "fear", 11: "bored", 12: "anger",
    13: "sex_drive", 14: "comfort",
}

NUM_ATTN = 40
NUM_DECN = 14
NUM_DRIVES = 20

# Key chemicals to track
CHEM_REWARD = 204
CHEM_PUNISHMENT = 205
CHEM_ADRENALINE = 117

# NOTE: brn: commands unavailable in openc2e TCP injection, so we cannot read
# brain neuron values (attn/decn winners). We measure behavioral outcomes only.
# Action/attention distribution metrics require the CfC brain's MetricsAccumulator.


# ── CAOS Sampling ─────────────────────────────────────────────────────

def build_sample_caos() -> str:
    """Build a single batched CAOS command that reads observable creature state.

    NOTE: brn: dmpn/dmpl commands are NOT available in openc2e TCP injection.
    We observe behavioral outcomes (drives, chemicals, position, state) instead
    of reading brain neurons directly.

    Returns a string that, when executed, produces pipe-separated sections:
      drives | chemicals | position_state
    """
    lines = ["enum 4 1 0"]

    # Drives (20)
    for i in range(NUM_DRIVES):
        lines.append(f"outv driv {i}")
        if i < NUM_DRIVES - 1:
            lines.append('outs ","')
    lines.append('outs "|"')

    # Key chemicals: reward, punishment, adrenaline + hunger-related
    chems = [CHEM_REWARD, CHEM_PUNISHMENT, CHEM_ADRENALINE, 3, 34, 35, 36]  # glucose, energy, ATP, ADP
    for i, chem in enumerate(chems):
        lines.append(f"outv chem {chem}")
        if i < len(chems) - 1:
            lines.append('outs ","')
    lines.append('outs "|"')

    # Position + state + held item
    lines.append("outv posx")
    lines.append('outs ","')
    lines.append("outv posy")
    lines.append('outs ","')
    lines.append("outv dead")
    lines.append('outs ","')
    lines.append("outv aslp")
    lines.append('outs ","')
    lines.append("outv cage")  # life stage

    lines.append("stop")
    lines.append("next")
    return "\n".join(lines)


def parse_sample(raw: str) -> dict | None:
    """Parse the pipe-separated output from build_sample_caos()."""
    raw = raw.strip()
    if not raw or "|" not in raw:
        return None

    sections = raw.split("|")
    if len(sections) < 3:
        return None

    try:
        drive_vals = [float(x.strip()) for x in sections[0].split(",") if x.strip()]
        chem_vals = [float(x.strip()) for x in sections[1].split(",") if x.strip()]
        state_vals = [float(x.strip()) for x in sections[2].split(",") if x.strip()]
    except (ValueError, IndexError):
        return None

    if len(drive_vals) < NUM_DRIVES:
        return None

    return {
        "drives": drive_vals[:NUM_DRIVES],
        "reward": chem_vals[0] if len(chem_vals) > 0 else 0.0,
        "punishment": chem_vals[1] if len(chem_vals) > 1 else 0.0,
        "adrenaline": chem_vals[2] if len(chem_vals) > 2 else 0.0,
        "glucose": chem_vals[3] if len(chem_vals) > 3 else 0.0,
        "energy": chem_vals[4] if len(chem_vals) > 4 else 0.0,
        "atp": chem_vals[5] if len(chem_vals) > 5 else 0.0,
        "adp": chem_vals[6] if len(chem_vals) > 6 else 0.0,
        "x": state_vals[0] if len(state_vals) > 0 else 0.0,
        "y": state_vals[1] if len(state_vals) > 1 else 0.0,
        "dead": int(state_vals[2]) if len(state_vals) > 2 else 0,
        "asleep": int(state_vals[3]) if len(state_vals) > 3 else 0,
        "life_stage": int(state_vals[4]) if len(state_vals) > 4 else 0,
    }


# ── Metrics Computation ──────────────────────────────────────────────

def shannon_entropy(counts: list, n_classes: int) -> float:
    """Normalised Shannon entropy (0.0 = uniform, 1.0 = max diversity)."""
    total = sum(counts)
    if total == 0 or n_classes <= 1:
        return 0.0
    ent = 0.0
    for c in counts:
        if c > 0:
            p = c / total
            ent -= p * math.log(p)
    max_ent = math.log(n_classes)
    return ent / max_ent if max_ent > 0 else 0.0


def compute_metrics(samples: list) -> dict:
    """Compute aggregate metrics from a list of sample dicts.

    NOTE: brn: commands unavailable in openc2e TCP injection, so we measure
    behavioral outcomes (drives, chemicals, survival, movement) rather than
    brain neuron distributions. Both SVRule and CfC benchmarks use the same
    observable metrics for apples-to-apples comparison.
    """
    n = len(samples)
    if n == 0:
        return {"brain_type": "SVRule", "num_samples": 0, "error": "no samples collected"}

    # Drive homeostasis: mean absolute drive change between consecutive samples
    # Lower = more stable drive regulation
    drive_changes = []
    for i in range(1, n):
        prev_d = samples[i - 1]["drives"]
        curr_d = samples[i]["drives"]
        total_delta = sum(abs(curr_d[j] - prev_d[j]) for j in range(min(len(prev_d), len(curr_d), NUM_DRIVES)))
        drive_changes.append(total_delta / NUM_DRIVES)
    drive_homeostasis = sum(drive_changes) / len(drive_changes) if drive_changes else 0.0

    # Mean drives over observation
    mean_drives = {}
    for i in range(min(15, NUM_DRIVES)):
        vals = [s["drives"][i] for s in samples if len(s["drives"]) > i]
        mean_drives[DRIVE_NAMES.get(i, f"drive_{i}")] = round(sum(vals) / len(vals), 4) if vals else 0.0

    # Max drives (worst case)
    max_drives = {}
    for i in range(min(15, NUM_DRIVES)):
        vals = [s["drives"][i] for s in samples if len(s["drives"]) > i]
        max_drives[DRIVE_NAMES.get(i, f"drive_{i}")] = round(max(vals), 4) if vals else 0.0

    # Drive satisfaction: percentage of time each drive stays below 0.5
    drive_satisfaction = {}
    for i in range(min(15, NUM_DRIVES)):
        vals = [s["drives"][i] for s in samples if len(s["drives"]) > i]
        satisfied = sum(1 for v in vals if v < 0.5)
        drive_satisfaction[DRIVE_NAMES.get(i, f"drive_{i}")] = round(satisfied / len(vals) * 100, 1) if vals else 0.0

    # Reward/punishment rates
    reward_rate = sum(s["reward"] for s in samples)
    punishment_rate = sum(s["punishment"] for s in samples)
    mean_adrenaline = sum(s["adrenaline"] for s in samples) / n

    # Energy metabolism
    mean_glucose = sum(s.get("glucose", 0) for s in samples) / n
    mean_energy = sum(s.get("energy", 0) for s in samples) / n
    mean_atp = sum(s.get("atp", 0) for s in samples) / n

    # Survival stats
    deaths = sum(1 for s in samples if s["dead"])
    sleep_pct = sum(1 for s in samples if s["asleep"]) / n * 100
    alive_samples = sum(1 for s in samples if not s["dead"])

    # Life stage progression
    stages = [s.get("life_stage", 0) for s in samples]
    start_stage = stages[0]
    end_stage = stages[-1]

    # Distance traveled (exploration)
    total_dist = 0.0
    for i in range(1, n):
        dx = samples[i]["x"] - samples[i - 1]["x"]
        dy = samples[i]["y"] - samples[i - 1]["y"]
        total_dist += math.sqrt(dx * dx + dy * dy)

    # Movement variety: how many distinct positions visited (gridded to 100px cells)
    positions = set()
    for s in samples:
        gx = int(s["x"] / 100)
        gy = int(s["y"] / 100)
        positions.add((gx, gy))

    # Hunger management: did hunger decrease over time?
    hunger_start = sum(samples[0]["drives"][i] for i in range(1, 4)) / 3  # protein, carb, fat
    hunger_end = sum(samples[-1]["drives"][i] for i in range(1, 4)) / 3
    hunger_trend = round(hunger_end - hunger_start, 4)  # negative = improving

    # Fear management: time spent with fear > 0.25
    fear_pct = sum(1 for s in samples if len(s["drives"]) > 10 and s["drives"][10] > 0.25) / n * 100

    return {
        "brain_type": "SVRule",
        "timestamp": datetime.now().isoformat(),
        "num_samples": n,
        "duration_seconds": n * 2,  # approximate (2s interval)
        # Primary comparison metrics
        "drive_homeostasis": round(drive_homeostasis, 6),
        "reward_rate": round(reward_rate, 4),
        "punishment_rate": round(punishment_rate, 4),
        "mean_adrenaline": round(mean_adrenaline, 6),
        # Survival
        "deaths": deaths,
        "alive_samples": alive_samples,
        "sleep_percent": round(sleep_pct, 1),
        "life_stage_start": start_stage,
        "life_stage_end": end_stage,
        # Drive management
        "mean_drives": mean_drives,
        "max_drives": max_drives,
        "drive_satisfaction_pct": drive_satisfaction,
        "hunger_trend": hunger_trend,
        "fear_time_pct": round(fear_pct, 1),
        # Metabolism
        "mean_glucose": round(mean_glucose, 4),
        "mean_energy": round(mean_energy, 4),
        "mean_atp": round(mean_atp, 4),
        # Exploration
        "total_distance": round(total_dist, 1),
        "unique_cells_visited": len(positions),
        # Raw samples for detailed analysis
        "samples": samples,
    }


# ── Engine Management ─────────────────────────────────────────────────

def check_engine() -> bool:
    """Check if openc2e is running and world is loaded."""
    try:
        result = caos("outv totl 0 0 0")
        count = int(result)
        return count > 100
    except Exception:
        return False


def count_norns() -> int:
    """Count living norns (genus 1)."""
    try:
        return int(caos("outv totl 4 1 0"))
    except Exception:
        return 0


def spawn_norn() -> bool:
    """Spawn a norn via egg layer, skip incubation, wait for hatch."""
    print("  Spawning norn via egg layer...")
    try:
        # Press hatch button
        caos("enum 3 3 31 mesg wrt+ targ 1001 0 0 0 next")
        time.sleep(1.5)
        # Skip incubation
        caos("enum 3 4 1 pose 3 tick 1 next")
        # Wait for hatch (up to 15s)
        for _ in range(15):
            time.sleep(1)
            if count_norns() > 0:
                print("  Norn hatched!")
                return True
        print("  WARNING: Norn didn't hatch within timeout")
        return False
    except Exception as e:
        print(f"  ERROR spawning: {e}")
        return False


def disable_grendels_ettins():
    """Stop grendel/ettin mothers from spawning."""
    try:
        caos("enum 2 6 0 tick 0 next")   # grendel mothers
        caos("enum 2 7 0 tick 0 next")   # ettin mothers
        caos("enum 2 15 0 tick 0 next")  # grendel spawn points
        caos("enum 2 16 0 tick 0 next")  # ettin spawn points
    except Exception:
        pass


# ── Main Benchmark Loop ──────────────────────────────────────────────

def run_benchmark(duration: int, interval: float, no_spawn: bool) -> dict:
    """Run the benchmark observation loop."""
    print(f"\n{'='*60}")
    print(f"  SVRule Baseline Benchmark")
    print(f"  Duration: {duration}s  |  Interval: {interval}s  |  Samples: ~{int(duration / interval)}")
    print(f"{'='*60}\n")

    # Check engine
    print("[1/4] Checking engine...")
    if not check_engine():
        print("  ERROR: openc2e not running or world not loaded.")
        print("  Start engine WITHOUT --brain-module for SVRule mode:")
        print('  cd <PROJECT_ROOT>/openc2e/build64/RelWithDebInfo')
        print('  start "" "./openc2e.exe" --data-path "<PROJECT_ROOT>/creaturesexodusgame/Creatures Exodus/Creatures 3" --gamename "Creatures 3"')
        sys.exit(1)

    # Verify SVRule mode (no PythonBrain)
    # If PythonBrain is active, brain_debug.log would have [v2] entries
    # We can't directly query this, but we check if --brain-module was passed
    # by looking for the [v2] marker in dmpn output format
    print("  Engine running, world loaded.")

    # Spawn or find norn
    print("[2/4] Preparing norn...")
    disable_grendels_ettins()

    norn_count = count_norns()
    if norn_count == 0 and not no_spawn:
        if not spawn_norn():
            print("  FATAL: Could not spawn norn.")
            sys.exit(1)
    elif norn_count == 0 and no_spawn:
        print("  ERROR: No norns alive and --no-spawn set.")
        sys.exit(1)
    else:
        print(f"  Found {norn_count} norn(s), using first.")

    # Build the sample command once
    sample_cmd = build_sample_caos()
    samples = []
    num_expected = int(duration / interval)

    print(f"[3/4] Observing for {duration}s ({num_expected} samples)...")
    start_time = time.time()
    sample_num = 0
    consecutive_failures = 0

    while time.time() - start_time < duration:
        try:
            raw = caos(sample_cmd)
            sample = parse_sample(raw)
            if sample:
                sample["t"] = round(time.time() - start_time, 2)
                sample["sample_num"] = sample_num
                samples.append(sample)
                consecutive_failures = 0

                # Progress indicator every 10 samples
                if sample_num % 10 == 0:
                    alive = "DEAD" if sample["dead"] else "alive"
                    sleep = " (asleep)" if sample["asleep"] else ""
                    hunger = sum(sample["drives"][i] for i in range(1, 4)) / 3
                    fear = sample["drives"][10] if len(sample["drives"]) > 10 else 0
                    pos = f"({sample['x']:.0f},{sample['y']:.0f})"
                    elapsed = int(time.time() - start_time)
                    print(f"  [{elapsed:>3}s] #{sample_num:>3}: {pos:<16} hunger={hunger:.2f} fear={fear:.2f} [{alive}{sleep}]")
            else:
                consecutive_failures += 1
        except Exception as e:
            consecutive_failures += 1
            if consecutive_failures > 5:
                print(f"  WARNING: {consecutive_failures} consecutive failures: {e}")

        if consecutive_failures > 20:
            print("  FATAL: Too many consecutive failures - norn may be dead or engine crashed.")
            break

        sample_num += 1
        time.sleep(interval)

    elapsed = round(time.time() - start_time, 1)
    print(f"\n  Collected {len(samples)} samples in {elapsed}s")

    if len(samples) < 10:
        print("  WARNING: Very few samples collected - results may be unreliable.")

    # Compute metrics
    print("[4/4] Computing metrics...")
    metrics = compute_metrics(samples)
    metrics["actual_duration_seconds"] = elapsed
    metrics["sample_interval"] = interval
    return metrics


def print_summary(metrics: dict):
    """Print a human-readable summary of the benchmark results."""
    n = metrics.get("num_samples", 0)
    brain = metrics.get("brain_type", "Unknown")
    print(f"\n{'='*60}")
    print(f"  {brain} Benchmark Results")
    print(f"{'='*60}")
    print(f"  Samples:      {n}")
    print(f"  Duration:     {metrics.get('actual_duration_seconds', metrics.get('duration_seconds', '?'))}s")
    if n == 0:
        print(f"  ERROR: No samples collected!")
        print(f"{'='*60}")
        return
    print(f"  Deaths:       {metrics['deaths']}")
    print(f"  Sleep:        {metrics['sleep_percent']}%")
    print(f"  Life stage:   {metrics['life_stage_start']} -> {metrics['life_stage_end']}")
    print()
    print("  -- Behavioral Metrics --")
    print(f"  Drive homeostasis:    {metrics['drive_homeostasis']:.6f}  (lower = more stable)")
    print(f"  Reward rate:          {metrics['reward_rate']:.4f}")
    print(f"  Punishment rate:      {metrics['punishment_rate']:.4f}")
    print(f"  Mean adrenaline:      {metrics['mean_adrenaline']:.6f}")
    print(f"  Hunger trend:         {metrics['hunger_trend']:+.4f}  (negative = improving)")
    print(f"  Fear time:            {metrics['fear_time_pct']}%")
    print()
    print("  -- Exploration --")
    print(f"  Distance traveled:    {metrics['total_distance']:.0f} px")
    print(f"  Unique cells visited: {metrics['unique_cells_visited']}")
    print()
    print("  -- Metabolism --")
    print(f"  Mean glucose:         {metrics['mean_glucose']:.4f}")
    print(f"  Mean energy:          {metrics['mean_energy']:.4f}")
    print(f"  Mean ATP:             {metrics['mean_atp']:.4f}")
    print()
    print("  -- Drive Satisfaction (% time below 0.5) --")
    sat = metrics.get("drive_satisfaction_pct", {})
    for drive, pct in sorted(sat.items(), key=lambda x: x[1]):
        bar = "#" * int(pct / 5)
        print(f"    {drive:<14} {pct:>5.1f}% {bar}")
    print()
    print("  -- Mean Drives --")
    for drive, val in sorted(metrics["mean_drives"].items(), key=lambda x: -x[1]):
        if val > 0.01:
            bar = "#" * int(val * 40)
            print(f"    {drive:<14} {val:.4f} {bar}")
    print(f"{'='*60}")


# ── Entry Point ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Brain Benchmark - observable behavioral metrics")
    parser.add_argument("--duration", type=int, default=300, help="Observation duration in seconds (default: 300)")
    parser.add_argument("--interval", type=float, default=2.0, help="Sampling interval in seconds (default: 2.0)")
    parser.add_argument("--no-spawn", action="store_true", help="Don't spawn a norn, use existing")
    parser.add_argument("--brain-type", type=str, default="SVRule", help="Label: SVRule, CfC-instinct, CfC-RL, CfC-RL-LTM")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path (auto-generated if omitted)")
    args = parser.parse_args()

    metrics = run_benchmark(args.duration, args.interval, args.no_spawn)
    metrics["brain_type"] = args.brain_type  # Override label

    # Strip raw samples from the saved file (too large) - keep summary only
    save_metrics = {k: v for k, v in metrics.items() if k != "samples"}

    # Determine output path
    if args.output:
        out_path = args.output
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
        tag = args.brain_type.lower().replace(" ", "_").replace("+", "_")
        out_path = os.path.join(_PROJECT_ROOT, "eval", f"benchmark_{tag}_{date_str}.json")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(save_metrics, f, indent=2)
    print(f"\n  Results saved to: {out_path}")

    print_summary(metrics)


if __name__ == "__main__":
    main()
