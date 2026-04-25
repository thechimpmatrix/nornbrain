# Brain in a Vat: File Formats

Evidence-based reading of the two on-disk formats `Vat_1.9.exe` consumes: `CreaturesArchive` (the compressed binary container that holds genomes, brain dumps, and creature snapshots) and `*.catalogue` (text-based lookup tables). All addresses are relative to `Vat_1.9.exe`. Decompiled output is in `analysis/braininavat/notes/decompiled/`. String references resolve against `analysis/braininavat/notes/strings.txt`.

## CreaturesArchive container

### Header

The header is the only part of a CreaturesArchive that lives outside the zlib stream. The reader constructor at `0x00435a60` does this in order (lines 86 to 122 of `00435a60_FUN_00435a60.c`):

1. Build the expected banner string `"Creatures Evolution Engine - Archived information file. zLib 1.13 compressed."` (78 bytes, address `0x0047c904`).
2. Append two NUL bytes (`FUN_00414c10(buf, 1)` called twice; `FUN_00414c10` zero-extends the string by `param_1` bytes, confirmed at `00414c10_FUN_00414c10.c`).
3. Initialise the inflate stream (`FUN_00445a40`, which is a thin wrapper around `inflateInit2_` with window-bits 15 and `sizeof(z_stream) = 0x38` - see `00445a40_FUN_00445a40.c` and `00445930_FUN_00445930.c`). Throws `CRA0001` on failure.
4. Read 80 raw bytes from the file into a buffer via `FUN_0041d870` (the file read primitive - bypasses the inflate path entirely; line 111 of the constructor).
5. Compare the 80-byte buffer to the expected banner using `FUN_0040a010` (std::string::compare). Any mismatch throws `CRA0002: Not a creatures archive`.
6. After the banner, every subsequent byte goes through inflate. The first compressed dword is the **archive version**, read by `FUN_00436b10` (Read4) into `this+0x48` at line 123.

The on-disk layout:

```
offset 0x00       offset 0x4E      offset 0x50      offset 0x50+N
+----------------+----------------+----------------+--------------+
| banner (78 B)  | NUL NUL (2 B)  | zlib stream:   | (EOF)        |
| ASCII, raw     | raw            |   version u32  |              |
| not deflated   |                |   ...objects   |              |
+----------------+----------------+----------------+--------------+
   raw header  ->|                <- zlib deflate compressed ----->|
```

The banner ends `"compressed.\0\0"` so a magic-byte test for the format is: read 80 bytes, memcmp against the literal at `0x0047c904`.

### Banner cosmetic note

The banner says `"zLib 1.13"` (no dot). The actual zlib copyright strings linked into the binary are `"deflate 1.1.3 Copyright 1995-1998 Jean-loup Gailly"` (`0x0046e748`) and `"inflate 1.1.3 Copyright 1995-1998 Mark Adler"` (`0x0046f274`). Same library, just typo'd marketing text in the banner. Do not chase a phantom version mismatch.

### Archive version

`FUN_00437a80` (`00437a80_FUN_00437a80.c`) returns the constant `0x25` (37). This is the highest archive version Vat 1.9 understands. Constructor line 126 does `if (CODE_VERSION < FILE_VERSION) throw archive_error` - the runtime refuses files newer than 37 (when the bypass-version flag `param_3` is false).

The version is **also a behaviour switch**, not just a sanity check. In `FUN_00436fc0` (the polymorphic object reader, line 71 of `00436fc0_FUN_00436fc0.c`):

```c
iVar4 = FUN_00437a60((int)this);   // GetFileVersion (reads this+0x48)
if (iVar4 < 0xe) {                 // file version < 14
    // if class-name string is "Creature", rewrite to "SkeletalCreature"
}
```

So pre-version-14 archives store the polymorphic creature class as `"Creature"`, and the runtime upgrades the tag to `"SkeletalCreature"` on read. Useful concrete versioning anecdote.

### Compression scope and integrity

