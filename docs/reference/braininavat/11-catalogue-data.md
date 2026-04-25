# Brain in a Vat: Catalogue Runtime Data

The Vat tool and the C3 engine load all canonical brain layout, action mapping, and chemical naming data from plain-text `.catalogue` files at startup via the engine SDK's `Catalogue` class. The Vat `.exe` references the tag names (`Brain Lobe Quads`, `Brain Lobes`, `Brain Lobe Neuron Names`, `Brain Parameters`, `Migration Parameters`, `Action Script To Neuron Mappings`, `Decision Offsets to Expected Agent Script`) but holds none of the values. This document captures what those files actually contain in the English C3 install at:

`<PROJECT_ROOT>\creaturesexodusgame\Creatures Exodus\Creatures 3\Catalogue\`

Companion docs: [00-architecture.md](00-architecture.md), [04-data-model.md](04-data-model.md) §7, [10-svrule-engine.md](10-svrule-engine.md), [06-file-formats.md](06-file-formats.md) §5.

---

## 1. Catalogue inventory (English C3, brain-relevant only)

Localised copies (`-de`, `-es`, `-fr`, `-it`, `-nl`, `-ru`) are ignored. Only files that contribute brain runtime data are listed.

| File | Size | Holds |
|---|---|---|
| `Brain.catalogue` | 2,062 B | Lobe type tags, lobe name list, per-lobe neuron-list type, brain global params, migration params |
| `Creatures 3.catalogue` | 5,926 B | Action-to-neuron mappings, decision-to-script offsets, agent categories, classifiers, CA names |
| `ChemicalNames.catalogue` | 4,090 B | Drive chemical numbers, full 256-entry chemical name table |
| `CAOS.catalogue` | 5,458 B | CAOS error message strings (no opcodes - see §7) |
| `Norn.catalogue` | 3,264 B | Vocabulary defaults - used by the speech-learning system, not the brain core |
| `Genome.catalogue` | 776 B | Moniker name pools (cosmetic, not brain layout) |

The Vat does not load `AgentHelp`, `Materia Medica`, `Scrolls of Learning`, `System`, `GUItext`, `Creature History`, `World Switcher`, `Pressies`, `Patch`, `Progress`, or any of the agent-specific files (`BeachBall`, `crobster`, `chilli`, etc.) for brain layout. They feed gameplay text and agent scripts.

---

## 2. Brain Lobe Quads - IMPORTANT: not (x, y, w, h)

This contradicts the brief's expectation. `Brain.catalogue` near line 64:

```
ARRAY "Brain Lobe Quads" 12
"attn"
"decn"
"verb"
"noun"
"visn"
"smel"
"driv"
"sitn"
"detl"
"resp"
"prox"
"stim"
```

Each entry is a single 4-character ASCII type tag, not a quadruple of coordinates. The "Quad" in the tag name refers to the **4-character lobe type code**, not a 4-tuple of geometry. The Vat ctor evidence in [04-data-model.md](04-data-model.md) §3 corroborates this: the Lobe ctor reads a 4-byte type tag from the wire stream into `Lobe + 0x250`, then null-terminates it as a string at `Lobe + 0x254`. That 4-char tag is what the Vat looks up against `Brain Lobe Quads` to validate / index the lobe.

| Index | Tag | Lobe long name (from `Brain Lobes`) |
|---|---|---|
| 0 | `attn` | attention |
| 1 | `decn` | decision |
| 2 | `verb` | verb |
| 3 | `noun` | noun |
| 4 | `visn` | vision |
| 5 | `smel` | smell |
| 6 | `driv` | drive |
| 7 | `sitn` | situation |
| 8 | `detl` | detail |
| 9 | `resp` | response |
| 10 | `prox` | proximity |
| 11 | `stim` | stim source |

So the **canonical 12-lobe layout** is in the catalogue as type-tag list. **Visual quad geometry (where each lobe is drawn on the BrainViewport) is not in the catalogue.** Where it actually lives is an open question: it may be hardcoded in `Vat_1.9.exe` resources, in MFC dialog templates, or computed from the per-lobe `W * H` grid dimensions plus a layout algorithm. Our existing reference `docs/reference/svrule-brain-complete-reference.md` carries quad geometry as part of its lobe table; that should remain the authoritative geometry source for our viewer.

---

## 3. Brain Lobes - long names (master list)

`Brain.catalogue` near line 10:

```
ARRAY "Brain Lobes" 12
```

| Index | Long name |
|---|---|
| 0 | attention |
| 1 | decision |
| 2 | verb |
| 3 | noun |
| 4 | vision |
| 5 | smell |
| 6 | drive |
| 7 | situation |
| 8 | detail |
| 9 | response |
| 10 | proximity |
| 11 | stim source |

Index alignment with `Brain Lobe Quads` is positional (entry `i` of one matches entry `i` of the other). The data model in [04-data-model.md](04-data-model.md) §7 confirms the Vat keys both arrays by the same lobe index.

### Output and input lobe partition

`Brain.catalogue` distinguishes which lobes are decision outputs versus sensory inputs:

`ARRAY "Brain Output Lobes" 2` (line 47):
- `attention`
- `decision`

`ARRAY "Brain Input Lobes" 9` (line 52):
- `verb`, `noun`, `vision`, `smell`, `drive`, `situation`, `detail`, `response`, `proximity`

Note that `stim source` is in `Brain Lobes` but listed in **neither** the output nor the input partition. It is internal - populated by the engine when stimuli arrive but not surfaced as a sensory or decision lobe per se.

---

## 4. Brain Lobe Neuron Names - per-lobe label source

`Brain.catalogue` near line 29:

```
ARRAY "Brain Lobe Neuron Names" 12
```

This array does **not** hold neuron name strings directly. It holds, per lobe, the **name of another catalogue array** that provides the neuron labels for that lobe. Indirection by tag name.

| Lobe idx | Lobe tag | Neuron-name array tag |
|---|---|---|
| 0 | attn | `Agent Categories` |
| 1 | decn | `Creature Actions` |
| 2 | verb | `Creature Actions` |
| 3 | noun | `Agent Categories` |
| 4 | visn | `Agent Categories` |
| 5 | smel | `Agent Categories` |
| 6 | driv | `Creature Drives` |
| 7 | sitn | `Situation Neurons` |
| 8 | detl | `Detail Neurons` |
| 9 | resp | `Creature Drives` |
| 10 | prox | `Creature Drives` |
| 11 | stim | `Agent Categories` |

So lobes 0/3/4/5/11 share `Agent Categories` (40 entries; live in `Creatures 3.catalogue`), lobes 1/2 share `Creature Actions` (17 entries, in `Brain.catalogue`), lobes 6/9/10 share `Creature Drives` (20 entries, in `Brain.catalogue`).

### Neuron name arrays referenced

**`Creature Drives` (20)** - `Brain.catalogue` line 79:

| idx | name |
|---|---|
| 0 | hurt |
| 1 | hungry for protein |
| 2 | hungry for starch |
| 3 | hungry for fat |
| 4 | cold |
| 5 | hot |
| 6 | tired |
| 7 | sleepy |
| 8 | lonely |
| 9 | crowded |
| 10 | scared |
| 11 | bored |
| 12 | angry |
| 13 | friendly |
| 14 | homesick |
| 15 | low down |
| 16 | high up |
| 17 | trapped |
| 18 | trapped (duplicate label, second slot) |
| 19 | patient |

**`Creature Actions` (17)** - `Brain.catalogue` line 102:

| idx | name | comment |
|---|---|---|
| 0 | look |  |
| 1 | push |  |
| 2 | pull |  |
| 3 | deactivate | unused per source comment |
| 4 | approach |  |
| 5 | retreat |  |
| 6 | get |  |
| 7 | drop |  |
| 8 | express |  |
| 9 | rest |  |
| 10 | left |  |
| 11 | right |  |
| 12 | eat |  |
| 13 | hit |  |
| 14 | up | source comment: "not used" |
| 15 | down | "not used" |
| 16 | exit | "not used" |

**`Situation Neurons` (9)** - `Brain.catalogue` line 123:

| idx | name |
|---|---|
| 0 | I am this old |
| 1 | I am inside a vehicle |
| 2 | I am carrying something |
| 3 | I am being carried |
| 4 | I am falling |
| 5 | I am near a creature of the opposite sex any my genus (sic) |
| 6 | I am musically at this mood |
| 7 | I am musically at this threat level |
| 8 | I am the selected norn |

**`Detail Neurons` (11)** - `Brain.catalogue` line 138:

| idx | name |
|---|---|
| 0 | It is being carried by me |
| 1 | It is being carried by someone else |
| 2 | It is this close to me |
| 3 | It is a creature |
| 4 | It is my sibling |
| 5 | It is my parent |
| 6 | It is my child |
| 7 | It is of opposite sex and my genus |
| 8 | It is of this size |
| 9 | It is smelling this much |
| 10 | It is stopped |

**`Agent Categories` (40)** - `Creatures 3.catalogue` line 162:

| idx | name | idx | name | idx | name | idx | name |
|---|---|---|---|---|---|---|---|
| 0 | self | 10 | detritus | 20 | bad | 30 | norn home |
| 1 | hand | 11 | food | 21 | toy | 31 | grendel home |
| 2 | door | 12 | button | 22 | incubator | 32 | ettin home |
| 3 | seed | 13 | bug | 23 | dispenser | 33 | gadget |
| 4 | plant | 14 | pest | 24 | tool | 34 | something |
| 5 | weed | 15 | critter | 25 | potion | 35 | vehicle |
| 6 | leaf | 16 | beast | 26 | elevator | 36 | norn |
| 7 | flower | 17 | nest | 27 | teleporter | 37 | grendel |
| 8 | fruit | 18 | animal egg | 28 | machinery | 38 | ettin |
| 9 | manky | 19 | weather | 29 | creature egg | 39 | something |

The Vat's per-lobe neuron count matches the size of its referenced array: e.g. `attention` lobe has 40 neurons (one per agent category), `decision` lobe has 17 neurons (one per creature action - but only 14 are wired to scripts; see §6).

---

## 5. Brain Parameters and Migration Parameters

`Brain.catalogue` near line 159:

```
ARRAY "Brain Parameters" 2
"213"
"212"
```

The Brain ctor (`FUN_0041b270` in the Vat) reads two byte-valued entries from this array into Brain offsets `+0x28` and `+0x2c`. From [04-data-model.md](04-data-model.md) §1: these are likely **chemical indices** that the brain reads / writes per tick. Cross-reference against `ChemicalNames.catalogue`:

| Brain Parameters idx | Value | Chemical name (from ChemicalNames idx 213) |
|---|---|---|
| 0 (Brain+0x28) | 213 | REM sleep |
| 1 (Brain+0x2c) | 212 | Pre-REM sleep |

So `Brain+0x28` is the REM sleep chemical index, and `Brain+0x2c` is the Pre-REM sleep chemical index. The brain consults these two chemicals per tick - almost certainly the gating chemicals for sleep-state behaviour.

`Brain.catalogue` near line 155:

```
ARRAY "Migration Parameters" 2
"5"
"7"
```

The Tract ctor reads these into `Tract+0x2b2` and `Tract+0x2b3`. These bytes are passed through the SVRule operand-byte clamp at `&DAT_0047bd10` (range 0..7 for "small operand" indices), so plausible interpretations:

- Migration params idx 0 = **5** → byte 5 in the SVRule operand-index lookup → "random number" type (per [10-svrule-engine.md](10-svrule-engine.md) §3 class-1 case 5).
- Migration params idx 1 = **7** → byte 7 → "direct chemical read" type (case 7).

But these are byte-valued config knobs the engine consumes; the exact field semantics are still uncertain ([04-data-model.md](04-data-model.md) §10 lists this under open questions).

---

## 6. Action Script To Neuron Mappings - the 14-entry decision table

From `Creatures 3.catalogue` line 220 (NOT `Brain.catalogue`):

```
ARRAY "Action Script To Neuron Mappings" 14
```

| Decision idx | Neuron idx in `decision` lobe | Decision lobe neuron name (from `Creature Actions`) | Script meaning |
|---|---|---|---|
| 0 | 0 | look | quiescent |
| 1 | 1 | push | activate1 |
| 2 | 6 | get | get |
| 3 | 7 | drop | drop |
| 4 | 12 | eat | eat |
| 5 | 2 | pull | activate2 |
| 6 | 4 | approach | approach |
| 7 | 13 | hit | hit |
| 8 | 5 | retreat | retreat |
| 9 | 8 | express | express need |
| 10 | 9 | rest | rest |
| 11 | 10 | left | travel west |
| 12 | 11 | right | travel east |
| 13 | 3 | deactivate | deactivate (source comment: "unused") |

The **comments in the source file** narrate the order: "first six neurons are: quiescent, activate1, get, drop, eat, activate2"; "next two: approach, hit"; "next four: retreat, express_need, rest, right, left"; "next four: deactivate - unused".

`TAG "Decision Offsets to Expected Agent Script"` (line 255 of `Creatures 3.catalogue`, **TAG not ARRAY**, 16 entries) gives the parallel CAOS script number for each of 16 decisions:

| Decision idx | Script number | Comment in source |
|---|---|---|
| 0 | -1 | Quiescent |
| 1 | 1 | Activate1 |
| 2 | 2 | Activate2 |
| 3 | 0 | Deactivate |
| 4 | -1 | Approach |
| 5 | -1 | Retreat |
| 6 | 4 | Get |
| 7 | 5 | Drop |
| 8 | -1 | Express need |
| 9 | -1 | Rest |
| 10 | -1 | Travel west |
| 11 | -1 | Travel east |
| 12 | 12 | Eat |
| 13 | 3 | Hit |
| 14 | -1 | Undefined |
| 15 | -1 | Undefined |

A `-1` means "no agent-script fires for this decision" (the engine handles it internally - e.g. movement and approach are CA pathing, not script invocations). The `Action Script To Neuron Mappings` array has 14 entries (only the wired actions), but `Decision Offsets to Expected Agent Script` has 16 (with 14/15 reserved). The Vat caches both via `&DAT_00480fa8` and `&DAT_00480fe0` (per `FUN_0042b710` in the binary; see [04-data-model.md](04-data-model.md) §8). The 14 in the loop guard `if (0xd < iVar9)` matches this array's length exactly.

Two related arrays in `Creatures 3.catalogue`:

- `ARRAY "Bad Action Script" 1` → `"13"` (= hit). Tells the engine which script counts as a "bad" action for reinforcement.
- `ARRAY "Good Action Script" 2` → `"1"` (Activate1), `"2"` (Activate2). Reinforcement-positive scripts.

---

## 7. SVRule opcodes - NOT in any catalogue

I checked every catalogue file in the directory. **There is no SVRule opcode mnemonic table** in `Brain.catalogue`, `CAOS.catalogue`, `Creatures 3.catalogue`, or anywhere else. `CAOS.catalogue` contains only error-message strings tagged `"caos"`, `"caos_user_abort_frozen_script"`, and `"orderiser"` - these are localisation strings shown to the user when a CAOS script throws, not opcode names.

Where I looked:

| File | What it has | SVRule opcodes? |
|---|---|---|
| `Brain.catalogue` | Lobe layout, neuron name arrays, brain/migration params | No |
| `CAOS.catalogue` | CAOS engine error strings + orderiser parser errors | No |
| `Creatures 3.catalogue` | Action-script mappings, agent categories, CA names, classifiers | No |
| `ChemicalNames.catalogue` | 256 chemical names | No |
| `Genome.catalogue` | Moniker friendly names | No |
| `Norn.catalogue` | Vocab defaults (verb/noun/drive babble per genus) | No |

Confirmed against the Vat decompilation: [10-svrule-engine.md](10-svrule-engine.md) §8 already states that "the binary contains no opcode-name strings; the editor (`SVRuleDlg`) almost certainly fetches mnemonics from a `.catalogue` file at runtime". **That assumption appears to be wrong.** The mnemonics are not in any shipped C3 catalogue.

Three remaining hypotheses:

1. The mnemonics live in **`SVRuleDlg`'s MFC resource section** (string table or dialog template inside `Vat_1.9.exe` itself), not in a `.catalogue` file. MFC string-table resources are not strings the Ghidra string scan would necessarily surface as referenced-from-decompilation.
2. The mnemonics live in a `.catalogue` file shipped only with the **separate Brain in a Vat tool installer**, not the main C3 game install we have on disk.
3. The mnemonics never had user-visible names: SVRuleDlg uses bare opcode index numbers + slider values, with no mnemonic display.

Given the binary's slider format string `"%s%1.3f"` at `0x47b2d4` (per [10-svrule-engine.md](10-svrule-engine.md) §6), hypothesis 3 is consistent: `%s` would be a label like `"Op:"` and `%1.3f` the float - no mnemonic needed.

For our own viewer / brain inspector, this means we use the descriptive opcode names already documented in [10-svrule-engine.md](10-svrule-engine.md) §3 (derived from binary behaviour) and `docs/reference/svrule-brain-complete-reference.md` (community names), not anything from the catalogue.

---

## 8. Other interesting tags found while reading

### From `Creatures 3.catalogue`

- `ARRAY "Creature Reach" 2` → `"20"`, `"45"`. Probable: the X and Y reach distances in pixels for "what the creature can interact with at arm's length". Used by attention / interaction scoring.
- `ARRAY "Category Representative Algorithms" 40` → 40 single-digit codes (0/1/4) selecting which algorithm chooses the representative agent of each `Agent Category` for the attention lobe. Source comments: "0 means nearest in X direction; 1 means randomly assigned; 2 means nearest in current room; 3 means nearest to ground; 4 means seeds random nearest" (different rule per category).
- `ARRAY "Agent Classifiers" 40` → 40 three-tuple strings `"family genus species"`. The first entry `"999 999 999"` is the wildcard `self`; subsequent entries match the 40 `Agent Categories` slots positionally.
- `ARRAY "Cellular Automata Names" 20` → 20 CA channel names: sound, light, heat, precipitation, nutrient, water, protein, carbohydrate, fat, flowers, machinery, eggs, norn, grendel, ettin, norn home, grendel home, ettin home, gadget, "19".
- `TAG "Pointer Information"` → `"2 1 1"`, `"2 2"`, `"hand"`. Hand-agent classifier identifiers.
- `TAG "Navigable CA Indices"` → 12 indices listing which Cellular Automata channels are navigable (used by C3 pathfinding). Cross-reference: indices `6 7 8 10 11 12 13 14 15 16 17 18`.

### From `ChemicalNames.catalogue`

- `ARRAY "drive_chemical_numbers" 20` (line 8) - chemical IDs `148..162` plus navigation drives `199..203`. These are the chemical numbers that the `drive` lobe's 20 neurons read from. The mapping aligns with `Creature Drives`:

| Drive idx (lobe neuron) | Drive name | Chemical id | Chemical name |
|---|---|---|---|
| 0 | hurt | 148 | Pain |
| 1 | hungry for protein | 149 | Hunger for protein |
| 2 | hungry for starch | 150 | Hunger for carbohydrate |
| 3 | hungry for fat | 151 | Hunger for fat |
| 4 | cold | 152 | Coldness |
| 5 | hot | 153 | Hotness |
| 6 | tired | 154 | Tiredness |
| 7 | sleepy | 155 | Sleepiness |
| 8 | lonely | 156 | Loneliness |
| 9 | crowded | 157 | Crowded |
| 10 | scared | 158 | Fear |
| 11 | bored | 159 | Boredom |
| 12 | angry | 160 | Anger |
| 13 | friendly | 161 | Sex drive |
| 14 | homesick | 162 | Comfort |
| 15 | low down | 199 | Up |
| 16 | high up | 200 | Down |
| 17 | trapped | 201 | Exit |
| 18 | trapped (2nd) | 202 | Enter |
| 19 | patient | 203 | Wait |

This is the **drive→chemical binding** that connects the brain's drive lobe to creature biochemistry. Crucial for our viewer / NB engine.

- `ARRAY "chemical_names" 256` - full 256-entry chemical name table. Most numeric placeholders ("14", "15", ...) are unused slots; named slots are the metabolites, hormones, drives, drive backups, and 20 CA-smell channels. The drive backups at `131..145` are the per-drive emergency stores; the active drives at `148..162` are what the drive lobe reads.

### From `Brain.catalogue`

The complete tag list found:

| Tag | Type | Size | Purpose |
|---|---|---|---|
| `Brain Lobes` | ARRAY | 12 | Long lobe names |
| `Brain Lobe Neuron Names` | ARRAY | 12 | Per-lobe neuron-array name reference |
| `Brain Output Lobes` | ARRAY | 2 | Decision-emitting lobes |
| `Brain Input Lobes` | ARRAY | 9 | Sensory-input lobes |
| `Brain Lobe Quads` | ARRAY | 12 | 4-char lobe type tags |
| `Creature Drives` | ARRAY | 20 | Drive lobe neuron names |
| `Creature Actions` | ARRAY | 17 | Verb / decision lobe neuron names |
| `Situation Neurons` | ARRAY | 9 | Situation lobe neuron names |
| `Detail Neurons` | ARRAY | 11 | Detail lobe neuron names |
| `Migration Parameters` | ARRAY | 2 | Tract migration byte params |
| `Brain Parameters` | ARRAY | 2 | Brain-level chemical indices (REM, Pre-REM) |

---

## 9. What's NOT here that the Vat references

Tags the Vat binary references (per the `notes/strings.txt` and the data-model decompilation) but that have **no matching entry in any C3 catalogue**:

| Referenced tag | Where Vat uses it | Found in catalogue? | Notes |
|---|---|---|---|
| `Brain Lobe Quads` | Lobe layout lookup | Yes - but as 4-char type tags, not (x,y,w,h) coordinates | Geometry source unknown. See §2. |
| SVRule opcode mnemonics | `SVRuleDlg` editor labels | **No** | See §7. Possibly in `Vat_1.9.exe` MFC resources, not in any `.catalogue`. |
| `LobeNames` | Mentioned in brief | **No catalogue contains this tag** | Not found in any file. The brief may have conflated it with `Brain Lobes`. |
| Tract layout / source-dest pairs | Tract::Read | **No** | Tract topology comes from the genome wire format, not the catalogue. The catalogue holds none of the `(srcLobe, dstLobe)` connections. |
| Per-neuron position within a lobe | Implicit `(x, y) = (i % W, i / W)` | N/A | Not catalogue-driven; computed from grid dims. |
| Reinforcement parameters (threshold/gain) | `Tract::ReinforcementDetails` | **No** | These come from the genome stream, not the catalogue. |
| Per-lobe `W * H` grid dimensions | `Lobe + 0x278/+0x27c` | **No** | Read from the genome stream, not the catalogue. The catalogue tells you a lobe **exists** and **what to call its neurons**, but the actual neuron count and grid shape comes from the per-creature genome. |

So the catalogue is **layout vocabulary** (names, indices, identifiers, pointers to chemical IDs and script numbers). The actual brain **shape** (lobe dimensions, tract topology, dendrite counts, weights) lives in the genome / dump stream.

---

## 10. Summary for the porting effort

| Question | Answer |
|---|---|
| Where do lobe quad coordinates live? | **Not in the catalogue.** The catalogue's `Brain Lobe Quads` array holds 4-char lobe type tags (`attn`, `decn`, ...), not `(x, y, w, h)`. Coordinates for our viewer should come from `docs/reference/svrule-brain-complete-reference.md`. |
| Where do lobe long names come from? | `Brain.catalogue` `Brain Lobes` array - 12 entries: attention, decision, verb, noun, vision, smell, drive, situation, detail, response, proximity, stim source. |
| Where do per-neuron labels come from? | `Brain.catalogue` `Brain Lobe Neuron Names` indirects to `Agent Categories` (40, in `Creatures 3.catalogue`), `Creature Actions` (17), `Creature Drives` (20), `Situation Neurons` (9), or `Detail Neurons` (11) depending on lobe. |
| What are `Brain Parameters`? | Two chemical IDs: 213 (REM sleep) and 212 (Pre-REM sleep). The Brain ctor reads them into `Brain+0x28` and `Brain+0x2c`. |
| What are `Migration Parameters`? | Two bytes: 5 and 7. Stored in every Tract at `+0x2b2` and `+0x2b3`. Probable: SVRule operand-index hints. |
| Is the action-to-neuron table in the catalogue? | Yes. `Creatures 3.catalogue` `Action Script To Neuron Mappings` (14 entries, neuron indices into `decision` lobe) plus `Decision Offsets to Expected Agent Script` (16 entries, parallel script numbers with -1 = no script). |
| Are SVRule opcode mnemonics in the catalogue? | **No.** Not in any `.catalogue` file. Most likely embedded in `Vat_1.9.exe` MFC string-table resources or simply absent (sliders are bare numeric editors). |
| What about drive→chemical bindings? | `ChemicalNames.catalogue` `drive_chemical_numbers` array - 20 entries mapping drive lobe neurons 0..19 to chemical IDs 148..162 + 199..203. |
| Is the agent-category list in the catalogue? | Yes. `Creatures 3.catalogue` `Agent Categories` (40 entries) drives every lobe whose neurons represent agent categories: `attn`, `noun`, `visn`, `smel`, `stim`. |

For our own NB engine viewer:

1. Read `Brain.catalogue` and `Creatures 3.catalogue` and `ChemicalNames.catalogue` at startup.
2. Use the `Brain Lobes` × `Brain Lobe Quads` × `Brain Lobe Neuron Names` triple to build the canonical 12-lobe layout with tags, long names, and per-neuron label arrays.
3. Use the visual quad geometry from `docs/reference/svrule-brain-complete-reference.md` (catalogue does **not** carry it).
4. Use `drive_chemical_numbers` to bind drive lobe neurons to creature chemicals.
5. Use `Action Script To Neuron Mappings` + `Decision Offsets to Expected Agent Script` for the decision→action→script pipeline.
6. SVRule opcode mnemonics: keep using descriptive names from [10-svrule-engine.md](10-svrule-engine.md) §3 and the SVRule reference doc - the catalogue files don't supply them.
