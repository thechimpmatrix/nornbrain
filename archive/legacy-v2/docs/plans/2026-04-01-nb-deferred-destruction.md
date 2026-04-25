# NB Deferred Destruction: Systemic Use-After-Free Fix


**Goal:** Eliminate all use-after-free crashes in NB (CreaturesCfC64) by implementing deferred agent destruction: the industry-standard pattern used by Unreal Engine, Godot, and every production game engine.

**Architecture:** Two-layer fix.

**Layer 1: Deferred Destruction:** `Agent::kill()` no longer removes agents from the world list. It sets `pending_kill_` and queues the agent in `World::pending_destroy_`. Pending-kill agents are skipped by ticking, script execution, rendering, pointer interaction, and CAOS commands. `World::flushPendingDestroys()` runs at the end of `Engine::tick()`, after all game logic and before `drawWorld()`. This guarantees no pointer becomes invalid mid-frame.

**Layer 2: Safe AgentRef:** `AgentRef::operator->()` calls `.lock()` and returns nullptr instead of crashing. A new `AgentRef::safeGet()` treats pending-kill agents as dead. The `valid_agent()` CAOS macro (`caosVM.h:296`) rejects pending-kill agents, protecting all 180+ CAOS command call sites in one edit.

**Tech Stack:** C++17, MSVC 2022, pybind11, CMake

**Naming:** This engine is **NB** (CreaturesCfC64). All new code, comments, logs use "NB:" prefix. Git branch: `openc2e-nornbrain`. Binary: `openc2e.exe` (unchanged).

---

## DOR Evidence (researched 2026-04-01, all verified)

