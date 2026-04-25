# openc2e Data-Driven Fixes: Clean C3 Bootstrap


**Goal:** Make openc2e boot GOG Creatures 3 without errors: clean bootstrap, no missing-file warnings, no script-not-found noise. First clean run of C3 on 64-bit Windows 11.

**Architecture:** Three targeted fixes derived from NornWatch session data (6,086 log entries, 2 ERR + 17 WRN). The CAOS parser gets error-token tolerance so real game .cos files parse cleanly. The image loader gets stub sprites for DS-only files missing from C3 installs. Agent script warnings get downgraded from WRN to DBG since they're engine probing for optional scripts, not real failures.

**Tech Stack:** C++17, gtest, openc2e engine (cmake + VS 2022)

**Build command:**
```bash
cd <PROJECT_ROOT>/openc2e/build64
cmake --build . --config RelWithDebInfo --parallel 16
```

**Test command:**
```bash
cd <PROJECT_ROOT>/openc2e/build64
ctest --build-config RelWithDebInfo --output-on-failure -R "CaosLexer|CaosTest"
```

**Run command (verify live):**
```bash
cd <PROJECT_ROOT>/openc2e/build64/RelWithDebInfo
./openc2e.exe --data-path "<PROJECT_ROOT>/creaturesexodusgame/Creatures Exodus/Creatures 3" --gamename "Creatures 3"
```

**Branch:** `openc2e-nornbrain` in `<PROJECT_ROOT>/openc2e/`

---

## Task 1: CAOS Parser: Skip TOK_ERROR Tokens

The meerk_fix.cos bootstrap script has `scrp 2 15 23 9"` (trailing quote). The lexer correctly produces a TOK_ERROR token for the unclosed string, but the parser keeps it in the token stream and crashes when it tries to get a logical type for it. The original C3 engine is more lenient.

**Root cause:** `caosScript.cpp:271` includes `TOK_ERROR` in the kept-tokens list. When the parser later calls `logicalType()` on it (line 208-209), it throws.

**Fix:** Filter out `TOK_ERROR` tokens during the parse phase (move them to the filtered-out group alongside comments/whitespace/newlines). Log a warning when skipping them so we know what was dropped.

**Files:**
- Modify: `src/openc2e/caosScript.cpp:248-282`
- Test: `src/fileformats/tests/CaosLexerTest.cpp` (lexer test: verify TOK_ERROR still produced)
- Create: `src/openc2e/tests/CaosScriptErrorRecoveryTest.cpp` (parser test: verify error tokens skipped)

### Steps

- [ ] **Step 1: Write the failing test: lexer still produces TOK_ERROR for trailing quote**

This test verifies the lexer's behavior doesn't change: it should still emit TOK_ERROR for the malformed input. Add to `src/fileformats/tests/CaosLexerTest.cpp`:

```cpp
TEST(lexcaos, trailing_quote_after_int) {
	assert_lexcaos("scrp 2 15 23 9\"",
		{
			{caostoken::TOK_WORD, "scrp", 1},
			{caostoken::TOK_WHITESPACE, " ", 1},
			{caostoken::TOK_INT, "2", 1},
			{caostoken::TOK_WHITESPACE, " ", 1},
			{caostoken::TOK_INT, "15", 1},
			{caostoken::TOK_WHITESPACE, " ", 1},
			{caostoken::TOK_INT, "23", 1},
			{caostoken::TOK_WHITESPACE, " ", 1},
			{caostoken::TOK_INT, "9", 1},
			{caostoken::TOK_ERROR, "\"", 1},
			{caostoken::TOK_EOI, 1},
		});
}
```

- [ ] **Step 2: Run test to verify it passes (lexer behavior is already correct)**

```bash
cd <PROJECT_ROOT>/openc2e/build64
cmake --build . --config RelWithDebInfo --parallel 16 -t caoslexer_tests
ctest --build-config RelWithDebInfo --output-on-failure -R CaosLexer
```

Expected: PASS (the lexer already produces TOK_ERROR correctly).

