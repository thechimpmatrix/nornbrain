#!/usr/bin/env python3
"""NB Data Analyser - generates an HTML report from captured brain data.

Parses brain_debug.log, LTM memory banks, and crash logs to produce
interactive charts viewable in a browser.

Usage:
    python analyse_brain_data.py
    python analyse_brain_data.py --output eval/custom_report.html
"""

import json
import math
import os
import sys
from collections import Counter
from datetime import datetime

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.normpath(os.path.join(_THIS_DIR, ".."))

DEBUG_LOG = os.path.join(_PROJECT_ROOT, "openc2e", "build64", "RelWithDebInfo", "brain_debug.log")
LTM_PATH = os.path.join(_PROJECT_ROOT, "runtime", "memory_banks", "norn-live_memories.json")
CRASH_LOG = os.path.join(_PROJECT_ROOT, "openc2e", "build64", "RelWithDebInfo", "brain_crash.log")
DEFAULT_OUTPUT = os.path.join(_PROJECT_ROOT, "eval", "data_analysis.html")

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

DRIVE_COLOURS = {
    0: "#ff4444", 1: "#ff8800", 2: "#ffaa00", 3: "#ffcc00",
    4: "#4488ff", 5: "#ff4400", 6: "#8888aa", 7: "#6666aa",
    8: "#ff88cc", 9: "#aa4488", 10: "#ff0000", 11: "#888888",
    12: "#cc0000", 13: "#ff66aa", 14: "#44aa44",
}


def parse_debug_log(path):
    """Parse brain_debug.log into structured entries."""
    entries = []
    if not os.path.exists(path):
        return entries
    with open(path) as f:
        for line in f:
            try:
                parts = line.strip().split()
                if len(parts) < 4:
                    continue
                tick = int(parts[1].split("=")[1])
                attn = int(parts[2].split("=")[1])
                # Handle STIM tag after decn
                decn_str = parts[3].split("=")[1]
                decn = int(decn_str)

                # Parse drives
                drives = {}
                drive_start = line.find("drives=[")
                if drive_start >= 0:
                    drive_end = line.find("]", drive_start)
                    drive_str = line[drive_start + 8 : drive_end]
                    if drive_str:
                        for pair in drive_str.split("), "):
                            pair = pair.strip("()")
                            if "," in pair:
                                idx, val = pair.split(",")
                                drives[int(idx.strip())] = float(val.strip())

                # Parse RL info
                rl_steps = 0
                loss = 0.0
                reward = 0.0
                for p in parts:
                    if p.startswith("rl_steps="):
                        rl_steps = int(p.split("=")[1])
                    elif p.startswith("loss="):
                        loss = float(p.split("=")[1])
                    elif p.startswith("reward="):
                        reward = float(p.split("=")[1])

                entries.append({
                    "tick": tick,
                    "attn": attn,
                    "decn": decn,
                    "drives": drives,
                    "rl_steps": rl_steps,
                    "loss": loss,
                    "reward": reward,
                })
            except (ValueError, IndexError):
                continue
    return entries


def parse_ltm(path):
    """Parse LTM memory bank JSON."""
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def compute_windowed_diversity(entries, window=20):
    """Compute Shannon entropy of action distribution over sliding windows."""
    results = []
    for i in range(window, len(entries)):
        window_entries = entries[i - window : i]
        counts = Counter(e["decn"] for e in window_entries)
        total = sum(counts.values())
        entropy = 0.0
        for c in counts.values():
            if c > 0:
                p = c / total
                entropy -= p * math.log(p)
        max_entropy = math.log(14) if total > 0 else 1.0
        normalised = entropy / max_entropy if max_entropy > 0 else 0.0
        results.append({
            "tick_idx": i,
            "tick": entries[i]["tick"],
            "diversity": round(normalised, 4),
            "unique_actions": len(counts),
        })
    return results