Everything after byte 80 is a single zlib deflate stream. No application-level CRC. zlib's stream-level adler32 is the only integrity check, and it's verified implicitly by `inflate` returning `Z_STREAM_END` (1) instead of an error.

The decompressor refill path is `FUN_00436e60` (`00436e60_FUN_00436e60.c`). It maintains a 16 KiB inflate output buffer (`operator_new(0x4000)` at constructor line 72). When the buffer drains, it calls `FUN_00445a60` (the `inflate` step). Status codes:

- Return value `0` (`Z_OK`) or `1` (`Z_STREAM_END`) → continue or end normally.
- Anything else → throw `CRA0004` or `CRA0005` ("zlib inflate error reading compressed stream"). The two codes distinguish the calling context: `CRA0004` is from the slow path (when no input is buffered), `CRA0005` from the fast path.
- If the stream ends before the requested number of bytes was produced → throw `CRA0006: decompression stream ended before expected`.

### End of stream

There is no explicit end-of-archive sentinel byte at the application level. The reader stops when the consumer's last `Read*` returns. The deflate stream itself ends with the standard zlib trailer (adler32 + Z_STREAM_END marker).

## Object serialisation primitives

The archive object exposes a fixed set of read/write primitives. The this-pointer carries inflate/deflate state plus a 16 KiB I/O buffer. Confirmed primitives:

| Primitive | Read | Write | Notes |
|---|---|---|---|
| Raw bytes (n) | `FUN_00436e60(buf, n)` | `FUN_004366a0(buf, n)` | Buffered through the deflate window. |
| u32 / int32 | `FUN_00436b10(this, &out)` | `FUN_00436400(this, val)` | Both are `Read/Write 4 raw bytes`. Endianness: little-endian on disk (x86 host, no byte-swapping observed). |
| String | `FUN_00436b30(this, &out)` | (writer counterpart not isolated yet) | See below. |

### String wire format

The string reader at `FUN_00436b30` (`00436b30_FUN_00436b30.c`) does:

```
1. Read u32 length L                      (FUN_00436e60 with n=4)
2. If L < 0:        throw CRA0009: negative string size
3. If L >= 100000:  copy a hardcoded fallback string (0x00481210, "string too long")
                    and skip-read L bytes
4. Else: ensure capacity; read L bytes raw; null-terminate
```

```
+-----------+-----------------------+
| u32 len   | char[len]   no NUL    |
+-----------+-----------------------+
```

The 100000-byte cap is a hard sanity limit, not a true protocol constraint - anything bigger gets replaced with a placeholder rather than rejected. So an attacker-controlled archive cannot exhaust memory through one giant string field, but it also cannot smuggle a > 100 KB string through.

### FloatRef (the type-checked float reference)

`CreaturesArchive::WriteFloatRef` is at `0x004373a0` (`004373a0_FUN_004373a0.c`). Behaviour reconstructed from decompilation:

1. `FUN_004363e0(this, *param_1)` - write a u32 (this is `Write4` again; the value is the FloatRef *id* / type tag).
2. Look up the id in a map at `this+0x84` via `FUN_00438140`.
3. Compare the looked-up entry's type tag (slot at `entry+0` in the iterator return) against the expected tag at `this+0x88`.
4. If they do not match, throw `archive_error` with the function name `"CreaturesArchive::WriteFloatRef"` baked into the exception. (Two copies of that string at `0x0047cba4` and `0x0047cbd4` - separate inlined throw sites.)
5. If they match, look up the *value* (a float) at `this+0x90` via `FUN_00438cd0` and update its slot at `entry+0x10`.

So a "FloatRef" is a typed handle: an integer id whose registered type tag must match what the calling code expects for that slot. The map at `this+0x84` is a per-archive registry of `id → { type, float_value }` pairs. The wire format of one FloatRef is just the u32 id; the float value lives in the registry the archive maintains during serialisation. The read counterpart `CreaturesArchive::ReadFloatRef` is referenced by the string at `0x0047cc04` but its function body was not isolated in this pass - recommend a follow-up pass before reimplementing.

