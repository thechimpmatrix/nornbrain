# Pluggable Python Brain for openc2e: Design Spec

**Date:** 2026-03-31
**Status:** Approved

## Purpose

Make openc2e's brain architecture pluggable so any Python module can replace the SVRule brain at runtime. The plumbing: not the brain architecture. Configurable via `--brain-module path/to/brain.py`. Default remains SVRule when no module is specified.

## Non-Goals

- Designing the CfC brain architecture (separate concern)
- Implementing SOUL command (not needed: we replace the brain class directly)
- Network protocol between Python and C++ (pybind11 is in-process)
- Training infrastructure
- Monitor/dashboard integration (existing monitor works once the Python brain emits data)

## Architecture

### Brain Class Hierarchy

```
c2eBrain (virtual base)
  ├── c2eSVRuleBrain : c2eBrain    (default: current SVRule implementation, renamed)
  └── PythonBrain : c2eBrain       (new: delegates tick() to Python via pybind11)
```

The existing `c2eBrain` class becomes the abstract base. Its current implementation moves to `c2eSVRuleBrain`. `PythonBrain` is a new subclass that loads a Python module and calls it each tick.

### Python Brain Interface

Any Python module passed to `--brain-module` must implement:

```python
def init(lobe_info: dict) -> None:
    """Called once when the creature is created.
    
    lobe_info = {
        "lobes": {
            "driv": {"count": 20, "id": "driv"},
            "visn": {"count": 40, "id": "visn"},
            ...
        },
        "n_chemicals": 256,
    }
    """
    pass

def tick(inputs: dict) -> dict:
    """Called every brain tick (~4 game ticks).
    
    inputs = {
        "lobes": {
            "driv": [float, ...],    # 20 drive values
            "visn": [float, ...],    # 40 vision values
            "smel": [float, ...],    # 40 smell values
            "verb": [float, ...],    # 17 verb values
            "noun": [float, ...],    # 40 noun values
            "sitn": [float, ...],    # 9 situation values
            "detl": [float, ...],    # 11 detail values
            "resp": [float, ...],    # 20 response values
            "prox": [float, ...],    # 20 proximity values
            "stim": [float, ...],    # 40 stimulus values
        },
        "chemicals": [float] * 256,
        "tick": int,
    }
    
    Must return:
    {
        "attention": int,     # winner index 0-39
        "decision": int,      # winner index 0-13
    }
    """
    pass
```

That's the complete contract. Everything else (CfC architecture, hidden states, LTM, training, telemetry) lives inside the Python module and is invisible to the engine.

### Data Flow Per Tick

```
Game loop (Engine::tick())
  └── c2eCreature::tickBrain()          [every 4 game ticks]
        ├── Sensory Faculty populates input lobes (visn, driv, smel, etc.)
        ├── brain->tick()
        │     ├── [SVRuleBrain] Run SVRules on all lobes/tracts
        │     └── [PythonBrain]
        │           ├── Gather neuron[0] from each input lobe → dict
        │           ├── Gather chemicals[0..255] → list
        │           ├── Call Python module.tick(inputs_dict)
        │           ├── Read attention/decision from return dict
        │           ├── Set attn lobe spare neuron = attention winner
        │           └── Set decn lobe spare neuron = decision winner
        └── Motor Faculty reads attn/decn spare neurons, fires scripts
```

### C++ Changes Required

#### 1. `c2eBrain.h`: Make virtual

Current:
```cpp
class c2eBrain {
public:
    void tick();
    void init();
    void processGenes();
    c2eLobe* getLobeById(std::string id);
    // ...
};
```

Changed to:
```cpp
class c2eBrain {
public:
    virtual ~c2eBrain() = default;
    virtual void tick();
    virtual void init();
    virtual void processGenes();
    c2eLobe* getLobeById(std::string id);
    // ... (non-virtual accessors stay the same)
};
```

Only `tick()`, `init()`, `processGenes()` become virtual. Lobe access methods stay non-virtual: PythonBrain still uses the real lobe data structures (it reads neuron values from them and writes spare neurons back).

#### 2. `PythonBrain.h` / `PythonBrain.cpp`: New files

```cpp
class PythonBrain : public c2eBrain {
public:
    PythonBrain(c2eCreature* parent, const std::string& module_path);
    ~PythonBrain() override;
    
    void tick() override;
    void init() override;
    void processGenes() override;

private:
    py::module_ brain_module_;
    py::object tick_fn_;
    py::object init_fn_;
    std::string module_path_;
    
    py::dict gather_inputs();
    void apply_outputs(const py::dict& result);
};
```

`processGenes()` still calls the base implementation to create lobes from genome genes: the PythonBrain needs the lobe data structures to exist (for reading sensory inputs and writing outputs). It just doesn't run SVRules on them.

`tick()`:
1. Call `c2eBrain::tick()`: NO. Skip SVRule processing entirely.
2. Gather neuron state[0] from each input lobe into a Python dict.
3. Gather all 256 chemicals from the creature.
4. Call `tick_fn_(inputs_dict)`.
5. Read `attention` and `decision` from the return dict.
6. Write to the output lobes' spare neurons.

`init()`:
1. Call `c2eBrain::init()`: YES. Initialize lobe data structures from genome.
2. Build lobe_info dict.
3. Call `init_fn_(lobe_info)`.