- [ ] **Step 3: Modify caosScript.cpp to filter out TOK_ERROR tokens**

In `src/openc2e/caosScript.cpp`, change the token filtering in `parse()` (around line 248-282). Move `TOK_ERROR` from the kept group to the filtered group, and log a warning:

```cpp
void caosScript::parse(const std::string& caostext) {
	assert(!tokens);
	// run the token parser
	{
		std::vector<caostoken> rawtokens;
		lexcaos(rawtokens, caostext.c_str());

		tokens = std::make_shared<std::vector<caostoken>>();
		size_t index = 0;
		for (auto& t : rawtokens) {
			switch (t.type) {
				case caostoken::TOK_WORD:
					t.data = to_ascii_lowercase(t.data);
					t.index = index++;
					tokens->push_back(t);
					break;
				case caostoken::TOK_BYTESTR:
				case caostoken::TOK_STRING:
				case caostoken::TOK_CHAR:
				case caostoken::TOK_BINARY:
				case caostoken::TOK_INT:
				case caostoken::TOK_FLOAT:
				case caostoken::TOK_EOI:
					t.index = index++;
					tokens->push_back(t);
					break;
				case caostoken::TOK_ERROR:
					// Skip lexer error tokens: the original C3 engine tolerates
					// trailing junk in .cos files (e.g. meerk_fix.cos has scrp 2 15 23 9")
					fmt::print(stderr, "caosScript: skipping lexer error token {:?} at line {}\n", t.data, t.lineno);
					break;
				case caostoken::TOK_COMMENT:
				case caostoken::TOK_WHITESPACE:
				case caostoken::TOK_NEWLINE:
				case caostoken::TOK_COMMA:
					break;
			}
		}
	}
	// ... rest unchanged
```

- [ ] **Step 4: Build and run existing tests**

```bash
cd <PROJECT_ROOT>/openc2e/build64
cmake --build . --config RelWithDebInfo --parallel 16
ctest --build-config RelWithDebInfo --output-on-failure
```

Expected: ALL PASS.

- [ ] **Step 5: Verify live: meerk_fix.cos now loads without errors**

```bash
cd <PROJECT_ROOT>/openc2e/build64/RelWithDebInfo
./openc2e.exe --data-path "<PROJECT_ROOT>/creaturesexodusgame/Creatures Exodus/Creatures 3" --gamename "Creatures 3" &
sleep 5
# Check logs for meerk_fix errors
python -c "
import json
with open('logs/'+ sorted([f for f in __import__('os').listdir('logs/')])[-1]) as f:
    for line in f:
        e = json.loads(line)
        if 'meerk' in e.get('msg','').lower():
            print(e['lvl'], e['msg'][:200])
print('Done: no meerk errors means success')
"
```

Expected: No ERR entries mentioning meerk_fix.cos. The script should parse and load cleanly.

- [ ] **Step 6: Commit**

```bash
cd <PROJECT_ROOT>/openc2e
git add src/openc2e/caosScript.cpp src/fileformats/tests/CaosLexerTest.cpp
git commit -m "fix: CAOS parser skips lexer error tokens (meerk_fix.cos trailing quote)"
```

---

## Task 2: Missing Sprite Placeholder: Warn Once, Return Stub

Five .c16 files are missing from C3-only installs (they ship with Docking Station): hand.c16, BlackOnTransparentChars.c16, WhiteOnTransparentChars.c16, heatherontransparentchars.c16. Currently each missing file produces two warnings (FILEIO + RENDER). The engine continues fine but the log is noisy.

**Fix:** In `imageManager.cpp`, when a file isn't found, create a 1x1 transparent stub image and cache it. Log one INF-level message per unique missing file instead of WRN. In `PathResolver.cpp`, downgrade the "File resolution failed" warning to DBG for image files.

**Files:**
- Modify: `src/openc2e/imageManager.cpp:39-51`
- Modify: `src/openc2e/PathResolver.cpp:130`

### Steps

- [ ] **Step 1: Modify imageManager.cpp: return stub sprite for missing files**

