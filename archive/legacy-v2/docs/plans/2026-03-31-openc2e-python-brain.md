# Pluggable Python Brain for openc2e: Implementation Plan


**Goal:** Make openc2e's brain swappable at runtime: `--brain-module path/to/brain.py` loads a Python CfC brain via pybind11 that replaces the SVRule brain while keeping all other creature systems (sensory, motor, biochemistry) running natively.

**Architecture:** Make `c2eBrain` virtual, create `PythonBrain` subclass that embeds Python via pybind11, conditionally instantiate based on command-line flag. Python module implements `init(lobe_info)` and `tick(inputs) -> {attention, decision}`.

**Tech Stack:** C++17, pybind11 (embedded), Python 3.14, CMake, Visual Studio 2022

**Spec:** `docs/superpowers/specs/2026-03-31-openc2e-python-brain-design.md`

**Repo:** `<PROJECT_ROOT>/openc2e/` branch `openc2e-nornbrain`

**Build:**
```bash
cd <PROJECT_ROOT>/openc2e/build64
"<USER_HOME>/AppData/Roaming/Python/Python314/site-packages/cmake/data/bin/cmake.exe" --build . --config RelWithDebInfo --parallel 16
```

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `src/openc2e/creatures/c2eBrain.h` | **Modify** | Make tick/init/processGenes virtual, add virtual destructor |
| `src/openc2e/creatures/PythonBrain.h` | **Create** | PythonBrain class declaration |
| `src/openc2e/creatures/PythonBrain.cpp` | **Create** | PythonBrain implementation: pybind11 calls |
| `src/openc2e/creatures/Creature.cpp` | **Modify** | Conditional brain creation based on engine flag |
| `src/openc2e/Engine.h` | **Modify** | Add brain_module_path_ member + accessor |
| `src/openc2e/Engine.cpp` | **Modify** | Add --brain-module CLI arg, store path |
| `src/openc2e/main.cpp` | **Modify** | Initialize Python interpreter |
| `CMakeLists.txt` | **Modify** | Add pybind11 dependency, link Python |
| `tools/dummy_brain.py` | **Create** | Minimal test brain (always returns push→food) |
| `tools/nornbrain_cfc.py` | **Create** | Wrapper around MultiLobeBrain for openc2e |

---

## Task 1: Add pybind11 to CMake Build

Get pybind11 compiling and linked before touching any C++ code.

**Files:**
- Modify: `CMakeLists.txt`

- [ ] **Step 1: Install pybind11**

```bash
pip install pybind11
```

Verify:
```bash
python -c "import pybind11; print(pybind11.get_cmake_dir())"
```

- [ ] **Step 2: Add pybind11 to CMakeLists.txt**

In `CMakeLists.txt`, find the existing `find_package(Python REQUIRED)` at line 60. Replace it with:

```cmake
find_package(Python3 REQUIRED COMPONENTS Interpreter Development)
find_package(pybind11 CONFIG HINTS "${Python3_SITELIB}/pybind11/share/cmake/pybind11")
if(NOT pybind11_FOUND)
    message(STATUS "pybind11 not found via config, trying pip location")
    execute_process(
        COMMAND ${Python3_EXECUTABLE} -c "import pybind11; print(pybind11.get_cmake_dir())"
        OUTPUT_VARIABLE PYBIND11_CMAKE_DIR
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
    find_package(pybind11 CONFIG HINTS "${PYBIND11_CMAKE_DIR}")
endif()
```

Find `target_link_libraries(openc2e openc2e_core openc2e_sdlbackend)` at line 350. Change to:

```cmake
target_link_libraries(openc2e openc2e_core openc2e_sdlbackend pybind11::embed)
```

Also add pybind11::embed to the openc2e_core library (where creature code lives). Find the `target_link_libraries` for openc2e_core and add `pybind11::embed`.

- [ ] **Step 3: Build and verify**

```bash
cd <PROJECT_ROOT>/openc2e/build64
"<USER_HOME>/AppData/Roaming/Python/Python314/site-packages/cmake/data/bin/cmake.exe" .. -G "Visual Studio 17 2022" -A x64 -DCMAKE_POLICY_VERSION_MINIMUM=3.5
"<USER_HOME>/AppData/Roaming/Python/Python314/site-packages/cmake/data/bin/cmake.exe" --build . --config RelWithDebInfo --parallel 16
```

