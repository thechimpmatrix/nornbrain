# Brain in a Vat: IPC Protocol

Protocol catalogue for the Win32 named-shared-memory IPC the 1999 Vat tool uses to talk to a running Creatures 3 engine. Reverse-engineered from the Ghidra full-decompilation set under `<PROJECT_ROOT>/analysis/braininavat/notes/`. The goal of this document is to be sufficient to write a Python responder that impersonates the engine.

The IPC client class is `BrainAccess` (RTTI label `0047a3f8`). All four synchronisation objects are opened by the connect path at `FUN_0043f8f0` and closed by the teardown path at `FUN_0043f890`. The send/wait core is `FUN_0043fa40`. The high-level "send a CAOS string and read the reply into a buffer" entry point is `FUN_00442580`.

The wire format is **a single shared-memory transport carrying ASCII CAOS commands prefixed with `execute\n`**. The engine processes the CAOS, leaves the reply text in the shared region, and signals the result event. There are no opcodes in the binary sense; the protocol is text-based on top of CyberLife's CAOS runtime.

---

## 1. Connection lifecycle

### 1.1 Named objects

The Vat reads a base name from the registry (`HKEY_CURRENT_USER\Software\CyberLife Technology\Creatures Engine`, strings at `0046e6e0` / `0046e720`) and constructs four object names by suffixing it.

| Object | API call | Suffix string | Access mask | Source |
|---|---|---|---|---|
| Mutex | `OpenMutexA` | `%s_mutex` (`0047d064`) | `0x001F0001` (full access) | `FUN_0043f8f0` |
| Request event | `OpenEventA` | `%s_request` (`0047d070`) | `0x001F0003` (full access + signal) | `FUN_0043f8f0` |
| Result event | `OpenEventA` | `%s_result` (`0047d07c`) | `0x001F0003` | `FUN_0043f8f0` |
| Shared memory | `OpenFileMappingA` + `MapViewOfFile` | `%s_mem` (`0047d088`) | `0x000F001F` (full FILE_MAP) | `FUN_0043f8f0` |

The format helper used to build each suffixed name is `FUN_00458dfa` (sprintf-equivalent). All four objects must already exist when the Vat calls `Open*A`; the engine is the creator.

### 1.2 Handshake (`FUN_0043f8f0`)

Pseudocode from the decompilation, with the `BrainAccess` instance fields named:

```
struct BrainAccess {
  HANDLE  hMutex;        // +0x00  -> "%s_mutex"
  HANDLE  hReqEvent;     // +0x04  -> "%s_request"
  HANDLE  hResEvent;     // +0x08  -> "%s_result"
  HANDLE  hMapping;      // +0x0C  -> "%s_mem"
  char*   pView;         // +0x10  -> mapped view of "%s_mem"
  // ... +0x14 and +0x15 are state flags (see 1.4)
};

bool Connect(BrainAccess* this, const char* baseName) {
  if (this->hMutex != 0) throw "Internal IPC mutex error";  // 0047d048

  this->hMutex    = OpenMutexA   (0x1F0001, FALSE, baseName + "_mutex");
  if (!this->hMutex) goto fail;
  GetHandleInformation(this->hMutex, ...);                  // sanity probe
  this->hReqEvent = OpenEventA   (0x1F0003, FALSE, baseName + "_request");
  if (!this->hReqEvent) goto fail;
  this->hResEvent = OpenEventA   (0x1F0003, FALSE, baseName + "_result");
  if (!this->hResEvent) goto fail;
  this->hMapping  = OpenFileMappingA(0xF001F, FALSE, baseName + "_mem");
  if (!this->hMapping) goto fail;
  this->pView     = MapViewOfFile(this->hMapping, 0xF001F, 0, 0, 0);
  if (!this->pView) goto fail;

  // Validate magic at view offset 0
  if (this->pView[0..3] != "c2e@") goto fail;

  return true;

fail:
  Disconnect(this);   // FUN_0043f890
  return false;
}
```

