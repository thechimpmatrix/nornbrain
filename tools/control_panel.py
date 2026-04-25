"""
NB Control Panel - tools/control_panel.py

Tkinter desktop GUI for NORNBRAIN project. Wraps test_harness.py functions
and sends CAOS to the openc2e NB engine via TCP port 20001.

Window: 1800x600, dark theme, monospace font.
All commands execute on background threads to keep the GUI responsive.
"""

import os
import sys
import json
import time
import datetime
import threading
import subprocess
import webbrowser
import tkinter as tk
from tkinter import ttk

# ---------------------------------------------------------------------------
# Path setup - import from sibling tool modules
# ---------------------------------------------------------------------------

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _TOOLS_DIR)

from test_harness import (
    caos,
    spawn_eggs, hatch_all, spawn_and_hatch, auto_name_all,
    list_creatures, population, kill_grendels, kill_ettins,
    save_world, activate_all_gadgets, world_info, tick_count,
    teleport_camera, teleport_all_norns, teleport_to_hand,
    spawn_food, spawn_toy, list_food, list_toys,
    inject_reward, inject_punishment, inject_chem,
    read_drives, creature_status, fire_stimulus,
)
from test_harness_caos import (
    generate_panel_script,
    generate_panel_handlers_script,
    remove_panel,
)
from test_harness_overlay import (
    generate_norn_labels_script,
    generate_remove_overlays_script,
)

# ---------------------------------------------------------------------------
# Engine / monitor paths
# ---------------------------------------------------------------------------

ENGINE_EXE   = r"<PROJECT_ROOT>\openc2e\build64\RelWithDebInfo\openc2e.exe"
DATA_PATH    = r"<PROJECT_ROOT>\creaturesexodusgame\Creatures Exodus\Creatures 3"
BRAIN_MODULE = r"<PROJECT_ROOT>\openc2e\tools\nornbrain_cfc_v2.py"
MONITOR_PY   = r"<PROJECT_ROOT>\openc2e\tools\web_monitor.py"
MONITOR_URL  = "http://localhost:8088/"

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

BG        = "#1a1a2e"
FG        = "#e0e0e0"
BTN_BG    = "#2d2d44"
BTN_FG    = "#e0e0e0"
ACCENT    = "#00d4ff"
ENTRY_BG  = "#242438"
LOG_BG    = "#0f0f1e"
FONT      = ("Consolas", 9)
HDR_FONT  = ("Consolas", 10, "bold")
LOG_FONT  = ("Consolas", 9)

BTN_W     = 18   # character width
BTN_H     = 1    # character height
BTN_PAD_X = 3
BTN_PAD_Y = 2

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")


# ---------------------------------------------------------------------------
# Main application class
# ---------------------------------------------------------------------------