Expected: Builds without errors. pybind11 found and linked.

- [ ] **Step 4: Commit**

```bash
cd <PROJECT_ROOT>/openc2e
git add CMakeLists.txt
git commit -m "build: add pybind11 dependency for Python brain embedding"
```

---

## Task 2: Make c2eBrain Virtual

Make the brain class polymorphic so PythonBrain can override tick/init/processGenes.

**Files:**
- Modify: `src/openc2e/creatures/c2eBrain.h`

- [ ] **Step 1: Add virtual to c2eBrain class**

In `c2eBrain.h` (lines 127-145), change the class declaration:

Old:
```cpp
class c2eBrain {
  protected:
	class c2eCreature* parent;
	std::multiset<c2eBrainComponent*, c2ebraincomponentorder> components;

  public:
	std::map<std::string, std::unique_ptr<c2eLobe>> lobes;
	std::vector<std::unique_ptr<c2eTract>> tracts;

	c2eBrain(c2eCreature* p);
	~c2eBrain();
	void processGenes();
	void tick();
	void init();
	c2eLobe* getLobeById(std::string id);
	c2eLobe* getLobeByTissue(unsigned int id);
	c2eCreature* getParent() { return parent; }
};
```

New:
```cpp
class c2eBrain {
  protected:
	class c2eCreature* parent;
	std::multiset<c2eBrainComponent*, c2ebraincomponentorder> components;

  public:
	std::map<std::string, std::unique_ptr<c2eLobe>> lobes;
	std::vector<std::unique_ptr<c2eTract>> tracts;

	c2eBrain(c2eCreature* p);
	virtual ~c2eBrain();
	virtual void processGenes();
	virtual void tick();
	virtual void init();
	c2eLobe* getLobeById(std::string id);
	c2eLobe* getLobeByTissue(unsigned int id);
	c2eCreature* getParent() { return parent; }
};
```

Only 3 changes: `virtual ~c2eBrain()`, `virtual void processGenes()`, `virtual void tick()`, `virtual void init()`.

- [ ] **Step 2: Build and verify**

```bash
cd <PROJECT_ROOT>/openc2e/build64
"<USER_HOME>/AppData/Roaming/Python/Python314/site-packages/cmake/data/bin/cmake.exe" --build . --config RelWithDebInfo --parallel 16
```