def generate_html(entries, ltm_data, diversity, output_path):
    """Generate the HTML report with Chart.js visualisations."""

    # Action distribution
    action_counts = Counter(e["decn"] for e in entries)
    action_labels = [ACTION_NAMES.get(i, f"#{i}") for i in range(14)]
    action_values = [action_counts.get(i, 0) for i in range(14)]
    action_colours = ["#9ece6a" if action_counts.get(i, 0) > 0 else "#333" for i in range(14)]

    # Attention distribution
    attn_counts = Counter(e["attn"] for e in entries)
    attn_top = attn_counts.most_common(15)
    attn_labels = [CATEGORY_NAMES.get(idx, f"cat{idx}") for idx, _ in attn_top]
    attn_values = [count for _, count in attn_top]

    # Drive trajectories - collect all unique ticks with drive data
    drive_ticks = []
    drive_series = {i: [] for i in range(15)}
    for e in entries:
        if e["drives"]:
            drive_ticks.append(e["tick"])
            for i in range(15):
                drive_series[i].append(e["drives"].get(i, 0.0))

    # Build drive datasets (only include drives that ever exceed 0.05)
    drive_datasets = []
    for i in range(15):
        if drive_series[i] and max(drive_series[i]) > 0.05:
            drive_datasets.append({
                "label": DRIVE_NAMES.get(i, f"drive{i}"),
                "data": [round(v, 3) for v in drive_series[i]],
                "borderColor": DRIVE_COLOURS.get(i, "#888"),
                "fill": False,
                "tension": 0.3,
                "borderWidth": 1.5,
                "pointRadius": 0,
            })

    # Diversity over time
    div_ticks = [d["tick_idx"] for d in diversity]
    div_values = [d["diversity"] for d in diversity]

    # Reward over time
    reward_ticks = [e["tick"] for e in entries]
    reward_values = [e["reward"] for e in entries]

    # LTM analysis
    ltm_html = ""
    ltm_chart_data = ""
    if ltm_data and ltm_data.get("memories"):
        memories = ltm_data["memories"]
        ltm_points = []
        for m in memories:
            ltm_points.append({
                "x": CATEGORY_NAMES.get(m["attention_idx"], f"cat{m['attention_idx']}"),
                "y": round(m["valence"], 3),
                "r": max(3, min(20, m["recall_count"] + 3)),
                "intensity": round(m["intensity"], 3),
                "action": ACTION_NAMES.get(m["action_idx"], f"#{m['action_idx']}"),
                "recalls": m["recall_count"],
            })

        # Group by attention category for the chart
        ltm_categories = sorted(set(p["x"] for p in ltm_points))
        ltm_cat_idx = {c: i for i, c in enumerate(ltm_categories)}
        ltm_scatter = [{
            "x": ltm_cat_idx[p["x"]],
            "y": p["y"],
            "r": p["r"],
        } for p in ltm_points]

        recalled = sum(1 for m in memories if m["recall_count"] > 0)
        max_recalls = max((m["recall_count"] for m in memories), default=0)
        neg = sum(1 for m in memories if m["valence"] < 0)
        pos = sum(1 for m in memories if m["valence"] >= 0)

        ltm_html = f"""
        <div class="stat-row">
            <div class="stat"><span class="stat-val">{len(memories)}</span><span class="stat-label">memories</span></div>
            <div class="stat"><span class="stat-val">{recalled}</span><span class="stat-label">ever recalled</span></div>
            <div class="stat"><span class="stat-val">{max_recalls}</span><span class="stat-label">max recalls</span></div>
            <div class="stat"><span class="stat-val" style="color:#ff4444">{neg}</span><span class="stat-label">negative</span></div>
            <div class="stat"><span class="stat-val" style="color:#44ff44">{pos}</span><span class="stat-label">positive</span></div>
        </div>
        """
        ltm_chart_data = json.dumps({
            "categories": ltm_categories,
            "points": ltm_scatter,
        })

    # Summary stats
    total = len(entries)
    unique_actions = len(action_counts)
    top_action = ACTION_NAMES.get(action_counts.most_common(1)[0][0], "?") if action_counts else "?"
    top_action_pct = round(100 * action_counts.most_common(1)[0][1] / total, 1) if total else 0
    top_attn = CATEGORY_NAMES.get(attn_counts.most_common(1)[0][0], "?") if attn_counts else "?"
    mean_div = round(sum(div_values) / len(div_values), 3) if div_values else 0

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NB Brain Data Analysis</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0"></script>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ background: #1a1b26; color: #c0caf5; font-family: 'Segoe UI', sans-serif; padding: 20px; }}
    h1 {{ color: #7dcfff; margin-bottom: 5px; font-size: 1.8em; }}
    h2 {{ color: #bb9af7; margin: 30px 0 15px; font-size: 1.3em; border-bottom: 1px solid #333; padding-bottom: 5px; }}
    .subtitle {{ color: #565f89; margin-bottom: 20px; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0; }}
    .panel {{ background: #24283b; border-radius: 8px; padding: 20px; }}
    .panel-full {{ grid-column: 1 / -1; }}
    .stat-row {{ display: flex; gap: 20px; margin: 10px 0; flex-wrap: wrap; }}
    .stat {{ text-align: center; background: #1a1b26; border-radius: 6px; padding: 12px 20px; min-width: 80px; }}
    .stat-val {{ display: block; font-size: 1.8em; font-weight: bold; color: #7dcfff; }}
    .stat-label {{ display: block; font-size: 0.75em; color: #565f89; margin-top: 4px; }}
    canvas {{ max-height: 350px; }}
    .verdict {{ background: #1a1b26; border-left: 3px solid #e0af68; padding: 12px 16px; margin: 15px 0;
               font-size: 0.9em; line-height: 1.5; }}
    .verdict strong {{ color: #e0af68; }}
</style>
</head>
<body>

<h1>NB Brain Data Analysis</h1>
<p class="subtitle">Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} from {total} debug log entries</p>

<div class="stat-row">
    <div class="stat"><span class="stat-val">{total}</span><span class="stat-label">tick samples</span></div>
    <div class="stat"><span class="stat-val">{unique_actions}/14</span><span class="stat-label">actions used</span></div>
    <div class="stat"><span class="stat-val">{top_action}</span><span class="stat-label">dominant ({top_action_pct}%)</span></div>
    <div class="stat"><span class="stat-val">{top_attn}</span><span class="stat-label">top attention</span></div>
    <div class="stat"><span class="stat-val">{mean_div}</span><span class="stat-label">mean diversity</span></div>
</div>

<div class="grid">

<div class="panel">
    <h2>Action Distribution</h2>
    <canvas id="actionChart"></canvas>
</div>

<div class="panel">
    <h2>Attention Distribution (top 15)</h2>
    <canvas id="attnChart"></canvas>
</div>

<div class="panel panel-full">
    <h2>Drive Trajectories Over Time</h2>
    <canvas id="driveChart"></canvas>
</div>

<div class="panel panel-full">
    <h2>Action Diversity (sliding window, n=20)</h2>
    <canvas id="diversityChart"></canvas>
    <div class="verdict">
        <strong>Reading:</strong> 0.0 = one action repeated, 1.0 = all 14 actions equally.
        Healthy range is 0.3-0.7. Below 0.2 = perseveration. Above 0.8 = random thrashing.
    </div>
</div>

<div class="panel panel-full">
    <h2>Reward Signal Over Time</h2>
    <canvas id="rewardChart"></canvas>
</div>

{"<div class='panel panel-full'><h2>Long-Term Memory Bank</h2>" + ltm_html + "<canvas id='ltmChart'></canvas><div class='verdict'><strong>Reading:</strong> Each bubble is a memory. X = attention category at encoding. Y = valence (negative=bad, positive=good). Size = recall frequency. All-negative memories mean the norn never experienced reward.</div></div>" if ltm_data and ltm_data.get("memories") else ""}

</div>

<script>
Chart.defaults.color = '#c0caf5';
Chart.defaults.borderColor = '#333';

// Action distribution
new Chart(document.getElementById('actionChart'), {{
    type: 'bar',
    data: {{
        labels: {json.dumps(action_labels)},
        datasets: [{{
            data: {json.dumps(action_values)},
            backgroundColor: {json.dumps(action_colours)},
            borderWidth: 0,
        }}]
    }},
    options: {{
        plugins: {{ legend: {{ display: false }} }},
        scales: {{ y: {{ beginAtZero: true, title: {{ display: true, text: 'count' }} }} }}
    }}
}});

// Attention distribution
new Chart(document.getElementById('attnChart'), {{
    type: 'bar',
    data: {{
        labels: {json.dumps(attn_labels)},
        datasets: [{{
            data: {json.dumps(attn_values)},
            backgroundColor: '#7dcfff',
            borderWidth: 0,
        }}]
    }},
    options: {{
        indexAxis: 'y',
        plugins: {{ legend: {{ display: false }} }},
        scales: {{ x: {{ beginAtZero: true }} }}
    }}
}});

// Drive trajectories
new Chart(document.getElementById('driveChart'), {{
    type: 'line',
    data: {{
        labels: {json.dumps(drive_ticks)},
        datasets: {json.dumps(drive_datasets)}
    }},
    options: {{
        plugins: {{ legend: {{ position: 'right', labels: {{ boxWidth: 12, font: {{ size: 10 }} }} }} }},
        scales: {{
            x: {{ title: {{ display: true, text: 'tick' }}, ticks: {{ maxTicksLimit: 20 }} }},
            y: {{ beginAtZero: true, max: 1.0, title: {{ display: true, text: 'drive level' }} }}
        }},
        interaction: {{ mode: 'index', intersect: false }},
    }}
}});

// Diversity
new Chart(document.getElementById('diversityChart'), {{
    type: 'line',
    data: {{
        labels: {json.dumps(div_ticks)},
        datasets: [{{
            label: 'diversity',
            data: {json.dumps(div_values)},
            borderColor: '#9ece6a',
            fill: {{ target: 'origin', above: 'rgba(158,206,106,0.1)' }},
            tension: 0.3,
            borderWidth: 1.5,
            pointRadius: 0,
        }}]
    }},
    options: {{
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
            x: {{ title: {{ display: true, text: 'entry index' }}, ticks: {{ maxTicksLimit: 20 }} }},
            y: {{ beginAtZero: true, max: 1.0, title: {{ display: true, text: 'Shannon entropy (normalised)' }} }}
        }}
    }}
}});

// Reward
new Chart(document.getElementById('rewardChart'), {{
    type: 'line',
    data: {{
        labels: {json.dumps(reward_ticks)},
        datasets: [{{
            label: 'reward',
            data: {json.dumps(reward_values)},
            borderColor: '#e0af68',
            fill: false,
            tension: 0.1,
            borderWidth: 1,
            pointRadius: 0,
        }}]
    }},
    options: {{
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
            x: {{ title: {{ display: true, text: 'tick' }}, ticks: {{ maxTicksLimit: 20 }} }},
            y: {{ title: {{ display: true, text: 'reward signal' }} }}
        }}
    }}
}});

// LTM scatter
{"" if not ltm_chart_data else f'''
(function() {{
    var ltmData = {ltm_chart_data};
    new Chart(document.getElementById('ltmChart'), {{
        type: 'bubble',
        data: {{
            datasets: [{{
                label: 'memories',
                data: ltmData.points,
                backgroundColor: ltmData.points.map(function(p) {{
                    return p.y < 0 ? 'rgba(255,68,68,0.6)' : 'rgba(68,255,68,0.6)';
                }}),
                borderColor: ltmData.points.map(function(p) {{
                    return p.y < 0 ? '#ff4444' : '#44ff44';
                }}),
                borderWidth: 1,
            }}]
        }},
        options: {{
            plugins: {{ legend: {{ display: false }} }},
            scales: {{
                x: {{
                    type: 'linear',
                    title: {{ display: true, text: 'attention category' }},
                    ticks: {{
                        callback: function(v) {{ return ltmData.categories[v] || v; }},
                        maxTicksLimit: ltmData.categories.length
                    }}
                }},
                y: {{
                    title: {{ display: true, text: 'valence (neg=bad, pos=good)' }},
                    min: -1, max: 1,
                }}
            }}
        }}
    }});
}})();
'''}

</script>
</body>
</html>"""

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="NB Brain Data Analyser")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--debug-log", default=DEBUG_LOG)
    parser.add_argument("--ltm", default=LTM_PATH)
    args = parser.parse_args()

    print("NB Brain Data Analyser")
    print("=" * 40)

    entries = parse_debug_log(args.debug_log)
    print(f"  Debug log: {len(entries)} entries")

    ltm_data = parse_ltm(args.ltm)
    if ltm_data:
        print(f"  LTM bank: {len(ltm_data.get('memories', []))} memories")
    else:
        print("  LTM bank: not found")

    diversity = compute_windowed_diversity(entries, window=20)
    print(f"  Diversity windows: {len(diversity)}")

    path = generate_html(entries, ltm_data, diversity, args.output)
    print(f"\n  Report: {path}")

    # Auto-archive: timestamped copy to eval/archive/ and <BACKUP_DIR>/
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    archive_dir = os.path.join(_PROJECT_ROOT, "eval", "archive")
    external_dir = "<BACKUP_DIR>"
    os.makedirs(archive_dir, exist_ok=True)

    import shutil
    archive_path = os.path.join(archive_dir, f"data_analysis_{stamp}.html")
    shutil.copy2(path, archive_path)
    print(f"  Archived: {archive_path}")

    if os.path.isdir("D:/"):
        os.makedirs(external_dir, exist_ok=True)
        ext_path = os.path.join(external_dir, f"data_analysis_{stamp}.html")
        shutil.copy2(path, ext_path)
        print(f"  External: {ext_path}")
    else:
        print(f"  External: D:/ not available, skipped")

    print(f"  Open in browser to view.")


if __name__ == "__main__":
    main()
