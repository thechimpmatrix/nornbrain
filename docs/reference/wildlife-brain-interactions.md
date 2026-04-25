# C3 Wildlife, Critters & Brain Interactions: Exhaustive Reference
# Extracted from live Steam Creatures 3 Bootstrap .cos files
# Generated 2026-03-29
# Source: I:/SteamLibrary/steamapps/common/Creatures Docking Station/Creatures 3/Bootstrap/001 World/

---

## TABLE OF CONTENTS

1. [Classifier Registry](#1-classifier-registry)
2. [Individual Species Profiles](#2-individual-species-profiles)
3. [Predator/Prey Relationships](#3-predatorprey-relationships)
4. [STIM Calls: Complete Audit](#4-stim-calls--complete-audit)
5. [CHEM Injections: Complete Audit](#5-chem-injections--complete-audit)
6. [z_creaturesAffectingAnimals](#6-z_creaturesaffectinganimals)
7. [Creature Detector](#7-creature-detector)
8. [Life Event Factory](#8-life-event-factory)
9. [Creature History](#9-creature-history)
10. [Stars & Pickup Panel](#10-stars--pickup-panel)
11. [Population Management](#11-population-management)
12. [CA Emissions from Wildlife](#12-ca-emissions-from-wildlife)
13. [Room Nutrient Modification on Death](#13-room-nutrient-modification-on-death)
14. [Surprising Findings & Brain Implications](#14-surprising-findings--brain-implications)

---

## 1. CLASSIFIER REGISTRY

All wildlife classifiers found in the analysed .cos files. Family 2 = compound/simple agents.

### Birds (Genus 15, 16, 17, 18)

| Classifier | Name | File | Type |
|------------|------|------|------|
| 2 15 1 | Robin | Robin2.cos | Songbird |
| 2 15 2 | Grazer | grazer2.cos | Herbivore (creature-interactive) |
| 2 15 3 | Hummingbird | Hummingbird.cos | Nectar feeder |
| 2 15 5 | Hedgehog | hedgehog.cos | Ground animal |
| 2 15 8 | Dragonfly (adult) | dragonfly.cos | Flying insect |
| 2 15 9 | Stickleback | stickleback.cos | River fish |
| 2 15 10 | Kingfisher | kingfisher.cos | Fishing bird |
| 2 15 11 | Woodpigeon (adult) | woodpigeon2.cos | Nesting bird |
| 2 15 12 | Hoppity (frog) | hoppity.cos | Amphibian |
| 2 15 13 | Woodpigeon chick | woodpigeon2.cos | Bird chick |
| 2 15 14 | Angelfish | angel fish.cos | Predatory fish |
| 2 15 15 | Clownfish | clown fish.cos | Predatory fish |
| 2 15 16 | Handlefish | handlefish.cos | Predatory fish |
| 2 15 19 | Neon fish | neon fish.cos | Schooling fish |
| 2 15 20 | Cuttlefish | cuttlefish.cos | Camouflage fish |
| 2 15 21 | Nudibranch | nudibranch.cos | Sea slug |
| 2 15 23 | Meerkat | meerk.cos | Burrowing mammal |
| 2 16 1 | Hawk | Hawk.cos | Apex predator bird |
| 2 16 3 | Piranha | piranha.cos | **KILLS CREATURES** |
| 2 16 4 | Rainbow sharkling | rainbow_sharkling.cos | Predatory fish |
| 2 16 7 | Kobold | Kobold.cos | Aggressive critter |
| 2 16 8 | Uglee | Uglee.cos | Flying predator |
| 2 17 1 | Robin nest | Robin2.cos | Nest |
| 2 17 2 | Hummingbird nest | Hummingbird.cos | Nest |
| 2 17 3 | Kingfisher nest | kingfisher.cos | Nest |
| 2 17 4 | Hawk perch | Hawk.cos | Perch |
| 2 18 2 | Butterfly egg | Butterfly.cos | Egg |
| 2 18 5 | Dragonfly egg | dragonfly.cos | Egg |
| 2 18 6 | Stickleback egg | stickleback.cos | Egg |
| 2 18 12 | Woodpigeon nest | woodpigeon2.cos | Nest |
| 2 18 14 | Angelfish egg | angel fish.cos | Egg |
| 2 18 15 | Clownfish egg | clown fish.cos | Egg |
| 2 18 17 | Neon fish egg | neon fish.cos | Egg |
| 2 18 21 | Handlefish egg | handlefish.cos | Egg |
| 2 18 22 | Piranha egg | piranha.cos | Egg |

### Insects / Small Critters (Genus 13, 14, 11, 8)

| Classifier | Name | File | Type |
|------------|------|------|------|
| 2 13 1 | Butterfly | Butterfly.cos | Flying insect |
| 2 13 2 | Caterpillar | Butterfly.cos | Larval insect |
| 2 13 5 | Dragonfly nymph | dragonfly.cos | Aquatic larva |
| 2 13 8 | (various small aquatic critters) | prey reference | Nudibranch/fish prey |
| 2 13 9 | Grubs | prey reference | Meerkat prey |

### Dead Bodies / Debris

| Classifier | Name | Source |
|------------|------|--------|
| 2 10 1 | Dead robin | Robin2.cos |
| 2 10 6 | Grazer droppings | grazer2.cos |
| 2 10 7 | Dead stickleback | stickleback.cos |
| 2 10 11 | Dead butterfly | Butterfly.cos |
| 2 10 12 | Dead caterpillar | Butterfly.cos |
| 2 10 15 | Dead hedgehog | hedgehog.cos |
| 2 10 22 | Dead hoppity | hoppity.cos |
| 2 10 30 | Bones | Hawk.cos, piranha.cos |
| 2 10 34 | Dead hummingbird | Hummingbird.cos |

### Infrastructure / Gadgets

| Classifier | Name | File |
|------------|------|------|
| 1 1 5 | Kingfisher perch | kingfisher.cos |
| 1 1 8 | Meerkat burrow | meerk.cos |
| 1 1 24 | Piranha bubble attack | piranha.cos |
| 1 1 46 | Pickup stars | stars and pickup panel.cos |
| 1 2 22 | Pickup notification panel | stars and pickup panel.cos |
| 1 2 23 | Creature history UI | creature history.cos |
| 1 2 24 | Life event factory | life event factory.cos |
| 1 2 25 | Life event notification icon | life event factory.cos |
| 1 2 37 | Photo agent (birth snapshot) | life event factory.cos |
| 2 24 4 | Pickup item | stars and pickup panel.cos |
| 3 3 67 | Fish egg launcher | fixed position fish egg launcher.cos |
| 3 8 1 | Creature detector | Creature detector.cos |

---

## 2. INDIVIDUAL SPECIES PROFILES

### 2.1 Grazer (2 15 2): grazer2.cos
**THE MOST CREATURE-INTERACTIVE WILDLIFE AGENT.**
- **Script 1 (activate by creature):** When `from` is family 4 (creature), applies `stim writ targ 86 1` to the creature. This is STIM 86 = "I've activated something" / creature-was-scared-by-animal. Triggers panic: grazer flees, broadcasts alarm to nearby grazers via `mesg wrt+ targ 1001`.
- Lifecycle: baby (ov05=0) -> juvenile (ov05=1) -> adult (ov05=2). Mating/courtship system.
- Eats fruit (2 6 1, 2 6 0) via `mesg writ ov16 12`.
- Creates droppings (2 10 6) that modify room nutrients.
- Population managed via life stages.
- **No eat script (12) for creatures eating it.**
- **No STIM on eat.**

### 2.2 Hawk (2 16 1): Hawk.cos
- Apex aerial predator. Hunts grazers (2 15 2).
- Attacks when 7+ grazers visible within range 1000.
- On contact: plays `"hawk"` sound, sends `mesg writ ov18 4` (hit message to target grazer), carries prey to perch (2 17 4), drops bones (2 10 30).
- Teleport/reposition effect if found in water/outdoor rooms.
- **No direct STIM to creatures.**
- **No eat script for creatures.**

### 2.3 Robin (2 15 1): Robin2.cos
- Songbird with full lifecycle: roaming, feeding, nesting, mating, sleeping.
- Eats seeds (2 14 0). Population spawns from nest (2 17 1).
- Dead body: 2 10 1.
- **On eat (script 12): `stim writ from 80 2`**: creature gets STIM 80 at intensity 2.
- No activate script for creatures.

### 2.4 Hummingbird (2 15 3): Hummingbird.cos
- Flying bird, feeds on flowers (2 7 0). Creates droppings.
- Dead body: 2 10 34. Population from nest (2 17 2).
- **On eat (script 12): `stim writ from 80 4`**: creature gets STIM 80 at intensity 4 (TWO separate lines, both intensity 4).
- No activate script for creatures.

### 2.5 Woodpigeon (2 15 11 adult, 2 15 13 chick): woodpigeon2.cos
- Full lifecycle bird with nesting/mating/feeding. Nest: 2 18 12.
- Population cap: `totl 2 15 11 lt 18` at init.
- **On eat (script 12):**
  - Adult (2 15 11): `stim writ from 80 4`
  - Chick (2 15 13): `stim writ from 80 3`
  - Nest (2 18 12): `stim writ from 80 2`

### 2.6 Butterfly (2 13 1) / Caterpillar (2 13 2): Butterfly.cos
- Full metamorphosis: egg (2 18 2) -> caterpillar -> cocoon -> butterfly.
- Caterpillar eats flowers (2 7 0), climbs plants (2 4 0).
- **On eat (script 12): BOTH butterfly and caterpillar: `stim writ from 80 1`**
- Dead bodies (2 10 11, 2 10 12) modify room nutrients:
  - `altr room targ 3 0.1` (organic)
  - `altr room targ 4 0.1` (nutrients)

### 2.7 Dragonfly (2 15 8 adult, 2 13 5 nymph): dragonfly.cos
- Aquatic nymph lifecycle, emerges as flying adult. Egg: 2 18 5.
- **On eat (script 12):**
  - Nymph: `stim writ from 80 1`
  - Adult: `stim writ from 80 2`
- Dead bodies modify room nutrients.

### 2.8 Angelfish (2 15 14): angel fish.cos
- 3-stage growth (baby/juvenile/adult). Egg: 2 18 14.
- Predatory: hunts 2 13 8, 2 3 6, 2 3 7, 2 3 8. Flocking behaviour.
- **On eat (script 12): adult: `stim writ from 80 1`**
- **Egg on eat: `stim writ from 80 1`**
- Population cap: ~14-16 total (checked via egg count).
- `emit 6 .15` (CA food smell) at growth stages.

### 2.9 Clownfish (2 15 15): clown fish.cos
- Very similar to angelfish. 3-stage growth. Egg: 2 18 15.
- Predatory. `emit 6 .15` at growth stages.
- **On eat (script 12): `stim writ from 80 1`**
- **Egg on eat: `stim writ from 80 1`**

### 2.10 Handlefish (2 15 16): handlefish.cos
- 4-stage growth fish. Egg: 2 18 21. Predatory. Flocking at maturity.
- **On eat (script 12): adult: `stim writ from 80 1`**
- **Egg on eat: `stim writ from 80 1`**

### 2.11 Neon Fish (2 15 19): neon fish.cos
- 3-stage growth fish. Egg: 2 18 17.
- `emit 6 .15` (CA food smell).
- **On eat (script 12): adult: `stim writ from 80 1`**
- **Egg on eat: `stim writ from 80 1`**

### 2.12 Stickleback (2 15 9): stickleback.cos
- River/water fish. Egg: 2 18 6.
- Feeds on seeds (2 14 0) and detritus (2 13 0). Sex differentiation via ov06.
- **On eat (script 12): `stim writ from 80 4`**
- Dead body (2 10 7): `altr room targ 3 0.2`, `altr room targ 4 0.1`.

### 2.13 Cuttlefish (2 15 20): cuttlefish.cos
- Unique figure-8 swimming. 3 spawned initially.
- **Camouflage behaviour:** Changes base sprite when near piranhas (2 16 3), sharklings (2 16 4), or creatures (4 0 0).
- **No STIM. No eat script. Purely decorative/ambient.**

### 2.14 Nudibranch (2 15 21): nudibranch.cos
- Sea slug. Feeds on 2 13 8, 2 15 18, 2 3 8.
- 3-stage growth (sprite base changes at ov05=0/1/2). Breeds when mature (ov05=2), spawns 2 offspring then dies.
- Drifts in water rooms (rtyp 9), dies if out of water for 200+ ticks.
- **No STIM. No eat script for creatures.**

### 2.15 Meerkat (2 15 23): meerk.cos
- Ground animal. Eats grubs (2 13 9). Behaviours: walk, run, sit, dig, push.
- Digs burrows: creates 1 1 8 agent, hides inside (ov00=5 state), re-emerges after rand 100-300 ticks.
- Dead body: `altr room targ 4 0.4`, `altr room targ 3 0.2`.
- **No STIM to creatures. No eat script.**

### 2.16 Hedgehog (2 15 5): hedgehog.cos
- Feeds on seeds/detritus/food. Can curl into ball (hide).
- Dead body (2 10 15) modifies room nutrients.
- **On eat (script 12): `stim writ from 80 4`**

### 2.17 Hoppity / Frog (2 15 12): hoppity.cos
- Frog-like. Eats bugs (2 11 0, 2 8 0). Has cocoon/metamorphosis stage.
- Dead body (2 10 22): `altr room targ 3 0.4`, `altr room targ 4 0.4`.
- **No STIM on eat or interaction.**

### 2.18 Kingfisher (2 15 10): kingfisher.cos
- Fishing bird. Nest: 2 17 3. Perch: 1 1 5.
- Hunts stickleback (2 15 9). Dives from perch, catches fish, returns to eat.
- Navigates toward water using CA property 5 (water smell).
- **On eat (script 12): `stim writ from 80 4`**

### 2.19 Piranha (2 16 3): piranha.cos
**THE MOST DANGEROUS WILDLIFE AGENT. KILLS CREATURES OUTRIGHT.**
- Egg: 2 18 22. Bubble attack agent: 1 1 24.
- Hunts creatures (family 4) and critters (2 13 0, 2 14 0, 2 15 0, 2 16 0 excluding self).
- **Attack mechanism:** Creates bubble agent (1 1 24) at prey location. Bubble script 1:
  - `esee 4 1 0`: scans for nearby norns
  - **`chem 117 0.5`**: injects chemical 117 into creature (this is the ONLY direct chem injection from wildlife into a creature in the entire codebase)
  - **`dead`**: KILLS the creature outright
- Creates bones (2 10 30): 10 bones for creatures, 5 for large critters (genus 15/16), 2 default.
- Population managed via egg system (2 18 22).

### 2.20 Rainbow Sharkling (2 16 4): rainbow_sharkling.cos
- **Genetic colour inheritance.** Tinted with random RGB at birth.
- Hunts other fish: ov71 cycles through species 14, 15, 16, 19 (angelfish, clownfish, handlefish, neon).
- Offspring inherit colour via averaging parent colours with mutation chance.
- After reproduction: parent marked for death (ov80=1, dies after 15 ticks).
- **No STIM. No eat script for creatures.**

### 2.21 Kobold (2 16 7): Kobold.cos
- **Aggressive critter.** In "gmad" mode, iterates through nearby critters (2 15 0, 2 16 0, 2 13 0, 2 14 0) and punches them: `velo va70 -25`.
- Eats seeds/bugs/food (2 11 0, 2 8 0, 2 13 0, 2 14 0).
- Dies in water.
- **No direct STIM to creatures.**

### 2.22 Uglee (2 16 8): Uglee.cos
- Flying predator bird. Hunts Uglee eggs (2 21 4) and specific prey (2 18 18).
- Dives to grab prey, carries back, eats. Creates droppings (2 10 6).
- **No STIM to creatures.**

---

## 3. PREDATOR/PREY RELATIONSHIPS

### Food Web

```
APEX PREDATORS (attack other animals):
  Hawk (2 16 1) -----> Grazer (2 15 2)
  Piranha (2 16 3) --> ALL creatures (family 4), ALL critters (2 13/14/15/16 0)
  Kobold (2 16 7) --> ALL nearby critters (2 15/16/13/14 0) [punches, doesn't kill]
  Uglee (2 16 8) ---> Uglee eggs (2 21 4), prey 2 18 18

FISH PREDATORS (eat smaller fish/critters):
  Rainbow Sharkling (2 16 4) --> Angelfish, Clownfish, Handlefish, Neon
  Angelfish (2 15 14) ---------> 2 13 8, 2 3 6, 2 3 7, 2 3 8
  Clownfish (2 15 15) ---------> (same prey as angelfish)
  Handlefish (2 15 16) --------> (similar prey pattern)

MEDIUM PREDATORS:
  Kingfisher (2 15 10) --------> Stickleback (2 15 9)
  Nudibranch (2 15 21) --------> 2 13 8, 2 15 18, 2 3 8

HERBIVORES / INSECTIVORES:
  Grazer (2 15 2) -------------> Fruit (2 6 0, 2 6 1)
  Robin (2 15 1) --------------> Seeds (2 14 0)
  Hummingbird (2 15 3) --------> Flowers (2 7 0)
  Stickleback (2 15 9) --------> Seeds (2 14 0), Detritus (2 13 0)
  Hedgehog (2 15 5) -----------> Seeds, detritus, food
  Meerkat (2 15 23) -----------> Grubs (2 13 9)
  Hoppity (2 15 12) -----------> Bugs (2 11 0, 2 8 0)
  Caterpillar (2 13 2) --------> Flowers (2 7 0)
  Woodpigeon (2 15 11) --------> (feeds during lifecycle)
  Kobold (2 16 7) -------------> Seeds, bugs, food (2 11 0, 2 8 0, 2 13 0, 2 14 0)

NO DIET / DECORATIVE:
  Cuttlefish (2 15 20): purely ambient
  Butterfly (2 13 1): adult does not feed
```

### Danger to Creatures

| Threat Level | Species | Mechanism |
|-------------|---------|-----------|
| **LETHAL** | Piranha (2 16 3) | `chem 117 0.5` + `dead` = instant kill |
| **Indirect** | Hawk (2 16 1) | Kills grazers that creatures interact with |
| **None** | All others | No harm to creatures |

---

## 4. STIM CALLS: COMPLETE AUDIT

### Wildlife STIM calls that affect creatures

**STIM 80: "I've eaten critter/animal" (via `stim writ from`)**

The `from` keyword means the STIM is applied to whatever creature last interacted with ("ate") the agent. This is the primary wildlife-brain feedback channel.

| Source Agent | Classifier | Intensity | Context |
|-------------|-----------|-----------|---------|
| Butterfly | 2 13 1 | 1 | On eat (script 12) |
| Caterpillar | 2 13 2 | 1 | On eat (script 12) |
| Dragonfly nymph | 2 13 5 | 1 | On eat (script 12) |
| Dragonfly adult | 2 15 8 | 2 | On eat (script 12) |
| Robin | 2 15 1 | 2 | On eat (script 12) |
| Hedgehog | 2 15 5 | 4 | On eat (script 12) |
| Stickleback | 2 15 9 | 4 | On eat (script 12) |
| Kingfisher | 2 15 10 | 4 | On eat (script 12) |
| Woodpigeon adult | 2 15 11 | 4 | On eat (script 12) |
| Woodpigeon chick | 2 15 13 | 3 | On eat (script 12) |
| Woodpigeon nest | 2 18 12 | 2 | On eat (script 12) |
| Hummingbird | 2 15 3 | 4 | On eat (script 12): TWO calls, both intensity 4 |
| Angelfish | 2 15 14 | 1 | On eat (script 12) |
| Angelfish egg | 2 18 14 | 1 | On eat (script 12) |
| Clownfish | 2 15 15 | 1 | On eat (script 12) |
| Clownfish egg | 2 18 15 | 1 | On eat (script 12) |
| Handlefish | 2 15 16 | 1 | On eat (script 12) |
| Handlefish egg | 2 18 21 | 1 | On eat (script 12) |
| Neon fish | 2 15 19 | 1 | On eat (script 12) |
| Neon fish egg | 2 18 17 | 1 | On eat (script 12) |
| Man-o-war | 2 15 17? | 3 | On eat (script 12) |
| Rocklice | (rocklice) | 5 | On eat (script 12): highest intensity |
| Rocklice (alt) | (rocklice) | 2 | Alternate eat context |
| Snail | (snail) | 1 | On eat (script 12) |
| Wasp | (wasp) | 1 | On eat (script 12) |
| Ant | (ant) | 1 | On eat (script 12) |
| Bee | (bee) | 1 | On eat (script 12) |
| Beetle | (beetle) | 1 | On eat (script 12) |
| Grasshopper | (grasshopper) | 1 | On eat (script 12): TWO calls |
| Wysts | (wysts) | 1 | On eat (script 12) |

**STIM 86: "I've been scared" / creature-touched-animal**

| Source Agent | Classifier | Intensity | Context |
|-------------|-----------|-----------|---------|
| Grazer | 2 15 2 | 1 | Script 1 (activate), only when `from` is family 4 (creature) |

**STIM 88: "Something bit/stung me"**

| Source Agent | Classifier | Intensity | Context |
|-------------|-----------|-----------|---------|
| Ant | (ant) | 1 | Ant sting script |
| Man-o-war | (man-o-war) | 1 | On eat (script 12): second STIM after 80 |
| Wasp | (wasp) | 1 | On eat (script 12): second STIM after 80 |
| Bee | (bee) | 1 | On eat (script 12): second STIM after 80 |
| Rocklice | (rocklice) | 1 | On eat (script 12): second STIM after 80 |
| Beetle | (beetle) | 1 | On eat (script 12): second STIM after 80 |
| Mosquito | (mosquito) | 1 | Bite script |
| Gnats | (gnats) | 1 | Three separate contexts |

**Creature Detector STIMs (3 8 1)**

| STIM | Intensity | Context |
|------|-----------|---------|
| 90 | 1 | Script 1 (activate) |
| 91 | 1 | Script 4 (pickup), only if from is family 4 |
| 92 | 1 | Script 3 (hit) |

**Fish Egg Launcher STIM (3 3 67)**

| STIM | Intensity | Context |
|------|-----------|---------|
| 92 | 1 | Script 3 (hit) |

### STIM Summary by Number

| STIM # | Meaning (wildlife context) | Sources |
|--------|---------------------------|---------|
| 80 | "I've eaten a critter" | ALL edible wildlife on script 12 |
| 86 | "I've been scared by animal" | Grazer only (script 1, creature activates) |
| 88 | "Something bit/stung me" | Ant, bee, wasp, beetle, rocklice, man-o-war, mosquito, gnats |
| 90 | "I've activated a gadget" | Creature detector, fish launcher |
| 91 | "I've picked up a gadget" | Creature detector (script 4) |
| 92 | "I've hit a gadget" | Creature detector, fish launcher |

---

## 5. CHEM INJECTIONS: COMPLETE AUDIT

### Wildlife-to-Creature Chemical Injections

There is exactly ONE direct chemical injection from wildlife into creatures in the entire C3 wildlife codebase:

| Source | Chemical | Amount | Context |
|--------|----------|--------|---------|
| Piranha bubble (1 1 24) | **117** | **0.5** | Injected into nearby norns (esee 4 1 0) during piranha attack |

Chemical 117's identity should be cross-referenced with the Creatures 3 chemistry catalogue. In the context of the medicine maker, `chem 117 .45` appears as one of the "cure everything" medicines, suggesting chemical 117 may be a toxin or harmful agent that the medicine addresses.

**Important note:** No other wildlife agent directly injects chemicals into creatures. The STIM system (STIM 80, 86, 88) is the primary feedback mechanism. STIMs trigger the creature's own neurochemistry via their brain/biochemistry genes. The wildlife does NOT directly manipulate creature chemicals: it sends neurological signals that the creature's genome interprets.

---

## 6. z_creaturesAffectingAnimals

**File:** `z_creaturesAffectingAnimals.cos`

This is the universal "creatures can hit animals" system. It runs as an install script (iscr) at world boot.

### Install Script
```
enum 2 0 0         : iterate ALL family-2 agents
  check attr bit 2 : if agent is carryable
  orrv bhvr 8      : add BHVR bit 8 (hittable by creatures)
```

This means: every family-2 agent that has the "carryable" attribute also gets the "hittable" flag. Creatures can punch/slap any carryable wildlife.

### Hit Script (2 0 0 3)
```
setv velx rand -10 10  : random horizontal velocity
setv vely rand -10 -1  : random upward velocity (always flung up)
```

When a creature hits ANY family-2 agent, the agent is flung in a random direction. This is purely physical: no STIM is applied to the creature from this script. (The creature's own `creatureDoneTo.cos` handles the STIM feedback for the act of hitting.)

### Remove Script
```
scrx 2 0 0 3  : removes the hit handler on world unload
```

**Brain implication:** The creature's decision to hit wildlife produces physical feedback (the animal flies away) but the neurological reward/punishment comes from the creature's own scripts, not from the wildlife.

---

## 7. CREATURE DETECTOR

**File:** `Creature detector.cos`: Classifier: 3 8 1

### Setup
- 4 instances at fixed world positions
- Each emits CA 18 at 0.2 (gadget smell: helps creatures find them)
- Toggleable on/off, type-selectable (norn/grendel/ettin)

### Creature Interaction Scripts

| Script | Trigger | STIM | Target | Notes |
|--------|---------|------|--------|-------|
| 1 (activate) | Creature activates | `stim writ from 90 1` | The creature | "I've activated a gadget" |
| 3 (hit) | Creature hits | `stim writ from 92 1` | The creature | "I've hit a gadget" |
| 4 (pickup) | Creature picks up | `stim writ targ 91 1` | The creature (if from is family 4) | "I've picked up a gadget" |

### Timer Behaviour
- Scans for creatures (4 1 0, 4 2 0, 4 3 0 = norn, grendel, ettin)
- Outputs proximity signal via port system
- Visual indicator changes based on detected creature type

---

## 8. LIFE EVENT FACTORY

**File:** `life event factory.cos`: Classifier: 1 2 24

### Agent Setup
- `new: simp 1 2 24 "blnk" 0 0 0`: invisible agent
- `attr 16`: not interactive

### Script 127: Life Event Monitor
Triggered by the engine's `hist` system with parameters `_p1_` (moniker) and `_p2_` (event index).

**Event Type Mapping:**
| `hist type` value | va01 (icon index) | Meaning |
|-------------------|-------------------|---------|
| 7 | 0 | Death |
| 11 | 1 | (Unknown: possibly world event) |
| 3 | 2 | Birth |
| 8 | 3 | (Unknown: possibly aging event) |

### Grettin Gate
```
doif game "Grettin" = 0
    doif 1 <> hist gnus _p1_   : if not a norn (genus 1)
        if death event: hist utxt _p1_ _p2_ "don't register"
        stop                    : skip non-norn events
    endi
endi
```
When Grettin mode is OFF (default), only norn (genus 1) life events are registered. When ON, all creature types (grendel, ettin) are tracked too.

### Music
- Birth: `strk 30 "events.mng\\Birth"`
- Death: `strk 20 "events.mng\\Death"`

### Photo Agent (1 2 37)
- Created on birth events (va00=3) if creature exists (`mtoc _p1_`)
- Auto-takes creature photo via `snap` after rand 90-120 ticks
- Stores via `hist foto` system

### Notification Icons (1 2 25)
- Scrolling UI icons for each life event
- `clac 1000`: clickable (triggers script 1000)
- Positioned via floating layout system, auto-scroll

---

## 9. CREATURE HISTORY

**File:** `creature history.cos`: Classifier: 1 2 23

### GAME Variables Referenced
| Variable | Value | Purpose |
|----------|-------|---------|
| `game "c3_after_shee_dates"` | 0 | Date format flag |
| `game "Grettin"` | 0/1 | Grettin mode (all species tracking) |
| `game "c3_default_focus"` |: | Default camera focus |
| `game "c3_inventory"` |: | Inventory agent reference |

### 4-Page Tabbed UI
| Page | Message | Content |
|------|---------|---------|
| Info | 1001 | Creature name, species, age, generation |
| Events | 1002 | Timeline of life events |
| Photos | 1003 | Photo gallery from `hist foto` |
| Genetics | 1004 | Moniker, crossover count, mutation count |

### Events Page: Tracked Event Types
| Type Code | Meaning |
|-----------|---------|
| 3 | Birth |
| 4 (stage 4) | Reached adulthood |
| 5, 8 | Pregnancy events |
| 6 | Mutation |
| 7 | Death |
| 10 | Clone |
| 12 | Export |
| 13 | Photo taken |
| 100 | Starter family |

### Genetics Page Data
- `stoi`: moniker string to integer
- `hist cros`: crossover count
- `hist mute`: mutation count

---

## 10. STARS & PICKUP PANEL

**File:** `stars and pickup panel.cos`

### Pickup Star Effect (Script 2 0 0 12345)
- Creates particle stars (1 1 46) with `"andtheworldexplodedintostars"` sprite
- Star velocity scales with `_p2_` parameter (1-5 intensity levels)
- Stars have accg 8, elas 40, random poses, tick rand 30-40

### Special Pickups (2 24 4)
When a creature picks up a special item (2 24 4), ov01 determines the effect:

| ov01 | Effect | Details |
|------|--------|---------|
| 1-4 | Progress tracking | Reads catalogue "Pick-ups", displays completion % |
| 7 | **Grettin unlock** | `setv game "Grettin" 1`, `setv game "c3_max_norns" 14` |
| 8 | (Text display only) | Reads catalogue entry |
| 9 | **Full creature pickup** | `setv game "engine_creature_pickup_status" 3`, `rgam` |

### Notification Panel (1 2 22)
- Floating compound agent with text display
- Shows pickup item description from catalogue
- Auto-destroys previous panel before creating new one

**Brain implications:** The Grettin unlock (ov01=7) is significant: it raises max norns from default to 14 and enables tracking of all creature species events. The creature pickup unlock (ov01=9) changes how the pointer interacts with creatures.

---

## 11. POPULATION MANAGEMENT

### Spawn Counts at World Init

| Species | Init Count | Method |
|---------|-----------|--------|
| Robin | From nest (2 17 1) | Nest timer spawns |
| Hummingbird | From nest (2 17 2) | Nest timer spawns |
| Woodpigeon | `totl 2 15 11 lt 18` cap | Init check |
| Grazer | Lifecycle-managed | Baby->juvenile->adult stages |
| Angelfish | ~14-16 total cap | Egg count check |
| Clownfish | Similar to angelfish | Egg count check |
| Handlefish | Similar to angelfish | Egg count check |
| Neon fish | Similar to angelfish | Egg count check |
| Nudibranch | `reps 3` | 3 at init |
| Meerkat | `reps 3` | 3 at init |
| Cuttlefish | 3 at init | Direct spawn |
| Piranha | Egg-based | 2 18 22 hatching system |

### Fish Egg Launcher (3 3 67)
- Uses `game "Bioenergy"` to charge
- Launches specific species eggs based on ov05:
  - 2 = wysteria (2 18 16)
  - 3 = angelfish (2 18 14)
  - 4 = neon (2 18 17)
  - 5 = handlefish (2 18 21)
  - 6 = clownfish (2 18 15)
- **Hard population cap: 75 total (eggs + adults) per species**
- STIM: script 3 `stim writ from 92 1` (hit)

### Self-Regulating Populations
- **Nudibranch:** Breeds when mature (ov05=2), spawns 2 offspring, then dies. Net population stable.
- **Robin/Hummingbird:** Nest-based respawn timers.
- **Sharkling:** Parent dies after reproduction (ov80=1). 1-for-1 or 1-for-2 replacement.
- **All fish:** Egg-based reproduction with population count checks before spawning.

---

## 12. CA EMISSIONS FROM WILDLIFE

| Agent | CA Channel | Amount | Meaning |
|-------|-----------|--------|---------|
| Angelfish | 6 | 0.15 | Food smell |
| Clownfish | 6 | 0.15 | Food smell |
| Neon fish | 6 | 0.15 | Food smell |
| Creature detector | 18 | 0.2 | Gadget smell |

CA channel 6 = food/critter smell. This is how creatures can detect nearby fish: the CA system propagates through rooms and creatures navigate toward CA gradients.

---

## 13. ROOM NUTRIENT MODIFICATION ON DEATH

When wildlife dies, many species modify room properties, feeding the ecosystem:

| Species | altr channel 3 (organic) | altr channel 4 (nutrients) |
|---------|-------------------------|---------------------------|
| Dead butterfly (2 10 11) | +0.1 | +0.1 |
| Dead caterpillar (2 10 12) | +0.1 | +0.1 |
| Dead stickleback (2 10 7) | +0.2 | +0.1 |
| Dead hedgehog (2 10 15) | (present) | (present) |
| Dead hoppity (2 10 22) | +0.4 | +0.4 |
| Dead meerkat | +0.2 | +0.4 |
| Dead dragonfly | (present) | (present) |

This creates a nutrient cycle: dead animals enrich rooms, which helps plants grow, which feeds herbivores.

---

## 14. SURPRISING FINDINGS & BRAIN IMPLICATIONS

### 14.1 STIM 80 Intensity Varies by Species: This is a Learning Signal

The most important finding for NORNBRAIN: **STIM 80 intensity is NOT uniform.** It ranges from 1 to 5 depending on what the creature eats:

- Intensity 1: Small critters (butterfly, caterpillar, nymph, small fish, eggs, snail, wasp, ant, bee, beetle)
- Intensity 2: Medium animals (robin, dragonfly adult, woodpigeon nest, rocklice alt)
- Intensity 3: Larger animals (woodpigeon chick, man-o-war)
- Intensity 4: Large/valuable animals (hedgehog, stickleback, kingfisher, woodpigeon adult, hummingbird)
- Intensity 5: Rocklice (primary eat context: highest value critter)

**Brain implication:** The creature's brain receives a graded reward signal for eating different animals. A CfC/NCP network needs to distinguish these intensity levels to learn food preferences. This is NOT a binary ate/didn't-eat signal: it's an analog nutritional value indicator.

### 14.2 Only ONE Species Can Kill Creatures

Piranhas are the sole lethal wildlife. They both inject chem 117 AND call `dead`. This is the only direct creature-death mechanism in all wildlife scripts. All other wildlife is harmless to creatures.

### 14.3 The Grazer is the Only "Socially Interactive" Wildlife

The grazer (2 15 2) is the ONLY wildlife agent that responds differently when a creature activates it. Its script 1 checks `fmly eq 4` and applies STIM 86 specifically to the creature. All other wildlife treats creature interaction the same as any other interaction. This makes grazers unique training targets for creature behaviour.

### 14.4 Hummingbird Double-STIM

Hummingbird eat script calls `stim writ from 80 4` TWICE. This means eating a hummingbird gives double the STIM 80 signal at intensity 4: effectively an intensity-8 reward. This may be intentional (hummingbirds are rare/valuable) or a bug.

### 14.5 Dual-STIM Animals (80 + 88)

Several animals apply BOTH STIM 80 (ate critter) and STIM 88 (got stung) on eat: ant, bee, wasp, beetle, rocklice, man-o-war. This means eating these animals is both rewarding (food) and punishing (pain). The creature's brain must learn to weigh these competing signals. This is a rich training scenario for the CfC network.

### 14.6 The z_creaturesAffectingAnimals Script is Boot-Order Dependent

The `z_` prefix ensures it loads last (alphabetical boot order). It iterates ALL existing family-2 agents and adds hit capability. Any family-2 agent spawned AFTER boot that has the carryable attribute would need its own BHVR setup: which is why many individual .cos files set their own BHVR flags.

### 14.7 Cuttlefish Detects Creatures for Camouflage

The cuttlefish (2 15 20) scans for creatures (4 0 0) and changes its appearance when one is nearby. This is purely visual: no STIM, no interaction. But it means the cuttlefish is "aware" of creature presence, making it one of the few wildlife agents that actively responds to creatures without any brain feedback.

### 14.8 Wildlife Does NOT Use `stim writ targ` for Eat Scripts

All wildlife eat scripts use `stim writ from` (the creature that initiated the eat action), NOT `stim writ targ`. This is important: the STIM goes to the EATING creature, not to the eaten animal. The `from` variable in script 12 is the creature that issued the eat command.

### 14.9 No Wildlife Provides STIM on Pickup (Script 4)

No wildlife agent has a script 4 (pickup) that applies STIM to creatures. The only pickup STIM comes from gadgets (creature detector). Creatures picking up animals get no neurological feedback from the animal itself: only from their own internal `creatureDoneTo.cos` scripts.

### 14.10 Fish Emit CA 6 (Food Smell): Creatures Navigate to Them

Angelfish, clownfish, and neon fish all `emit 6 .15`. CA channel 6 is food smell. This means underwater rooms with fish populations generate a food smell gradient that creatures can follow. The creature's sensory system detects CA gradients, making fish populations act as navigational beacons.

### 14.11 The Piranha Chem 117 is Cross-Referenced in Medicine Maker

`medicine maker.cos` line 654 has `chem 117 .45` as part of a "cure everything" recipe. This confirms chemical 117 is a harmful/toxic substance: the piranha injects a toxin, and the medicine maker can cure it.

---

## APPENDIX: STIM NUMBER QUICK REFERENCE (Wildlife Context)

| STIM # | Meaning | Primary Sources |
|--------|---------|----------------|
| 80 | Ate critter/animal | All edible wildlife (script 12) |
| 86 | Scared by animal | Grazer (script 1, creature activates) |
| 88 | Bitten/stung | Ant, bee, wasp, beetle, rocklice, man-o-war, mosquito, gnats |
| 90 | Activated gadget | Creature detector, fish launcher |
| 91 | Picked up gadget | Creature detector |
| 92 | Hit gadget | Creature detector, fish launcher |