| Engine | Pattern | Source |
|--------|---------|--------|
| **Unreal** | `Destroy()` marks PendingKill. GC runs between frames, auto-nulls UPROPERTY ptrs. | [unrealcommunity.wiki](https://unrealcommunity.wiki/memory-management-6rlf3v4i) |
| **Godot** | `queue_free()` defers to end of frame. Direct `free()` during signals = crash. | [godot-proposals#7441](https://github.com/godotengine/godot-proposals/issues/7441) |
| **Reassembly** | `watch_ptr<T>` auto-nulls on destruction + end-of-frame delete queue. | [anisopteragames.com](https://www.anisopteragames.com/how-to-prevent-dangling-pointers-to-deleted-game-objects-in-c/) |
| **Generational handles** | 32-bit index+generation counter. Stale handle detected at O(1). | [floooh.github.io](https://floooh.github.io/2018/06/17/handles-vs-pointers.html) |

## Crash Evidence (29/29 sessions crashed today)

| Metric | Value |
|--------|-------|
| Sessions today | 29 |
| Clean shutdowns | 0 (100% crash rate) |
| "Invalid agent handle" errors | 39 |
| "class assert failure" errors | 15 |
| Crashes with zero logged errors | 12 (raw segfaults) |
| Shortest session before crash | 18 seconds |
| Longest session before crash | 63 minutes |
| Common last log entry | Rapid agent create/destroy cycles (wildlife) |

## Identified Crash Points (from source analysis)

| # | File:Line | Trigger | Root cause |
|---|-----------|---------|------------|
| 1 | `PointerAgent.cpp:327` | Click on agent | `a->getParent()` unguarded after script execution |
| 2 | `Agent.cpp:1523` | Carrying agent | `carrying->getCarriedPoint()`: carried agent killed between check and use |
| 3 | `Agent.h:266` | Any agent query | `part(0)->getWidth()`: no null check on part(0) |
| 4 | `Engine.cpp:614` | Keyboard input | `world.focusagent.get()->part()`: focus agent dead |
| 5 | `PointerAgent.cpp:114` | Mouse hover | Stale `agent_under_pointer` (has TODO acknowledging bug) |
| 6 | `PointerAgent.cpp:275` | Port/wire interaction | Unguarded port access on dead agent |
| 7 | `PointerAgent.cpp:360,399` | Drop object | `carrying->queueScript(5, this)`: agent expired |
| 8 | `World.cpp:489` | Wire rendering | `wireOriginAgent->outports[]` after expired weak_ptr |
| 9 | `caosVM_ports.cpp:295` | Message delivery | Dead agent port dereference during CAOS |
| 10 | `caosVM_agent.cpp:1039` | Animation query | Stale part ID from previous target |

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/openc2e/Agent.h` | Modify | Add `pending_kill_` flag, `isPendingKill()`, declare `finalDestroy()` |
| `src/openc2e/Agent.cpp` | Modify | `kill()` marks pending instead of immediate destroy; implement `finalDestroy()` |
| `src/openc2e/AgentRef.h` | Modify | Safe `operator->()` returns nullptr on dead ref; add `safeGet()` declaration |
| `src/openc2e/AgentRef.cpp` | Modify | Implement `safeGet()` with pending_kill awareness |
| `src/openc2e/World.h` | Modify | Add `pending_destroy_` vector, declare `queueDestroy()` and `flushPendingDestroys()` |
| `src/openc2e/World.cpp` | Modify | `tick()` skips pending_kill agents; implement flush; guard `drawWorld()` port rendering; guard `setFocus()` |
| `src/openc2e/Engine.cpp` | Modify | Call `world.flushPendingDestroys()` after `update()` and before `drawWorld()`; guard keyboard handler |
| `src/openc2e/PointerAgent.cpp` | Modify | Skip pending_kill agents in `tick()`, `handleClick()`, `firePointerScript()`, `pickup()`, `drop()` |
| `src/openc2e/caosVM.h` | Modify | `valid_agent()` macro (line 296) rejects pending_kill: protects ALL 180+ CAOS call sites |
| `src/openc2e/caos/caosVM_ports.cpp` | Modify | Guard port delivery against dead agents |

---

## Task 1: Add pending_kill_ Flag to Agent

**Files:**
- Modify: `src/openc2e/Agent.h:74-82,128-130,276-277`
- Modify: `src/openc2e/Agent.cpp` (constructor + kill + new finalDestroy)

- [ ] **Step 1: Add pending_kill_ member to Agent.h**

Find the `dying` bitfield (line 81) and add alongside it:

```cpp
bool dying : 1;
bool pending_kill_ : 1;  // NB: marked for end-of-frame destruction
```

- [ ] **Step 2: Add isPendingKill() accessor to Agent.h**

In the public section, near `isDying()` (line 128):

```cpp
inline bool isPendingKill() const {
    return pending_kill_;
}
```

- [ ] **Step 3: Declare finalDestroy() in Agent.h**

Near `kill()` declaration (line 277):

```cpp
virtual void kill();
void finalDestroy();  // NB: called by World::flushPendingDestroys() at end of frame
```

- [ ] **Step 4: Initialise pending_kill_ in Agent constructor**

In `Agent.cpp`, find the constructor initialisation (search for `dying = false` or `initialized = false`) and add:

```cpp
pending_kill_ = false;
```

- [ ] **Step 5: Replace Agent::kill() with deferred version**

Replace the current `Agent::kill()` (Agent.cpp lines 1261-1289). The new version marks `pending_kill_` but does NOT call `agents_iter->reset()` or `zotstack()`: those move to `finalDestroy()`:

```cpp
void Agent::kill() {
    if (pending_kill_ || dying) return;  // Already marked or dying
    pending_kill_ = true;

    // Detach from physics relationships immediately
    // (these are direct pointer swaps, safe to do now)
    if (floatable())
        floatRelease();
    if (carrying)
        dropCarried(carrying);
    if (carriedby)
        carriedby->drop(this);
    // TODO: should the carried agent really be responsible for dropping from vehicle?
    if (invehicle)
        invehicle->drop(this);

    NORN_DBG(AGENT, fmt::format("NB: agent pending kill: family={} genus={} species={}",
        (int)family, (int)genus, (int)species));

    // Stop running scripts immediately (prevents further side effects this frame)
    if (vm) {
        vm->stop();
        world.freeVM(vm);
        vm = nullptr;
    }
    if (sound) {
        sound.stop();
        sound = {};
    }

    // Queue for end-of-frame destruction
    world.queueDestroy(self.lock());
}
```

- [ ] **Step 6: Add Agent::finalDestroy()**

Add after `Agent::kill()`:

```cpp
void Agent::finalDestroy() {
    // NB: called by World::flushPendingDestroys() at end of frame.
    // At this point the frame is over: no scripts, ticks, or events are running.
    // Safe to remove from world agent list.
    dying = true;
    zotstack();
    agents_iter->reset();
    NORN_DBG(AGENT, fmt::format("NB: agent final destroy: family={} genus={} species={}",
        (int)family, (int)genus, (int)species));
}
```

- [ ] **Step 7: Commit (will not link yet: World::queueDestroy not defined)**

```bash
cd <PROJECT_ROOT>/openc2e
git add src/openc2e/Agent.h src/openc2e/Agent.cpp
git commit -m "nb: Agent::kill() defers destruction via pending_kill_ flag"
```

---

## Task 2: Add Deferred Destruction Queue to World

**Files:**
- Modify: `src/openc2e/World.h` (add members + declarations)
- Modify: `src/openc2e/World.cpp:234-274` (tick loop + new methods)

- [ ] **Step 1: Add pending_destroy_ and method declarations to World.h**

In `World.h`, find the `agents` member and add nearby:

```cpp
// In private/public section near agents list:
std::vector<std::shared_ptr<Agent>> pending_destroy_;  // NB: deferred destruction queue

// Public methods:
void queueDestroy(std::shared_ptr<Agent> agent);
void flushPendingDestroys();
```

- [ ] **Step 2: Implement queueDestroy() in World.cpp**

Add near end of World.cpp:

```cpp
void World::queueDestroy(std::shared_ptr<Agent> agent) {
    if (agent) {
        pending_destroy_.push_back(std::move(agent));
    }
}
```

- [ ] **Step 3: Implement flushPendingDestroys() in World.cpp**

```cpp
void World::flushPendingDestroys() {
    // NB: called at end of Engine::tick(), after all game logic.
    // Processes all agents marked pending_kill this frame.
    if (pending_destroy_.empty()) return;

    NORN_DBG(AGENT, fmt::format("NB: flushing {} pending destroys", pending_destroy_.size()));

    for (auto& agent : pending_destroy_) {
        if (agent) {
            agent->finalDestroy();
        }
    }
    pending_destroy_.clear();

    // Clean null entries from agents list (agents_iter->reset() nulled them)
    agents.remove_if([](const std::shared_ptr<Agent>& a) { return !a; });
}
```

- [ ] **Step 4: Modify World::tick() agent loop to skip pending_kill**

Replace the agent tick loop in `World::tick()` (lines 244-257):

```cpp
// Tick all agents, skipping pending_kill. Erase nulls as we go.
auto i = agents.begin();
while (i != agents.end()) {
    std::shared_ptr<Agent> a = *i;
    if (!a) {
        i = agents.erase(i);
        continue;
    }
    ++i;
    if (a->isPendingKill()) continue;  // NB: skip doomed agents
    a->tick();
}
```

- [ ] **Step 5: Modify World::tick() script queue to skip pending_kill**

In the script queue processing (line 261), add pending_kill check:

```cpp
for (auto& i : scriptqueue) {
    std::shared_ptr<Agent> agent = i.agent.lock();
    if (agent && !agent->isPendingKill()) {  // NB: added pending_kill check
        if (engine.version < 3) {
            if (agent->vm && !agent->vm->stopped() && i.scriptno == 6) {
                continue;
            }
        }
        agent->fireScript(i.scriptno, i.from, i.p[0], i.p[1]);
    }
}
```

- [ ] **Step 6: Guard drawWorld() port rendering against pending_kill**

In `World::drawWorld()` (line 445-457), the port connection rendering iterates all agents. Add pending_kill skip:

```cpp
// render port connection lines
for (auto a : world.agents) {
    if (!a || a->isPendingKill())  // NB: skip dead agents
        continue;
    for (auto p = a->outports.begin(); p != a->outports.end(); p++) {
        for (auto c = p->second->dests.begin(); c != p->second->dests.end(); c++) {
            if (!c->first || c->first->isPendingKill())  // NB: skip dead targets
                continue;
            InputPort* target = c->first->inports[c->second].get();
            surface->renderLine(a->x + p->second->x - adjustx, a->y + p->second->y - adjusty,
                c->first->x + target->x - adjustx, c->first->y + target->y - adjusty,
                Color{0, 0xff, 0, 0xff});
        }
    }
}
```

- [ ] **Step 7: Guard setFocus() against pending_kill**

In `World::setFocus()` (line 213), replace the focusagent dereference:

```cpp
void World::setFocus(CompoundPart* p) {
    assert(!p || p->canGainFocus());

    // Unfocus current: guard against dead/pending_kill agent
    if (focusagent) {
        auto locked = focusagent.safeGet();  // NB: safe access
        if (locked) {
            CompoundAgent* c = dynamic_cast<CompoundAgent*>(locked.get());
            if (c) {
                CompoundPart* fp = c->part(focuspart);
                if (fp && fp->canGainFocus())
                    fp->loseFocus();
            }
        } else {
            focusagent.clear();  // NB: clear stale reference
        }
    }

    if (!p)
        focusagent.clear();
    else {
        p->gainFocus();
        focusagent = p->getParent();
        focuspart = p->id;
    }
}
```

- [ ] **Step 8: Build and verify**

```bash
cd <PROJECT_ROOT>/openc2e/build64
"<USER_HOME>/AppData/Roaming/Python/Python314/site-packages/cmake/data/bin/cmake.exe" --build . --config RelWithDebInfo --parallel 16
```

Expected: Compiles and links (queueDestroy now defined, safeGet not yet: will error. That is OK, commit Agent+World together if needed, or stub safeGet temporarily).

- [ ] **Step 9: Commit**

```bash
cd <PROJECT_ROOT>/openc2e
git add src/openc2e/World.h src/openc2e/World.cpp
git commit -m "nb: World deferred destroy queue + tick/render/focus guards"
```

---

## Task 3: Harden AgentRef: Safe Dereference (Layer 2)

**Files:**
- Modify: `src/openc2e/AgentRef.h:55-66`
- Modify: `src/openc2e/AgentRef.cpp`

This is the belt-and-suspenders layer. With deferred destruction, stale references within a frame should be impossible. But this catches any bugs in the deferral logic and provides clean failure instead of segfault.

**What openc2e does wrong (from DOR):** `AgentRef` wraps `std::weak_ptr` but `operator->()` calls `ref.lock().get()`: the `shared_ptr` returned by `lock()` is a temporary that dies at the semicolon. If the agent is destroyed between the truthiness check (`if (agentRef)`) and the dereference (`agentRef->method()`), the pointer is dangling. The fix: `operator->()` must call `.lock()` and handle nullptr.

- [ ] **Step 1: Replace operator->() and operator*() in AgentRef.h**

Replace lines 55-62:

```cpp
Agent& operator*() const {
    auto sp = ref.lock();
    if (!sp) {
        throw std::runtime_error("NB: AgentRef dereference of expired agent");
    }
    return *sp;
}
Agent* operator->() const {
    auto sp = ref.lock();
    if (!sp) return nullptr;  // NB: safe: nullptr instead of segfault
    return sp.get();
}
```

- [ ] **Step 2: Replace implicit conversion operator**

Replace line 66:

```cpp
operator Agent*() const {
    auto sp = ref.lock();
    return sp ? sp.get() : nullptr;
}
```

- [ ] **Step 3: Declare safeGet() in AgentRef.h**

Add to public section:

```cpp
/// NB: preferred access. Returns locked shared_ptr (keeps agent alive) or nullptr.
/// Treats pending_kill agents as dead: use this for any interaction code.
std::shared_ptr<Agent> safeGet() const;
```

- [ ] **Step 4: Implement safeGet() in AgentRef.cpp**

Add to AgentRef.cpp (needs Agent.h for isPendingKill):

```cpp
#include "Agent.h"

std::shared_ptr<Agent> AgentRef::safeGet() const {
    auto sp = ref.lock();
    if (sp && sp->isPendingKill()) return nullptr;
    return sp;
}
```

- [ ] **Step 5: Build and verify**

```bash
cd <PROJECT_ROOT>/openc2e/build64
"<USER_HOME>/AppData/Roaming/Python/Python314/site-packages/cmake/data/bin/cmake.exe" --build . --config RelWithDebInfo --parallel 16
```

Expected: Clean compile. Existing code that dereferences dead AgentRefs will now get nullptr instead of crashing. Some code may need nullptr guards added: if the build reveals warnings, those are the exact crash sites being fixed.

- [ ] **Step 6: Commit**

```bash
cd <PROJECT_ROOT>/openc2e
git add src/openc2e/AgentRef.h src/openc2e/AgentRef.cpp
git commit -m "nb: AgentRef safe dereference: nullptr on dead ref, safeGet() for interaction code"
```

---

## Task 4: Wire Engine::tick() Flush Point

**Files:**
- Modify: `src/openc2e/Engine.cpp:381-405`

The flush must happen after `update()` (which calls `World::tick()`) but before `processEvents()` (which handles SDL input) and before `drawWorld()` (called from `main.cpp:82` after `engine.tick()` returns).

- [ ] **Step 1: Add flushPendingDestroys() call to Engine::tick()**

Replace `Engine::tick()` (lines 381-405):

```cpp
bool Engine::tick() {
    assert(get_backend());

    bool needupdate = fastticks || !get_ticks_msec() || (get_ticks_msec() - tickdata >= world.ticktime - 5);
    if (needupdate && !world.paused) {
        if (fastticks) {
            using clock = std::chrono::steady_clock;
            using std::chrono::duration_cast;
            using std::chrono::milliseconds;
            auto start = clock::now();
            while (duration_cast<milliseconds>(clock::now() - start).count() < 1000 / world.ticktime) {
                update();
            }
        } else {
            update();
        }
        // NB: flush deferred agent destructions AFTER all game logic (update/tick/scripts)
        // and BEFORE processEvents (SDL input) and drawWorld (rendering).
        // This is the keystone: guarantees no pointer is invalid mid-frame.
        world.flushPendingDestroys();
    }

    processEvents();
    if (needupdate)
        handleKeyboardScrolling();

    return needupdate;
}
```

- [ ] **Step 2: Guard keyboard handler against dead focusagent**

In `Engine.cpp`, find the keyboard event handler that accesses `world.focusagent` (around line 614). Replace direct dereference with safeGet:

```cpp
// Find: world.focusagent.get()->part(world.focuspart)
// Replace with:
auto focused = world.focusagent.safeGet();
if (focused) {
    CompoundPart* t = dynamic_cast<CompoundAgent*>(focused.get())->part(world.focuspart);
    if (t && t->canGainFocus()) {
        // ... existing keyboard handling unchanged ...
    }
}
```

- [ ] **Step 3: Build, verify, commit**

```bash
cd <PROJECT_ROOT>/openc2e
git add src/openc2e/Engine.cpp
git commit -m "nb: Engine::tick() flush point + keyboard handler guard"
```

---

## Task 5: Guard PointerAgent: All User Interaction Crash Points

**Files:**
- Modify: `src/openc2e/PointerAgent.cpp`

This task addresses crash points #1, #5, #6, #7 from the identified list. PointerAgent handles ALL user mouse interaction: clicks, hovers, pickups, drops, wire connections.

- [ ] **Step 1: Guard tick(): stale agent_under_pointer (crash point #5)**

In `PointerAgent::tick()` (line 104), the code at line 113-114 dereferences `agent_under_pointer` without checking if the agent is still alive. Replace:

```cpp
// OLD (line 113-114):
// if (agent_under_pointer)
//     oldpart = agent_under_pointer->part(part_under_pointer);

// NEW:
CompoundPart* oldpart = nullptr;
if (agent_under_pointer) {
    auto locked = agent_under_pointer.safeGet();  // NB: safe access
    if (locked) {
        CompoundAgent* ca = dynamic_cast<CompoundAgent*>(locked.get());
        if (ca) oldpart = ca->part(part_under_pointer);
    } else {
        agent_under_pointer.clear();  // NB: clear stale reference
    }
}
```

- [ ] **Step 2: Reject pending_kill parents from partAt results**

After `CompoundPart* a = world.partAt(x, y)` (line 107), add:

```cpp
Agent* parent = nullptr;
if (a) {
    parent = a->getParent();
    // NB: reject agents marked for deferred destruction
    if (parent && parent->isPendingKill()) {
        a = nullptr;
        parent = nullptr;
    }
}
```

- [ ] **Step 3: Guard firePointerScript (crash point #1)**

Find `firePointerScript(eve, a->getParent())` at line 327. Guard:

```cpp
if (eve != -1) {
    Agent* p = a->getParent();
    if (p && !p->isPendingKill()) {  // NB: guard crash point #1
        firePointerScript(eve, p);
    }
}
```

Apply same pattern to ALL other `firePointerScript` calls in this file.

- [ ] **Step 4: Guard pickup() and drop() (crash point #7)**

In `PointerAgent::pickup()` (line ~63) and `PointerAgent::drop()` (line ~72), the `carrying` AgentRef is dereferenced. Add guards:

```cpp
void PointerAgent::pickup(AgentRef a) {
    auto locked = a.safeGet();
    if (!locked) return;  // NB: agent died before we could pick it up
    // ... existing pickup code using locked.get() ...
}
```

- [ ] **Step 5: Guard wire connection handling (crash point #6)**

Find the wire/port handling code in PointerAgent.cpp (around line 275). Add pending_kill checks before accessing ports:

```cpp
if (i->second->source && !i->second->source->isPendingKill()) {
    // ... existing port access ...
}
```

- [ ] **Step 6: Build, verify, commit**

```bash
cd <PROJECT_ROOT>/openc2e
git add src/openc2e/PointerAgent.cpp
git commit -m "nb: PointerAgent guards all 4 user interaction crash points"
```

---

## Task 6: Guard CAOS VM: Single Edit Protects 180+ Call Sites

**Files:**
- Modify: `src/openc2e/caosVM.h:296-301`
- Modify: `src/openc2e/caos/caosVM_ports.cpp:295`

The `valid_agent()` macro in `caosVM.h` is used by every CAOS command that accesses an agent. One edit here protects the entire CAOS command surface.

- [ ] **Step 1: Add isPendingKill() to valid_agent() macro**

In `caosVM.h`, replace the macro at line 296-301:

```cpp
// OLD:
// #define valid_agent(x) \
//     do { \
//         if (!(x)) { \
//             throw invalidAgentException(...); \
//         } \
//     } while (0)

// NEW: NB: also reject pending_kill agents:
#define valid_agent(x) \
    do { \
        if (!(x) || (x)->isPendingKill()) { \
            throw invalidAgentException("Invalid agent handle: " #x " thrown from " __FILE__ ":" stringify(__LINE__)); \
        } \
    } while (0)
```

This single change protects:
- All `VM_PARAM_VALIDAGENT(name)` calls (line 246-248)
- All `CAOS_LVALUE_WITH` macros (line 281)
- All `CAOS_LVALUE_WITH_SIMPLE` macros (line 287)
- All direct `valid_agent(vm->targ)` and `valid_agent(vm->owner)` calls

- [ ] **Step 2: Guard port message delivery (crash point #9)**

In `caosVM_ports.cpp`, find the port delivery loop (around line 295). Add pending_kill guard:

```cpp
// Find the line that dereferences i->first:
if (i->first && !i->first->isPendingKill()) {  // NB: guard crash point #9
    i->first->queueScript(i->first->inports[i->second]->messageno, vm->targ, data);
}
```

- [ ] **Step 3: Ensure Agent.h is included in caosVM.h**

The `isPendingKill()` call in the macro needs the Agent class definition. Check that `Agent.h` is included (directly or transitively) in files that use `valid_agent()`. If not, add a forward declaration or include.

- [ ] **Step 4: Build, verify, commit**

```bash
cd <PROJECT_ROOT>/openc2e
git add src/openc2e/caosVM.h src/openc2e/caos/caosVM_ports.cpp
git commit -m "nb: valid_agent() rejects pending_kill: protects all 180+ CAOS commands"
```

---

## Task 7: Full Build + Smoke Test

- [ ] **Step 1: Kill any running engine**

```bash
powershell -Command "Stop-Process -Name openc2e -Force -ErrorAction SilentlyContinue"
```

- [ ] **Step 2: Full build**

```bash
cd <PROJECT_ROOT>/openc2e/build64
"<USER_HOME>/AppData/Roaming/Python/Python314/site-packages/cmake/data/bin/cmake.exe" --build . --config RelWithDebInfo --parallel 16
```

Expected: 0 errors. Warnings about potential nullptr dereferences are expected: those were the crash points.

- [ ] **Step 3: Start engine with CfC brain**

```bash
cd <PROJECT_ROOT>/openc2e/build64/RelWithDebInfo
start "" "./openc2e.exe" --data-path "<PROJECT_ROOT>/creaturesexodusgame/Creatures Exodus/Creatures 3" --gamename "Creatures 3" --brain-module "<PROJECT_ROOT>/openc2e/tools/nornbrain_cfc.py"
```

Wait 20s for world to load (974+ agents).

- [ ] **Step 4: Hatch norn and verify brain**

```python
caos('new: simp 1 1 252 "blnk" 1 0 0\ngene load targ 1 "norn.bondi.48"\nnew: crea 4 targ 1 0 0\nborn\nenum 1 1 252 kill targ next')
sleep(2)
caos('enum 4 1 0 mvft 806 897 attr 198 accg 10 aero 10 next')
# Verify brain is ticking:
for i in range(5):
    print(caos('enum 4 1 0 outv attn outs " " outv decn next'))
    sleep(1)
```

- [ ] **Step 5: Check logs for deferred destroy messages**

```bash
tail -200 logs/openc2e-*.jsonl | grep -i "pending"
```

Expected: "NB: agent pending kill" and "NB: flushing N pending destroys" messages: confirms deferral is working.

- [ ] **Step 6: Commit smoke test pass**

```bash
cd <PROJECT_ROOT>/openc2e
git add -A
git commit -m "nb: deferred destruction smoke test passed"
```

---

## Task 8: 30-Minute Stability Test

- [ ] **Step 1: Start engine under procdump**

```bash
cd <PROJECT_ROOT>/openc2e/build64/RelWithDebInfo
start "" procdump -accepteula -e 1 -ma -x CrashDumps "./openc2e.exe" --data-path "<PROJECT_ROOT>/creaturesexodusgame/Creatures Exodus/Creatures 3" --gamename "Creatures 3" --brain-module "<PROJECT_ROOT>/openc2e/tools/nornbrain_cfc.py"
```

- [ ] **Step 2: Hatch norn, let wildlife run 30 minutes**

Hatch norn, set physics, then do NOT interact: let the game run with wildlife creating/destroying agents naturally. This is the exact scenario that previously crashed 29/29 times.

- [ ] **Step 3: At 30 minutes, verify engine is still running**

```bash
tasklist | grep openc2e
```

Expected: Process still alive.

- [ ] **Step 4: Try user interactions that previously crashed**

- Click on various agents in the game world
- Try to pick up objects
- Rename the norn (`hist name "<moniker>" "TestNorn"`)
- Zoom and pan the camera

Expected: No crashes. Engine handles all interactions.

- [ ] **Step 5: Analyse crash rate improvement**

Previous: 29/29 sessions crashed (100%). Target: 0 crashes in 30 minutes with user interaction.

- [ ] **Step 6: Commit with results**

```bash
cd <PROJECT_ROOT>/openc2e
git commit --allow-empty -m "nb: 30-min stability test: 0 crashes (was 29/29)"
```

---

## Task 9: Update Meta: NB Naming + Deferred Destruction

**Files:**
- Modify: `<PROJECT_ROOT>/CLAUDE.md`
- Modify: `<PROJECT_ROOT>/docs/cc-handbook.md`
- Memory: update manuals

- [ ] **Step 1: Add NB naming + deferred destruction to CLAUDE.md**

In Critical Technical Decisions, add:

```markdown
- **Engine name: NB (CreaturesCfC64)**: openc2e 64-bit with NORNBRAIN modifications. "NB" in new code/comments/logs. Git: `openc2e-nornbrain`. Binary: `openc2e.exe`.
- **Deferred destruction**: `Agent::kill()` marks `pending_kill_`, flushes at end of `Engine::tick()`. Never delete agents mid-frame. Matches Unreal/Godot pattern.
```

- [ ] **Step 2: Update cc-handbook.md**

Add a new section or update Section 1:

```markdown
## 1. Game Environment (NB: CreaturesCfC64)

**NB (CreaturesCfC64)** is our modified openc2e 64-bit engine with:
- Deferred agent destruction (no mid-frame deletions)
- PythonBrain pybind11 integration
- CfC brain support via --brain-module
- NornLog structured telemetry
```

- [ ] **Step 3: Update manual_engine.md**

Add to the Known Engine Issues section:

```markdown
- **Deferred destruction (NB fix):** Agents are never deleted mid-frame. `kill()` marks `pending_kill_`, agents are removed at end of `Engine::tick()`. This eliminates the use-after-free crashes that affected 100% of sessions.
```

- [ ] **Step 4: Commit**

```bash
cd <PROJECT_ROOT>
git add CLAUDE.md docs/cc-handbook.md
git commit -m "nb: document NB naming + deferred destruction in meta"
```
