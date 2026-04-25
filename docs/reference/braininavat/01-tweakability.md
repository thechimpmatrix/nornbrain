# Brain in a Vat: Tweakability Verdict

## Headline

Tweakable. The hardest part of any reverse-engineering effort (recovering symbols and class boundaries) is already done by the binary itself: RTTI is intact, all 3,140 functions decompiled cleanly, and the IPC contract is small and fully understood after one Ghidra pass.

Three viable paths, ranked by effort.

---

## Path 1: Spoof the engine side (recommended)

**Idea.** Leave `Vat_1.9.exe` untouched. Build a Python sidecar (or C++ shim inside openc2e) that creates the four named Win32 kernel objects with the magic `c2e@` and answers the Vat protocol from NB state.

**What you build:**
1. A "fake engine" process that calls `CreateMutexA`, `CreateEventA` x2, `CreateFileMappingA` with the suffixes `_mutex`, `_request`, `_result`, `_mem`.
2. Write `c2e@` at offset 0 of the shared memory.
3. Wait on the request event, parse the request body, fetch live state from NB (CfC layer or SVRule layer), pack the response into shared memory in the format the Vat client expects, signal the result event.
4. Set the registry key `HKEY_CURRENT_USER\Software\CyberLife Technology\Creatures Engine` so the Vat tool finds the right name prefix.

**What you need to learn from Ghidra (well-bounded):**
- The full request/response opcode set used over shared memory. The Vat tool is the only client, so reading its `BrainAccess` methods reveals every opcode it sends. Maybe 10-30 message types: "list lobes", "read neuron N in lobe L", "read dendrite list for tract T", and similar reads. Almost no writes (Vat is mostly a viewer; the only writes are dendrite migration commands during instinct sim).
- The shared memory layout: header, request body, response body, sizes. The decompilation makes this trivial.

**Why this wins:**
- Does not require modifying or shipping a patched .exe.
- Keeps the original UI exactly as Creature Labs designed it. Free polish.
- All NB-side work is in our own code, in a language we control.
- Reusable: any other tool that speaks the c2e shared-memory protocol (there are a few) becomes compatible for free.

**Effort estimate:** 2-3 sessions of focused work. Mapping the opcode set from `BrainAccess` decompilations is the bulk; once mapped, the Python responder is mechanical.

**Risks:**
- The opcode set might include awkward bits (transfer buffers, paginated downloads - strings already mention "Lobe to big for transfer", "Tract to big for transfer", which hint at chunked protocols).
- Endianness and struct packing must match exactly. Ghidra recovers all of this.

---

## Path 2: Patch the IPC client to use TCP

**Idea.** Binary-patch `BrainAccess` to drop the shared-memory path and instead open a TCP socket to openc2e's CAOS port (20001).

**Why not.** The Vat protocol is request/response over a binary blob. CAOS is a text-based scripting protocol. They are not interchangeable; you would have to translate every IPC opcode into one or more CAOS injections and parse `outv` results. That is the work of Path 1 anyway, just done inside a patched binary instead of cleanly outside it. No advantage, more pain.

**Effort estimate:** larger than Path 1. Skip.

---

## Path 3: Reimplement the Vat in Python/Qt

**Idea.** Keep only the data model. Write a fresh viewer in Python/Qt that reads NB state directly and renders the same lobes/tracts/neurons/dendrites visualisations.

**Why later.** The Vat's strength is the offline mode (load a genome, drive synthetic inputs, watch dendrites migrate). Reproducing the dendrite migration logic from scratch means re-deriving the SVRule equations from `docs/reference/svrule-brain-complete-reference.md` and validating against the original. Worth doing eventually, but only after we have proven via Path 1 that we want this UI at all.

**Effort estimate:** several weeks of dedicated work. Defer until Path 1 reveals whether the UI is actually what we want.

---

## Recommendation

Take Path 1. Concretely:

1. **Spike (next session):** Read the `BrainAccess` decompilations and write `notes/02-ipc-protocol.md` documenting every opcode the Vat tool sends.
2. **Prototype:** Python responder that handles "list lobes" and "read neuron variables" only. Confirm Vat connects, lists lobes, and shows live neuron values from NB.
3. **Iterate:** add dendrite, tract, and graph opcodes one by one, driven by what the Vat UI tries to read.
4. **Decide:** at this point we know the UI well. Either keep using Path 1 in production (simple, free polish) or graduate to Path 3 (clean rewrite once the data flows are understood).

This is a significantly easier problem than building an SVRule layer from scratch. It is a protocol-mapping exercise on a binary that has already given up its secrets.

---

## Open questions for the next pass

1. Does the engine name suffix (the `<name>` in `<name>_mutex` etc.) come from the registry value, an environment variable, or a hardcoded default? Need to read `BrainAccess` constructor + the function that builds the suffix string.
2. What is the request/response opcode set? Need to enumerate `BrainAccess` member functions and their internal switch statements.
3. Does the protocol depend on sharing virtual address space layout (raw pointers in shared memory)? If yes, the responder needs more care with the memory layout. Ghidra will tell us this when we read the response writers.
4. The "Tract to big for transfer" / "Lobe to big for transfer" strings imply size-bounded transfers and possibly chunked downloads. Need to identify the chunking mechanism.

All four are well-bounded: open the relevant decompilations in Ghidra, read for an hour, write the answers down.