In `src/openc2e/imageManager.cpp`, modify `tryOpenImage()`:

```cpp
#include <set>

// Track which files we've already warned about (warn once per file)
static std::set<std::string> s_missing_warned;

std::shared_ptr<creaturesImage> tryOpenImage(std::string fname) {
	path realfile(findImageFile(fname));
	std::string basename = realfile.filename().stem().string();

	if (exists(realfile)) {
		auto img = std::make_shared<creaturesImage>(basename);
		img->images = ImageUtils::ReadImage(realfile.string());
		NORN_DBG(RENDER, fmt::format("Image loaded: {}", realfile.string()));
		return img;
	}

	// Create a 1x1 transparent stub instead of returning null
	if (s_missing_warned.insert(fname).second) {
		NORN_INF(RENDER, fmt::format("Missing sprite '{}': using transparent stub (DS-only file?)", fname));
	}
	auto stub = std::make_shared<creaturesImage>(fname);
	Image placeholder;
	placeholder.width = 1;
	placeholder.height = 1;
	placeholder.format = if_rgb565;
	placeholder.data = shared_array<uint8_t>(2);  // 1 pixel * 2 bytes (rgb565)
	std::memset(placeholder.data.data(), 0, 2);
	stub->images.push_back(placeholder);
	return stub;
}
```

- [ ] **Step 2: Downgrade PathResolver file-not-found to DBG**

In `src/openc2e/PathResolver.cpp:130`, change `NORN_WRN` to `NORN_DBG`:

```cpp
	NORN_DBG(FILEIO, fmt::format("File resolution failed: {}", name.string()));
```

This affects ALL file types, not just images. File resolution failures are expected (the engine probes multiple directories) and are not actionable warnings.

- [ ] **Step 3: Build and run tests**

```bash
cd <PROJECT_ROOT>/openc2e/build64
cmake --build . --config RelWithDebInfo --parallel 16
ctest --build-config RelWithDebInfo --output-on-failure
```

Expected: ALL PASS.

- [ ] **Step 4: Verify live: no more FILEIO/RENDER warnings for missing sprites**

Start openc2e, wait 5 seconds, check logs:

```bash
cd <PROJECT_ROOT>/openc2e/build64/RelWithDebInfo
./openc2e.exe --data-path "<PROJECT_ROOT>/creaturesexodusgame/Creatures Exodus/Creatures 3" --gamename "Creatures 3" &
sleep 5
python -c "
import json, os
logdir = 'logs/'
latest = sorted(os.listdir(logdir))[-1]
warns = 0
with open(logdir + latest) as f:
    for line in f:
        e = json.loads(line)
        if e.get('lvl') in ('WRN','ERR') and e.get('cat') in ('FILEIO','RENDER'):
            warns += 1
            print(e['lvl'], e['msg'][:150])
if warns == 0:
    print('SUCCESS: No FILEIO/RENDER warnings')
"
```

Expected: No WRN/ERR entries from FILEIO or RENDER categories. Missing sprites logged at INF level once each.

- [ ] **Step 5: Commit**

```bash
cd <PROJECT_ROOT>/openc2e
git add src/openc2e/imageManager.cpp src/openc2e/PathResolver.cpp
git commit -m "fix: stub sprites for missing DS-only files, downgrade file-not-found to DBG"
```

---

## Task 3: Downgrade Missing-Script Warnings to DBG

The "Script N not found for agent" warnings fire when the engine probes for optional scripts that agents don't define. This is normal engine behavior, not a failure. Events 0-5, 12-14, 92 have built-in engine code and run regardless. Other events are optional hooks.

**Fix:** Change `NORN_WRN` to `NORN_DBG` on line 341 of Agent.cpp.

**Files:**
- Modify: `src/openc2e/Agent.cpp:341`

### Steps

- [ ] **Step 1: Change WRN to DBG in Agent.cpp**

In `src/openc2e/Agent.cpp:341`, change:

```cpp
		NORN_DBG(AGENT, fmt::format("Script {} not found for agent family={} genus={} species={}", event, (int)family, (int)genus, (int)species));
```

- [ ] **Step 2: Build and run tests**

```bash
cd <PROJECT_ROOT>/openc2e/build64
cmake --build . --config RelWithDebInfo --parallel 16
ctest --build-config RelWithDebInfo --output-on-failure
```

Expected: ALL PASS.

- [ ] **Step 3: Verify live: no more AGENT warnings in log**

```bash
cd <PROJECT_ROOT>/openc2e/build64/RelWithDebInfo
./openc2e.exe --data-path "<PROJECT_ROOT>/creaturesexodusgame/Creatures Exodus/Creatures 3" --gamename "Creatures 3" &
sleep 10
python -c "
import json, os
logdir = 'logs/'
latest = sorted(os.listdir(logdir))[-1]
with open(logdir + latest) as f:
    wrn = sum(1 for l in f if json.loads(l).get('lvl') in ('WRN','ERR'))
print(f'Total WRN+ERR: {wrn}')
if wrn == 0:
    print('CLEAN BOOT: zero warnings, zero errors')
"
```

Expected: `CLEAN BOOT: zero warnings, zero errors`

- [ ] **Step 4: Commit**

```bash
cd <PROJECT_ROOT>/openc2e
git add src/openc2e/Agent.cpp
git commit -m "fix: downgrade missing-script warning to DBG (engine probing, not failure)"
```

---

## Task 4: Extended Stability Session: Hatch Norns, Prove It Works

This is the validation task. Run openc2e for 30+ minutes with creatures alive, NornWatch monitoring, and verify zero crashes, zero errors, zero warnings.

**Files:**
- No code changes: this is a validation run

### Steps

- [ ] **Step 1: Start NornWatch monitor**

```bash
cd <PROJECT_ROOT>/openc2e/tools
python nornwatch.py --port 9999 &
```

- [ ] **Step 2: Start openc2e with C3 data**

```bash
cd <PROJECT_ROOT>/openc2e/build64/RelWithDebInfo
./openc2e.exe --data-path "<PROJECT_ROOT>/creaturesexodusgame/Creatures Exodus/Creatures 3" --gamename "Creatures 3"
```

- [ ] **Step 3: Wait for world to load, then verify clean bootstrap**

Check logs after 10 seconds: should be zero WRN/ERR entries.

- [ ] **Step 4: Let engine run for 30+ minutes with NornWatch collecting data**

Monitor perf metrics (tick_ms, frame_ms, fps, agent count) for stability. Watch for any new error categories.

- [ ] **Step 5: Generate final session report**

```bash
python -c "
import json, os
from collections import Counter
logdir = '<PROJECT_ROOT>/openc2e/build64/RelWithDebInfo/logs/'
latest = sorted(os.listdir(logdir))[-1]
severity = Counter()
total = 0
with open(logdir + latest) as f:
    first = json.loads(f.readline())
    total = 1
    severity[first.get('lvl','')] += 1
    for line in f:
        e = json.loads(line)
        total += 1
        severity[e.get('lvl','')] += 1
        last = e

duration = last['t'] - first['t']
print(f'=== FINAL SESSION REPORT ===')
print(f'Duration: {duration:.0f}s ({duration/60:.1f} min)')
print(f'Total entries: {total}')
for k,v in severity.most_common():
    print(f'  {k}: {v}')
if severity.get('ERR',0) == 0 and severity.get('WRN',0) == 0 and severity.get('FATAL',0) == 0:
    print()
    print('CLEAN SESSION: Zero errors, zero warnings.')
    print('openc2e: first clean run of GOG Creatures 3 on 64-bit Windows 11.')
"
```

- [ ] **Step 6: Commit session report**

Save the NornWatch session log and final report to `openc2e/docs/`.

```bash
cd <PROJECT_ROOT>/openc2e
mkdir -p docs
# Copy session report to docs/
git add docs/
git commit -m "docs: clean 30-min C3 session report: zero errors on Win11 x64"
```
