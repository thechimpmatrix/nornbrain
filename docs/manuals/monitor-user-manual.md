# NORN MISSION CONTROL: User Manual

A guide to reading and understanding every element of the Mission Control monitor, in the context of both the original Creatures 3 game and the NORNBRAIN CfC brain transplant project.

---

## 1. What You're Looking At

The monitor is a real-time dashboard showing the inner workings of a single norn's brain and body. It merges two data streams:

- **TCP (port 20001):** Creature state polled from openc2e via CAOS commands: drives, chemicals, position, alive/dead
- **UDP (port 20002):** Brain telemetry sent directly from the Python CfC brain module: neuron activations, attention/decision outputs, RL training metrics

The display updates every 200ms (~5 frames/sec). The theme is Tokyo Night dark.

---

## 2. Top Bar

```
NORN MISSION CONTROL  connected  Norn (genus 1)  tick 6318  4.7 tps
```

| Element | Meaning |
|---------|---------|
| **connected / disconnected** | Whether the monitor has a live link to openc2e. Green = good, red = no connection, yellow = stale (UDP data >5s old) |
| **Norn (genus 1)** | Species and genus of the tracked creature. genus 1 = norn, 2 = grendel, 3 = ettin |
| **tick 6318** | The game's internal clock. One tick = one full simulation cycle (brain tick + biochemistry + physics) |
| **4.7 tps** | Ticks per second: how fast the simulation is running. The original C3 target was ~10 tps. Lower means the engine or brain is under load |

---

## 3. Left Panel: SENSORY INPUTS

These are the creature's **raw perceptions**: what the brain receives as input each tick. In the original C3, these were separate brain lobes (clusters of neurons). In NORNBRAIN, they are input vectors fed into the CfC modules via tract projections.

| Lobe | Full Name | Neurons | What It Represents |
|------|-----------|---------|-------------------|
| **visn** | Vision | 40 | What the creature can see. Each of 40 neurons corresponds to one agent category (norn, food, bug, door, etc.). Higher activation = that category is more visible/closer |
| **smel** | Smell | 40 | What the creature can smell. Driven by Cellular Automata (CA): invisible gas-like signals that spread through rooms. Food emits protein/carb/fat smell, creatures emit creature smell, machinery emits its own smell |
| **driv** | Drive | 20 | The creature's internal needs (hunger, pain, fear, etc.). These are the same values shown in the DRIVES panel, packaged as brain input |
| **prox** | Proximity | 20 | Navigation signals from CA gradients. Tells the brain about nearby navigational features: exits, elevators, up/down paths |
| **sitn** | Situation | 9 | Contextual state: life stage (baby→senile), whether carrying something, falling, near a mate, inside a vehicle, music mood. Think of it as "what's happening to me right now" |
| **detl** | Detail | 11 | Properties of the currently-attended object: is it a creature? a sibling? opposite sex? how far away? how big? being carried? Think of it as "what is this thing I'm looking at" |
| **noun** | Noun | 40 | Language input from the player. When you type "food" or click a teaching word, the corresponding noun neuron fires. Same 40 categories as vision |
| **verb** | Verb | 17 | Action commands from the player. When you type "push" or "eat", the corresponding verb neuron fires. Same 14 actions as the decision system (plus 3 unused) |
| **resp** | Response | 20 | Feedback from the last action. After the creature does something, the response lobe tells the brain how each drive changed: "eating reduced hunger" or "getting hit increased pain" |

**Not shown on the left panel but visible as brain map input nodes:**

| Lobe | Neurons | What It Represents |
|------|---------|-------------------|
| **stim** | 40 | Which agent category caused the last stimulus (reward/punishment). If eating food triggered a reward, the "food" stim neuron fires |
| **chem** | 16 | A subset of key chemicals (reward, punishment, adrenalin, fear, anger, pain, hungers, loneliness, boredom, stress, injury, life force) fed directly to the emotional and decision modules |
| **loc** | 2 | Creature's X/Y position in the world, normalized |
| **ltm** | 6 | Long-term memory injection (Phase 4B: currently zeroed/inactive) |

