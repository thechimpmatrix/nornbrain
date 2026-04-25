"""Quick KB lookups for common project questions.

Each subcommand wraps a small SQL query against kb/kb.sqlite. Designed
for project sessions to use as the first stop before falling back to raw
file reads.

Usage:
  python tools/kb_lookup.py contract           # comb contract for CfC build
  python tools/kb_lookup.py lobe <token>       # one lobe's attrs (e.g. comb, decn)
  python tools/kb_lookup.py tract <src> <dst>  # tracts between two lobes
  python tools/kb_lookup.py actions            # decision-action mapping (catalogue-resolved)
  python tools/kb_lookup.py drives             # drive index -> chemical index
  python tools/kb_lookup.py opcode <n>         # one SVRule opcode
  python tools/kb_lookup.py chemical <n>       # one chemical
  python tools/kb_lookup.py search <query>     # FTS5 prose search
  python tools/kb_lookup.py decisions          # all locked decisions + supersession
  python tools/kb_lookup.py gotchas            # all gotchas
  python tools/kb_lookup.py meta               # KB build metadata + counts
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "kb" / "kb.sqlite"


def _connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        print("kb.sqlite not found; run python -m kb.build first.",
              file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def cmd_contract(_):
    """Print the locked CfC comb contract for v1."""
    conn = _connect()
    print("=== CfC Comb Contract (Phase E.2 LOCKED 2026-04-26) ===")
    print()
    print("Source: norn.bondi.48.gen, breed-stable across 5 sampled genomes.")
    print("Spec:   docs/specs/2026-04-26-cfc-comb-replacement-design.md")
    print()
    print("Comb lobe:")
    for r in conn.execute(
        "SELECT key, value_text, value_num FROM attr "
        "WHERE host_id='lobe.comb' "
        "AND key IN ('neuron_count','grid_w','grid_h','update_time','tissue_id','rgb_r','rgb_g','rgb_b') "
        "ORDER BY key"
    ):
        v = r["value_text"] if r["value_text"] is not None else int(r["value_num"])
        print(f"  {r['key']:14s} = {v}")
    print()
    print("Inputs to comb (107-d concatenated, declaration order):")
    for r in conn.execute("""
        SELECT e.id, e.display_name, a1.value_text AS migrates,
               (SELECT value_num FROM attr WHERE host_id=e.id AND key='src_range_min') AS smin,
               (SELECT value_num FROM attr WHERE host_id=e.id AND key='src_range_max') AS smax,
               (SELECT value_num FROM attr WHERE host_id=e.id AND key='dst_range_min') AS dmin,
               (SELECT value_num FROM attr WHERE host_id=e.id AND key='dst_range_max') AS dmax,
               (SELECT value_num FROM attr WHERE host_id=e.id AND key='src_conn') AS sconn,
               (SELECT value_num FROM attr WHERE host_id=e.id AND key='dst_conn') AS dconn
        FROM entity e LEFT JOIN attr a1 ON a1.host_id=e.id AND a1.key='migrates'
        WHERE e.kind='tract' AND e.display_name LIKE '%->comb'
        ORDER BY e.id
    """):
        print(f"  {r['display_name']:14s} src[{int(r['smin']):>3d}..{int(r['smax']):>3d}] "
              f"dst[{int(r['dmin']):>3d}..{int(r['dmax']):>3d}]  "
              f"src_conn={int(r['sconn'])}  dst_conn={int(r['dconn'])}  "
              f"mig={r['migrates']}")
    print()
    print("Outputs from comb (51-d concatenated):")
    for r in conn.execute("""
        SELECT e.display_name,
               (SELECT value_num FROM attr WHERE host_id=e.id AND key='src_range_min') AS smin,
               (SELECT value_num FROM attr WHERE host_id=e.id AND key='src_range_max') AS smax,
               (SELECT value_num FROM attr WHERE host_id=e.id AND key='dst_range_min') AS dmin,
               (SELECT value_num FROM attr WHERE host_id=e.id AND key='dst_range_max') AS dmax,
               (SELECT value_num FROM attr WHERE host_id=e.id AND key='src_conn') AS sconn,
               (SELECT value_num FROM attr WHERE host_id=e.id AND key='dst_conn') AS dconn
        FROM entity e
        WHERE e.kind='tract' AND e.display_name LIKE 'comb->%'
        ORDER BY e.id
    """):
        print(f"  {r['display_name']:14s} src[{int(r['smin']):>3d}..{int(r['smax']):>3d}] "
              f"dst[{int(r['dmin']):>3d}..{int(r['dmax']):>3d}]  "
              f"src_conn={int(r['sconn'])}  dst_conn={int(r['dconn'])}")
    print()
    print("Reward signal: scalar (chemical[204] - chemical[205]) per tick.")
    print("Hidden:        440-d NCP-wired CfC.")
    print("Learning:      A2C eligibility trace 20 ticks gamma=0.95, "
          "entropy 0.1->0.01.")


def cmd_lobe(args):
    conn = _connect()
    eid = f"lobe.{args.token}"
    print(f"=== {eid} ===")
    for r in conn.execute(
        "SELECT key, value_text, value_num FROM attr WHERE host_id=? ORDER BY key",
        (eid,)
    ):
        v = r["value_text"] if r["value_text"] is not None else r["value_num"]
        print(f"  {r['key']:18s} {v}")


def cmd_tract(args):
    conn = _connect()
    print(f"=== {args.src} -> {args.dst} tracts ===")
    for r in conn.execute("""
        SELECT e.id, key, value_text, value_num FROM entity e
        JOIN attr a ON a.host_id=e.id
        WHERE e.kind='tract' AND e.display_name = ?
        ORDER BY e.id, a.key
    """, (f"{args.src}->{args.dst}",)):
        v = r["value_text"] if r["value_text"] is not None else r["value_num"]
        print(f"  {r['id']:30s} {r['key']:18s} {v}")


def cmd_actions(_):
    conn = _connect()
    print("=== Action -> decn-neuron mapping (catalogue-resolved) ===")
    print(f"{'idx':>3s} {'C3 source name':22s} {'common':12s} {'CAOS event':>10s} "
          f"{'decn neuron':>12s}")
    for offset in range(14):
        e = conn.execute(
            "SELECT name, display_name FROM entity WHERE id=?", (f"action.{offset}",)
        ).fetchone()
        ev = conn.execute(
            "SELECT value_num FROM attr WHERE host_id=? AND key='caos_event_openc2e'",
            (f"action.{offset}",)
        ).fetchone()
        nm = conn.execute(
            "SELECT value_num FROM attr WHERE host_id=? AND key='decn_neuron_id'",
            (f"catalogue.action_script_to_neuron.{offset}",)
        ).fetchone()
        print(f"{offset:>3d} {e['name']:22s} {e['display_name']:12s} "
              f"{int(ev['value_num']):>10d} {int(nm['value_num']) if nm else '-':>12}")


def cmd_drives(_):
    conn = _connect()
    print("=== Drive index -> chemical mapping ===")
    print(f"{'idx':>3s} {'C3 source name':22s} {'common':18s} {'chemical':>10s}")
    for offset in range(20):
        e = conn.execute(
            "SELECT name, display_name FROM entity WHERE id=?", (f"drive.{offset}",)
        ).fetchone()
        c = conn.execute(
            "SELECT value_num FROM attr WHERE host_id=? AND key='chemical_index'",
            (f"drive.{offset}",)
        ).fetchone()
        print(f"{offset:>3d} {e['name']:22s} {e['display_name']:18s} "
              f"{int(c['value_num']):>10d}")


def cmd_opcode(args):
    conn = _connect()
    eid = f"svrule_opcode.{args.n}"
    print(f"=== {eid} ===")
    e = conn.execute(
        "SELECT name, display_name, category, source_ref FROM entity WHERE id=?",
        (eid,)
    ).fetchone()
    if not e:
        print("Not found")
        return
    print(f"  name:       {e['name']}")
    print(f"  category:   {e['category']}")
    print(f"  source_ref: {e['source_ref']}")
    for r in conn.execute(
        "SELECT key, value_text, value_num FROM attr WHERE host_id=? ORDER BY key",
        (eid,)
    ):
        v = r["value_text"] if r["value_text"] is not None else r["value_num"]
        print(f"  {r['key']:18s} {v}")
    for r in conn.execute("SELECT tag FROM tag WHERE host_id=? ORDER BY tag", (eid,)):
        print(f"  tag:               {r['tag']}")


def cmd_chemical(args):
    conn = _connect()
    eid = f"chemical.{args.n}"
    print(f"=== {eid} ===")
    e = conn.execute(
        "SELECT name, display_name, category FROM entity WHERE id=?", (eid,)
    ).fetchone()
    if not e:
        print("Not found")
        return
    print(f"  name:           {e['name']}")
    print(f"  display_name:   {e['display_name']}")
    print(f"  role:           {e['category']}")
    for r in conn.execute(
        "SELECT key, value_text, value_num FROM attr WHERE host_id=? ORDER BY key",
        (eid,)
    ):
        v = r["value_text"] if r["value_text"] is not None else r["value_num"]
        print(f"  {r['key']:18s} {v}")


def cmd_search(args):
    conn = _connect()
    print(f"=== FTS5 search: {args.query!r} ===")
    sql = """
        SELECT rm.kind, rm.title, rm.source_path,
               snippet(reference_material_fts, 1, '**', '**', '...', 10) AS snip
        FROM reference_material_fts
        JOIN reference_material rm ON rm.id = reference_material_fts.rowid
        WHERE reference_material_fts MATCH ?
        ORDER BY rank
        LIMIT 8
    """
    for r in conn.execute(sql, (args.query,)):
        print(f"  [{r['kind']}] {r['source_path']}")
        print(f"    title: {r['title']}")
        print(f"    snip:  {r['snip'][:200]}")
        print()


def cmd_decisions(_):
    conn = _connect()
    print("=== Decisions (locked + supersession) ===")
    for r in conn.execute("""
        SELECT e.id, e.category AS status,
               (SELECT value_text FROM attr WHERE host_id=e.id AND key='choice') AS choice,
               (SELECT value_text FROM attr WHERE host_id=e.id AND key='locked') AS locked
        FROM entity e WHERE e.kind='decision' ORDER BY e.id
    """):
        print(f"  {r['id']:50s} status={r['status']:25s} locked={r['locked']}")
        if r["choice"]:
            print(f"      choice: {r['choice'][:100]}")
        for s in conn.execute(
            "SELECT to_id FROM link WHERE from_id=? AND kind='superseded_by'", (r["id"],)
        ):
            print(f"      superseded by: {s['to_id']}")
        for s in conn.execute(
            "SELECT to_id FROM link WHERE from_id=? AND kind='supersedes'", (r["id"],)
        ):
            print(f"      supersedes:    {s['to_id']}")


def cmd_gotchas(_):
    conn = _connect()
    print("=== Gotchas ===")
    for r in conn.execute("""
        SELECT e.id,
               (SELECT value_text FROM attr WHERE host_id=e.id AND key='wrong')   AS w,
               (SELECT value_text FROM attr WHERE host_id=e.id AND key='right')   AS rt,
               (SELECT value_text FROM attr WHERE host_id=e.id AND key='failure') AS f
        FROM entity e WHERE e.kind='gotcha' ORDER BY e.id
    """):
        print(f"\n  {r['id']}")
        if r["w"]:
            print(f"    WRONG:   {r['w'][:120]}")
        if r["rt"]:
            print(f"    RIGHT:   {r['rt'][:120]}")
        if r["f"]:
            print(f"    FAILURE: {r['f'][:120]}")


def cmd_meta(_):
    conn = _connect()
    print("=== KB build metadata ===")
    for r in conn.execute("SELECT key, value FROM meta ORDER BY key"):
        print(f"  {r['key']:18s} {r['value']}")
    print()
    print("=== Entity counts by kind ===")
    for r in conn.execute(
        "SELECT kind, count(*) AS n FROM entity GROUP BY kind ORDER BY n DESC"
    ):
        print(f"  {r['kind']:25s} {r['n']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="KB quick lookup")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("contract", help="Print the locked CfC comb contract").set_defaults(func=cmd_contract)

    p = sub.add_parser("lobe", help="One lobe's attrs")
    p.add_argument("token", help="4-char lobe token (comb, decn, attn, ...)")
    p.set_defaults(func=cmd_lobe)

    p = sub.add_parser("tract", help="Tracts between two lobes")
    p.add_argument("src", help="source lobe token")
    p.add_argument("dst", help="destination lobe token")
    p.set_defaults(func=cmd_tract)

    sub.add_parser("actions", help="Action -> decn-neuron + CAOS-event mapping").set_defaults(func=cmd_actions)
    sub.add_parser("drives", help="Drive index -> chemical mapping").set_defaults(func=cmd_drives)

    p = sub.add_parser("opcode", help="One SVRule opcode")
    p.add_argument("n", type=int, help="opcode index 0..68")
    p.set_defaults(func=cmd_opcode)

    p = sub.add_parser("chemical", help="One chemical")
    p.add_argument("n", type=int, help="chemical index 0..255")
    p.set_defaults(func=cmd_chemical)

    p = sub.add_parser("search", help="FTS5 prose search across all reference docs")
    p.add_argument("query", help="search terms")
    p.set_defaults(func=cmd_search)

    sub.add_parser("decisions", help="Locked decisions + supersession").set_defaults(func=cmd_decisions)
    sub.add_parser("gotchas",   help="All gotchas").set_defaults(func=cmd_gotchas)
    sub.add_parser("meta",      help="KB build metadata + entity counts").set_defaults(func=cmd_meta)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
