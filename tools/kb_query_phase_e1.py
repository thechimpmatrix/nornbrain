"""Phase E.1 canonical KB query.

Question: What is comb's input/output contract, and which decisions
and reference docs cover the comb-as-replacement pivot?

This script demonstrates the "single front door" pattern for CC: from
a small initial input ('comb' as the topic), one round trip through the
KB returns the entity, all attrs, all outbound external_refs, and all
relevant FTS5 hits.

Run:
  python tools/kb_query_phase_e1.py             # prints to stdout
  python tools/kb_query_phase_e1.py --json      # emits JSON
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "kb" / "kb.sqlite"


def gather_comb_context(conn: sqlite3.Connection) -> dict:
    """Single-topic gather: entity + attrs + external_refs + FTS hits."""
    out: dict = {
        "entity": None,
        "attrs": [],
        "external_refs": [],
        "links": {"outbound": [], "inbound": []},
        "fts5_hits": [],
        "supersession": [],
    }
    conn.row_factory = sqlite3.Row

    # 1. Entity
    cur = conn.execute(
        "SELECT id, kind, name, display_name, category, tier, source_id, "
        "source_ref FROM entity WHERE id='lobe.comb'"
    )
    row = cur.fetchone()
    if not row:
        out["entity"] = None
        return out
    out["entity"] = dict(row)

    # 2. Attrs
    for r in conn.execute(
        "SELECT key, value_text, value_num, source_id, source_ref "
        "FROM attr WHERE host_id='lobe.comb' ORDER BY key"
    ):
        out["attrs"].append(dict(r))

    # 3. External refs (outbound)
    for r in conn.execute(
        "SELECT er.store_id, er.ref_key, er.ref_kind, er.label, "
        "       sr.location, sr.provenance "
        "FROM external_ref er "
        "JOIN source_registry sr ON sr.id = er.store_id "
        "WHERE er.entity_id='lobe.comb'"
    ):
        out["external_refs"].append(dict(r))

    # 4. Links
    for r in conn.execute(
        "SELECT to_id, kind, source_id, source_ref FROM link "
        "WHERE from_id='lobe.comb'"
    ):
        out["links"]["outbound"].append(dict(r))
    for r in conn.execute(
        "SELECT from_id, kind, source_id, source_ref FROM link "
        "WHERE to_id='lobe.comb'"
    ):
        out["links"]["inbound"].append(dict(r))

    # 5. FTS5 prose hits relevant to comb
    for r in conn.execute("""
        SELECT rm.kind, rm.title, rm.source_path,
               snippet(reference_material_fts, 1, '**', '**', '...', 12) AS snip
        FROM reference_material_fts
        JOIN reference_material rm ON rm.id = reference_material_fts.rowid
        WHERE reference_material_fts MATCH 'comb dendrite migration OR comb learning OR combination lobe'
        ORDER BY rank
        LIMIT 8
    """):
        out["fts5_hits"].append(dict(r))

    # 6. Architecture pivot decisions and supersession
    for r in conn.execute("""
        SELECT e.id, e.category AS status,
               (SELECT value_text FROM attr WHERE host_id=e.id AND key='choice') AS choice,
               (SELECT value_text FROM attr WHERE host_id=e.id AND key='reason') AS reason,
               (SELECT value_text FROM attr WHERE host_id=e.id AND key='locked') AS locked
        FROM entity e WHERE e.id LIKE 'decision.architecture_pivot%'
        ORDER BY e.id
    """):
        d = dict(r)
        # Append supersession links
        d["superseded_by"] = [
            row["to_id"] for row in conn.execute(
                "SELECT to_id FROM link WHERE from_id=? AND kind='superseded_by'",
                (d["id"],)
            )
        ]
        d["supersedes"] = [
            row["to_id"] for row in conn.execute(
                "SELECT to_id FROM link WHERE from_id=? AND kind='supersedes'",
                (d["id"],)
            )
        ]
        out["supersession"].append(d)

    return out


def render_text(ctx: dict) -> str:
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("Phase E.1 Canonical KB Query: comb input/output contract")
    lines.append("=" * 70)

    if not ctx["entity"]:
        lines.append("\nNo entity found for lobe.comb. KB build incomplete?")
        return "\n".join(lines)

    e = ctx["entity"]
    lines.append(f"\nEntity: {e['id']}  ({e['kind']})")
    lines.append(f"  Name:        {e['display_name']}")
    lines.append(f"  Category:    {e['category']}")
    lines.append(f"  Tier:        {e['tier']}")
    lines.append(f"  Source:      {e['source_id']}  ({e['source_ref']})")

    if ctx["attrs"]:
        lines.append("\nAttributes:")
        for a in ctx["attrs"]:
            v = a["value_text"] if a["value_text"] is not None else a["value_num"]
            lines.append(f"  - {a['key']:35s} = {str(v)[:120]}")
            lines.append(f"    (source: {a['source_id']}#{a['source_ref']})")

    if ctx["external_refs"]:
        lines.append("\nOutbound external references:")
        for r in ctx["external_refs"]:
            lines.append(f"  - [{r['ref_kind']}] {r['store_id']} :: {r['ref_key']}")
            if r["label"]:
                lines.append(f"      label: {r['label']}")
            lines.append(f"      location: {r['location']}  (provenance: {r['provenance']})")

    if ctx["links"]["outbound"]:
        lines.append("\nOutbound typed links:")
        for ln in ctx["links"]["outbound"]:
            lines.append(f"  - --[{ln['kind']}]--> {ln['to_id']}")

    if ctx["links"]["inbound"]:
        lines.append("\nInbound typed links:")
        for ln in ctx["links"]["inbound"]:
            lines.append(f"  - {ln['from_id']} --[{ln['kind']}]--> (this)")

    if ctx["supersession"]:
        lines.append("\nArchitecture pivot decision trail:")
        for d in ctx["supersession"]:
            lines.append(f"  - {d['id']}  (status={d['status']}, locked={d['locked']})")
            if d["choice"]:
                lines.append(f"      choice: {d['choice']}")
            if d["reason"]:
                lines.append(f"      reason: {d['reason']}")
            if d["supersedes"]:
                lines.append(f"      supersedes: {', '.join(d['supersedes'])}")
            if d["superseded_by"]:
                lines.append(f"      superseded by: {', '.join(d['superseded_by'])}")

    if ctx["fts5_hits"]:
        lines.append("\nFTS5 prose hits ('comb dendrite migration OR ...'):")
        for h in ctx["fts5_hits"]:
            lines.append(f"  - [{h['kind']}] {h['source_path']}")
            lines.append(f"      title: {h['title']}")
            lines.append(f"      snippet: {h['snip'][:200]}")

    lines.append("\n" + "=" * 70)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase E.1 canonical KB query: comb input/output contract"
    )
    parser.add_argument("--json", action="store_true",
                        help="Emit JSON instead of text")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print("kb.sqlite not found; run python -m kb.build first.",
              file=sys.stderr)
        return 1

    conn = sqlite3.connect(DB_PATH)
    try:
        ctx = gather_comb_context(conn)
    finally:
        conn.close()

    if args.json:
        print(json.dumps(ctx, indent=2, default=str))
    else:
        print(render_text(ctx))
    return 0


if __name__ == "__main__":
    sys.exit(main())
