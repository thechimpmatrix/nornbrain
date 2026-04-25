"""Decode a C3 .gen genome file to enumerate brain lobe + tract genes.

Format reference: C3 source Creature/Genome.h:29-87 + lisdude CDN article 25.
- File starts with 4-byte DNA3 token: 'd','n','a','3'
- Each gene starts with 'gene' marker (4 bytes)
- 8-byte header after marker: TYPE, SUB, ID, GEN, SWITCHON, FLAGS, MUTABILITY, VARIANT
- Gene body follows; size depends on type/subtype
- File ends with 'gend' marker

Brain lobe gene (BRAINGENE=0, G_LOBE=0): size 121 bytes
Brain tract gene (BRAINGENE=0, G_TRACT=2): size 128 bytes
"""

from __future__ import annotations

import sys
import struct
from pathlib import Path


GENE_TYPES = {
    0: "BRAINGENE",
    1: "BIOCHEMISTRYGENE",
    2: "CREATUREGENE",
    3: "ORGANGENE",
}

BRAIN_SUBTYPES = {0: "G_LOBE", 1: "G_BORGAN", 2: "G_TRACT"}
BIOCHEM_SUBTYPES = {
    0: "G_RECEPTOR", 1: "G_EMITTER", 2: "G_REACTION",
    3: "G_HALFLIFE", 4: "G_INJECT", 5: "G_NEUROEMITTER",
}
CREATURE_SUBTYPES = {
    0: "G_STIMULUS", 1: "G_GENUS", 2: "G_APPEARANCE",
    3: "G_POSE", 4: "G_GAIT", 5: "G_INSTINCT",
    6: "G_PIGMENT", 7: "G_PIGMENTBLEED", 8: "G_EXPRESSION",
}
ORGAN_SUBTYPES = {0: "G_ORGAN"}


def subtype_name(gtype: int, gsub: int) -> str:
    if gtype == 0:
        return BRAIN_SUBTYPES.get(gsub, f"G_?{gsub}")
    if gtype == 1:
        return BIOCHEM_SUBTYPES.get(gsub, f"G_?{gsub}")
    if gtype == 2:
        return CREATURE_SUBTYPES.get(gsub, f"G_?{gsub}")
    if gtype == 3:
        return ORGAN_SUBTYPES.get(gsub, f"G_?{gsub}")
    return f"?{gsub}"


def safe_token(b4: bytes) -> str:
    """Render a 4-byte sequence as a token if printable, else hex."""
    if all(32 <= c < 127 for c in b4):
        return b4.decode("ascii")
    return b4.hex()