The "Internal IPC mutex error" guard at the top means `Connect` is non-reentrant: if `hMutex` is already held the call throws (`__CxxThrowException_8` at `0043f906`).

The wrapper `FUN_00442240` is what drives `Connect`: it reads the registry game name (via `FUN_00445300` against `DAT_005812b0`), then calls `FUN_0043f8f0`, then stores the boolean result into `this+0x15` as a "connected" flag.

### 1.3 Teardown (`FUN_0043f890`)

Symmetric tear-down, idempotent: each handle is closed only if non-null and zeroed afterwards. Order is `pView` (UnmapViewOfFile) → `hMapping` → `hReqEvent` → `hResEvent` → `hMutex`. The wrapper `FUN_004422e0` clears the connected flag at `+0x15` after teardown.

### 1.4 BrainAccess state byte map

Observed from `FUN_004422f0` (the high-level "issue a CAOS request") and friends:

| Offset | Type | Meaning |
|---|---|---|
| `+0x00` | HANDLE | mutex |
| `+0x04` | HANDLE | request event |
| `+0x08` | HANDLE | result event |
| `+0x0C` | HANDLE | file mapping |
| `+0x10` | char\* | mapped view base |
| `+0x14` | byte | "request in progress" flag (set on entry to send, cleared on exit; `004422f0:34/96/151`) |
| `+0x15` | byte | "connected" flag (set by `Connect`, cleared by `Disconnect` wrapper) |
| `+0x16` | byte | "auto-disconnect after request" flag (when set, `FUN_004422e0` is called after each transaction; `004422f0:35/92/148`) |

---

## 2. Wire format of shared memory

Reconstructed from `FUN_0043fa40` (send), the four accessors `FUN_0043fb30/40/50/60`, and the size-clamp checks in `FUN_00403200` against `*(DAT_00481288 + 0x10)`.

### 2.1 Header (offset 0..0x17)

| Offset | Size | Field | Direction | Source |
|---|---|---|---|---|
| `0x00` | 4 | Magic `"c2e@"` (0x40_65_32_63 LE) | static | `FUN_0043f8f0:39-40`, `FUN_0043fa40:19-20` |
| `0x04` | 4 | Server process id (DWORD) | engine → vat | `FUN_0043fa40:38` (`OpenProcess(..., view[1])`) |
| `0x08` | 4 | Result/status code (DWORD, 0 = OK, non-zero = error) | engine → vat | accessor `FUN_0043fb50` returns `view[2]` |
| `0x0C` | 4 | Payload length (DWORD; size of bytes at `0x18`) | both | accessor `FUN_0043fb30` returns `view[3]`; `FUN_0043fa40:35` writes it on send |
| `0x10` | 4 | Maximum payload capacity (DWORD; size in bytes available at `0x18`) | engine → vat | `FUN_0043fa40:19` and `FUN_00403200:216,451` use it as a cap |
| `0x14` | 4 | Unknown - never read or written by any decompiled function inspected; possibly reserved | - | needs deeper read of engine-side counterpart |

Magic ordering: bytes at `0..3` are checked individually as `'c','2','e','@'` (`FUN_0043f8f0:40`), so on disk the four bytes are exactly the ASCII string `c2e@`.

### 2.2 Payload region (offset 0x18 onwards)

Plain bytes. Length is whatever is in the `0x0C` field. The accessor `FUN_0043fb40` returns `view + 0x18` as the payload pointer. The same region is used for both the request body (when the Vat is writing) and the response body (when the engine has written and signalled).

The Vat consistently writes a NUL-terminated ASCII CAOS string and includes the trailing NUL in the byte count (see §3 for evidence). For responses, the engine writes ASCII text terminated by a NUL; the Vat copies bytes until it hits NUL when reading (`FUN_00442580:43-52` does a strlen on the response).

### 2.3 Capacity is engine-defined