### How to Read the Bars

Each bar shows the **mean activation** across all neurons in that lobe. A high driv bar means the creature has strong drives overall. A high visn bar means it can see many things. To see which *specific* category or drive is active, look at the brain map or the dedicated drives/attention panels.

### C3 Context

In the original game, these lobes were physical clusters of SVRule neurons that updated via fixed genetic rules. The creature's genome specified how each lobe's neurons fired and decayed. In NORNBRAIN, the same input data is fed to CfC (Closed-form Continuous-depth) neural network modules that learn their own response patterns: dramatically more flexible.

---

## 4. Left Panel: DRIVES

Drives are the creature's **motivations**: internal chemical signals that represent needs. They are the engine that makes a creature *want* things. Every behavior the creature performs is ultimately driven by these 20 values.

### The 20 Drives

| # | Drive | Chemical | What Raises It | What Lowers It | Creature Behavior When High |
|---|-------|----------|---------------|----------------|----------------------------|
| 0 | **Pain** | 148 | Injury, being hit, disease | Medicine, time decay | Retreats, vocalizes distress |
| 1 | **Hunger (Protein)** | 149 | Protein reserves depleting | Eating protein-rich food (critters, bugs) | Seeks food, eats |
| 2 | **Hunger (Carbs)** | 150 | Carbohydrate reserves depleting | Eating starchy food (seeds, fruit) | Seeks food, eats |
| 3 | **Hunger (Fat)** | 151 | Fat reserves depleting | Eating fatty food | Seeks food, eats |
| 4 | **Cold** | 152 | Low room temperature | Warm rooms, heat sources | Moves toward warmth |
| 5 | **Hot** | 153 | High room temperature | Cool rooms, water | Moves toward coolness |
| 6 | **Tired** | 154 | Physical activity, exertion | Resting, sleeping | Slows down, rests |
| 7 | **Sleepy** | 155 | Sleep deprivation, time awake | Sleep (entering REM) | Falls asleep |
| 8 | **Lonely** | 156 | No creatures nearby, isolation | Being near other creatures, being tickled | Approaches other creatures |
| 9 | **Crowded** | 157 | Too many creatures in same room | Moving to emptier room | Retreats from crowd |
| 10 | **Fear** | 158 | Pain, threats, seeing grendels | Safety, time decay, courage chemical | Retreats from threat |
| 11 | **Bored** | 159 | Inactivity, repetitive actions | Novel stimuli, playing with toys | Explores, plays |
| 12 | **Anger** | 160 | Frustration (failed actions), being hit | Successful actions, time decay | Hits things, aggressive |
| 13 | **Sex Drive** | 161 | Reproductive hormones (testosterone/oestrogen) | Mating (kisspop) | Approaches opposite sex |
| 14 | **Comfort** | 162 | General discomfort (sum of unmet needs) | Fulfilling needs, safe environment | General unease |
| 15-19 | **Navigation** | 199-203 | CA gradients (Up, Down, Exit, Enter, Wait) | Reaching destination | Movement in specific direction |

### How to Read the Bars

- **Green** (0.0–0.5): Low need, creature is fine
- **Yellow** (0.5–0.8): Moderate need, creature is motivated
- **Red** (0.8–1.0): Urgent need, creature is desperate

Multiple high drives create **drive conflict**: the brain must choose which need to address first. This is where the decision system earns its keep.

### C3 Context

In the original game, drives were the primary mechanism for emergent behavior. A creature with high hunger would (hopefully) seek food, eat, and reduce the drive. The entire charm of Creatures was watching these drive-behavior loops develop through learning. Drives are real chemicals in the biochemistry simulation: they decay over time, are modified by organs, and interact with each other through receptor/emitter genes.

---

## 5. Left Panel: CHEMICALS

The biochemistry panel shows key chemicals circulating in the creature's bloodstream. Creatures 3 simulates 256 chemicals with a full organ/receptor/emitter system. The monitor displays the most important ones, grouped by function.