class NBControlPanel:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("NB Control Panel")
        root.geometry("1800x600")
        root.configure(bg=BG)
        root.resizable(True, True)

        self._build_ui()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Top frame holds 6 columns (fixed 400px height), bottom frame holds log
        top = tk.Frame(self.root, bg=BG, height=400)
        top.pack(side=tk.TOP, fill=tk.X, expand=False, padx=6, pady=6)
        top.pack_propagate(False)

        bottom = tk.Frame(self.root, bg=BG)
        bottom.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        self._build_col1_creatures(top)
        self._build_col2_world(top)
        self._build_col3_food(top)
        self._build_col4_brain(top)
        self._build_col5_panel_overlay(top)
        self._build_col6_engine(top)
        self._build_log(bottom)

    def _column(self, parent, title: str, width: int) -> tk.Frame:
        """Create a labelled column frame."""
        outer = tk.Frame(parent, bg=BG, width=width)
        outer.pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=0)
        outer.pack_propagate(False)

        lbl = tk.Label(outer, text=title, bg=BG, fg=ACCENT,
                       font=HDR_FONT, anchor="w")
        lbl.pack(fill=tk.X, pady=(0, 4))

        sep = tk.Frame(outer, bg=ACCENT, height=1)
        sep.pack(fill=tk.X, pady=(0, 6))

        return outer

    def _btn(self, parent, label: str, cmd, **kw) -> tk.Button:
        """Create a styled button."""
        b = tk.Button(
            parent, text=label, command=cmd,
            bg=BTN_BG, fg=BTN_FG, activebackground=ACCENT,
            activeforeground=BG, font=FONT,
            width=BTN_W, height=BTN_H,
            relief=tk.FLAT, bd=0, cursor="hand2",
            **kw
        )
        b.pack(fill=tk.X, padx=BTN_PAD_X, pady=BTN_PAD_Y)
        return b

    def _label(self, parent, text: str) -> tk.Label:
        lbl = tk.Label(parent, text=text, bg=BG, fg=FG, font=FONT, anchor="w")
        lbl.pack(fill=tk.X, padx=BTN_PAD_X, pady=(6, 0))
        return lbl

    def _entry(self, parent, default: str = "") -> tk.Entry:
        e = tk.Entry(parent, bg=ENTRY_BG, fg=FG, insertbackground=ACCENT,
                     font=FONT, relief=tk.FLAT, bd=2)
        e.insert(0, default)
        e.pack(fill=tk.X, padx=BTN_PAD_X, pady=BTN_PAD_Y)
        return e

    # ------------------------------------------------------------------
    # Column 1: Creature Management
    # ------------------------------------------------------------------

    def _build_col1_creatures(self, parent):
        col = self._column(parent, "Creature Management", 230)
        self._btn(col, "Spawn 2 Eggs",    lambda: self._run("spawn_eggs(n=2)", spawn_eggs, n=2))
        self._btn(col, "Hatch All",        lambda: self._run("hatch_all()", hatch_all))
        self._btn(col, "Spawn & Hatch 2",  lambda: self._run("spawn_and_hatch(n=2)", spawn_and_hatch, n=2))
        self._btn(col, "Auto Name All",    lambda: self._run("auto_name_all()", auto_name_all))
        self._btn(col, "List Creatures",   lambda: self._run("list_creatures()", list_creatures))
        self._btn(col, "Population",       lambda: self._run("population()", population))
        self._btn(col, "Kill Grendels",    lambda: self._run("kill_grendels()", kill_grendels))
        self._btn(col, "Kill Ettins",      lambda: self._run("kill_ettins()", kill_ettins))

    # ------------------------------------------------------------------
    # Column 2: World Control
    # ------------------------------------------------------------------

    def _build_col2_world(self, parent):
        col = self._column(parent, "World Control", 235)
        self._btn(col, "Prep World",       lambda: self._run("prep_world()", self._prep_world))
        self._btn(col, "Save World",       lambda: self._run("save_world()", save_world))
        self._btn(col, "Activate Gadgets", lambda: self._run("activate_all_gadgets()", activate_all_gadgets))
        self._btn(col, "World Info",       lambda: self._run("world_info()", world_info))
        self._btn(col, "Tick Count",       lambda: self._run("tick_count()", tick_count))

        self._label(col, "Camera:")
        for name, key in [
            ("Norn Terrarium", "norn-terrarium"),
            ("Desert",         "ettin-desert"),
            ("Jungle",         "grendel-jungle"),
            ("Aquatic",        "aquatic"),
            ("Corridor",       "corridor"),
            ("Learning Room",  "learning-room"),
        ]:
            k = key  # capture
            self._btn(col, name, lambda k=k: self._run(
                f"teleport_camera({k!r})", teleport_camera, k))

    # ------------------------------------------------------------------
    # Column 3: Food & Toys
    # ------------------------------------------------------------------

    def _build_col3_food(self, parent):
        col = self._column(parent, "Food & Toys", 210)
        self._btn(col, "Spawn Fruit",  lambda: self._run("spawn_food('fruit')", spawn_food, "fruit"))
        self._btn(col, "Spawn Cheese", lambda: self._run("spawn_food('cheese')", spawn_food, "cheese"))
        self._btn(col, "Spawn Carrot", lambda: self._run("spawn_food('carrot')", spawn_food, "carrot"))
        self._btn(col, "Spawn Toy",    lambda: self._run("spawn_toy()", spawn_toy))
        self._btn(col, "List Food",    lambda: self._run("list_food()", list_food))
        self._btn(col, "List Toys",    lambda: self._run("list_toys()", list_toys))

    # ------------------------------------------------------------------
    # Column 4: Brain Chemistry
    # ------------------------------------------------------------------

    def _build_col4_brain(self, parent):
        col = self._column(parent, "Brain Chemistry", 280)

        self._btn(col, "Reward (0.5)",   lambda: self._run_targeted("inject_reward", inject_reward, 0.5))
        self._btn(col, "Reward (1.0)",   lambda: self._run_targeted("inject_reward", inject_reward, 1.0))
        self._btn(col, "Punish (0.5)",   lambda: self._run_targeted("inject_punishment", inject_punishment, 0.5))
        self._btn(col, "Punish (1.0)",   lambda: self._run_targeted("inject_punishment", inject_punishment, 1.0))
        self._btn(col, "Read Drives",    lambda: self._run_targeted("read_drives", read_drives))
        self._btn(col, "Creature Status",lambda: self._run_targeted("creature_status", creature_status))

        self._label(col, "Target Creature:")
        sel_row = tk.Frame(col, bg=BG)
        sel_row.pack(fill=tk.X, padx=BTN_PAD_X, pady=BTN_PAD_Y)
        self._creature_var = tk.StringVar(value="(all norns)")
        self._creature_dropdown = ttk.Combobox(
            sel_row, textvariable=self._creature_var,
            font=FONT, state="readonly", width=18,
        )
        self._creature_dropdown["values"] = ["(all norns)"]
        self._creature_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(sel_row, text="\u21bb", command=self._refresh_creatures,
                  bg=BTN_BG, fg=ACCENT, activebackground=ACCENT, activeforeground=BG,
                  font=("Consolas", 12), relief=tk.FLAT, bd=0, cursor="hand2", width=2,
                  ).pack(side=tk.LEFT, padx=(3, 0))
        # Style the combobox for dark theme
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox",
                        fieldbackground=ENTRY_BG, background=BTN_BG,
                        foreground=FG, arrowcolor=ACCENT, borderwidth=0)
        # Cache: display_name -> NB-id or None
        self._creature_map = {}
        # Auto-refresh on startup
        self.root.after(2000, self._refresh_creatures)

        self._label(col, "Chem #  Amount:")
        chem_row = tk.Frame(col, bg=BG)
        chem_row.pack(fill=tk.X, padx=BTN_PAD_X, pady=BTN_PAD_Y)
        self._chem_num_entry = tk.Entry(chem_row, bg=ENTRY_BG, fg=FG,
                                        insertbackground=ACCENT, font=FONT,
                                        relief=tk.FLAT, bd=2, width=5)
        self._chem_num_entry.insert(0, "204")
        self._chem_num_entry.pack(side=tk.LEFT)
        self._chem_amt_entry = tk.Entry(chem_row, bg=ENTRY_BG, fg=FG,
                                        insertbackground=ACCENT, font=FONT,
                                        relief=tk.FLAT, bd=2, width=6)
        self._chem_amt_entry.insert(0, "0.5")
        self._chem_amt_entry.pack(side=tk.LEFT, padx=(4, 0))
        tk.Button(chem_row, text="Inject Chem", command=self._inject_chem_clicked,
                  bg=BTN_BG, fg=BTN_FG, activebackground=ACCENT, activeforeground=BG,
                  font=FONT, relief=tk.FLAT, bd=0, cursor="hand2"
                  ).pack(side=tk.LEFT, padx=(4, 0))

        self._label(col, "Stim # (fire_stimulus):")
        stim_row = tk.Frame(col, bg=BG)
        stim_row.pack(fill=tk.X, padx=BTN_PAD_X, pady=BTN_PAD_Y)
        self._stim_num_entry = tk.Entry(stim_row, bg=ENTRY_BG, fg=FG,
                                        insertbackground=ACCENT, font=FONT,
                                        relief=tk.FLAT, bd=2, width=5)
        self._stim_num_entry.insert(0, "0")
        self._stim_num_entry.pack(side=tk.LEFT)
        tk.Button(stim_row, text="Fire Stimulus", command=self._fire_stimulus_clicked,
                  bg=BTN_BG, fg=BTN_FG, activebackground=ACCENT, activeforeground=BG,
                  font=FONT, relief=tk.FLAT, bd=0, cursor="hand2"
                  ).pack(side=tk.LEFT, padx=(4, 0))

    # ------------------------------------------------------------------
    # Column 5: In-Game Panel & Overlays
    # ------------------------------------------------------------------

    def _build_col5_panel_overlay(self, parent):
        col = self._column(parent, "In-Game Panel & Overlays", 230)
        self._btn(col, "Inject Panel",    lambda: self._run("inject-panel", self._inject_panel))
        self._btn(col, "Remove Panel",    lambda: self._run("remove-panel", self._remove_panel))
        self._btn(col, "Inject Overlays", lambda: self._run("inject-overlays", self._inject_overlays))
        self._btn(col, "Remove Overlays", lambda: self._run("remove-overlays", self._remove_overlays))
        self._btn(col, "TP All to Terr.", lambda: self._run(
            "teleport_all_norns('norn-terrarium')", teleport_all_norns, "norn-terrarium"))
        self._btn(col, "TP to Hand",      lambda: self._run("teleport_to_hand()", teleport_to_hand))

    # ------------------------------------------------------------------
    # Column 6: Engine Control
    # ------------------------------------------------------------------

    def _build_col6_engine(self, parent):
        col = self._column(parent, "Engine Control", 230)
        self._btn(col, "Kill Engine",          self._kill_engine)
        self._btn(col, "Start Engine (SVRule)", self._start_engine_svrule)
        self._btn(col, "Start Engine (CfC)",    self._start_engine_cfc)
        self._btn(col, "Start Monitor",         self._start_monitor)
        self._btn(col, "Open Monitor",          lambda: webbrowser.open(MONITOR_URL))

    # ------------------------------------------------------------------
    # Log feed
    # ------------------------------------------------------------------

    def _build_log(self, parent):
        hdr = tk.Frame(parent, bg=BG)
        hdr.pack(fill=tk.X)

        tk.Label(hdr, text="Log Feed", bg=BG, fg=ACCENT, font=HDR_FONT).pack(side=tk.LEFT)

        clear_btn = tk.Button(
            hdr, text="Clear Log", command=self._clear_log,
            bg=BTN_BG, fg=BTN_FG, activebackground=ACCENT, activeforeground=BG,
            font=FONT, relief=tk.FLAT, bd=0, cursor="hand2"
        )
        clear_btn.pack(side=tk.RIGHT, padx=4)

        sep = tk.Frame(parent, bg=ACCENT, height=1)
        sep.pack(fill=tk.X, pady=(2, 4))

        log_frame = tk.Frame(parent, bg=BG)
        log_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(log_frame, bg=BG, troughcolor=BTN_BG)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(
            log_frame, bg=LOG_BG, fg=FG, font=LOG_FONT,
            yscrollcommand=scrollbar.set,
            state=tk.DISABLED, relief=tk.FLAT, bd=0,
            wrap=tk.WORD, height=10,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)

        # Tag for command label
        self.log_text.tag_config("cmd", foreground=ACCENT)
        self.log_text.tag_config("rsp", foreground="#a0ffa0")
        self.log_text.tag_config("err", foreground="#ff6060")
        self.log_text.tag_config("sys", foreground="#888888")

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------

    def _log(self, text: str, tag: str = ""):
        def _write():
            self.log_text.config(state=tk.NORMAL)
            if tag:
                self.log_text.insert(tk.END, text + "\n", tag)
            else:
                self.log_text.insert(tk.END, text + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        self.root.after(0, _write)

    def _log_cmd(self, label: str):
        self._log(f"[{_ts()}] CMD: {label}", "cmd")

    def _log_rsp(self, data):
        if isinstance(data, (dict, list)):
            text = json.dumps(data, indent=None, separators=(", ", ": "), default=str)
        else:
            text = str(data)
        self._log(f"[{_ts()}] RSP: {text}", "rsp")

    def _log_err(self, exc: Exception):
        self._log(f"[{_ts()}] ERR: {exc}", "err")

    def _log_sys(self, msg: str):
        self._log(f"[{_ts()}] SYS: {msg}", "sys")

    def _clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Thread runner
    # ------------------------------------------------------------------

    def _run(self, label: str, fn, *args, **kwargs):
        """Execute fn(*args, **kwargs) on a background thread. Log result."""
        self._log_cmd(label)

        def worker():
            try:
                result = fn(*args, **kwargs)
                self._log_rsp(result)
            except Exception as exc:
                self._log_err(exc)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    # ------------------------------------------------------------------
    # Targeted command helper (reads creature dropdown at click time)
    # ------------------------------------------------------------------

    def _run_targeted(self, name: str, fn, *extra_args):
        """Run fn(creature_id, *extra_args) using the currently selected creature."""
        cid = self._get_selected_creature_id()
        label = f"{name}({cid!r}" + (f", {', '.join(str(a) for a in extra_args)}" if extra_args else "") + ")"
        self._run(label, fn, cid, *extra_args)

    # ------------------------------------------------------------------
    # Creature selector
    # ------------------------------------------------------------------

    def _refresh_creatures(self):
        """Refresh the creature dropdown from the live engine."""
        def worker():
            try:
                creatures = list_creatures()
                # Build display names: try to get NB-name via GTOS/hist
                entries = ["(all norns)"]
                cmap = {"(all norns)": None}
                genus_names = {1: "norn", 2: "grendel", 3: "ettin"}
                for i, c in enumerate(creatures):
                    gname = genus_names.get(c["genus"], "?")
                    name = c.get("name", "")
                    if name:
                        display = f"{name} ({gname})"
                    else:
                        display = f"{gname} #{i+1} ({c['x']:.0f},{c['y']:.0f})"
                    entries.append(display)
                    cmap[display] = name if name else None
                self._creature_map = cmap
                self.root.after(0, lambda: self._creature_dropdown.configure(values=entries))
                self._log_sys(f"Refreshed creatures: {len(creatures)} found")
            except Exception as exc:
                self._log_err(exc)
        threading.Thread(target=worker, daemon=True).start()

    def _get_selected_creature_id(self) -> str | None:
        """Return the NB-name of the selected creature, or None for all."""
        sel = self._creature_var.get()
        return self._creature_map.get(sel)

    # ------------------------------------------------------------------
    # Parametrised button handlers (brain chem column)
    # ------------------------------------------------------------------

    def _inject_chem_clicked(self):
        creature_id = self._get_selected_creature_id()
        try:
            chem_num = int(self._chem_num_entry.get().strip())
            amount   = float(self._chem_amt_entry.get().strip())
        except ValueError as exc:
            self._log_err(exc)
            return

        label = f"inject_chem({creature_id!r}, {chem_num}, {amount})"
        if creature_id:
            self._run(label, inject_chem, creature_id, chem_num, amount)
        else:
            def _inject_first():
                cmd = f"enum 4 1 0\nchem {chem_num} {amount:.4f}\nstop\nnext"
                caos(cmd)
                return {"status": "ok", "chem": chem_num, "amount": amount,
                        "target": "all_norns"}
            self._run(label, _inject_first)

    def _fire_stimulus_clicked(self):
        creature_id = self._get_selected_creature_id()
        try:
            stim_num = int(self._stim_num_entry.get().strip())
        except ValueError as exc:
            self._log_err(exc)
            return

        if not creature_id:
            self._log_err(Exception("Creature ID required for fire_stimulus"))
            return

        label = f"fire_stimulus({creature_id!r}, {stim_num})"
        self._run(label, fire_stimulus, creature_id, stim_num)

    # ------------------------------------------------------------------
    # Inline prep_world
    # ------------------------------------------------------------------

    def _prep_world(self):
        activate_all_gadgets()
        time.sleep(0.5)
        spawn_and_hatch(n=2)
        time.sleep(4)
        auto_name_all()
        return {"status": "ok", "action": "prep_world"}

    # ------------------------------------------------------------------
    # In-game panel / overlay dispatch
    # ------------------------------------------------------------------

    def _inject_panel(self):
        panel_caos = generate_panel_script()
        r1 = caos(panel_caos)
        handler_caos = generate_panel_handlers_script()
        r2 = caos(handler_caos)
        return {"panel": r1 or "ok", "handlers": r2 or "ok"}

    def _remove_panel(self):
        results = []
        for sp in range(20):
            try:
                caos(f"enum 3 103 {sp}\nkill targ\nnext")
                results.append(sp)
            except Exception:
                pass
        return {"removed_species": results, "status": "ok"}

    def _inject_overlays(self):
        script = generate_norn_labels_script()
        r = caos(script)
        return {"status": r or "ok"}

    def _remove_overlays(self):
        script = generate_remove_overlays_script()
        r = caos(script)
        return {"status": r or "ok"}

    # ------------------------------------------------------------------
    # Engine control (subprocess)
    # ------------------------------------------------------------------

    def _kill_engine(self):
        self._log_cmd("Kill engine (powershell Stop-Process openc2e)")
        def worker():
            try:
                subprocess.run(
                    ["powershell", "-Command", "Stop-Process -Name openc2e -Force"],
                    capture_output=True, timeout=10,
                )
                self._log_sys("Engine kill signal sent.")
            except Exception as exc:
                self._log_err(exc)
        threading.Thread(target=worker, daemon=True).start()

    def _start_engine_svrule(self):
        self._log_cmd("Start Engine (SVRule)")
        def worker():
            try:
                subprocess.Popen(
                    [ENGINE_EXE,
                     "--data-path", DATA_PATH,
                     "--gamename", "Creatures 3"],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
                self._log_sys("Engine (SVRule) launched.")
            except Exception as exc:
                self._log_err(exc)
        threading.Thread(target=worker, daemon=True).start()

    def _start_engine_cfc(self):
        self._log_cmd("Start Engine (CfC)")
        def worker():
            try:
                subprocess.Popen(
                    [ENGINE_EXE,
                     "--data-path", DATA_PATH,
                     "--gamename", "Creatures 3",
                     "--brain-module", BRAIN_MODULE],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
                self._log_sys("Engine (CfC) launched.")
            except Exception as exc:
                self._log_err(exc)
        threading.Thread(target=worker, daemon=True).start()

    def _start_monitor(self):
        self._log_cmd("Start Monitor (web_monitor.py)")
        def worker():
            try:
                subprocess.Popen(
                    [sys.executable, MONITOR_PY],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
                self._log_sys("Monitor launched - http://localhost:8088/")
            except Exception as exc:
                self._log_err(exc)
        threading.Thread(target=worker, daemon=True).start()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    root = tk.Tk()
    app = NBControlPanel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