#### 3. `Creature.cpp` (or `c2eCreature.cpp`): Conditional construction

Current (approximately):
```cpp
brain = std::make_unique<c2eBrain>(this);
```

Changed to:
```cpp
std::string brain_module = engine.getBrainModulePath();
if (!brain_module.empty()) {
    brain = std::make_unique<PythonBrain>(this, brain_module);
} else {
    brain = std::make_unique<c2eBrain>(this);
}
```

`Engine` stores the `--brain-module` path from command-line args.

#### 4. `CMakeLists.txt`: Add pybind11

```cmake
# Find Python and pybind11
find_package(Python3 REQUIRED COMPONENTS Interpreter Development)
find_package(pybind11 CONFIG)
if(NOT pybind11_FOUND)
    # Fetch pybind11 if not installed
    include(FetchContent)
    FetchContent_Declare(pybind11
        GIT_REPOSITORY https://github.com/pybind/pybind11.git
        GIT_TAG v2.12.0
    )
    FetchContent_MakeAvailable(pybind11)
endif()

# Link to openc2e target
target_link_libraries(openc2e PRIVATE pybind11::embed Python3::Python)
```

#### 5. `Engine.cpp` / `Engine.h`: Store brain module path

Add `--brain-module` to command-line args (already using cxxopts):
```cpp
options.add_options()
    ("brain-module", "Path to Python brain module", cxxopts::value<std::string>()->default_value(""))
;
```

Store in `Engine::brain_module_path_`. Accessor: `Engine::getBrainModulePath()`.

#### 6. `main.cpp`: Initialize Python interpreter

Before the engine starts:
```cpp
#include <pybind11/embed.h>
py::scoped_interpreter guard{};  // Start Python interpreter
```

This must happen once, early, and the guard must live for the engine's lifetime.

### What the Python Module Looks Like (Example)

```python
# nornbrain_cfc.py: example brain module for openc2e

import torch
from multi_lobe_brain import MultiLobeBrain

brain = None

def init(lobe_info: dict):
    global brain
    brain = MultiLobeBrain()
    brain.load_weights("brain_weights_multi_lobe.pt")

def tick(inputs: dict) -> dict:
    global brain
    raw_inputs = _convert_lobes_to_tensors(inputs["lobes"])
    raw_inputs["chemicals"] = torch.tensor([inputs["chemicals"]], dtype=torch.float32)
    
    output = brain.tick(raw_inputs)
    
    return {
        "attention": output.attention_winner,
        "decision": output.decision_winner,
    }

def _convert_lobes_to_tensors(lobes: dict) -> dict:
    return {k: torch.tensor([v], dtype=torch.float32) for k, v in lobes.items()}
```

This is our existing `MultiLobeBrain` with a thin wrapper. No changes to the brain code itself.

### Build & Run

```bash
# Build openc2e with Python brain support
cd <PROJECT_ROOT>/openc2e/build64
cmake .. -G "Visual Studio 17 2022" -A x64 \
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
    -DPython3_ROOT_DIR=C:/Python314
cmake --build . --config RelWithDebInfo --parallel 16

# Run with default SVRule brain (unchanged behaviour)
./openc2e.exe --data-path "<PROJECT_ROOT>/creaturesexodusgame/Creatures Exodus/Creatures 3" \
    --gamename "Creatures 3"

# Run with Python CfC brain
./openc2e.exe --data-path "<PROJECT_ROOT>/creaturesexodusgame/Creatures Exodus/Creatures 3" \
    --gamename "Creatures 3" \
    --brain-module "<PROJECT_ROOT>/phase2-bridge/nornbrain_cfc.py"
```

### Testing Strategy

1. **Build test:** openc2e compiles with pybind11 linked
2. **No-module test:** `openc2e` without `--brain-module` behaves identically to before (SVRule brain)
3. **Dummy module test:** `--brain-module dummy_brain.py` where dummy_brain always returns `{"attention": 11, "decision": 1}` (look at food, push). Creature should continuously push food.
4. **CfC module test:** `--brain-module nornbrain_cfc.py` loads the multi-lobe brain and runs it. Compare behaviour to the old CAOS bridge approach.
5. **Performance test:** Measure tick time with Python brain vs SVRule brain. Expect Python brain to be slower (torch inference) but faster than CAOS bridge (no shared memory round-trip).

### Success Criteria

1. `openc2e --brain-module brain.py` boots, loads a world, and a creature makes decisions driven by the Python module
2. The Python `tick()` function receives real sensory data from the engine
3. The creature's biochemistry runs independently (chemicals change, drives rise/fall)
4. The creature's motor system executes the Python brain's decisions (walks, eats, etc.)
5. No SVRule code runs when PythonBrain is active
6. Default mode (no flag) is identical to current openc2e behaviour
7. The monitor can connect to the Python brain's telemetry (if the Python module emits it via a separate channel)

### What This Enables

Once the plumbing works, we can:
- Swap brain architectures by changing the Python module (no recompile)
- Train offline, load weights, test immediately
- Add telemetry/monitoring inside the Python module
- Compare SVRule vs CfC on the same creature in the same world
- Eventually add LTM, emotional gating, online RL: all in Python
- The creature experiences a real simulated reality through C3's biochemistry, ecology, and physics
