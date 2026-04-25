"""Shared genome decoder used by both the KB loader and tools/decode_norn_genome.py.

Walks a C3 .gen file by 'gene' markers per Creature/Genome.h spec and
extracts brain lobe + tract genes with their fields.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path


GENE_TYPES = {
    0: "BRAINGENE",
    1: "BIOCHEMISTRYGENE",
    2: "CREATUREGENE",
    3: "ORGANGENE",
}

BRAIN_SUBTYPES = {0: "G_LOBE", 1: "G_BORGAN", 2: "G_TRACT"}


@dataclass
class LobeGene:
    token: str
    raw_token_hex: str
    neurons: int
    w: int
    h: int
    x: int
    y: int
    rgb: tuple
    update_time: int
    tissue: int
    marker_offset: int
    gene_id: int


@dataclass
class TractGene:
    src_token: str
    src_range: tuple
    src_conn: int
    dst_token: str
    dst_range: tuple
    dst_conn: int
    migrates: bool
    update_time: int
    marker_offset: int
    gene_id: int


@dataclass
class GenomeBrainSummary:
    file_path: Path
    file_size: int
    has_dna3_header: bool
    lobes: list = field(default_factory=list)
    tracts: list = field(default_factory=list)
    gene_counts: dict = field(default_factory=dict)


def _safe_token(b4: bytes) -> str:
    if all(32 <= c < 127 for c in b4):
        return b4.decode("ascii")
    return b4.hex()


def parse_genome(path: Path) -> GenomeBrainSummary:
    """Walk the .gen file and extract brain lobe + tract genes."""
    data = path.read_bytes()
    summary = GenomeBrainSummary(
        file_path=path,
        file_size=len(data),
        has_dna3_header=data[:4] == b"dna3",
    )

    pos = 4 if summary.has_dna3_header else 0

    while pos < len(data) - 4:
        marker = data.find(b"gene", pos)
        if marker < 0:
            break
        if data[marker:marker+4] == b"gend":
            break

        header_start = marker + 4
        if header_start + 8 > len(data):
            break

        gtype, gsub, gid, ggen, gswitch, gflags, gmut, gvar = data[header_start:header_start+8]
        body_start = header_start + 8

        type_name = GENE_TYPES.get(gtype, f"?type{gtype}")
        if gtype == 0:
            sub_name = BRAIN_SUBTYPES.get(gsub, f"G_?{gsub}")
        else:
            sub_name = f"?{gsub}"
        key = f"{type_name}.{sub_name}"
        summary.gene_counts[key] = summary.gene_counts.get(key, 0) + 1

        if gtype == 0 and gsub == 0:
            # G_LOBE; size 121 bytes
            if body_start + 16 <= len(data):
                token = data[body_start:body_start+4]
                upd_time = struct.unpack_from(">H", data, body_start + 4)[0]
                x_pos = struct.unpack_from(">H", data, body_start + 6)[0]
                y_pos = struct.unpack_from(">H", data, body_start + 8)[0]
                w = data[body_start + 10]
                h = data[body_start + 11]
                r, g, b = data[body_start + 12], data[body_start + 13], data[body_start + 14]
                tissue = data[body_start + 15]
                summary.lobes.append(LobeGene(
                    token=_safe_token(token),
                    raw_token_hex=token.hex(),
                    neurons=w * h,
                    w=w, h=h,
                    x=x_pos, y=y_pos,
                    rgb=(r, g, b),
                    update_time=upd_time,
                    tissue=tissue,
                    marker_offset=marker,
                    gene_id=gid,
                ))
                pos = body_start + 121
            else:
                pos = body_start + 1

        elif gtype == 0 and gsub == 2:
            # G_TRACT; size 128 bytes
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
                migrates = bool(data[body_start + 22])
                summary.tracts.append(TractGene(
                    src_token=_safe_token(src_lobe),
                    src_range=(src_min, src_max),
                    src_conn=src_conn,
                    dst_token=_safe_token(dst_lobe),
                    dst_range=(dst_min, dst_max),
                    dst_conn=dst_conn,
                    migrates=migrates,
                    update_time=upd_time,
                    marker_offset=marker,
                    gene_id=gid,
                ))
                pos = body_start + 128
            else:
                pos = body_start + 1
        else:
            pos = body_start + 1

    return summary