The `0x10` capacity field is never *written* by the Vat - only read for clamp checks. The "Lobe to big for transfer / Require transfer buffer of: %d" (`0047a63c`) and "Tract to big for transfer / Require transfer buffer of: %d" (`0047a674`) error paths in `FUN_00403200` (lines 216-220 for lobe, 451-455 for tract) compare the post-dump response length against `*(DAT_00481288 + 0x10)`. The number formatted into the error string is the response length, not the capacity, which means the Vat tells the user how big the engine's buffer would need to be. This implies the Vat does *not* know the capacity in advance - it just trusts `0x10` and aborts if a single dump exceeds it.

---

## 3. Request / response opcodes

There is no numeric opcode field. The "opcode" is a CAOS command line. Every request the Vat sends is a NUL-terminated ASCII string starting with the literal `"execute\n"` (`0047d0bc`) followed by a CAOS one-liner. The engine returns ASCII text.

The string-table evidence is conclusive: every `s_execute_*` constant fed to `FUN_00442580` (the high-level send) carries the `execute\n` prefix. `FUN_00442720` is the helper that prepends `execute\n` to a body string when `FUN_004422f0` is the entry point (the alternate non-debug path).

### 3.1 Confirmed in-use commands (called from decompiled paths)

| # | Request (CAOS body) | Source addr | Callsite | Purpose | Response |
|---|---|---|---|---|---|
| 1 | `OUTS WNAM` | `0047a520` | `FUN_00403200:96` | Get current world name | NUL-terminated ASCII world name |
| 2 | `TARG AGNT %d OUTS GTOS 0` | `0047a564` | `FUN_00403200:126` | Get genome filename for agent N | NUL-terminated path fragment |
| 3 | `TARG AGNT %d OUTV CAGE` | `0047a5a4` | `FUN_00403200:147` | Get life stage of agent N | ASCII integer |
| 4 | `TARG AGNT %d BRN: DMPB` | `0047a5f0` | `FUN_00403200:175` | Dump brain configuration | ASCII brain config block (lobe count, tract count, parameters; ends with `END DUMP` (`0047a6ac`) for v1.0 or `END DUMP V1.1` (`0047a6b8`) for v1.1) |
| 5 | `TARG AGNT %d BRN: DMPL %d` | `0047a6e0` | `FUN_00403200:598` | Dump lobe N (init phase) | ASCII binary-encoded lobe blob |
| 6 | `TARG AGNT %d BRN: DMPT %d` | `0047a724` | `FUN_00403200:614` | Dump tract N (init phase) | ASCII binary-encoded tract blob |
| 7 | `TARG AGNT %d BRN: DMPL %d` | `0047a8b8` | `FUN_00409160:26` | Re-dump lobe N (refresh during runtime) | as #5 |
| 8 | `TARG AGNT %d BRN: DMPT %d` | `0047a8dc` | `FUN_004092c0:26` | Re-dump tract N | as #6 |
| 9 | `TARG AGNT %d BRN: DMPN %d %d` | `0047a900` | `FUN_00409420:26` | Dump neuron in lobe (lobe-id, neuron-id) | per-neuron variables |
| 10 | `TARG AGNT %d BRN: DMPD %d %d` | `0047a928` | `FUN_00409590:26` | Dump dendrite (tract-id, dendrite-id) | per-dendrite variables |
| 11 | `DBG: TOCK` | `0047a80c` and `0047a820` | `FUN_00404d30:74,100` | Step the engine one tick (debugger) | empty / status |
| 12 | `DBG: PLAY` | `0047af18` and `0047afe8` | `FUN_00411bf0:23`, `FUN_00412280:157` | Resume engine | empty / status |
| 13 | `DBG: PAWS` | `0047b068` | `FUN_004129d0:32` | Pause engine | empty / status |
| 14 | `ENUM 0 0 0 DOIF TYPE TARG = 7 OUTS HIST NAME GTOS 0 OUTS "\n" OUTV UNID OUTS "\n" ENDI NEXT` | `0047b0e0` | `FUN_00412ac0:60` | Enumerate all creatures (type 7), one per line: `name\nUNID\n` | newline-separated creature roster |