### REINFORCEMENT (Yellow)

| Chemical | # | What It Does |
|----------|---|-------------|
| **Reward** | 204 | The "good job" signal. Injected when the creature successfully performs an action (eats food, retreats from danger, sleeps when tired). This is the primary learning signal: it tells the brain "do that again." In NORNBRAIN, `reward = chem_204 - chem_205` is the RL training signal |
| **Punishment** | 205 | The "bad idea" signal. Injected when an action fails or produces pain (failed interaction, being slapped by player, hitting another creature). Tells the brain "don't do that." |

These chemicals are **the most important values on the entire monitor** for understanding learning. When you see reward spike after an action, the brain is being reinforced. When punishment spikes, the brain is being discouraged.

### AROUSAL (Red)

| Chemical | # | What It Does |
|----------|---|-------------|
| **Adrenalin** | 117 | Fight-or-flight hormone. Spikes during threats, pain, and excitement. Modifies how other chemicals are processed. High adrenalin = heightened state |
| **Fear** | 158 | The fear drive chemical (also shown in drives). Included here because it's a key emotional signal for the amygdala module |
| **Anger** | 160 | The anger drive chemical. Same dual display reason |

### METABOLISM (Green)

| Chemical | # | What It Does |
|----------|---|-------------|
| **Glucose** | 3 | Blood sugar: the creature's moment-to-moment fuel. Consumed by activity. If this hits zero, the creature starts dying |
| **Glycogen** | 4 | Liver storage: converted to glucose when blood sugar drops. Medium-term energy reserve |
| **Starch** | 5 | Dietary carbohydrate: converted to glycogen by digestion. Comes from eating plants/seeds |
| **Fat** | 10 | Long-term energy storage. Slowly converted to glycogen when other reserves are low |
| **Protein** | 12 | Building blocks for growth and repair. Comes from eating critters/bugs/food |
| **ATP** | 35 | The actual energy molecule. Produced by mitochondria from glucose + oxygen. This is what muscles burn. Healthy range: 0.4–0.8 |
| **ADP** | 36 | Spent energy molecule. ATP becomes ADP after use. Recycled back to ATP by mitochondria. ADP + ATP should roughly sum to ~1.0 |

**How to read metabolism:** A healthy creature has moderate glucose (0.1–0.3), some glycogen reserves, and ATP around 0.5–0.7. If glucose drops to zero and ATP crashes, the creature is starving. If ATP is very high (>0.9), the creature is well-fed and idle.

### DRIVES (Blue)

A compact view of 10 key drive chemicals (same data as the DRIVES panel, just the chemical concentrations). Useful for seeing exact numeric values.

### NEUROTROPHIN (Cyan)

| Chemical | # | What It Does |
|----------|---|-------------|
| **Downatrophin** | 17 | Promotes neural pruning: weakens unused connections. In C3, this sculpted the brain by removing pathways the creature didn't use |
| **Upatrophin** | 18 | Promotes neural growth: strengthens active connections. The opposite of downatrophin. Together they implement use-it-or-lose-it plasticity |