What this means in practice: the brain serialisation cannot just blat a flat array of floats. Each float is referenced via a typed slot id, and slot ids are validated. This is the mechanism that lets the brain code carry shared / aliased float references (e.g., a chemical level read by multiple lobes) without re-serialising the same number, and detect type drift between writer and reader versions.

## Polymorphic / type-tagged object serialisation

The polymorphic object reader is `FUN_00436fc0` (`00436fc0_FUN_00436fc0.c`). The wire format for one object:

```
+--------------------------+--------------+--------------------------+
| string: class name       | object body  | string: end marker       |
+--------------------------+--------------+--------------------------+
                           ^              ^
                       start marker     CRA0008 if mismatch
                  CRA0007 if mismatch
```

Or rather, looking again at the code: the class name comes first, then a fixed start-marker string is read and compared, then the object's own `ReadFromArchive` virtual method runs (`(**(code **)(*(int *)*puVar2 + 0x10))(this);` at line 158), then a fixed end-marker string is read and compared.

The start marker is the 80 bytes at `0x0047cb48` and the end marker is the bytes at `0x0047cb78`. **The exact byte content of these markers was not extracted by the string-dump pass** (probably because they are either short, contain non-ASCII, or fall below the dumper's minimum-length threshold). Recover them by opening `Vat_1.9.exe` in a hex viewer at those VAs, or by re-running Ghidra's string dump with a length threshold of 1.

What we know:
- They are non-empty, NUL-terminated strings (since `FUN_0040a010` is a string-compare).
- They are short (between 8 and 32 bytes, judging from spacing between adjacent string literals at `0x0047cb34` "SkeletalCreature" → `0x0047cb50` "CRA0007").
- They are distinct (otherwise CRA0007 and CRA0008 would not be needed as separate error codes).

### Polymorphic factory

The class-name string is looked up via `FUN_0043bf50` (`0043bf50_FUN_0043bf50.c`), which is a singleton-init wrapper around `FUN_0043bfe0` lookup on the global registry at `DAT_00581bbc`. By inference (not yet directly observed): when each concrete class loads (likely from a static initialiser registered at `DAT_00581bb8`), it inserts a `(class_name → factory_fn)` pair into that registry. `FUN_0043bf50` returns the factory pointer; the reader then constructs a default-initialised instance and calls its virtual `ReadFromArchive`. See `09-class-registry.md` for the registry surface; document there as soon as the factory-registration call sites are mapped.

A useful concrete oddity confirming the mechanism: the version-14 rewrite (`Creature` → `SkeletalCreature`) is implemented exactly where the class-name string is read but before it is looked up in the factory.

## CRA error codes

Complete list of `CRA*` codes in `Vat_1.9.exe`, with the throwing function and meaning:

| Code | Address | Meaning | Thrown at |
|---|---|---|---|
| CRA0001 | `0x0047c95c` | zlib failed to initialise (inflate side) | `0x00435a60` line 102 |
| CRA0002 | `0x0047c980` | Not a creatures archive (banner mismatch) | `0x00435a60` line 118 |
| CRA0003 | `0x0047ca30` | zlib failed to initialise (deflate side) | `0x00435e50` line 95 |
| CRA0004 | `0x0047ca84` | zlib inflate error reading compressed stream (slow path) | `0x00436e60` line 64 |
| CRA0005 | `0x0047cabc` | zlib inflate error reading compressed stream (fast path) | `0x00436e60` line 74 |
| CRA0006 | `0x0047caf4` | decompression stream ended before expected | `0x00436e60` line 80 |
| CRA0007 | `0x0047cb50` | object start marker mismatch | `0x00436fc0` line 152 |
| CRA0008 | `0x0047cb80` | object end marker mismatch | `0x00436fc0` line 183 |
| CRA0009 | `0x0047ca64` | negative string size | `0x00436b30` line 33 |
| CRA0010 | `0x0047cc34` | range check failed | `0x00437ac0` (the generic range-check helper) |

All ten are wrapped in `CreaturesArchive::Exception` (RTTI type descriptor at `0x0047cc50`, type string `.?AVException@CreaturesArchive@@`).

## Catalogue format (`*.catalogue`)

The catalogue subsystem is the engine's name-keyed lookup table. It is **text-based**, not binary. It maps a tag string (e.g. `"Brain Lobe Quads"`, `"Brain Lobes"`, `"Brain Lobe Neuron Names"`) to either a single string, a numbered string, or an array of strings.

### Loading

`CatalogueDirectory` walks a directory using `FindFirstFileA` / `FindNextFileA` with the wildcard `"*.catalogue"` (string at `0x0047cd60` and `0x0047cd8c`). The directory walker is `FUN_0043c780` (`0043c780_FUN_0043c780.c`); each found file is parsed by `FUN_0043c970` (`0043c970_FUN_0043c970.c`). The directory string key is `"Catalogue Directory"` (at `0x0047d23c`) and is looked up from the registry by `WhichEngine` (see `03-ipc-protocol.md` for registry handling).

### File format (text)

`FUN_0043c970` is a token-based parser. The grammar reconstructed from the parser plus the error strings:

```
catalogue := entry+
entry     := tag_decl ( "OVERRIDE" )? string_or_array
tag_decl  := "TAG" quoted_string
            | "ARRAY" quoted_string number
string_or_array
          := quoted_string                      // single-string TAG
            | quoted_string{count}              // ARRAY of N strings
```

Inferred from token-handling case statements in the parser (`switch (iVar4) { case 0: ... }` at line 126; cases 0, 2, 3 are end-of-file, identifier-token, and quoted-string-token respectively). The literal `"OVERRIDE"` (`0x0047ce74`) is matched at line 300, `"ARRAY"` (`0x0047ce14`, `0x0047ce6c`) at the array-tag entry path. `TAG` is a separate keyword as seen in real-world `.catalogue` files but the literal string is consumed by the lexer and not present as a comparison literal in extracted strings (suggesting the lexer maps keywords by hash or by character switch, not by `strcmp`).

### CLE error codes

The full set of `CLE*` codes, with meaning derived from the format strings:

| Code | Address | Meaning |
|---|---|---|
| CLE0001 | `0x0047cd6c` | Couldn't localise `"%s"` |
| CLE0002 | `0x0047cd98` | Error reading directory `"%s"` |
| CLE0003 | `0x0047cdc0` | Couldn't open `"%s"` |
| CLE0004 | `0x0047cddc` | String ID clash (id `%d` in `"%s"`, line `%d`) |
| CLE0005 | `0x0047ce80` | Expecting string or OVERRIDE (in `"%s"`, line `%d`) |
| CLE0006 | `0x0047cebc` | Tag identifier clash (tag `%s` in `"%s"`, line `%d`) |
| CLE0007 | `0x0047cef4` | Expecting number (in `"%s"`, line `%d`) |
| CLE0008 | `0x0047cf24` | Syntax error (`"%s"`, line `%d`) |
| CLE0009 | `0x0047cf4c` | Error parsing file (`"%s"`, line `%d`) |
| CLE0010 | `0x0047cfa4` | Number of strings doesn't match array count (tag `%s` in `"%s"`, line `%d`) |
| CLE0011 | `0x0047ce1c` | Number of strings doesn't match array count (tag `%s` in `"%s"`, line `%d`) - duplicate text, separate code-path |
| CLE0012 | `0x0047abb4` | Index `%d` out of range 0 to `%d` for tag `%s` |
| CLE0013 | `0x0047abec` | Internal catalogue error, unexpected -1 |
| CLE0014 | `0x0047cf78` | Unexpected number (`"%s"`, line `%d`) |
| CLE0015 | `0x0047aeb4` | Couldn't find Tag `"%s"` |
| CLE0016 | `0x0047ac44` | Couldn't find Tag `"%s"` |
| CLE0017 | `0x0047ac20` | Couldn't find string `<%d>` |
| CLE0019 | `0x0047cffc` | Two tags with the same name `"%s"` but different contents at item `%d` |

(There is no CLE0018 in the extracted strings. Either it never existed or it was elided in this build.)

The exception class is `Catalogue::Err` (RTTI at `0x0047aba0`, type string `.?AVErr@Catalogue@@`). User-facing errors are prefixed `"Catalogue Error: "` (`0x0047cd4c`).

## What this means for NORNBRAIN

We do not need to load CreaturesArchive files into our own viewer. Our genome handling in `nornbrain/brain_genome_v2.py` is the source of truth. The format documentation here exists so we can:

1. Distinguish a CreaturesArchive blob from a NORNBRAIN-native artefact at a glance (banner test, 80-byte memcmp).
2. Recognise the error codes if the user runs Vat against an archive we generated (we will see CRA0002 if our header is wrong).
3. Understand what `*.catalogue` tags the original engine assumed, so we can decide whether to emulate or replace the catalogue lookup in our own brain.

### The "Brain Lobe Quads" coordinates: actionable finding

`FUN_00410ab0` (the BrainViewport layout function) builds the lobe-coordinate display by **looking up the lobe name as a tag in the global Catalogue** at `DAT_00481048` / `DAT_0048105c` (lines 188 to 200 of `00410ab0_FUN_00410ab0.c`). Specifically:

- Tag `"Brain Lobe Quads"` (`0x0047ae34` / `0x0047ae48`) - lobe-name → quad coordinates table.
- Tag `"Brain Lobes"` (`0x0047ae5c`) - list of lobe names.
- Tag `"Brain Lobe Neuron Names"` (`0x0047ae68`) - per-lobe neuron name lists.
- Tag `"LobeNames"` (`0x0047ae9c`) - alternative lobe name lookup.

**The coordinates are not baked as static data in `Vat_1.9.exe`.** They are loaded at runtime from a `.catalogue` file that ships alongside Vat (or alongside Creatures 3 - Vat reads the same catalogue directory the game uses, via the registry key `"Catalogue Directory"`). To extract the coordinates, find the `.catalogue` file in the C3 install that contains a `TAG "Brain Lobe Quads"` entry. The data-model agent investigating the same area should look in the C3 install's catalogue directory rather than disassembling the `.exe`.

If the `.catalogue` file is not bundled with Vat itself (it's likely not - the standalone Vat installer pre-1999 was tiny), the original C3 installation under `Bootstrap/001 World/` or its sibling `Catalogue/` directory is the source.

## Open questions

1. **Object start/end marker bytes** - addresses `0x0047cb48` and `0x0047cb78`. Not extracted by the string dump in this pass. Recover by hex-viewing the `.exe` at those VAs or re-running Ghidra's string analyser with `min length = 1`. Required to validate any third-party CreaturesArchive parser.
2. **`CreaturesArchive::ReadFloatRef`** - function body was not isolated. Search for cross-references to the string at `0x0047cc04` to find it. Required to confirm symmetric semantics with `WriteFloatRef`.
3. **FloatRef registry layout** - the maps at `this+0x84` (id → entry) and `this+0xa4` (the FUN_004398d0-initialised second map). Looks like a two-tiered (id-by-tag) registry but the reading-side counterpart needs to be examined to confirm.
4. **Polymorphic class registry registration** - `FUN_0043bfe0` is the lookup-by-name; the registration call sites (which embed every concrete class type at static-init time) were not enumerated here. See `09-class-registry.md` for the registry's external surface; cross-reference there.
5. **Compressed payload structure for a Brain object specifically** - the per-class `ReadFromArchive` virtual is what defines the actual brain wire format (lobe count, tract count, neuron variable layout). That is a separate document; this one stops at the container level.
6. **Which `.catalogue` file in the C3 install holds the `Brain Lobe Quads` tag**, and whether it ships in the GOG / Steam C3 distributions or only in the original CD release. Worth a fast filesystem grep before assuming anything is missing.
7. **CLE0018** - no string for it in the binary. Either the code skips that number or it was scrubbed in the 1.9 build. Low priority.