The version probe at `FUN_00403200:558-582` decides protocol version by string-matching the trailing line of the DMPB output: if the response ends with `END DUMP` the Vat sets a constant to `0x3F800000` (1.0f), if `END DUMP V1.1` it sets it to `0x3F8CCCCD` (1.1f). This is the only versioning signal in the protocol.

### 3.2 Strings present but unreferenced from the decompiled set

Four format strings exist in the binary string table but no decompiled function calls them with their formatted form:

| Address | String | Likely purpose |
|---|---|---|
| `0047b310` | `execute\nTARG AGNT %d BRN: SETL %d %d %f` | Set a lobe variable (lobe, var, float value) |
| `0047b35c` | `execute\nTARG AGNT %d BRN: SETT %d %d %f` | Set a tract variable |
| `0047b490` | `execute\nTARG AGNT %d BRN: SETN %d %d %d %f` | Set a neuron variable |
| `0047b4f8` | `execute\nTARG AGNT %d BRN: SETD %d %d %d %f` | Set a dendrite variable |

These are write-back counterparts to commands #5/6/9/10. They are not invoked from any decompiled function we inspected (verified by grepping the aggregated decompilation `decompiled_all.c` for both the address and the literal `BRN..SET` substring - zero hits). Possibilities:

- The format strings live behind dialog edit-handlers whose decompilation didn't preserve the string symbol mapping
- A `Tweak` write path exists but is wired through a function pointer table we haven't traced
- They are dead code from an unshipped feature

A Python responder should still implement these (treat them as parametric writes against the appropriate Lobe/Tract/Neuron/Dendrite variable). They are listed as **best-effort opcodes - implement defensively, expect them on receipt**.

### 3.3 Invariants per request

For every request, the following must hold at the moment the Vat writes to shared memory:

- Bytes `0x00..0x03` of the view are still `c2e@` (re-checked on every send by `FUN_0043fa40:19-20`)
- The request payload (CAOS string) is `<= view[0x10]` bytes long (clamp check `param_2 <= *(uint*)(view + 0x10)` on `FUN_0043fa40:19`)
- Length includes the NUL terminator (`FUN_00442580:33` calls strlen and passes `~uVar5` which is `strlen+1`)

Failure of any of these aborts the send and the BrainAccess instance returns `false`, which propagates up as `"Start transaction failed"` (`0047d0c8` / `0047d0e4`).

---

## 4. Synchronisation pattern

From `FUN_0043fa40` lines 21-50, the request cycle is:

```
                      Vat (client)                       Engine (server)
                      ============                       ===============
1. WaitForSingleObject(hMutex, 500)            ──────►  (mutex acquired)
2. memcpy(view+0x18, request, length)
3. view[0x0C] = length
4. ResetEvent(hResEvent)                                 (no-op for server yet)
5. SetEvent(hReqEvent)                         ──────►  (request event seen)
                                                        ► engine reads view, processes
                                                        ► engine writes response into view+0x18
                                                        ► engine sets view[0x0C] = response length
                                                        ► engine sets view[0x08] = status (0=ok)
                                                        ► engine SetEvent(hResEvent)
6. WaitForMultipleObjects(2,
     [hResEvent, hServerProcess], FALSE, INF) ◄──────  (result event signalled)
7. CloseHandle(hServerProcess)
8. memcpy(caller_buffer, view+0x18, view[0x0C])
9. (mutex released by FUN_0043fb60 → ReleaseMutex)
```

Critical details:

- **Mutex timeout is 500 ms.** If the Vat cannot acquire the mutex within 500 ms it gives up the entire transaction (`FUN_0043fa40:21`). A Python responder must release the mutex promptly between transactions or the Vat will see `"Start transaction failed"`.
- **Result event must be reset before signalling request.** Step 4 (`ResetEvent`) is performed by the *Vat*, not by the engine. This is unusual but correct: the Vat clears the slate, then asks for new work. The engine should only ever `SetEvent` on the result, never `ResetEvent`.
- **The wait list is two-handle: result event AND server process handle.** `WaitForMultipleObjects(2, ..., FALSE, INFINITE)` returns 0 if the result event signals, 1 if the server process dies. If the server dies (`DVar3 != 0`), the Vat releases the mutex (`FUN_0043fa40:47`) and returns failure - surfacing as `"Could not download brain.\nDisconnected."` (`0047aaf4`) at the dialog layer.
- **Server PID is read from the view at every send.** `OpenProcess(0x1f0fff, FALSE, view[1])` happens inside the request loop, so the engine must keep its PID written at offset `0x04` for the lifetime of the connection.
- **The mutex is NOT released inside `FUN_0043fa40` on success.** Release is the caller's responsibility, via `FUN_0043fb60` (which is just `ReleaseMutex(*this)`). This is what allows callers to read the response (steps 7-8 above) under the same mutex hold that wrote the request. `FUN_00442580:54` releases the mutex after copying the response into the static reply buffer at `&DAT_00481294`.

The result-status field at `view+0x08` is examined by `FUN_00442580:36-39` after a successful WaitForMultipleObjects: any non-zero value causes the function to release the mutex and return false, even though the wait succeeded. So **the engine has two ways to fail a request**: leave `view[0x08]` non-zero, or simply let its process die. Both paths surface to the user as the same generic error.

---

## 5. Error paths

Mapping observed error strings to the conditions that fire them.

| String | Address | Fired from | Condition |
|---|---|---|---|
| `Internal IPC mutex error` | `0047d048` | `FUN_0043f8f0:16` | `Connect` called when `hMutex` field is already non-zero |
| `Initial connection failed` | `0047d0a0` | `FUN_004422f0:158-181` | `FUN_00442240` (`Connect`+state-set) returned false - any of the four `Open*A` calls failed, or magic check failed |
| `Start transaction failed` | `0047d0c8` | `FUN_004422f0:124-147` | `FUN_0043fa40` returned false - mutex acquire timed out, payload exceeds capacity, magic now corrupt, or server died during wait |
| `Start transaction failed` | `0047d0e4` | `FUN_00442580:57-79` | Same as above, from the alternate (CAOS-string-only) entry point |
| `Lobe to big for transfer\nRequire transfer buffer of: %d` | `0047a63c` | `FUN_00403200:221-292` | A `BRN: DMPL` response exceeds `view[0x10]` capacity; `%d` is the *response* length |
| `Tract to big for transfer\nRequire transfer buffer of: %d` | `0047a674` | `FUN_00403200:456-526` | A `BRN: DMPT` response exceeds capacity |
| `Could not download brain lobe` | `0047a704` | `FUN_00403200:722` | The DMPL transaction itself failed (either `FUN_00442580` returned false, or response was truncated). Used for init-phase failures. |
| `Could not download brain tract` | `0047a748` | `FUN_00403200:743` | Same as above for DMPT |
| `Could not fetch brain` | `0047a610` | `FUN_00403200:336` | DMPB failed - first probe of brain structure |
| `There are no lobes` | `0047a628` | `FUN_00403200:312` | DMPB succeeded but reported zero lobes |
| `Could not create brain` | `0047a6c8` | `FUN_00403200:702` | Brain object construction failed after a successful download |
| `Could not initialize brain` | `0047a768` | (referenced by `FUN_00403200`-family) | Brain init step failed mid-way |
| `Could not create brain support` | `0047a784` | `FUN_00403200:678` | Support-data step failed (wraps post-DMPL/DMPT processing) |
| `Could not download brain.\nDisconnected.` | `0047aaf4` | `FUN_00409160:58`, `FUN_004092c0:58`, etc. | A runtime-refresh DMPL/DMPT/DMPN/DMPD failed. Vat treats this as fatal: posts `WM_COMMAND 0x9CB2` to the parent (close the brain view) and throws `OnlineFailedException` |