def parse_genome(path: Path) -> None:
    data = path.read_bytes()
    print(f"=== {path.name} ===")
    print(f"File size: {len(data):,} bytes")

    # Verify DNA3 marker
    if data[:4] != b"dna3":
        print(f"WARNING: file does not start with 'dna3'; "
              f"first 4 bytes = {data[:4]!r}")

    # Walk gene markers
    pos = 4 if data[:4] == b"dna3" else 0
    gene_count = 0
    lobe_count = 0
    tract_count = 0
    lobes: list[dict] = []
    tracts: list[dict] = []
    other_brain: list[dict] = []
    summary_by_type: dict[str, int] = {}

    # NOTE: C3 genome integers are big-endian (Genome.h GetInt() reads
    # high-byte-first). All struct.unpack_from calls below use ">H".
    while pos < len(data) - 4:
        # Find next 'gene' marker
        marker = data.find(b"gene", pos)
        if marker < 0:
            break
        # Check we are not inside a 'gend' (end marker)
        if data[marker:marker+4] == b"gend":
            break
        # Header: 8 bytes after marker
        header_start = marker + 4
        if header_start + 8 > len(data):
            break
        gtype, gsub, gid, ggen, gswitch, gflags, gmut, gvar = data[header_start:header_start+8]

        body_start = header_start + 8

        type_name = GENE_TYPES.get(gtype, f"?type{gtype}")
        sub_name = subtype_name(gtype, gsub)
        key = f"{type_name}.{sub_name}"
        summary_by_type[key] = summary_by_type.get(key, 0) + 1

        # If brain lobe gene (gtype=0, gsub=0), pull the next bytes for token + W/H
        if gtype == 0 and gsub == 0:
            lobe_count += 1
            # Token at body_start (4 bytes), then W, H, X, Y, RGB...
            if body_start + 16 <= len(data):
                token = data[body_start:body_start+4]
                # Lobe gene body layout (per c2eBrainLobeGene):
                # token(4), updatetime(2), x(2), y(2), w(1), h(1),
                # red(1), green(1), blue(1), tissue(1), wta(1),
                # initrulealways(1), spare[7](7), initrule[48], updaterule[48]
                # Total: 4+2+2+2+1+1+1+1+1+1+1+1+7+48+48 = 121 bytes
                upd_time = struct.unpack_from(">H", data, body_start + 4)[0]
                x_pos = struct.unpack_from(">H", data, body_start + 6)[0]
                y_pos = struct.unpack_from(">H", data, body_start + 8)[0]
                w = data[body_start + 10]
                h = data[body_start + 11]
                r, g, b = data[body_start + 12], data[body_start + 13], data[body_start + 14]
                tissue = data[body_start + 15]
                neurons = w * h
                token_str = safe_token(token)
                lobes.append({
                    "token": token_str,
                    "raw_token_hex": token.hex(),
                    "neurons": neurons,
                    "w": w, "h": h,
                    "x": x_pos, "y": y_pos,
                    "rgb": (r, g, b),
                    "update_time": upd_time,
                    "tissue": tissue,
                    "marker_offset": marker,
                    "id": gid,
                })
                pos = body_start + 121
            else:
                pos = body_start + 1

        # If brain tract gene (gtype=0, gsub=2), pull source + dest tokens
        elif gtype == 0 and gsub == 2:
            tract_count += 1
            # Tract gene body layout (per c2eBrainTractGene):
            # updatetime(2), srclobe(4), srcmin(2), srcmax(2), src_conn(2),
            # destlobe(4), destmin(2), destmax(2), dest_conn(2),
            # migrates(1), norandom(1), srcvar(1), destvar(1),
            # initrulealways(1), spare[5], initrule[48], updaterule[48]
            # Total: 2+4+2+2+2+4+2+2+2+1+1+1+1+1+5+48+48 = 128 bytes
            if body_start + 28 <= len(data):
                upd_time = struct.unpack_from(">H", data, body_start)[0]
                src_lobe = data[body_start + 2:body_start + 6]
                src_min = struct.unpack_from(">H", data, body_start + 6)[0]
                src_max = struct.unpack_from(">H", data, body_start + 8)[0]
                src_conn = struct.unpack_from(">H", data, body_start + 10)[0]
                dst_lobe = data[body_start + 12:body_start + 16]
                dst_min = struct.unpack_from(">H", data, body_start + 16)[0]
                dst_max = struct.unpack_from(">H", data, body_start + 18)[0]
                dst_conn = struct.unpack_from(">H", data, body_start + 20)[0]
                migrates = data[body_start + 22]
                tracts.append({
                    "src_token": safe_token(src_lobe),
                    "src_range": (src_min, src_max),
                    "src_conn": src_conn,
                    "dst_token": safe_token(dst_lobe),
                    "dst_range": (dst_min, dst_max),
                    "dst_conn": dst_conn,
                    "migrates": bool(migrates),
                    "update_time": upd_time,
                    "marker_offset": marker,
                    "id": gid,
                })
                pos = body_start + 128
            else:
                pos = body_start + 1

        elif gtype == 0:
            # Other brain gene (G_BORGAN etc.)
            other_brain.append({"sub": sub_name, "id": gid,
                                "marker_offset": marker})
            pos = body_start + 1
        else:
            pos = body_start + 1

    print(f"\nGene marker count: {gene_count if gene_count else 'walking by find()'}")
    print(f"Total genes by type/subtype:")
    for k in sorted(summary_by_type):
        print(f"  {k:30s} {summary_by_type[k]}")

    print(f"\n=== Lobe genes ({lobe_count}) ===")
    print(f"{'token':6s} {'neurons':>8s} {'w':>3s} {'h':>3s} "
          f"{'tissue':>6s} {'updt':>5s} {'rgb':>14s} {'marker_off':>10s}")
    for lobe in lobes:
        rgb_s = f"({lobe['rgb'][0]:3d},{lobe['rgb'][1]:3d},{lobe['rgb'][2]:3d})"
        print(f"{lobe['token']:6s} {lobe['neurons']:8d} "
              f"{lobe['w']:3d} {lobe['h']:3d} {lobe['tissue']:6d} "
              f"{lobe['update_time']:5d} {rgb_s:>14s} "
              f"{lobe['marker_offset']:10d}")

    print(f"\n=== Tract genes ({tract_count}) ===")
    print(f"{'src':6s}{'dst':6s} {'src_range':>14s} {'src_conn':>9s} "
          f"{'dst_range':>14s} {'dst_conn':>9s} {'mig':>4s} "
          f"{'updt':>5s}")
    for tract in tracts:
        sr = f"[{tract['src_range'][0]:3d},{tract['src_range'][1]:3d}]"
        dr = f"[{tract['dst_range'][0]:3d},{tract['dst_range'][1]:3d}]"
        print(f"{tract['src_token']:6s}{tract['dst_token']:6s} "
              f"{sr:>14s} {tract['src_conn']:9d} "
              f"{dr:>14s} {tract['dst_conn']:9d} "
              f"{'Y' if tract['migrates'] else 'N':>4s} "
              f"{tract['update_time']:5d}")

    if other_brain:
        print(f"\n=== Other brain genes ({len(other_brain)}) ===")
        for og in other_brain:
            print(f"  {og['sub']} id={og['id']} offset={og['marker_offset']}")


if __name__ == "__main__":
    paths = sys.argv[1:]
    if not paths:
        # Default targets
        gen_root = Path(r"<PROJECT_ROOT>/creaturesexodusgame/Creatures Exodus/Creatures 3/Genetics")
        paths = [
            str(gen_root / "norn.bondi.48.gen"),
            str(gen_root / "norn.harlequin.48.gen"),
        ]
    for p in paths:
        parse_genome(Path(p))
        print()