Expected: Builds clean. All existing tests pass (virtual doesn't break anything).

- [ ] **Step 3: Run openc2e to verify SVRule brain still works**

```bash
cd <PROJECT_ROOT>/openc2e/build64/RelWithDebInfo
./openc2e.exe --data-path "<PROJECT_ROOT>/creaturesexodusgame/Creatures Exodus/Creatures 3" --gamename "Creatures 3"
```

Expected: Identical behaviour to before: creatures walk, eat, make decisions.

- [ ] **Step 4: Commit**

```bash
cd <PROJECT_ROOT>/openc2e
git add src/openc2e/creatures/c2eBrain.h
git commit -m "refactor: make c2eBrain virtual for pluggable brain implementations"
```

---

## Task 3: Add --brain-module Command-Line Argument

Add the flag to Engine so we know at runtime whether to use Python brain.

**Files:**
- Modify: `src/openc2e/Engine.h`
- Modify: `src/openc2e/Engine.cpp`

- [ ] **Step 1: Add member to Engine.h**

In `Engine.h`, add to the private section (near other cmdline_ members):

```cpp
	std::string brain_module_path_;
```

Add to public section:

```cpp
	const std::string& getBrainModulePath() const { return brain_module_path_; }
```

- [ ] **Step 2: Add CLI arg to Engine.cpp parseCommandLine()**

In `Engine.cpp`, find the cxxopts options block (around line 931-943). Add after the existing options:

```cpp
	desc.add_options()("brain-module", "Path to Python brain module (.py file)", cxxopts::value<std::string>(brain_module_path_));
```

- [ ] **Step 3: Build and test**

```bash
cd <PROJECT_ROOT>/openc2e/build64
"<USER_HOME>/AppData/Roaming/Python/Python314/site-packages/cmake/data/bin/cmake.exe" --build . --config RelWithDebInfo --parallel 16
```

Test the flag parses:
```bash
cd <PROJECT_ROOT>/openc2e/build64/RelWithDebInfo
./openc2e.exe --help | grep brain
```

Expected: Shows `--brain-module` in help output.

- [ ] **Step 4: Commit**

```bash
cd <PROJECT_ROOT>/openc2e
git add src/openc2e/Engine.h src/openc2e/Engine.cpp
git commit -m "feat: add --brain-module CLI arg for Python brain path"
```

---

## Task 4: Initialize Python Interpreter in main.cpp

Start the embedded Python interpreter before the engine runs.

**Files:**
- Modify: `src/openc2e/main.cpp`

- [ ] **Step 1: Add pybind11 include and interpreter guard**

At the top of `main.cpp`, add:

```cpp
#include <pybind11/embed.h>
namespace py = pybind11;
```

In `main()`, BEFORE the `try` block (after NornLogger init, around line 47), add:

```cpp
	// Initialize Python interpreter for brain embedding
	// Must be created before any pybind11 calls and live for the engine's lifetime
	py::scoped_interpreter python_guard{};
```

This MUST be before `engine.initialSetup()` because creature creation (which may create PythonBrain) happens during world loading.

- [ ] **Step 2: Build and test**

```bash
cd <PROJECT_ROOT>/openc2e/build64
"<USER_HOME>/AppData/Roaming/Python/Python314/site-packages/cmake/data/bin/cmake.exe" --build . --config RelWithDebInfo --parallel 16
```

Test that openc2e still starts:
```bash
cd <PROJECT_ROOT>/openc2e/build64/RelWithDebInfo
./openc2e.exe --data-path "<PROJECT_ROOT>/creaturesexodusgame/Creatures Exodus/Creatures 3" --gamename "Creatures 3"
```

Expected: Starts normally. Python interpreter initialized but unused.

- [ ] **Step 3: Commit**

```bash
cd <PROJECT_ROOT>/openc2e
git add src/openc2e/main.cpp
git commit -m "feat: initialize embedded Python interpreter in main()"
```

---

## Task 5: Create PythonBrain Class

The core: a brain subclass that calls Python each tick.

**Files:**
- Create: `src/openc2e/creatures/PythonBrain.h`
- Create: `src/openc2e/creatures/PythonBrain.cpp`

- [ ] **Step 1: Create PythonBrain.h**

```cpp
#pragma once

#include "c2eBrain.h"
#include <pybind11/embed.h>
#include <string>

namespace py = pybind11;

class PythonBrain : public c2eBrain {
public:
    PythonBrain(c2eCreature* parent, const std::string& module_path);
    ~PythonBrain() override;

    void processGenes() override;
    void tick() override;
    void init() override;

private:
    std::string module_path_;
    py::module_ brain_module_;
    py::object tick_fn_;
    py::object init_fn_;
    bool python_ready_ = false;

    py::dict gather_inputs();
    void apply_outputs(const py::dict& result);
};
```

- [ ] **Step 2: Create PythonBrain.cpp**

```cpp
#include "PythonBrain.h"
#include "c2eCreature.h"
#include "common/NornLog.h"

#include <pybind11/stl.h>
#include <fmt/format.h>
#include <filesystem>

namespace py = pybind11;

PythonBrain::PythonBrain(c2eCreature* parent, const std::string& module_path)
    : c2eBrain(parent), module_path_(module_path) {
    NORN_INF(ENGINE, fmt::format("PythonBrain: loading module from {}", module_path));
}

PythonBrain::~PythonBrain() {
    NORN_INF(ENGINE, "PythonBrain: destroyed");
}

void PythonBrain::processGenes() {
    // Call base to create lobe data structures from genome
    // We need lobes to exist so we can read sensory inputs and write outputs
    c2eBrain::processGenes();
}

void PythonBrain::init() {
    // Init lobe data structures (base class)
    c2eBrain::init();

    // Load the Python module
    try {
        // Add module directory to Python path
        std::filesystem::path mod_path(module_path_);
        std::string dir = mod_path.parent_path().string();
        std::string mod_name = mod_path.stem().string();

        py::module_ sys = py::module_::import("sys");
        py::list path = sys.attr("path");
        path.attr("insert")(0, dir);

        brain_module_ = py::module_::import(mod_name.c_str());
        tick_fn_ = brain_module_.attr("tick");
        init_fn_ = brain_module_.attr("init");

        // Build lobe info dict for Python init
        py::dict lobe_info;
        py::dict lobes_dict;
        for (auto& [id, lobe] : lobes) {
            py::dict lobe_entry;
            lobe_entry["id"] = id;
            lobe_entry["count"] = static_cast<int>(lobe->getNoNeurons());
            lobes_dict[py::cast(id)] = lobe_entry;
        }
        lobe_info["lobes"] = lobes_dict;
        lobe_info["n_chemicals"] = 256;

        init_fn_(lobe_info);
        python_ready_ = true;
        NORN_INF(ENGINE, fmt::format("PythonBrain: module '{}' loaded, {} lobes",
                                      mod_name, lobes.size()));
    } catch (py::error_already_set& e) {
        NORN_LOG(ERR, ENGINE, fmt::format("PythonBrain: Python error during init: {}", e.what()));
        python_ready_ = false;
    }
}

void PythonBrain::tick() {
    if (!python_ready_) {
        // Fall back to SVRule tick if Python failed
        c2eBrain::tick();
        return;
    }

    try {
        py::dict inputs = gather_inputs();
        py::dict result = tick_fn_(inputs).cast<py::dict>();
        apply_outputs(result);
    } catch (py::error_already_set& e) {
        NORN_LOG(ERR, ENGINE, fmt::format("PythonBrain: Python error during tick: {}", e.what()));
        // Fall back to SVRule for this tick
        c2eBrain::tick();
    }
}

py::dict PythonBrain::gather_inputs() {
    py::dict inputs;
    py::dict lobes_dict;

    // Gather neuron state[0] from each input lobe
    for (auto& [id, lobe] : lobes) {
        py::list neuron_values;
        for (unsigned int n = 0; n < lobe->getNoNeurons(); n++) {
            auto* neuron = lobe->getNeuron(n);
            neuron_values.append(neuron->variables[0]);
        }
        lobes_dict[py::cast(id)] = neuron_values;
    }
    inputs["lobes"] = lobes_dict;

    // Gather all 256 chemicals from the creature
    py::list chemicals;
    for (int i = 0; i < 256; i++) {
        chemicals.append(parent->getChemical(i));
    }
    inputs["chemicals"] = chemicals;

    // Tick counter
    static int tick_count = 0;
    inputs["tick"] = tick_count++;

    return inputs;
}

void PythonBrain::apply_outputs(const py::dict& result) {
    // Read attention and decision winners from Python
    int attn_winner = result["attention"].cast<int>();
    int decn_winner = result["decision"].cast<int>();

    // Write to the attention lobe's spare neuron
    auto* attn_lobe = getLobeById("attn");
    if (attn_lobe) {
        // Set the winning neuron's state high, others low
        for (unsigned int n = 0; n < attn_lobe->getNoNeurons(); n++) {
            auto* neuron = attn_lobe->getNeuron(n);
            neuron->variables[0] = (n == static_cast<unsigned int>(attn_winner)) ? 1.0f : 0.0f;
        }
        attn_lobe->setSpare(attn_winner);
    }

    // Write to the decision lobe's spare neuron
    auto* decn_lobe = getLobeById("decn");
    if (decn_lobe) {
        for (unsigned int n = 0; n < decn_lobe->getNoNeurons(); n++) {
            auto* neuron = decn_lobe->getNeuron(n);
            neuron->variables[0] = (n == static_cast<unsigned int>(decn_winner)) ? 1.0f : 0.0f;
        }
        decn_lobe->setSpare(decn_winner);
    }
}
```

**Note:** `setSpare()` may not exist as a public method on `c2eLobe`. If not, we need to add it or set the spare neuron via the SVRule opcode 31 mechanism. Check during implementation: if `spare` is a protected member, add a public setter:

```cpp
// In c2eBrain.h, add to c2eLobe public section:
void setSpare(unsigned int n) { spare = n; }
```

- [ ] **Step 3: Add PythonBrain.cpp to CMake build**

In `CMakeLists.txt`, find where creature source files are listed (the openc2e_core sources). Add `src/openc2e/creatures/PythonBrain.cpp` to the list.

- [ ] **Step 4: Build**

```bash
cd <PROJECT_ROOT>/openc2e/build64
"<USER_HOME>/AppData/Roaming/Python/Python314/site-packages/cmake/data/bin/cmake.exe" --build . --config RelWithDebInfo --parallel 16
```

- [ ] **Step 5: Commit**

```bash
cd <PROJECT_ROOT>/openc2e
git add src/openc2e/creatures/PythonBrain.h src/openc2e/creatures/PythonBrain.cpp CMakeLists.txt
git commit -m "feat: PythonBrain class: pybind11 bridge from c2eBrain::tick() to Python module"
```

---

## Task 6: Wire PythonBrain into Creature Construction

Conditionally create PythonBrain when --brain-module is specified.

**Files:**
- Modify: `src/openc2e/creatures/Creature.cpp`

- [ ] **Step 1: Add include and conditional construction**

At the top of `Creature.cpp`, add:

```cpp
#include "PythonBrain.h"
#include "Engine.h"
```

Find line 314 where the brain is created:

```cpp
	brain = std::make_unique<c2eBrain>(this);
```

Replace with:

```cpp
	const std::string& brain_module = engine.getBrainModulePath();
	if (!brain_module.empty()) {
		brain = std::make_unique<PythonBrain>(this, brain_module);
	} else {
		brain = std::make_unique<c2eBrain>(this);
	}
```

- [ ] **Step 2: Build and test with NO brain module (default SVRule)**

```bash
cd <PROJECT_ROOT>/openc2e/build64
"<USER_HOME>/AppData/Roaming/Python/Python314/site-packages/cmake/data/bin/cmake.exe" --build . --config RelWithDebInfo --parallel 16

cd RelWithDebInfo
./openc2e.exe --data-path "<PROJECT_ROOT>/creaturesexodusgame/Creatures Exodus/Creatures 3" --gamename "Creatures 3"
```

Expected: Identical behaviour: SVRule brain used by default.

- [ ] **Step 3: Commit**

```bash
cd <PROJECT_ROOT>/openc2e
git add src/openc2e/creatures/Creature.cpp
git commit -m "feat: conditional PythonBrain construction via --brain-module flag"
```

---

## Task 7: Create Test Brain Modules + End-to-End Test

Create a dummy Python brain and our CfC wrapper, then test both.

**Files:**
- Create: `tools/dummy_brain.py`
- Create: `tools/nornbrain_cfc.py`

- [ ] **Step 1: Create dummy_brain.py**

```python
"""Minimal test brain for openc2e PythonBrain integration.
Always decides: push (decision=1) food (attention=11).
"""

def init(lobe_info: dict) -> None:
    print(f"[dummy_brain] init: {len(lobe_info.get('lobes', {}))} lobes, "
          f"{lobe_info.get('n_chemicals', 0)} chemicals")

def tick(inputs: dict) -> dict:
    tick_num = inputs.get("tick", 0)
    if tick_num % 50 == 0:
        drives = inputs.get("lobes", {}).get("driv", [])
        if drives:
            print(f"[dummy_brain] tick {tick_num}: pain={drives[0]:.2f} "
                  f"hunger={drives[1]:.2f}")
    return {
        "attention": 11,   # food
        "decision": 1,     # push (eat)
    }
```

- [ ] **Step 2: Test with dummy brain**

```bash
cd <PROJECT_ROOT>/openc2e/build64/RelWithDebInfo
./openc2e.exe --data-path "<PROJECT_ROOT>/creaturesexodusgame/Creatures Exodus/Creatures 3" --gamename "Creatures 3" --brain-module "<PROJECT_ROOT>/openc2e/tools/dummy_brain.py"
```

Expected:
- Console shows `[dummy_brain] init: 9 lobes, 256 chemicals`
- Every 50 ticks shows drive values
- Creature continuously pushes food (walks to food and activates it)

- [ ] **Step 3: Create nornbrain_cfc.py wrapper**

```python
"""CfC brain wrapper for openc2e PythonBrain integration.
Loads the multi-lobe CfC brain and wraps it in the openc2e interface.
"""

import sys
import os

# Add phase1-prototype and phase2-bridge to path
sys.path.insert(0, "<PROJECT_ROOT>/phase1-prototype")
sys.path.insert(0, "<PROJECT_ROOT>/phase2-bridge")

import torch
from multi_lobe_brain import MultiLobeBrain

brain = None

def init(lobe_info: dict) -> None:
    global brain
    print(f"[nornbrain_cfc] Initializing CfC brain...")
    brain = MultiLobeBrain()
    
    weights_path = "<PROJECT_ROOT>/phase2-bridge/brain_weights_multi_lobe.pt"
    if os.path.exists(weights_path):
        brain.load_weights(weights_path)
        print(f"[nornbrain_cfc] Loaded weights from {weights_path}")
    else:
        print(f"[nornbrain_cfc] No weights found, using random initialization")
    
    print(f"[nornbrain_cfc] Ready: {lobe_info.get('n_chemicals', 0)} chemicals, "
          f"{len(lobe_info.get('lobes', {}))} lobes")

def tick(inputs: dict) -> dict:
    global brain
    lobes = inputs.get("lobes", {})
    chemicals = inputs.get("chemicals", [0.0] * 256)
    
    # Convert to the format MultiLobeBrain expects
    raw_inputs = {}
    for lobe_id, values in lobes.items():
        raw_inputs[lobe_id] = torch.tensor([values], dtype=torch.float32)
    raw_inputs["chemicals"] = torch.tensor([chemicals], dtype=torch.float32)
    raw_inputs["location"] = torch.tensor([[0.0, 0.0]], dtype=torch.float32)
    
    output = brain.tick(raw_inputs)
    
    return {
        "attention": int(output.attention_winner),
        "decision": int(output.decision_winner),
    }
```

- [ ] **Step 4: Test with CfC brain**

```bash
cd <PROJECT_ROOT>/openc2e/build64/RelWithDebInfo
./openc2e.exe --data-path "<PROJECT_ROOT>/creaturesexodusgame/Creatures Exodus/Creatures 3" --gamename "Creatures 3" --brain-module "<PROJECT_ROOT>/openc2e/tools/nornbrain_cfc.py"
```

Expected:
- Console shows CfC initialization
- Creature makes varied decisions (not just push food)
- No crashes or Python errors

- [ ] **Step 5: Commit**

```bash
cd <PROJECT_ROOT>/openc2e
git add tools/dummy_brain.py tools/nornbrain_cfc.py
git commit -m "feat: dummy + CfC brain modules for openc2e Python brain integration"
```

---

## Task 8: Update Desktop Shortcuts + Documentation

Update the shortcuts and docs to reflect the new capability.

**Files:**
- Modify: `<PROJECT_ROOT>/CLAUDE.md`
- Desktop shortcut update

- [ ] **Step 1: Add shortcut for openc2e with Python brain**

```powershell
$WshShell = New-Object -ComObject WScript.Shell
$lnk = $WshShell.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\NORNBRAIN - openc2e CfC Brain.lnk')
$lnk.TargetPath = '<PROJECT_ROOT>\openc2e\build64\RelWithDebInfo\openc2e.exe'
$lnk.Arguments = '--data-path "<PROJECT_ROOT>/creaturesexodusgame/Creatures Exodus/Creatures 3" --gamename "Creatures 3" --brain-module "<PROJECT_ROOT>/openc2e/tools/nornbrain_cfc.py"'
$lnk.WorkingDirectory = '<PROJECT_ROOT>\openc2e\build64\RelWithDebInfo'
$lnk.Save()
```

- [ ] **Step 2: Update CLAUDE.md with new run commands**

- [ ] **Step 3: Commit**

```bash
cd <PROJECT_ROOT>
git add CLAUDE.md
git commit -m "docs: openc2e Python brain integration: shortcuts and run commands"
```