The two "Start transaction failed" entries are *separate* string copies because they are baked into separate code paths (cdecl `FUN_004422f0` vs. thiscall `FUN_00442580`). Same string, different addresses, same meaning.

---

## 6. Engine-side responsibilities (Python responder checklist)

To impersonate the engine, a Python process must:

1. **Create the four named objects before the Vat starts**
   - `CreateMutexA(NULL, FALSE, "<base>_mutex")` - initially unowned
   - `CreateEventA(NULL, TRUE, FALSE, "<base>_request")` - manual-reset, not signalled
   - `CreateEventA(NULL, TRUE, FALSE, "<base>_result")` - manual-reset, not signalled
   - `CreateFileMappingA(INVALID_HANDLE_VALUE, NULL, PAGE_READWRITE, 0, capacity, "<base>_mem")` - backed by pagefile
   - `<base>` is the engine's game name, normally read from `HKEY_CURRENT_USER\Software\CyberLife Technology\Creatures Engine` (string `0046e6e0`). The responder must either set that registry key or hard-code the same name.

2. **Initialise the shared memory header**
   - `view[0..3] = "c2e@"` (must be present *before* the Vat connects - the Vat's `Connect` validates this in `FUN_0043f8f0:39-40`)
   - `view[0x04] = GetCurrentProcessId()` (must remain valid for the lifetime of the connection - re-read on every Vat send)
   - `view[0x08] = 0` (status idle)
   - `view[0x0C] = 0` (no payload)
   - `view[0x10] = capacity_in_bytes - 0x18` (the maximum number of payload bytes that fit; the Vat treats this as the per-request cap). 64 KiB is a safe default; whether the original engine used more is unverified.

3. **Service loop**
   - `WaitForSingleObject("<base>_request", INFINITE)` (or a poll with `WAIT_OBJECT_0`)
   - `ResetEvent("<base>_request")`
   - Read length from `view[0x0C]`, read that many bytes from `view + 0x18` (treat as ASCII, NUL-terminated)
   - Strip the leading `execute\n` prefix, parse the CAOS command
   - Compute the response (see §3 table for command semantics)
   - Write response bytes into `view + 0x18`, set `view[0x0C] = len(response_including_nul)`, set `view[0x08] = 0` for success or non-zero for engine-side error
   - `SetEvent("<base>_result")`
   - Loop

4. **Honour the mutex**
   - Do not modify the view while it is held by the Vat (which is from `WaitForSingleObject(hMutex, 500)` until `ReleaseMutex` after the response copy)
   - In practice the responder does not need to acquire the mutex itself - the Vat acquires it on the client side. But the responder must **not** preempt a transaction by writing to the view between `request` set and `result` set.

5. **Stay alive for the duration**
   - If the responder process dies, the Vat's `WaitForMultipleObjects` returns 1 and surfaces "Disconnected" to the user. Restart of the Vat is required to recover (it does not retry `Connect`).

6. **Implement the in-use opcodes (table §3.1)**
   - Minimum viable set for the Vat to load a brain: WNAM, GTOS, CAGE, DMPB, DMPL × N, DMPT × M
   - Required for refresh/inspection: DMPL, DMPT, DMPN, DMPD (runtime variants)
   - Required for control: DBG: TOCK / PLAY / PAWS, ENUM ... NEXT
   - Treat the SETL/SETT/SETN/SETD strings (§3.2) as plausibly-incoming - implement them defensively

7. **Match the DMPB v1.1 footer**
   - The Vat probes for `END DUMP` vs `END DUMP V1.1` to pick a protocol version constant (`FUN_00403200:558-582`). For modern compatibility, emit `END DUMP V1.1` so the Vat selects the 1.1 codepath.

---

## 7. Open questions

Items the decompilation alone could not resolve. These need either deeper static analysis, dynamic capture (running the Vat against a real or stub engine and logging the shared memory), or recovery of original CyberLife source / docs.

1. **Exact `view[0x14]` semantics.** The 4 bytes between `capacity` (`0x10`) and `payload start` (`0x18`) are never read or written by any `BrainAccess`-side function inspected. They could be a flags field (e.g., async/streaming hint), a sequence number, or simply padding. *Resolve by: dynamic capture, or by analysing the engine-side `BrainAccess` peer if recoverable from the GOG `engine.exe` binary.*

2. **Are the SET* commands ever sent?** Strings `0047b310 / 0047b35c / 0047b490 / 0047b4f8` exist in the binary but no decompiled callsite formats them. *Resolve by: searching with stricter pattern match against `decompiled_all.c` for any code that loads the constant addresses, or by exercising the Tweak/Edit dialogs in the Vat against a stub engine and observing what it sends.*

3. **Exact format of DMPB / DMPL / DMPT / DMPN / DMPD response bodies.** The Vat parses each into Lobe/Tract/Neuron/Dendrite C++ objects (via `FUN_004594bc` for atoi, `FUN_0044d638/26d` for some serialisation framework, `FUN_0041bbf0` and `FUN_0041bf20` for lobe/tract decoders). The byte-level grammar of those responses is the next reverse-engineering target - without it, a Python responder cannot synthesise valid replies. *Resolve by: reading the decoder functions named above, or by capturing real engine responses on the wire.*

4. **Capacity of `_mem` mapping.** The Vat reads it from `view[0x10]` and never writes it, so the responder picks the value. But the original engine likely used a fixed size, and per-lobe / per-tract dumps have to fit into one transaction (no chunking visible). The error string "Require transfer buffer of: %d" suggests the original buffer was occasionally too small for large brains. *Resolve by: examining the engine, or empirically sizing to the largest plausible lobe blob.*

5. **Whether `execute\n` is the only prefix the engine accepts.** The Vat sends only `execute\n`-prefixed commands. Whether the engine also accepts other dispatch prefixes (e.g., `query\n`, `inject\n`) is unverified from the Vat side. For a Python responder targeting only this Vat, supporting `execute\n` is sufficient.

6. **Behaviour of `BrainAccess+0x16` (auto-disconnect flag).** Set by some code path we did not chase, causing each transaction to close the connection on completion. Likely tied to a debug or one-shot mode in the dialog layer. *Resolve by: tracing writers of the `+0x16` byte across the decompilation set.*

7. **Registry key fallback.** Strings `0047d180` ("Default game name not found. Check you have a correct registry entry...") and `0046e720` (`Software\CyberLife Technology\`) suggest a fallback / discovery path. The exact subkey value the Vat reads (game name) needs confirmation. *Resolve by: reading `WhichEngine::GetStringKey` (`0047d2c4`) and `FUN_00445020` / `FUN_00445300`.*

---

## Cross-references

- Connect / disconnect: `FUN_0043f8f0` (`0043f8f0`), `FUN_0043f890` (`0043f890`), `FUN_00442240` (`00442240`), `FUN_004422e0` (`004422e0`)
- Send / wait core: `FUN_0043fa40` (`0043fa40`)
- Header accessors: `FUN_0043fb30` (size), `FUN_0043fb40` (payload ptr), `FUN_0043fb50` (status), `FUN_0043fb60` (release mutex)
- High-level send entry points: `FUN_00442580` (CAOS-string + reply-into-static-buffer), `FUN_004422f0` (CAOS-body + prefix builder + UI error wrapping)
- Brain-init driver: `FUN_00403200` - the canonical sequence that exercises WNAM, GTOS, CAGE, DMPB, DMPL × N, DMPT × M
- Runtime refresh callers: `FUN_00409160` (lobe), `FUN_004092c0` (tract), `FUN_00409420` (neuron), `FUN_00409590` (dendrite)
- Debug-control callers: `FUN_00404d30` (TOCK), `FUN_00411bf0` / `FUN_00412280` (PLAY), `FUN_004129d0` (PAWS), `FUN_00412ac0` (ENUM creature roster)