In NORNBRAIN's CfC brain, neurotrophins are read as input signals but don't directly modify weights (that's handled by the RL optimizer). They serve as contextual signals about the creature's developmental state.

---

## 6. Center Panel: BRAIN MAP

The brain map is the heart of the monitor. It visualizes all 239 neurons of the CfC brain, organized into four modules with 22 tract connections.

### The Four Modules

The brain processes information in two stages, inspired by mammalian neuroscience:

#### Stage 1: Parallel Processing (left side of map)

These three modules run simultaneously, each specializing in a different aspect of perception:

**Thalamus (70 neurons, 10x7 grid)**
- **Role:** Sensory gateway and attention selection
- **Inputs:** Vision (what can I see?), Smell (what can I smell?), Drive (what do I need?), Proximity (what's nearby?)
- **Output:** 40 attention neurons: one per agent category. The winner determines what the creature focuses on
- **C3 analogy:** Combines the function of C3's perception and attention lobes
- **Time dynamics:** Fast: updates quickly to track changing sensory input. If a new object appears, the thalamus reacts within 1-2 ticks

**Amygdala (52 neurons, 8x7 grid)**
- **Role:** Emotional processing and threat/reward evaluation
- **Inputs:** Drive (what do I need?), Stimulus (what just happened?), Chemicals (reward/punishment/adrenalin/fear/anger)
- **Output:** 16-dimensional continuous emotional state vector (not a winner-take-all: it's a rich emotional signal)
- **C3 analogy:** Closest to C3's stimulus-response pathways in the drive lobe
- **Time dynamics:** Mixed: can react quickly to sudden stimuli (adrenalin spike) but also maintains persistent emotional states (lingering fear)

**Hippocampus (52 neurons, 8x7 grid)**
- **Role:** Context and memory binding
- **Inputs:** Situation (what's happening to me?), Detail (what is this thing?), Noun (what did the player say?), Verb (what did the player command?), Location (where am I?)
- **Output:** 16-dimensional continuous context vector
- **C3 analogy:** Combines C3's situation, detail, noun, and verb lobes into a unified context representation
- **Time dynamics:** Slow: intentionally retains information across many ticks. This is the module that "remembers" what just happened 50 ticks ago

#### Stage 2: Integration (right side of map)

**Prefrontal Cortex (65 neurons, 9x8 grid)**
- **Role:** Executive decision-making: integrates everything and chooses an action
- **Inputs:** All three Stage 1 outputs PLUS direct access to drives, verbs, nouns, response feedback, stimulus history, chemicals, and long-term memory
- **Output:** 17 decision neurons (only 0–13 are active). The winner determines what the creature does
- **C3 analogy:** The decision lobe: the final arbiter of behavior
- **Time dynamics:** Moderate: must be reactive enough to change actions when circumstances change, but stable enough to commit to multi-tick action sequences (walking to food, picking it up, eating it)

### Reading the Neurons (Dots)

Each dot is one neuron. Color indicates activation level:
- **Black/dark blue** (0.0–0.33): Silent: this neuron isn't contributing
- **Cyan/light blue** (0.33–0.66): Active: moderate signal
- **White/bright** (0.66–1.0): Strongly active: this neuron is firing hard

A healthy, learning brain shows a mix of activations: some bright, some dim, patterns shifting tick to tick. If an entire module is uniformly dark or uniformly bright, something may be wrong.

### Reading the Tracts (Curved Lines)

The lines connecting input nodes to modules (and modules to each other) are **tracts**: neural pathways that carry information between brain regions. Each tract is a learned sparse linear projection.

Tract color indicates signal strength:
- **Dim gray** (<0.01): Nearly silent pathway
- **Blue** (0.01–0.33): Weak signal flowing
- **Cyan** (0.33–0.66): Moderate signal
- **Yellow** (0.66–0.85): Strong signal
- **Red** (0.85–1.0): Very strong signal

**22 Tracts total:**
- 4 feeding Thalamus (visn, smel, driv, prox)
- 3 feeding Amygdala (driv, stim, chem)
- 5 feeding Hippocampus (sitn, detl, noun, verb, loc)
- 10 feeding Prefrontal (thal, amyg, hipp outputs + driv, verb, noun, resp, stim, chem, ltm direct)

### Input Nodes (Left Edge Labels)

The labeled boxes on the far left of the brain map (visn, smel, driv, prox, sitn, detl, noun, verb, resp, stim, chem, loc, ltm) are sensory input sources. Their color indicates mean activation of that input: brighter means more information flowing in.

### Output Nodes (Right Edge Boxes)

- **ATTN** box (green border): Shows the attention winner label (e.g., "nest", "food", "norn")
- **DECN** box (yellow border): Shows the decision winner label (e.g., "right", "eat", "approach")

### Module Statistics

Below each module's neuron grid:
```
thal  v=0.0995  E=2.8
```

| Metric | Full Name | What It Means |
|--------|-----------|--------------|
| **v=** | Variance | How spread out the neuron activations are within this module. Low variance = neurons are all similar (could mean the module is "stuck" or highly focused). High variance = diverse activations (module is differentiating between inputs) |
| **E=** | Energy | The Euclidean norm (magnitude) of the hidden state. Higher energy = more total neural activity. Very low energy might mean the module is barely contributing to decisions |

---

## 7. Center Panel: Health Metrics

```
entropy=3.41  conf=0.11  diversity=0.07  [?]
```

| Metric | Range | What It Means |
|--------|-------|--------------|
| **entropy** | 0.0–~3.7 | Shannon entropy of the attention distribution (before argmax). **High entropy** = attention is spread across many categories (the creature is "looking everywhere," undecided about what to focus on). **Low entropy** = attention is concentrated on one or two categories (the creature knows what it wants to look at). Healthy range: 1.5–3.0 |
| **conf** | 0.0–1.0 | Confidence of the decision: the softmax probability assigned to the winning action. **High confidence** (>0.5) = the brain strongly favors one action. **Low confidence** (<0.2) = the brain is nearly guessing. The example shows conf=0.11, meaning the "right" decision barely edged out alternatives |
| **diversity** | 0.0–1.0 | How many different actions the creature has taken over the last 50 ticks. **High diversity** (>0.5) = exploring many actions. **Low diversity** (<0.1) = stuck repeating one action (perseveration). 0.07 in the screenshot is extremely low: the creature is stuck on "right" |
| **[status]** | text | "healthy" (green), "stuck" (yellow, diversity <0.1), or "converged" (dim, all module variances <0.001) |

### Interpreting the Screenshot

entropy=3.41, conf=0.11, diversity=0.07 tells a clear story: the creature has broad sensory awareness (high entropy) but can't commit to any action with confidence (low conf), and has been repeating "right" almost exclusively (near-zero diversity). This is classic early-training perseveration: the brain hasn't yet learned which actions produce rewards.

---

## 8. Center Panel: TIMELINE

The timeline is a 200-tick scrolling bar chart showing **which decision was active at each tick**. Each vertical slice is one tick, colored by the action taken.

### How to Read It

- **Solid block of one color** = the creature is repeating one action for many ticks (perseveration or intentional sustained behavior)
- **Rainbow / rapidly alternating colors** = decision thrashing: the brain is switching actions every tick (confusion, high drive conflict)
- **Gradual transitions between colors** = natural behavioral sequences (approach → get → eat → rest)

### What Healthy Behavior Looks Like

A learning creature's timeline evolves over time:
1. **Early training:** Random color noise (exploring)
2. **Mid training:** Patches of consistent color emerging (learning associations)
3. **Mature:** Deliberate sequences: approach (green) → eat (bright green) → rest (white), with occasional exploration

### The Legend

Below the timeline bar, the last 3-4 unique decisions are shown with their color squares and labels, so you can quickly identify what the colors mean.

---

## 9. Center Panel: EVENT LOG

```
[16:11:34] right -> nest (conf 0.11)
[16:11:34] right -> nest (conf 0.13)
[16:11:33] right -> nest (conf 0.13)
```

Each line records one brain tick:
- **[HH:MM:SS]**: wall-clock time of the event
- **right**: the decision winner (what the creature chose to do)
- **-> nest**: the attention winner (what the creature was focused on)
- **(conf 0.11)**: the decision confidence

### What to Watch For

- **Repeating entries** (like the screenshot): Perseveration: the creature is stuck in a loop
- **Rapid attention shifts** ("food" → "norn" → "bug" → "door"): Attention instability: could be healthy exploration or sensory overload
- **Decision-attention mismatches** ("eat → norn"): The creature wants to eat but is focused on another creature: possible confusion or social feeding behavior
- **Confidence climbing** (0.05 → 0.12 → 0.30 → 0.65): The brain is learning and becoming more decisive

---

## 10. Right Panel: ATTENTION (Top 10)

The attention system determines **what the creature focuses on**: which object in the world it considers as its target ("IT" in CAOS).

### The 40 Categories

Creatures 3 classifies every object in the world into one of 40 categories. The attention output has 40 neurons, one per category. The winner (highest activation) becomes the creature's focus.

Key categories:

| # | Category | What It Is |
|---|----------|-----------|
| 0 | self | The creature itself |
| 1 | hand | The player's hand/pointer: the primary way you interact with creatures. Tickling (rewarding) and slapping (punishing) come from the hand. Creatures can learn to approach or retreat from it |
| 4 | plant | Growing plants |
| 8 | fruit | Edible fruit |
| 11 | food | Prepared food items |
| 13 | bug | Small creatures (food source) |
| 16 | beast | Large creatures (potential threat) |
| 17 | nest | Animal/creature nests |
| 21 | toy | Toys and entertainment objects |
| 26 | elevator | Lifts and vertical transport |
| 34 | something | Miscellaneous objects |
| 36 | norn | Other norns |
| 37 | grendel | Grendels (often hostile) |
| 38 | ettin | Ettins (often steal things) |

### How to Read the Panel

The panel shows the top 10 most active attention neurons ranked by activation strength. The **winner** (highest) is highlighted with a green border: this is what the creature is currently targeting.

- **High activation on one category** (>0.5) with others low: Strong focus, creature knows what it wants
- **Multiple categories with similar activation** (0.3–0.5): Attention conflict: the brain is torn between targets
- **"something" dominating**: The creature is attending to a generic/miscellaneous object: often means it can't classify what it's seeing

### C3 Context

In the original game, attention selection was done by a dedicated attention lobe with SVRule neurons. The creature would focus on whatever category had the strongest combined signal from vision + smell + drive need. A hungry creature would attend to food because hunger drives amplified food-related visual signals. The same principle applies in NORNBRAIN: the thalamus learns to combine sensory and drive information to select the most relevant target.

---

## 11. Right Panel: DECISION

The decision system determines **what the creature does**: which of 14 possible actions to perform on its attention target.

### The 14 Actions

| # | Action | What Happens | When It's Useful |
|---|--------|-------------|-----------------|
| 0 | **look** | Idle/quiescent: creature stands and looks around | Default when no strong drive motivates action |
| 1 | **push** | Activate the target (push a button, kiss a norn, shove an object) | Interacting with machines, social contact |
| 2 | **pull** | Secondary activate (pull a lever, groom a norn) | Alternative interaction |
| 3 | **deactivate** | Turn off/stop the target | Stopping machines, ending interactions |
| 4 | **approach** | Walk toward the attention target | Prerequisite for most other actions: must be close enough to interact |
| 5 | **retreat** | Run away from the target | Fear response, avoiding threats |
| 6 | **get** | Pick up the target | Collecting food, tools, toys |
| 7 | **drop** | Release whatever the creature is carrying | Putting things down, sometimes after getting confused |
| 8 | **express** | Vocalize the creature's highest drive | Communication: "I'm hungry!" or "I'm lonely!" |
| 9 | **rest** | Lie down and sleep | Recovering energy, reducing tiredness/sleepiness |
| 10 | **left** | Walk west continuously | Navigation |
| 11 | **right** | Walk east continuously | Navigation |
| 12 | **eat** | Consume the target | Eating food/fruit/seeds/bugs to reduce hunger |
| 13 | **hit** | Attack/strike the target | Aggression: usually discouraged by punishment chemicals |

### How to Read the Panel

All 14 actions are displayed with their activation levels. The **winner** (highest among indices 0–13) is highlighted with a yellow border.

- **One action clearly dominant** (>0.3, others <0.1): Strong decision: the brain is confident
- **Several actions with similar activation**: Decision conflict: the brain might flip between actions tick to tick
- **Negative values**: These can occur in the raw network output (before softmax). Negative just means "less preferred than average"

### Action Sequences

Real behavior involves sequences of decisions, not individual actions. A complete "eat food" sequence looks like:

1. **Attention → food** (thalamus selects food category)
2. **approach** (walk toward the food)
3. **get** (pick it up, if required)
4. **eat** (consume it)
5. **Drives decrease** (hunger drops)
6. **Reward fires** (chemical 204 spikes)
7. **Brain reinforced** (CfC weights update to repeat this pattern)

Watching these sequences form is watching the creature **learn**.

---

## 12. Right Panel: CONTROLS

| Button | What It Does | When to Use It |
|--------|-------------|----------------|
| **Pause** | Freezes the creature's movement (sends `zomb 1` to openc2e). The brain still ticks but the creature can't move or interact | When you want to observe brain state without the creature wandering off |
| **Resume** | Unfreezes movement (sends `zomb 0`) | After pausing |
| **Wipe Hidden** | Resets all CfC hidden states to zero. The brain "forgets" its short-term context: like waking up with amnesia. Learned weights are preserved | When the brain is stuck in a bad state and you want to give it a fresh start without losing training |
| **Save Weights** | Saves the current neural network weights to a `.pt` file on disk | Before risky experiments, at regular intervals during training, when the creature is behaving well |
| **Toggle RL** | Turns reinforcement learning on or off. When ON, the brain updates its weights every tick based on reward/punishment. When OFF, the brain runs in inference-only mode (uses what it's learned but doesn't change) | Turn RL off to evaluate stable behavior. Turn RL on during training. Toggle off if RL is destabilizing a good brain |
| **Capture** | Saves a snapshot of the current scenario (creature state + brain state + environment) | For later analysis or replay |

---

## 13. Right Panel: STATUS

```
LTM: 0 memories
tier: ?
action: right -> nest  flip=0.00
RL: ON  steps=1586  loss=-0.5641  reward=+(value)
```

| Field | What It Means |
|-------|--------------|
| **LTM: 0 memories** | Long-term memory count. Phase 4B feature: the hippocampus can consolidate experiences into persistent memories. 0 means no memories stored yet (feature may be inactive) |
| **tier: ?** | Emotional tier: an inferred label for the creature's dominant emotional state ("hungry", "scared", "content", etc.). "?" means the tier classifier couldn't determine a clear state |
| **action: right -> nest** | Current action and target, in plain text. "right -> nest" = walking right, focused on a nest |
| **flip=0.00** | Decision flip rate: how often the decision changes between consecutive ticks (0.0–1.0). 0.00 means the creature hasn't changed its decision at all recently. High flip rate (>0.5) means rapid switching |
| **RL: ON** | Whether reinforcement learning is active |
| **steps=1586** | Total RL training steps since the brain was loaded. Each tick with RL enabled = one step |
| **loss=-0.5641** | The current RL policy loss. Negative loss in REINFORCE means the policy gradient is working (rewarded actions are being reinforced). This value fluctuates: trends matter more than individual readings |
| **reward=+(value)** | The most recent reward signal (`chem_204 - chem_205`). Positive = net reward, negative = net punishment, zero = no reinforcement signal this tick |

### RL Status Colors
- **Green**: Positive reward (creature just did something good)
- **Red**: Negative reward (creature just did something bad)
- **Cyan**: Near-zero (no significant reward/punishment)

---

## 14. Putting It All Together: Reading the Full Picture

### The Decision Loop (Every Tick)

```
1. SENSE  → Sensory lobes fire (visn, smel, sitn, detl, etc.)
2. FEEL   → Drives and chemicals update (hunger rises, pain fades)
3. THINK  → CfC brain processes:
             Stage 1: Thalamus (what to attend to)
                      Amygdala (how to feel about it)
                      Hippocampus (what's the context)
             Stage 2: Prefrontal (what to do)
4. ACT    → Decision winner fires a CAOS event (approach, eat, retreat...)
5. RESULT → Action succeeds or fails → stimulus fires
6. LEARN  → Reward/punishment chemical injected → RL updates weights
7. REPEAT
```

### Example: Watching a Creature Learn to Eat

**Tick 0–100 (random exploration):**
- Timeline: rainbow noise (random decisions)
- Attention: cycling through whatever's nearby
- Drives: hunger slowly climbing (green → yellow)
- Confidence: very low (0.05–0.15)
- Diversity: high (0.5+)

**Tick 100–200 (accidental success):**
- Creature randomly approaches food, accidentally eats
- Reward chemical spikes (left panel, yellow bar)
- Hunger drops (drive bars return to green)
- Brain gets its first reinforcement signal

**Tick 200–500 (pattern forming):**
- When hungry, attention starts favoring food more often
- "eat" decision appears more frequently in timeline
- Confidence slowly rises when food is visible
- Diversity decreases slightly (fewer random actions)

**Tick 500+ (learned behavior):**
- Hungry → attention snaps to food → approach → eat
- Timeline shows clear eat sequences (consistent color patches)
- Confidence >0.3 when executing learned sequences
- Reward spikes regularly, hunger stays manageable

### Troubleshooting Patterns

| What You See | What It Means | What To Do |
|-------------|---------------|------------|
| One action dominates timeline for 200+ ticks | Perseveration: brain is stuck | Try "Wipe Hidden" to reset short-term state. If persistent, the RL signal may be too weak or absent |
| Decision flips every tick (flip=0.8+) | Extreme indecision | Check if multiple drives are equally high (drive conflict). May need RL training with clearer reward signals |
| All drives red | Creature is suffering | Ensure food/warmth/company are available in the world. Check if the creature can actually reach resources |
| Reward never fires | No learning happening | Check that stimulus genes are working. Verify the creature can actually interact with objects (not stuck behind a wall) |
| All neurons in a module are dark | Module is silent | May indicate a tract is broken or input data is zero. Check the input lobe bars |
| Entropy very low (<0.5) with wrong attention | Confidently wrong | The brain has learned a bad association. May need RL to correct, or wipe hidden + retrain |
| ATP crashing toward 0 | Creature is dying of starvation | Urgent: ensure food is accessible. Glucose → 0 causes death |

---

## 15. Glossary

| Term | Definition |
|------|-----------|
| **Agent** | Any object in the C3 world (food, door, creature, machine, etc.) |
| **CA (Cellular Automata)** | Invisible gas-like signals that spread through rooms. Creatures smell them. Used for navigation and food detection |
| **CAOS** | The scripting language of the Creatures engine. Every game event is a CAOS script |
| **CfC (Closed-form Continuous-depth)** | The neural network architecture used in NORNBRAIN. Unlike traditional RNNs, CfC neurons have continuous time dynamics: they "remember" with mathematically smooth decay, not discrete hidden states |
| **Classifier** | A 3-number identifier (family, genus, species) that uniquely identifies an object type in C3 |
| **Drive** | An internal chemical representing a need. Drives motivate behavior |
| **IT** | CAOS variable holding the creature's current attention target |
| **Lobe** | A cluster of neurons in the brain dedicated to a specific function |
| **NCP (Neural Circuit Policy)** | The wiring structure inside each CfC module: sensory → inter → command → motor layers with sparse, genetically-parameterized connections |
| **Perseveration** | Repeating the same action regardless of outcome: a sign that the brain hasn't learned to explore alternatives |
| **REINFORCE** | The policy gradient RL algorithm used to train the brain. Rewarded actions get higher probability; punished actions get lower probability |
| **Stimulus (STIM)** | A game event that fires when the creature interacts with the world. Stimuli trigger chemical injections via the creature's genes |
| **SVRule** | The original C3 brain's neuron update mechanism: fixed rules encoded in the genome. Replaced by CfC in NORNBRAIN |
| **Tick** | One complete simulation cycle. Everything updates once per tick: biochemistry, physics, brain, scripts |
| **Tract** | A neural pathway connecting one brain region to another, implemented as a sparse linear projection |
| **WTA (Winner-Take-All)** | Selection mechanism where only the highest-activated neuron "wins": used for attention (which of 40 categories?) and decision (which of 14 actions?) |
