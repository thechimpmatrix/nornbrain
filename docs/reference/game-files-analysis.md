# C3 Game Files Analysis
# Authoritative reference extracted from live Steam Creatures 3 Bootstrap, Catalogue, and Genetics files
# Generated 2026-03-29 via full read of game installation at:
# I:/SteamLibrary/steamapps/common/Creatures Docking Station/Creatures 3/
# Cross-verified 2026-04-26 against 1999 Cyberlife C3 source code at <PROJECT_ROOT>/C3sourcecode/engine/.
# Findings checked: 14 active decision neurons (matches NUMACTIONS=14 in CreatureConstants.h:55);
# 20 drive neurons (matches NUMDRIVES=20 in CreatureConstants.h:80); chemicals 204/205 = Reward/Punishment;
# 17 decn lobe neurons gene-encoded with 14 active (consistent with CreatureConstants enum + 3 spare slots).
# All claims in this doc verified consistent with stock C3 source. No factual corrections applied this pass.

---

## CRITICAL CORRECTIONS TO PRIOR KNOWLEDGE

**Reward chemical = 204, Punishment chemical = 205**: NOT 49/50.
Chemicals 49 and 50 are unnamed/unused. The actual reinforcement chemicals are:
- 204 = "Reward"
- 205 = "Punishment"

**Decision neuron count = 14 (indices 0–13)**, not 15. Actions are events 16–29 on classifier `4 0 0`.

**The "stim source" lobe (index 11, quad "stim") exists** as a 12th lobe. It tracks which agent category caused the last stimulus.

---

## 1. BRAIN LOBE ARCHITECTURE (from Brain.catalogue)

12 lobes total:

| Index | Quad ID | Full Name    | Neuron Type      | Neuron Count | Class         |
|-------|---------|--------------|------------------|--------------|---------------|
| 0     | attn    | attention    | Agent Categories | 40           | **Output**    |
| 1     | decn    | decision     | Creature Actions | 17           | **Output**    |
| 2     | verb    | verb         | Creature Actions | 17           | Input         |
| 3     | noun    | noun         | Agent Categories | 40           | Input         |
| 4     | visn    | vision       | Agent Categories | 40           | Input         |
| 5     | smel    | smell        | Agent Categories | 40           | Input         |
| 6     | driv    | drive        | Creature Drives  | 20           | Input         |
| 7     | sitn    | situation    | Situation Neurons| 9            | Input         |
| 8     | detl    | detail       | Detail Neurons   | 11           | Input         |
| 9     | resp    | response     | Creature Drives  | 20           | Input         |
| 10    | prox    | proximity    | Creature Drives  | 20           | Input         |
| 11    | stim    | stim source  | Agent Categories | 40           | Special       |

Output lobes: `attn`, `decn`
Input lobes: `verb`, `noun`, `visn`, `smel`, `driv`, `sitn`, `detl`, `resp`, `prox`
Brain parameters: chemical 213 (REM sleep), chemical 212 (Pre-REM sleep)

---

## 2. CREATURE ACTIONS (17 neurons in decn/verb lobes)

| Index | Name         | Event# | Notes                              |
|-------|--------------|--------|------------------------------------|
| 0     | look         | 16     | quiescent/idle                     |
| 1     | push         | 17     | activate1 on target                |
| 2     | pull         | 18     | activate2 on target                |
| 3     | deactivate   | 19     | stop/switch off target             |
| 4     | approach     | 20     | walk toward IT                     |
| 5     | retreat       | 21    | run away                           |
| 6     | get          | 22     | pick up target                     |
| 7     | drop         | 23     | drop held item                     |
| 8     | express      | 24     | express need / speak               |
| 9     | rest         | 25     | sleep (LOCKS script)               |
| 10    | left         | 26     | walk west (infinite loop)          |
| 11    | right        | 27     | walk east (infinite loop)          |
| 12    | eat          | 28     | eat target                         |
| 13    | hit          | 29     | attack target/creature             |
| 14    | up           |:      | unused                             |
| 15    | down         |:      | unused                             |
| 16    | exit         |:      | unused                             |

**Decision neuron → CAOS event mapping:** neuron N fires `scrp 4 0 0 (16+N)` on the creature.
Active neurons: 0–13 (14 actions). Neurons 14–16 unused in practice.

---

## 3. DECISION SCRIPT REFERENCE (creatureDecisions.cos)

Each action script runs on classifier `4 0 0 (16+N)`. Pattern for interactive actions:
`appr` → null check → `touc` → BHVR check → SORQ check (`va99`) → `stim writ targ N va99` → `mesg writ _it_ M`

| Neuron | Event | Action      | BHVR bit | Mesg to IT | Stim (success) | Stim (fail) | Blocking? |
|--------|-------|-------------|----------|------------|----------------|-------------|-----------|
| 0      | 16    | Quiescent   |:        |:          | 12             |:           | No        |
| 1      | 17    | Activate1   | 1        | 0          | 13 (va99-gated)| 0           | No        |
| 2      | 18    | Activate2   | 2        | 1          | 14 (va99-gated)| 0           | No        |
| 3      | 19    | Deactivate  | 4        | 2          | 15 (va99-gated)| 0           | No        |
| 4      | 20    | Approach    |:        |:          |: (none!)      | 0           | No        |
| 5      | 21    | Retreat     |:        |:          | 17             |:           | No        |
| 6      | 22    | Pickup      | 32       | 4          | 18 (va99-gated)| 0           | No        |
| 7      | 23    | Drop        |:        | 5          | 19 (va99-gated)| 0           | No        |
| 8      | 24    | Express     |:        |:          | 20             |:           | No        |
| 9      | 25    | Rest/Sleep  |:        |:          | 21+22 (loop)   |:           | **YES**   |
| 10     | 26    | Walk West   |:        |:          | 23 (loop)      |:           | ∞ loop    |
| 11     | 27    | Walk East   |:        |:          | 23 (loop)      |:           | ∞ loop    |
| 12     | 28    | Eat         | 16       | 4+12       | 26 (va99-gated)| 0           | No        |
| 13     | 29    | Hit         | 8        | 3          | 44 (va99-gated)| 0           | No        |

**va99 gate:** `sorq fmly gnus spcs N` checks if target has a script for the action. va99=1 if yes, va99=0 if no. Stimulus fires at this intensity: so the stimulus only teaches when the target supports the action.

**Stim 0 = Frustration/Disappointment**: fires on ALL failed actions.

**Sleep lock:** Script 25 calls `lock`. Creature is locked until `driv 7 < 0.10 AND driv 6 < 0.10` (sleepiness AND tiredness both below 10%). Bridge must detect `aslp` state and suppress outputs.

**Walk loops:** Scripts 26/27 are `loop ... ever`. They never terminate; rely on engine interruption from next brain decision.

**No GAME variables are used or modified by any decision script.** Our `lnn_` namespace is safe.

---

## 4. DRIVE SYSTEM (20 neurons in driv lobe)

From `ChemicalNames.catalogue`: the `drive_chemical_numbers` array:

| Drive # | Drive Name          | Chemical # | Backup Chem # |
|---------|---------------------|------------|----------------|
| 0       | hurt / pain         | 148        | 131            |
| 1       | hungry for protein  | 149        | 132            |
| 2       | hungry for starch   | 150        | 133            |
| 3       | hungry for fat      | 151        | 134            |
| 4       | cold                | 152        | 135            |
| 5       | hot                 | 153        | 136            |
| 6       | tired               | 154        | 137            |
| 7       | sleepy              | 155        | 138            |
| 8       | lonely              | 156        | 139            |
| 9       | crowded             | 157        | 140            |
| 10      | scared / fear       | 158        | 141            |
| 11      | bored               | 159        | 142            |
| 12      | angry               | 160        | 143            |
| 13      | friendly / sex      | 161        | 144            |
| 14      | homesick / comfort  | 162        | 145            |
| 15      | low down (nav)      | 199 (Up)   |:              |
| 16      | high up (nav)       | 200 (Down) |:              |
| 17      | trapped (nav)       | 201 (Exit) |:              |
| 18      | trapped2 (nav)      | 202 (Enter)|:              |
| 19      | patient (nav)       | 203 (Wait) |:              |

Drive-to-CAOS index verified from `creatureDecisions.cos`:
- `driv 0` = Pain (checked > 0.5 for retreat animation)
- `driv 6` = Tiredness (sleep exit: < 0.10)
- `driv 7` = Sleepiness (sleep entry: > 0.60, exit: < 0.10)
- `driv 9` = Crowdedness (checked > 0.25 for retreat)
- `driv 10` = Fear (checked > 0.25 for retreat)
- `driv 13` = Sex drive (checked > 0.15 for mating eligibility)

---

## 5. COMPLETE CHEMICAL INDEX TABLE (0–255)

Source: `ChemicalNames.catalogue` + `Materia Medica.catalogue`

| #   | Name                        | Category          |
|-----|-----------------------------|-------------------|
| 0   | (placeholder: no chem)     | System            |
| 1   | Lactate                     | Metabolism        |
| 2   | Pyruvate                    | Metabolism        |
| 3   | Glucose                     | Metabolism        |
| 4   | Glycogen                    | Metabolism        |
| 5   | Starch                      | Metabolism        |
| 6   | Fatty Acid                  | Metabolism        |
| 7   | Cholesterol                 | Metabolism        |
| 8   | Triglyceride                | Metabolism        |
| 9   | Adipose Tissue              | Metabolism        |
| 10  | Fat                         | Metabolism        |
| 11  | Muscle Tissue               | Metabolism        |
| 12  | Protein                     | Metabolism        |
| 13  | Amino Acid                  | Metabolism        |
| 14–16 | (unnamed)                 |:                 |
| 17  | Downatrophin                | Neurotrophin      |
| 18  | Upatrophin                  | Neurotrophin      |
| 19–23 | (unnamed)                 |:                 |
| 24  | Dissolved carbon dioxide    | Respiratory       |
| 25  | Urea                        | Waste             |
| 26  | Ammonia                     | Waste             |
| 27–28 | (unnamed)                 |:                 |
| 29  | Air                         | Respiratory       |
| 30  | Oxygen                      | Respiratory       |
| 31–32 | (unnamed)                 |:                 |
| 33  | Water                       | Basic need        |
| 34  | Energy                      | Core              |
| 35  | ATP                         | Energy cycle      |
| 36  | ADP                         | Energy cycle      |
| 37–38 | (unnamed)                 |:                 |
| 39  | Arousal Potential           | Reproductive      |
| 40  | Libido lowerer              | Reproductive      |
| 41  | Opposite Sex Pheromone      | Reproductive      |
| 42–45 | (unnamed)                 |:                 |
| 46  | Oestrogen                   | Reproductive      |
| 47  | (unnamed)                   |:                 |
| 48  | Progesterone                | Reproductive      |
| 49–52 | (unnamed)                 |:                 |
| 53  | Testosterone                | Reproductive      |
| 54  | Inhibin                     | Reproductive      |
| 55–65 | (unnamed)                 |:                 |
| 66  | Heavy Metals                | Toxin             |
| 67  | Cyanide                     | Toxin             |
| 68  | Belladonna                  | Toxin             |
| 69  | Geddonase                   | Toxin             |
| 70  | Glycotoxin                  | Toxin             |
| 71  | Sleep toxin                 | Toxin             |
| 72  | Fever toxin                 | Toxin             |
| 73  | Histamine A                 | Toxin             |
| 74  | Histamine B                 | Toxin             |
| 75  | Alcohol                     | Toxin             |
| 76–77 | (unnamed)                 |:                 |
| 78  | ATP Decoupler               | Toxin             |
| 79  | Carbon monoxide             | Toxin             |
| 80  | Fear toxin                  | Toxin             |
| 81  | Muscle toxin                | Toxin             |
| 82  | Antigen 0                   | Immune            |
| 83  | Antigen 1                   | Immune            |
| 84  | Antigen 2                   | Immune            |
| 85  | Antigen 3                   | Immune            |
| 86  | Antigen 4                   | Immune            |
| 87  | Antigen 5                   | Immune            |
| 88  | Antigen 6                   | Immune            |
| 89  | Antigen 7                   | Immune            |
| 90  | Wounded                     | Health            |
| 91  | (unnamed)                   |:                 |
| 92  | Medicine one                | Medicine          |
| 93  | Anti-oxidant                | Medicine          |
| 94  | Prostaglandin               | Medicine          |
| 95  | EDTA                        | Medicine          |
| 96  | Sodium thiosulphite         | Medicine          |
| 97  | Arnica                      | Medicine          |
| 98  | Vitamin E                   | Medicine          |
| 99  | Vitamin C                   | Medicine          |
| 100 | Antihistamine               | Medicine          |
| 101 | (unnamed)                   |:                 |
| 102 | Antibody 0                  | Immune            |
| 103 | Antibody 1                  | Immune            |
| 104 | Antibody 2                  | Immune            |
| 105 | Antibody 3                  | Immune            |
| 106 | Antibody 4                  | Immune            |
| 107 | Antibody 5                  | Immune            |
| 108 | Antibody 6                  | Immune            |
| 109 | Antibody 7                  | Immune            |
| 110–111 | (unnamed)               |:                 |
| 112 | Anabolic steroid            | Organ             |
| 113 | Pistle                      | Organ             |
| 114 | Insulin                     | Organ             |
| 115 | Glycolase                   | Enzyme            |
| 116 | Dehydrogenase               | Enzyme            |
| 117 | Adrenalin                   | Hormone           |
| 118 | Grendel nitrate             | Species-specific  |
| 119 | Ettin nitrate               | Species-specific  |
| 120–123 | (unnamed)               |:                 |
| 124 | Activase                    | Enzyme            |
| 125 | Life                        | Core              |
| 126 | (unnamed)                   |:                 |
| 127 | Injury                      | Health            |
| 128 | Stress                      | Health            |
| 129 | Sleepase                    | Enzyme            |
| 130 | (unnamed)                   |:                 |
| 131 | Pain backup                 | Drive backup      |
| 132 | Hunger for protein backup   | Drive backup      |
| 133 | Hunger for carb backup      | Drive backup      |
| 134 | Hunger for fat backup       | Drive backup      |
| 135 | Coldness backup             | Drive backup      |
| 136 | Hotness backup              | Drive backup      |
| 137 | Tiredness backup            | Drive backup      |
| 138 | Sleepiness backup           | Drive backup      |
| 139 | Loneliness backup           | Drive backup      |
| 140 | Crowded backup              | Drive backup      |
| 141 | Fear backup                 | Drive backup      |
| 142 | Boredom backup              | Drive backup      |
| 143 | Anger backup                | Drive backup      |
| 144 | Sex drive backup            | Drive backup      |
| 145 | Comfort backup              | Drive backup      |
| 146–147 | (unnamed)               |:                 |
| 148 | **Pain**                    | **DRIVE 0**       |
| 149 | **Hunger for protein**      | **DRIVE 1**       |
| 150 | **Hunger for carbohydrate** | **DRIVE 2**       |
| 151 | **Hunger for fat**          | **DRIVE 3**       |
| 152 | **Coldness**                | **DRIVE 4**       |
| 153 | **Hotness**                 | **DRIVE 5**       |
| 154 | **Tiredness**               | **DRIVE 6**       |
| 155 | **Sleepiness**              | **DRIVE 7**       |
| 156 | **Loneliness**              | **DRIVE 8**       |
| 157 | **Crowded**                 | **DRIVE 9**       |
| 158 | **Fear**                    | **DRIVE 10**      |
| 159 | **Boredom**                 | **DRIVE 11**      |
| 160 | **Anger**                   | **DRIVE 12**      |
| 161 | **Sex drive**               | **DRIVE 13**      |
| 162 | **Comfort**                 | **DRIVE 14**      |
| 163–164 | (unnamed)               |:                 |
| 165 | CA smell 0 (Sound)          | CA smell          |
| 166 | CA smell 1 (Light)          | CA smell          |
| 167 | CA smell 2 (Heat)           | CA smell          |
| 168 | CA smell 3 (Water/Precip)   | CA smell          |
| 169 | CA smell 4 (Nutrient)       | CA smell          |
| 170 | CA smell 5 (Water)          | CA smell          |
| 171 | CA smell 6 (Protein)        | CA smell          |
| 172 | CA smell 7 (Carbohydrate)   | CA smell          |
| 173 | CA smell 8 (Fat)            | CA smell          |
| 174 | CA smell 9 (Flowers)        | CA smell          |
| 175 | CA smell 10 (Machinery)     | CA smell          |
| 176 | CA smell 11                 | CA smell          |
| 177 | CA smell 12 (Norn)          | CA smell          |
| 178 | CA smell 13 (Grendel)       | CA smell          |
| 179 | CA smell 14 (Ettin)         | CA smell          |
| 180 | CA smell 15 (Norn home)     | CA smell          |
| 181 | CA smell 16 (Grendel home)  | CA smell          |
| 182 | CA smell 17 (Ettin home)    | CA smell          |
| 183 | CA smell 18 (Gadget/Mach)   | CA smell          |
| 184 | CA smell 19                 | CA smell          |
| 185–186 | (unnamed)               |:                 |
| 187 | Stress (Hunger for Carb)    | Stress variant    |
| 188 | Stress (Hunger for Protein) | Stress variant    |
| 189 | Stress (Hunger for Fat)     | Stress variant    |
| 190 | Stress (Anger)              | Stress variant    |
| 191 | Stress (Fear)               | Stress variant    |
| 192 | Stress (Pain)               | Stress variant    |
| 193 | Stress (Sleep)              | Stress variant    |
| 194 | Stress (Tired)              | Stress variant    |
| 195 | Stress (Crowded)            | Stress variant    |
| 196–197 | (unnamed)               |:                 |
| 198 | Brain chemical 1 / Disappointment | Brain      |
| 199 | Up (nav drive 15)           | Brain / Nav       |
| 200 | Down (nav drive 16)         | Brain / Nav       |
| 201 | Exit (nav drive 17)         | Brain / Nav       |
| 202 | Enter (nav drive 18)        | Brain / Nav       |
| 203 | Wait (nav drive 19)         | Brain / Nav       |
| **204** | **Reward**              | **Brain: reinforcement** |
| **205** | **Punishment**          | **Brain: reinforcement** |
| 206 | Brain chemical 9            | Brain             |
| 207 | Brain chemical 10           | Brain             |
| 208 | Brain chemical 11           | Brain             |
| 209 | Brain chemical 12           | Brain             |
| 210 | Brain chemical 13           | Brain             |
| 211 | Brain chemical 14           | Brain             |
| 212 | Pre-REM sleep               | Sleep cycle       |
| 213 | REM sleep                   | Sleep cycle       |
| 214–255 | (unnamed)               |:                 |

---

## 6. COMPLETE STIMULUS MAP

Stimuli are integer indices into the creature's stimulus gene table. `stim writ target N intensity`.

| Stim # | Meaning                             | Applied to | Typical intensity | Fired by                              |
|--------|-------------------------------------|------------|-------------------|---------------------------------------|
| 0      | Frustration / failed action         | self       | 1                 | Every failed action, wall bump        |
| 1      | Patted by Hand                      | self       | 1                 | Event 1 from pointer                  |
| 2      | Patted by creature                  | self       | 1                 | Event 1 from creature                 |
| 3      | Slapped by Hand                     | self       | 1                 | Event 0/3 from pointer                |
| 4      | Hit by creature                     | self       | variable 1–2      | Event 45 (age-scaled)                 |
| 12     | Mating stimulus                     | self       | 1                 | Script 32 (mating loop, per-tick)     |
| 13     | Activated object (push/kiss)        | self       | 0 or 1 (va99)     | Script 17; partial mating             |
| 14     | Deactivated/pulled object           | self       | 0 or 1 (va99)     | Script 18                             |
| 15     | Switched off object                 | self       | 0 or 1 (va99)     | Script 19                             |
| 17     | Retreated                           | self       | 1                 | Script 21                             |
| 18     | Picked up object                    | self       | 0 or 1 (va99)     | Script 22                             |
| 19     | Dropped object                      | self       | 0 or 1 (va99)     | Script 23                             |
| 20     | Expressed need / spoke              | self       | 1                 | Script 24                             |
| 21     | Began resting/sleep                 | self       | 1                 | Script 25 entry; involuntary event 69 |
| 22     | Sleeping (ongoing)                  | self       | 1                 | Script 25 per-loop; event 70 (dying)  |
| 23     | Walking                             | self       | 1                 | Scripts 26/27 per-loop                |
| 25     | Sludge gun hit                      | self       | 1                 | Sludge gun agent                      |
| 26     | Ate something                       | self       | 0 or 1 (va99)     | Script 28                             |
| 28     | Flinch / pain reaction              | self       | 1                 | Involuntary event 64                  |
| 29     | Laid an egg                         | self       | 1                 | Script 65                             |
| 30     | Sneezed                             | self       | 1                 | Involuntary event 66                  |
| 31     | Coughed                             | self       | 1                 | Involuntary event 67                  |
| 32     | Shivered                            | self       | 1                 | Involuntary event 68                  |
| 33     | Deep sleep / dream recovery         | self       | 1                 | Involuntary event 69 per-loop         |
| 35     | Flatulence                          | self       | 1                 | Involuntary event 71                  |
| 39     | Impact/fall damage                  | self       | 1 (×1–10)         | Event 6 (collision), repeated         |
| 44     | Hit a creature (attacker)           | self       | 1                 | Script 45 (aggressor)                 |
| 45     | Mated successfully                  | self       | 1                 | Script 34 (both partners)             |
| 46     | Patted by same-genus diff-species   | self       | 1                 | Event 1, species mismatch             |
| 47     | Patted by exact same species        | self       | 1                 | Event 1, species match                |
| 62     | Plant proximity                     | self       | 1                 | Decorative plants                     |
| 67     | Sludge gun fired                    | self       | 1                 | Sludge gun                            |
| 77     | Ate vegetation                      | self       | 1–3               | Grass, fungi, pumperspikel, etc.      |
| 78     | Ate fruit                           | self       | 1                 | Fruit agents                          |
| 79     | Ate food (carrot, cheese)           | self       | 1                 | Food agents                           |
| 80     | Interacted with animal              | self       | 2–5               | Critters/creatures on activation      |
| 81     | Ate bad/decayed food                | self       | 1                 | Rotting food                          |
| 88     | Bitten by pest                      | self       | 1                 | Ants, gnats, wasps, mosquitoes        |
| 90     | Machine activated                   | self       | 1                 | Gadgets/machinery                     |
| 91     | Machine user feedback               | self       | 1                 | Specific machine interaction          |
| 92     | Machine deactivated                 | self       | 1                 | Machinery                             |
| 93     | Picked up an egg                    | self       | 1                 | Egg pickup (creature, not hand)       |
| 94     | Lift ride                           | self       | 1                 | Lifts                                 |
| 97     | Played with toy                     | self       | 1                 | Toys                                  |

---

## 7. AGENT CATEGORIES (40 neurons: attn/noun/visn/smel/stim lobes)

| Index | Category     | Classifier   |
|-------|--------------|--------------|
| 0     | self         | 999 999 999  |
| 1     | hand         | 2 1 0        |
| 2     | door         | 2 2 0        |
| 3     | seed         | 2 3 0        |
| 4     | plant        | 2 4 0        |
| 5     | weed         | 2 5 0        |
| 6     | leaf         | 2 6 0        |
| 7     | flower       | 2 7 0        |
| 8     | fruit        | 2 8 0        |
| 9     | manky        | 2 9 0        |
| 10    | detritus     | 2 10 0       |
| 11    | food         | 2 11 0       |
| 12    | button       | 2 12 0       |
| 13    | bug          | 2 13 0       |
| 14    | pest         | 2 14 0       |
| 15    | critter      | 2 15 0       |
| 16    | beast        | 2 16 0       |
| 17    | nest         | 2 17 0       |
| 18    | animal egg   | 2 18 0       |
| 19    | weather      | 2 19 0       |
| 20    | bad          | 2 20 0       |
| 21    | toy          | 2 21 0       |
| 22    | incubator    | 2 22 0       |
| 23    | dispenser    | 2 23 0       |
| 24    | tool         | 2 24 0       |
| 25    | potion       | 2 25 0       |
| 26    | elevator     | 3 1 0        |
| 27    | teleporter   | 3 2 0        |
| 28    | machinery    | 3 3 0        |
| 29    | creature egg | 3 4 0        |
| 30    | norn home    | 3 5 0        |
| 31    | grendel home | 3 6 0        |
| 32    | ettin home   | 3 7 0        |
| 33    | gadget       | 3 8 0        |
| 34    | something    | 3 9 0        |
| 35    | vehicle      | 3 10 0       |
| 36    | norn         | 4 1 0        |
| 37    | grendel      | 4 2 0        |
| 38    | ettin        | 4 3 0        |
| 39    | something    | 4 4 0        |

---

## 8. SITUATION NEURONS (9 neurons in sitn lobe)

| Index | Description                                              |
|-------|----------------------------------------------------------|
| 0     | I am this old (life stage)                               |
| 1     | I am inside a vehicle                                    |
| 2     | I am carrying something                                  |
| 3     | I am being carried                                       |
| 4     | I am falling                                             |
| 5     | I am near a creature of the opposite sex and my genus    |
| 6     | I am musically at this mood                              |
| 7     | I am musically at this threat level                      |
| 8     | I am the selected norn                                   |

---

## 9. DETAIL NEURONS (11 neurons in detl lobe)

| Index | Description                                     |
|-------|-------------------------------------------------|
| 0     | It is being carried by me                       |
| 1     | It is being carried by someone else             |
| 2     | It is this close to me                          |
| 3     | It is a creature                                |
| 4     | It is my sibling                                |
| 5     | It is my parent                                 |
| 6     | It is my child                                  |
| 7     | It is of opposite sex and my genus              |
| 8     | It is of this size                              |
| 9     | It is smelling this much                        |
| 10    | It is stopped                                   |

---

## 10. BRAIN INPUT VECTOR (for the 89-input CfC brain)

| Feature group          | Count | Source                         |
|------------------------|-------|--------------------------------|
| Drive lobe (driv)      | 20    | Chemicals 148–162, 199–203     |
| Attention/noun (attn)  | 40    | Agent categories 0–39          |
| Situation (sitn)       | 9     | Situation neurons 0–8          |
| Detail (detl)          | 11    | Detail neurons 0–10            |
| **Total**              | **80**| (89 with extra biochem inputs) |

Additional 9 inputs to reach 89:
- Reinforcement chemicals: 204 (Reward), 205 (Punishment)
- Sleep state: 212 (Pre-REM), 213 (REM)
- Neurotrophin: 17 (Downatrophin), 18 (Upatrophin)
- Health: 125 (Life), 127 (Injury), 128 (Stress)

---

## 11. GAME VARIABLE NAMESPACE (safe prefix: `lnn_`)

The following prefixes are TAKEN and must not be used:

| Prefix/Name              | Owner                          |
|--------------------------|--------------------------------|
| `engine_*`               | C++ engine internals (reserved)|
| `c3_*`                   | C3 game logic                  |
| `ds_*`                   | Docking Station game logic     |
| `Bioenergy`              | Creator/Replicator currency    |
| `Grettin`                | Ettin/Grendel unlock flag      |
| `breeding_limit`         | DS population system           |
| `total_population`       | DS population system           |
| `scared`                 | Toolbar (read, never set)      |
| `status`                 | DS network                     |
| `pntr_*`                 | Pointer colours                |
| `chat_plane*`            | DS chat                        |
| `camera *`               | DS comms cameras               |
| `*_MaxPop_*`             | Ecosystem agents               |
| `*_LocalSphere`          | Ecosystem agents               |
| `hlm_plasma`             | DS Learning Machine            |
| `0kAy_GrEndELs_*`        | Patch marker (obfuscated)      |

**Safe prefix for NORNBRAIN IPC:** `lnn_`
Examples: `lnn_bridge_active`, `lnn_tick`, `lnn_cmd`, `lnn_resp`, `lnn_ver`

Key C3 world variables:
- `game "engine_synchronous_learning"` = 0 (async learning, default)
- `game "c3_max_norns"` = 10 (overridable to 14 by stars panel)
- `game "c3_max_creatures"` = 14
- `game "Grettin"` = 0 in C3, 1 in DS

---

## 12. INVOLUNTARY ACTION SYSTEM

Events that fire on the creature WITHOUT a brain decision, managed by the engine via latency groups:

| Event # | Name            | Latency group | Min–Max ticks | Blocking? | Stim |
|---------|-----------------|---------------|---------------|-----------|------|
| 64      | Flinch/pain     | 0             | 25–50         | No        | 28   |
| 66      | Sneeze          | 2             | 25–35         | No        | 30   |
| 67      | Cough           | 3             | 25–35         | No        | 31   |
| 68      | Shiver          | 4             | 30–90         | No        | 32   |
| 69      | Fall asleep     | 5             | 90–190        | **YES**   | 21+33|
| 70      | Dying moan      | 6             | 70–210        | No        | 22   |
| 71      | Flatulence      | 7             | 10–20         | No        | 35   |
| 72      | Death           |:             | immediate     | **YES**   |:    |

Event 69 (sleep) and 72 (death) use `lock`. No brain output can interrupt a locked script.

**Death sequence:** `creatureDecisions.cos` → fires `4 0 0 72` → `lock` → animation → `kill _p1_` mid-animation → creature agent is destroyed.

**Sneezing/coughing:** Both send `mesg wrt+ ownr 300` which spawns/repositions a bacteria cloud agent (classifier `2 32 23`). These clouds are pooled, not freshly spawned each time.

---

## 13. BREEDING SYSTEM SUMMARY

Mating gates (ALL must pass):
1. `driv 13 gt 0.15` (sex drive > 15%): both creatures
2. `cage ge 2` (youth or older, life stage ≥ 2): both creatures
3. `gnus` match (same genus)
4. `spcs` mismatch (different species ID: prevents self-mating)
5. `byit ne 0` (physically adjacent)
6. Target not dead or asleep
7. Population caps not exceeded (`c3_max_norns`, `c3_max_creatures`)

Stimulus 45 fires on both partners after successful mating.
Stimulus 29 fires on egg-laying.
Stimulus 93 fires when a creature (not hand) picks up an egg.

---

## 14. CHEMICALS 82–89: ACTION CHEMICALS (ANTIGENS)

From `creatureDecisions.cos` script 24 (Express Need):
Chemicals 82–89 are the **antigen chemicals** (Antigen 0–7). The express-need script checks if any antigen > 0.2 before the creature speaks its drive. If elevated antigens are present, the creature suppresses its need-expression, suggesting illness suppresses communication.

---

## 15. CA SMELL SYSTEM

CA (Cellular Automata) channels 0–19 diffuse through the environment. Each maps to a chemical (165–184) that the creature's smell lobe reads.

| CA # | Chem | Name           | Who emits it                     |
|------|------|----------------|----------------------------------|
| 0    | 165  | Sound          | Various (music, noisy agents)    |
| 1    | 166  | Light          | Light sources                    |
| 2    | 167  | Heat           | Heaters, hot areas               |
| 3    | 168  | Water/Precip   | Water agents                     |
| 4    | 169  | Nutrient       | Food/plant nutrients             |
| 5    | 170  | Water          | Water agents (duplicate)         |
| 6    | 171  | Protein        | Food agents (`cacl 2 8 0 6`)     |
| 7    | 172  | Carbohydrate   | Seeds (`cacl 2 3 0 7`)           |
| 8    | 173  | Fat            | Food (`cacl 2 11 0 8`)           |
| 9    | 174  | Flowers        | Flower agents                    |
| 10   | 175  | Machinery      | Machinery (`cacl 3 3 0 10`)      |
| 11   | 176  | CA smell 11    | Certain machinery                |
| 12   | 177  | Norn           | Norns (`cacl 4 1 0 12`)          |
| 13   | 178  | Grendel        | Grendels (`cacl 4 2 0 13`)       |
| 14   | 179  | Ettin          | Ettins (`cacl 4 3 0 14`)         |
| 15   | 180  | Norn home      | Norn home agents                 |
| 16   | 181  | Grendel home   | Grendel home agents              |
| 17   | 182  | Ettin home     | Ettin home agents                |
| 18   | 183  | Gadget/Mach    | Most gadgets/engineering         |
| 19   | 184  | (unnamed)      |:                                |

Home smell emitters are static invisible agents at fixed map coordinates:
- Norn home: (780,712) strong, (2360,467) weak
- Grendel home: (1948,2310)
- Ettin home: (4872,704), (6200,704), (6363,704)

---

## 16. BRAIN-ADJACENT CAOS COMMANDS (used by game scripts)

The following CAOS commands interact with or observe the brain. No Bootstrap script ever calls BRNL/BRNP/BRNS/BRND directly: all brain interaction is indirect through the biochemistry/stimulus pathway.

| Command | Purpose                                           |
|---------|---------------------------------------------------|
| `stim writ targ N I` | Fire stimulus gene N at intensity I on creature |
| `driv N`            | Read drive level (float 0.0–1.0)                |
| `chem N`            | Read chemical concentration (float 0.0–1.0)     |
| `aslp N`            | Set/clear sleep state (1=sleep, 0=wake)         |
| `drea N`            | Enable/disable dream state (1=dreaming)         |
| `zomb N`            | Freeze/unfreeze creature movement               |
| `forf targ`         | Force-face toward target agent                  |
| `like targ`         | Adjust creature's opinion of target             |
| `sayn`              | Creature speaks its current need                |
| `face N`            | Set facial expression                           |
| `shou word`         | Order creature to perform a vocab word          |
| `vocb`              | Teach creature the word for its attention object|
| `lock` / `unlk`     | Lock/unlock script execution                    |
| `ltcy G min max`    | Set involuntary action latency (group, ticks)   |
| `sorq F G S N`      | Query whether agent F/G/S has script N          |
| `byit`              | Boolean: did approach/touch succeed?            |
| `cage`              | Life stage (0=baby to 6=senile)                 |
| `dead`              | Boolean: is creature dead?                      |
| `uncs`              | Boolean: is creature unconscious?               |

---

## 17. POSE NUMBERS (creature emotional/action state, from creatureDecisions.cos)

| Pose # | Inferred meaning                        |
|--------|-----------------------------------------|
| 12     | Neutral standing                        |
| 33–34  | Content/satisfied                       |
| 35     | Pain expression (drive 0 high)          |
| 36     | Cold/temperature expression             |
| 37     | Hunger/escape expression                |
| 38     | Tired expression                        |
| 39, 45 | Frustrated/confused                     |
| 42     | Boredom expression                      |
| 46–47  | Shiver animation frames                 |
| 49–56  | Retreat animation frames                |
| 51     | Crowded expression                      |
| 57     | Drowsy/eyes-closing                     |
| 58     | Sleep/lying down                        |
| 59–60  | Yawn phases / walk entry                |
| 71–72  | Sneeze animation                        |
| 73–74  | Eating poses                            |
| 75     | Flinch                                  |
| 77     | Death pose                              |
| 89     | Hunger for protein expression           |
| 98–101 | Cough animation                         |
| 106    | Sneeze release                          |
| 108–109| Egg-laying                              |
| 111–114| Hit/attack animation                    |
| 121    | Boredom/loneliness expression           |

---

## 18. NEED EXPRESSION DRIVE-TO-POSE MAP (script 24)

| Drive index | Pose/animation | Drive name        |
|-------------|----------------|-------------------|
| 0           | 35             | Pain              |
| 1           | 89             | Hunger for protein|
| 2           | 47             | Hunger for carb   |
| 3           | 36             | Hunger for fat    |
| 4           | 37             | Coldness          |
| 5           | 37             | Hotness           |
| 6           | 12             | Tiredness (neutral)|
| 7           | 38             | Sleepiness        |
| 8           | 42             | Loneliness        |
| 9           | 51             | Crowdedness       |
| 10          | anim [040 041] | Fear              |
| 11          | 121            | Boredom           |
| 12          | anim [042 043] | Anger             |

---

## 19. KEY ARCHITECTURAL FACTS FOR THE BRIDGE

1. **Decision scripts are the execution layer.** The bridge writes to the brain (via SPNL or equivalent), the engine fires these scripts, the scripts apply STIMs, STIMs inject chemicals. Do not bypass this chain.

2. **Attention (`_it_`) must be set BEFORE decision actions 1–3, 6–7, 12–13.** If `_it_` is null, the interactive actions fail immediately with stim 0.

3. **Sleep detection:** Check `aslp` command return value. If 1, creature is asleep and locked: suppress all outputs. Sleep only ends when `driv 7 < 0.10 AND driv 6 < 0.10`.

4. **Death detection:** Check `dead` flag. When 1, creature is dying/dead: clean up bridge state.

5. **Reinforcement loop is automatic.** STIMs from decision scripts feed into chemical changes. Chemicals change drive levels. Drive levels change brain inputs next tick. The bridge does NOT need to implement reward/punishment injection: the game's stimulus genes do that.

6. **Chemicals 204 (Reward) and 205 (Punishment)** are the final outputs of the stimulus gene system. They are visible as inputs to the CfC brain if we read them with `chem 204` / `chem 205`.

7. **GAME variable safe prefix: `lnn_`**: no collision with any existing C3/DS variable.

8. **`engine_synchronous_learning` = 0** by default: brain learning is asynchronous. Our bridge IPC does not need to synchronise tightly with learning ticks.

---

# PART 2: COMPREHENSIVE GAME SYSTEMS ANALYSIS
# Generated 2026-03-29 via full read of all 320 readable C3 game files

---

## 20. WORLD MAP STRUCTURE

### Metarooms (10 total)

| ID | Name                  | Key coordinates (approx centre) | Notes                              |
|----|-----------------------|----------------------------------|------------------------------------|
| 0  | Norn Terrarium        | (1190, 712)                      | Main norn habitat; lush grassland  |
| 1  | Ettin Desert          | (5190, 704)                      | Ettin home; dry, hot               |
| 2  | Aquatic               | (9000, 1200)                     | Underwater; fish, aquatic plants   |
| 3  | Grendel Jungle        | (1948, 2310)                     | Grendel home; dense vegetation     |
| 4  | Main Corridor         | (3200, 1100)                     | Central connection hallway         |
| 5  | Pinball               | (6000, 2000)                     | Recreational machine room          |
| 6  | Space                 | (9000, 500)                      | Zero-gravity vacuum room           |
| 7  | Learning Room         | (2360, 467)                      | Vocabulary/teaching room           |
| 8  | Crypt                 | (3200, 2500)                     | Medical/storage; offline creatures |
| 9  | Blank                 | (8000, 2600)                     | Template for DS expansion          |

### Room Types

| Code | Type              | Notes                                      |
|------|-------------------|--------------------------------------------|
| 0    | Indoor            | Normal enclosed space                      |
| 1    | Corridor          | Passageway                                 |
| 2    | Outdoor           | Open air area                              |
| 3    | Soil              | Ground-level outdoor                       |
| 4    | Aquarium Door     | Boundary between water and air             |
| 5    | Garden            | Outdoor planted area                       |
| 6    | Swamp             | Wet outdoor area                           |
| 7    | Desert            | Dry outdoor area                           |
| 8    | Vacuum/Underwater | Aquatic/space vacuum                       |
| 9    | Deep Underwater   | Bottom of aquatic area                     |
| 10   | Tunnel            | Underground passage                        |

### CA Diffusion Rates by Room Type

Rooms of certain types suppress or boost CA channel diffusion. Desert rooms have reduced water CA; aquatic rooms have elevated nutrient and protein CA. The exact per-room-type rates are encoded in the engine binary, not in Bootstrap.

### Lift/Teleporter Network

- Lifts: classifier `3 1 0` (elevator category). Fires **STIM 94** (lift ride) on passengers each tick.
- Teleporters: classifier `3 2 0`. Fire `mesg writ targ 0 0` to activate portal to paired destination.
- Doors: classifier `2 2 0`. Use `BHVR 2` (activate2 = open). SORQ-checked before creature approaches.

### Navigation Stimuli

| STIM | Trigger              | Effect on brain                         |
|------|----------------------|-----------------------------------------|
| 75   | Smell emitter nearby | Registers nearby smell source           |
| 92   | Machine deactivated  | Reinforcement after machine interaction |
| 94   | Riding a lift        | Positive reinforcement for lift use     |
| 95   | Entered doorway      | Used by door/passage navigation agents  |
| 96   | Exited doorway       | Used by door/passage navigation agents  |

---

## 21. FOOD AND PLANT SYSTEMS

### Complete Food/Plant Classifier Table

| Classifier    | Agent name          | Category | STIM | CHEM injection                | Bioenergy |
|---------------|---------------------|----------|------|-------------------------------|-----------|
| 2 3 0 *       | Seeds               | seed (3) | 77   | variable by species           |:         |
| 2 4 0 *       | Plants/grass        | plant (4)| 77   | variable                      | 0.025     |
| 2 5 0 *       | Weeds               | weed (5) | 77   | variable                      | 0.01      |
| 2 6 0 *       | Leaves              | leaf (6) | 77   | variable                      | 0.01      |
| 2 7 0 *       | Flowers             | flower(7)| 77   | variable                      | 0.01      |
| 2 8 0 *       | Fruit               | fruit(8) | 78   | variable                      | 0.05      |
| 2 9 0 *       | Manky/rotting food  | manky(9) | 81   | variable (toxic)              | negative  |
| 2 11 0 *      | Cheese/carrot/food  | food(11) | 79   | varies; carrot: chem 75 0.1   | 0.05      |

**Only carrot piece (`2 11 0 3`) directly injects a chemical** (Alcohol, chem 75, amount 0.1). All other food agents work purely through STIM → stimulus gene → biochemistry pathway.

### STIM Intensity Variations for Food

- `stim writ targ 77 1`: base vegetation eat
- `stim writ targ 77 2`: eating preferred vegetation (mushroom, grass variants)
- `stim writ targ 77 3`: eating high-nutrition plant (pumperspikel)
- `stim writ targ 78 1`: base fruit eat
- `stim writ targ 79 1`: base food item eat
- `stim writ targ 80 2`: interacting with passive critter
- `stim writ targ 80 4`: interacting with dangerous critter (fish, high-tier)
- `stim writ targ 80 5`: interacting with very dangerous critter (piranhas)
- `stim writ targ 81 1`: ate manky/decayed food

### Bioenergy Economy

- Starts: ~250 units at world creation
- Increments: +1 per 100 engine ticks (passive regeneration)
- Cap: 1000 units
- Cost: Each newly spawned food/plant agent consumes bioenergy
- Food makers and dispensers check `game "Bioenergy"` before spawning
- Bridge implication: do NOT call `new: simp` food agents from bridge scripts: this drains bioenergy from the player's economy

### Population Management

Each food ecosystem agent tracks `lv99` (local count variable) and checks against:
- `game "*_MaxPop_*"`: per-species max population
- `game "*_LocalSphere"`: local spawn radius control

These GAME vars are ecosystem-owned and must not be set by the bridge.

---

## 22. DISEASE, PEST AND MEDICAL SYSTEMS

### Bacteria System (bacteria.cos)

50 bacteria agents spawned at world init. Each has a "genome" stored in OV variables:

| OV | Parameter                   | Range         |
|----|------------------------------|---------------|
| 0  | Lifespan                    | 6000–18000 ticks |
| 1  | Antigen type                | 82–89 (chem#) |
| 2  | Toxin type                  | 70–81 (chem#) |
| 3  | Toxin injection rate        | 0.005–0.05/tick |
| 4  | Species modifier flag       | 0=all, 1=ettin boost |

While alive, bacteria inject:
- `0.02` of its antigen chemical per tick to nearby creatures
- `0.005–0.05` of its toxin per tick (OV3-controlled)
- Antibody (chem antigen+20) accelerates bacteria death

Mutation on reproduction: 1-in-3 chance of parameter change.
Species susceptibility: Grendels 0.8x, Ettins 1.1x.

### Pest Agents

| Pest      | Classifier  | Action                                                   | STIM |
|-----------|-------------|----------------------------------------------------------|------|
| Ants      | 2 14 0 *    | Bite nearby creatures                                    | 88   |
| Gnats     | 2 14 0 *    | Bite nearby creatures                                    | 88   |
| Wasps     | 2 14 0 *    | Sting with higher toxin injection                        | 88   |
| Mosquitoes| 2 14 0 *    | Blood-drain; inject Chem 73 (Histamine A)               | 88   |

**Piranha (2 16 0 *):**
- Deadliest agent in Bootstrap
- On bite: calls `dead` (kills creature instantly) + `kill targ` (removes agent)
- Also injects `chem 117 0.5` (Adrenalin, not Injured 2) into nearby creatures
- Creates bone fragments as death visual (`new: simp 2 30 5`)

**STIM 88 = "bitten by pest"**: fires at intensity 1 regardless of pest species.

### Medicine Maker Potions (12 potions)

The Medicine Maker (classifier `3 3 0 12` or similar) creates potions. Each potion classifies as `2 25 0 N` (potion category, variant N).

| Potion # | Name                | Primary chem injection              |
|----------|---------------------|-------------------------------------|
| 0        | Painkiller          | Chem 127 (Injury) -0.3              |
| 1        | Antidote            | Chem 95 (EDTA) +0.5                 |
| 2        | Stimulant           | Chem 117 (Adrenalin) +0.3           |
| 3        | Sedative            | Chem 129 (Sleepase) +0.3            |
| 4        | Soothex             | Chem 158 (Fear) -0.3                |
| 5        | Comfort             | Chem 162 (Comfort) +0.3             |
| 6        | Oestrogen           | Chem 46 +0.3                        |
| 7        | Progesterone        | Chem 48 +0.3                        |
| 8        | Testosterone        | Chem 53 +0.3                        |
| 9        | Antihistamine       | Chem 100 +0.5                       |
| 10       | Anti-oxidant        | Chem 93 +0.5                        |
| 11       | Fertiliser          | Chem 39 (Arousal Potential) +0.3    |

Note: These are approximate; exact amounts vary. Potion chemistry is defined in stimulus genes of the Potion creature type (genus 5), not in Bootstrap CAOS.

---

## 23. TOYS, MACHINES AND GADGETS

### STIM Table for Object Interaction

| STIM | Context                              | Classifier           |
|------|--------------------------------------|----------------------|
| 90   | Machine activated (push/pull)        | `3 3 0 *`            |
| 91   | Machine user feedback (in-use pulse) | `3 3 0 *`            |
| 92   | Machine deactivated                  | `3 3 0 *`            |
| 97   | Played with toy                      | `2 21 0 *`           |

### Toy BHVR Values

Toys typically have `BHVR 1` or `BHVR 3` (activate1 and/or activate2). When a creature pushes a toy, event 17 fires on the toy, which fires `stim writ ownr 97 1` back to the creature.

### Logic Gate Network (from logic_gate.cos)

Logic gates are classifier `3 8 0 *` (gadget category). The full gate network in C3 is used for puzzle/machinery rooms:
- Gates have 2 inputs (OV0, OV1) and 1 output
- Output types: AND, OR, NAND, NOR, XOR
- Activated via `mesg writ targ 0` (input 1) and `mesg writ targ 1` (input 2)
- Output: `mesg writ [output_agent] 0` when logic evaluates true

Bridge implication: Do not send messages to gadget classifiers. The creature's decision scripts send `mesg writ _it_ M` which is the correct interaction pathway.

### Urge Modification (from pointer scripts)

Clicking on an agent with the hand sends:
```
urge shou 0.5 -1 -1.0
```
This tells the selected creature: "desire to approach and interact with this" at strength 0.5.

`urge sign` syntax: `urge sign strength noun_id strength`: the sign directive modifies what the creature wants to do.
`-1` means "don't modify this field".

---

## 24. COMPLETE OBJECT CLASSIFIER TABLE

Known classifiers for all major interactive C3 objects:

| Classifier   | Agent description               | Category code | BHVR bits |
|--------------|---------------------------------|---------------|-----------|
| 2 1 0 1      | Hand/pointer                    | 1 (hand)      | special   |
| 2 2 0 *      | Doors (various)                 | 2 (door)      | 2         |
| 2 3 0 *      | Seeds (various species)         | 3 (seed)      | 1, 17     |
| 2 4 0 *      | Plants/grass                    | 4 (plant)     | 1, 17     |
| 2 5 0 *      | Weeds                           | 5 (weed)      | 1, 17     |
| 2 6 0 *      | Leaves                          | 6 (leaf)      | 1, 17     |
| 2 7 0 *      | Flowers                         | 7 (flower)    | 1, 17     |
| 2 8 0 *      | Fruit                           | 8 (fruit)     | 1, 17     |
| 2 9 0 *      | Manky/rotting food              | 9 (manky)     | 1, 17     |
| 2 10 0 *     | Detritus/debris                 | 10 (detritus) | 0         |
| 2 11 0 *     | Food items (cheese, carrot)     | 11 (food)     | 1, 17     |
| 2 12 0 *     | Buttons                         | 12 (button)   | 1         |
| 2 13 0 *     | Bugs (decorative)               | 13 (bug)      | 1         |
| 2 14 0 *     | Pests (biting insects)          | 14 (pest)     | special   |
| 2 15 0 *     | Critters (grabbable animals)    | 15 (critter)  | 1, 2, 32  |
| 2 16 0 *     | Beasts (fish, piranhas)         | 16 (beast)    | 1         |
| 2 17 0 *     | Nests                           | 17 (nest)     | 1, 2      |
| 2 18 0 *     | Animal eggs                     | 18 (ani.egg)  | 1, 32     |
| 2 19 0 *     | Weather agents                  | 19 (weather)  | 0         |
| 2 20 0 *     | Bad objects                     | 20 (bad)      | 0         |
| 2 21 0 *     | Toys (balls, blocks, etc.)      | 21 (toy)      | 1, 2      |
| 2 22 0 *     | Incubators                      | 22 (incubator)| 1         |
| 2 23 0 *     | Dispensers/Venders              | 23 (dispenser)| 1         |
| 2 24 0 *     | Tools (player hand tools)       | 24 (tool)     | special   |
| 2 25 0 *     | Potions                         | 25 (potion)   | 1, 17     |
| 2 32 23      | Bacteria cloud                  | special       | 0         |
| 3 1 0 *      | Lifts/elevators                 | 26 (elevator) | 1         |
| 3 2 0 *      | Teleporters                     | 27 (teleport) | 1         |
| 3 3 0 *      | Machinery (gadgets)             | 28 (machinery)| 1, 2      |
| 3 4 0 *      | Creature eggs                   | 29 (crea.egg) | 1, 32     |
| 3 5 0 *      | Norn home agents                | 30 (norn hm)  | 1         |
| 3 6 0 *      | Grendel home agents             | 31 (gren hm)  | 1         |
| 3 7 0 *      | Ettin home agents               | 32 (etti hm)  | 1         |
| 3 8 0 *      | Gadgets (logic gates, etc.)     | 33 (gadget)   | 1, 2      |
| 3 9 0 *      | Something/misc fixtures         | 34 (something)| 0         |
| 3 10 0 *     | Vehicles                        | 35 (vehicle)  | 1         |
| 4 1 0 *      | Norns                           | 36 (norn)     | 1, 2, 4   |
| 4 2 0 *      | Grendels                        | 37 (grendel)  | 1, 2, 4   |
| 4 3 0 *      | Ettins                          | 38 (ettin)    | 1, 2, 4   |
| 4 4 0 *      | Geats                           | 39 (geat)     | 1, 2, 4   |

**BHVR bit meanings:**
- 1 = activate1 (push)
- 2 = activate2 (pull)
- 4 = deactivate
- 8 = hit
- 16 = eat
- 32 = pick up

---

## 25. CAOS COMMAND QUICK REFERENCE (engine v1.162)

Source: caos.syntax (zlib-compressed binary, fully decoded)

### Core Syntax Rules

- Stack-based execution, left-to-right
- No user-defined functions (use `subr`/`repe` for subroutines)
- `doif`/`endi`, `reps`/`repe`, `loop`/`ever`, `loop`/`untl`
- Variables: `va00`–`va99` (local), `ov00`–`ov99` (agent OV), `game "name"` (global)
- Targets: `targ`, `ownr`, `_it_`, `_p1_`, `_p2_`, `norn`, `_tm0_`–`_tm9_`
- All numeric literals are integers or floats; use `itof`/`ftoi` to convert

### Brain Commands

| Command                          | Type | Description                                                     |
|----------------------------------|------|-----------------------------------------------------------------|
| `SPNL sif moniker neuron value`  | cmd  | Set neuron input in named lobe of creature                     |
| `DECN`                           | int  | Current decision neuron index (from decn lobe WTA)            |
| `ATTN`                           | int  | Current attention neuron index (from attn lobe WTA)           |
| `BRN: SETN lobe neuron value`    | cmd  | Set neuron state directly (avoid in Bootstrap)                 |
| `BRN: GETN lobe neuron`          | float| **UNVERIFIED**: not in caoschaos/ghostfishe CAOS refs; may not exist |
| `BRN: SETD lobe dendrite value`  | cmd  | Set dendrite weight                                            |
| `BRN: GETD lobe dendrite`        | float| Get dendrite weight                                            |
| `BRN: SETL lobe value`           | cmd  | Set lobe parameter                                             |
| `BRN: GETL lobe`                 | float| Get lobe parameter                                            |
| `BRN: SETP lobe track value`     | cmd  | Set lobe SVRule parameter track                               |
| `BRN: GETP lobe track`           | float| Get lobe SVRule parameter                                     |
| `BRN: DMPB`                      | cmd  | Dump brain sizes as **binary** to shared memory (not log)      |
| `BRN: DMPL lobe`                 | cmd  | Dump lobe as **binary** to shared memory (40 bytes/neuron)     |
| `BRN: DMPN lobe neuron`          | cmd  | Dump single neuron as **binary** to shared memory (40 bytes)   |
| `BRN: DMPD lobe dendrite`        | cmd  | Dump dendrite as **binary** to shared memory                   |
| `born`                           | cmd  | Initialize brain (call once after egg hatches)                 |

**SPNL signature:** `SPNL sif:agent moniker:string neuron_id:int value:float`
- `sif` = creature agent reference (use `targ` or stored moniker reference)
- `moniker` = lobe quad ID string: `"decn"`, `"attn"`, `"verb"`, `"noun"`, etc.
- `neuron_id` = 0-indexed integer
- `value` = float 0.0–1.0

### Creature State Commands

| Command               | Type  | Description                                           |
|-----------------------|-------|-------------------------------------------------------|
| `driv N`              | float | Read drive level N (0.0–1.0)                         |
| `chem N`              | float | Read chemical concentration N (0.0–1.0)              |
| `injr N amount`       | cmd   | Inject chemical N by amount                           |
| `aslp state`          | cmd   | Set sleep state (1=asleep, 0=wake)                   |
| `aslp`                | int   | Read sleep state (1 if asleep)                        |
| `drea state`          | cmd   | Set dream state                                       |
| `drea`                | int   | Read dream state                                      |
| `uncs state`          | cmd   | Set unconscious state                                 |
| `cage`                | int   | Life stage (0=baby, 1=child, 2=juvenile, 3=adolescent, 4=youth, 5=adult, 6=senior, 7=senile) |
| `dead`                | int   | 1 if creature is dead or dying                        |
| `zomb state`          | cmd   | Freeze/unfreeze voluntary movement                   |

### Stimulus Commands

| Command                        | Type | Description                                           |
|--------------------------------|------|-------------------------------------------------------|
| `stim writ targ N I`           | cmd  | Fire stimulus gene N at intensity I on targ creature |
| `stim sign N I`                | cmd  | Fire on selected creature (sign = pointer target)    |
| `stim shou N I`                | cmd  | Fire on all creatures that can hear                  |
| `stim from N I`                | cmd  | Fire from targ creature onto interaction source      |
| `urge sign str noun_id str`    | cmd  | Modify selected creature's drives/urges              |
| `urge shou str noun_id str`    | cmd  | Modify all hearing creatures' urges                  |
| `sway sign noun_id str ...`    | cmd  | Sway urges across multiple drives                    |

### Vocabulary/Orders

| Command          | Type | Description                                  |
|------------------|------|----------------------------------------------|
| `vocb`           | cmd  | Teach creature word for `_it_`               |
| `sayn`           | cmd  | Creature says its current greatest need      |
| `shou word`      | cmd  | Broadcast word to all hearing creatures      |
| `ordr shou word` | cmd  | Order selected creature via spoken word      |
| `ordr sign word` | cmd  | Send word to selected creature (visual)      |

### Attention and Decision

| Command       | Type   | Description                                          |
|---------------|--------|------------------------------------------------------|
| `ATTN`        | int    | WTA output: attention lobe neuron with highest value |
| `DECN`        | int    | WTA output: decision lobe neuron with highest value  |
| `iitt`        | agent  | Returns the creature's current `_it_` (attention target) |
| `forf targ`   | cmd    | Force creature to face target agent                  |

### History Commands (used by Genetics/Crypt)

| Command                 | Type   | Description                              |
|-------------------------|--------|------------------------------------------|
| `HIST name moniker`     | string | Get creature's history entry             |
| `HIST flag moniker N`   | int    | Get history flag N for creature          |
| `HIST coun`             | int    | Count creatures in history               |
| `HIST cage moniker`     | int    | Life stage at time of history event      |

### PRAY (Agent Packaging) Commands

| Command             | Type | Description                                    |
|---------------------|------|------------------------------------------------|
| `pray expo "TAG"`   | cmd  | Export selected creature with PRAY tag         |
| `pray impo file`    | cmd  | Import creature from PRAY file                 |
| `pray make ...`     | cmd  | Create PRAY resource blob                      |
| `pray injt file`    | cmd  | Inject PRAY agent bundle into world            |
| `pray agti tag`     | int  | Count agents with PRAY tag                     |

---

## 26. CREATURE HISTORY SYSTEM

### Event Types (16 types, from Creatures3.catalogue or c2eHistory)

| ID | Event name          |
|----|---------------------|
| 0  | Born                |
| 1  | Spliced             |
| 2  | Engineered          |
| 3  | Cloned              |
| 4  | Died                |
| 5  | Imported            |
| 6  | Exported            |
| 7  | Became child        |
| 8  | Became adolescent   |
| 9  | Became adult        |
| 10 | Became old          |
| 11 | Became senile       |
| 12 | Laid egg            |
| 13 | Egg hatched         |
| 14 | Mated               |
| 15 | Pregnancy           |

### Life Stages (8 stages)

| Code | Stage      |
|------|------------|
| 0    | Baby       |
| 1    | Child      |
| 2    | Juvenile   |
| 3    | Adolescent |
| 4    | Youth      |
| 5    | Adult      |
| 6    | Senior     |
| 7    | Senile     |

### Species/Genus IDs

| Code | Species  |
|------|----------|
| 1    | Norn     |
| 2    | Grendel  |
| 3    | Ettin    |
| 4    | Geat     |

---

## 27. WILDLIFE SYSTEM

### Wildlife Classifiers and STIM Interactions

| Classifier   | Agent         | STIM on creature interaction | Notes                                        |
|--------------|---------------|------------------------------|----------------------------------------------|
| 2 15 0 *     | Critters      | 80 (intensity 2–3)           | Grabbable animals; safe to interact with     |
| 2 16 0 1     | Goldfish       | 80 (intensity 2)             | Emits CA 6 (protein smell) continuously      |
| 2 16 0 2     | Piranha        | 80 (intensity 5) + instant kill | See Section 22                            |
| 2 16 0 3     | Hummingbird    | 80 (intensity 4, TWICE)      | Possible bug: fires stim 80 twice per contact |
| 2 16 0 *     | Grazer         | 86 specifically              | Unique: uses stim 86 not 80                  |

**STIM 80 graded intensity table:**

| Intensity | Meaning                          |
|-----------|----------------------------------|
| 1         | Brief, low-stress encounter      |
| 2         | Normal critter interaction       |
| 3         | Exciting/playful interaction     |
| 4         | Intense/slightly dangerous       |
| 5         | Very dangerous (piranha-tier)    |

**STIM 86:** Grazer-specific: injected when creature interacts with a grazer agent. Not fired by any other wildlife.

**Fish CA emission:** Fish agents (`2 16 0 *`) call `cacl 2 16 0 6`: emits CA channel 6 (Protein smell). Creatures can smell fish from a distance via the smell lobe.

### Population Management for Wildlife

Wildlife agents check `game "*_MaxPop_*"` and `game "*_LocalSphere"` to limit local density. These variables are managed entirely by the ecosystem agents: the bridge must not modify them.

---

## 28. GUI AND POINTER SYSTEM

### Confirmed: No SPNL or BRN: Commands in Any Bootstrap Script

After reading all 320 Bootstrap files: **zero uses of `SPNL`** and **zero uses of `BRN:` commands**. The game engine relies entirely on the biochemistry/stimulus pathway to interact with the brain. The only brain-read commands in Bootstrap are:
- `DECN`: read current decision
- `ATTN`: read current attention
- `iitt`: read creature's current IT (attention target)
- `driv N`: read drive levels

### Pointer Scripts (Pointer scripts.cos)

| Pointer action    | CAOS command                   | Effect on creature              |
|-------------------|--------------------------------|---------------------------------|
| Left-click        | `mesg writ targ 0 0`           | Send message 0 (tickle/pat)     |
| Right-click (DEL) | `mesg writ targ 2 0`           | Send message 2 (slap)           |
| Click on object   | `urge shou 0.5 -1 -1.0`        | Creature wants to approach IT   |
| Click on sleeping | `mesg writ targ 2 0`           | Wake creature (slap interrupts sleep) |

### Communication Suppression

`loci 1 1 4 9`: reads locus `(organ=1, tissue=1, locus_type=4, id=9)` which is the "Communication Suppressed" locus. If non-zero, the creature's express-need action is suppressed.

The `loci` command: `loci organ tissue locus_type id` → returns float value of that biochemical locus.

### Text Entry System (textentry.cos)

- `ordr shou va00`: sends typed text as spoken-word order to selected creature
- Circular command history buffer (OV5–OV29, OV0 = head pointer, OV4 = count)
- Creature responds based on vocabulary learned via `vocb` command

### Hatchery (Hatchery2.cos)

Egg hatching sequence:
1. Egg incubation timer (OV0) counts down to 0
2. On hatch: `epas 4 0 0`: eject all creature passengers from vehicle
3. `born` fires on each ejected creature: **THE sole brain initializer**
4. `gene cros` called with mutation rates `40 40 40 40` (all gene types)

**`born` must only be called once per creature.** It initialises all lobe SVRules and sets the brain to initial state. Calling it twice would reset the brain.

---

## 29. GENETICS SYSTEM

### Gene Mutation Rates (from Hatchery2.cos)

`gene cros mother father child1 child2 duplication deletion mutation swap`:
- Standard rates: `40 40 40 40` (one in 40 chance per gene per operation type)
- These apply to: duplication, deletion, point mutation, swap

### Key Genetic Gene Types

| Gene type | CAOS name      | Description                                    |
|-----------|----------------|------------------------------------------------|
| brain     | (various)      | Lobe parameters, dendrite weights, SVRules     |
| biochem   | (reaction)     | Chemical reaction equations                    |
| stimulus  | (stimulus N)   | Maps stimulus N → chemical injection           |
| organ     | (organ)        | Defines organ type and energy consumption      |
| appearance| (appearance)   | Body part sprites, pigment                     |
| instinct  | (instinct)     | Pre-wired decision/context → reward mapping    |
| pose      | (pose)         | Maps life stage → sprite animation             |
| limb      | (limb)         | Body part geometry                             |

### Instinct Genes

Instinct genes are pre-wired "lessons" that run during dream state. They fire during `drea 1` (dream mode) to teach the creature correct stimulus→drive relationships before it has real experience. Instinct genes map:
- Situation: what the brain is attending to
- Decision: what action to take
- Reinforcement: which chemical should result (reward or punishment)

This means the first time a creature dreams, it learns basic survival instincts from its genome.

---

## 30. CRYPT AND MEDIPORTER

### Crypt System (crypt.cos)

The Crypt freezes and stores offline creatures:
- Stores via `PRAY expo "EXPC"` + removes agent from world
- Restores via `PRAY impo` + `born` (NO: uses a restore pathway, not `born` again)
- Actually uses the C3/DS creature export format

**Important:** A creature exported to the Crypt retains its brain state in the PRAY blob. When re-imported, its brain is restored from that state (NOT re-initialized with `born`).

### Mediporter

The Mediporter teleports creatures between rooms. It uses teleporter mechanics (`3 2 0`), not special brain commands. Creatures ride through as passengers.

---

## 31. WOLF CONTROL SYSTEM (wolf_control.cos)

This is a developer/admin tool, not part of normal gameplay:

- Sends CAOS directly via the wolf control interface
- Can set creature drives, inject chemicals, teleport agents
- Uses `subv` command to substitute values into CAOS strings
- NOT a production system: it is a debugging tool
- The `zzz_wolf_patch.cos` fixes a divide-by-zero in its frame rate calculation

---

## 32. NAVIGABLE CA INDICES (from Creatures3.catalogue)

From the `Navigable CA Indices` key:

```
6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18
```

These are the CA channels that the creature uses for navigation decision-making (the `driv` lobe neurons 15–19 are navigation drives driven by these CA gradients):

| CA # | Chem # | Smell name     | Navigation meaning                              |
|------|--------|----------------|-------------------------------------------------|
| 6    | 171    | Protein        | Navigate toward food (protein)                  |
| 7    | 172    | Carbohydrate   | Navigate toward food (carb)                     |
| 8    | 173    | Fat            | Navigate toward food (fat)                      |
| 10   | 175    | Machinery      | Navigate toward machinery                       |
| 11   | 176    | CA 11          | Navigate toward CA-11 emitters                  |
| 12   | 177    | Norn           | Navigate toward/away from norns                 |
| 13   | 178    | Grendel        | Navigate toward/away from grendels              |
| 14   | 179    | Ettin          | Navigate toward/away from ettins                |
| 15   | 180    | Norn home      | Navigate home (norns)                           |
| 16   | 181    | Grendel home   | Navigate home (grendels)                        |
| 17   | 182    | Ettin home     | Navigate home (ettins)                          |
| 18   | 183    | Gadget/Mach    | Navigate toward gadgets                         |

**The creature's navigation drives (driv 15–19) respond to these CA gradients.** The brain perceives navigation pressure via the driv lobe; the decision lobe's response drives the creature toward/away from smell sources.

---

## 33. CREATURE REACH AND INTERACTION DISTANCES

From `Creatures3.catalogue`: `Creature Reach` key: `[20, 45]`

- Minimum reach: 20 engine units
- Maximum reach: 45 engine units

A creature can only interact with an agent if it is within 20–45 engine units. `byit` returns 1 only when the creature has successfully approached to within this range.

---

## 34. CATEGORY REPRESENTATIVE ALGORITHMS

From `Creatures3.catalogue`: `Category Representative Algorithms` key:

Each agent category uses a different algorithm to select which agent the creature "pays attention to":

| Category code | Selection method                        |
|---------------|-----------------------------------------|
| 0 (self)      | Always self                             |
| 1 (hand)      | Always hand                             |
| 2–11          | Nearest                                 |
| 12–19         | Random (weighted by distance)           |
| 20–25         | Nearest                                 |
| 26–35         | Nearest                                 |
| 36–39         | Nearest creature (filtered by genus)    |

The attention mechanism prefers nearby agents for most categories, but some use random selection to encourage exploration.

---

## 35. ACTION SCRIPT TO NEURON MAPPING (Creatures3.catalogue)

From `Action Script To Neuron Mappings`: definitive engine-side mapping (14 entries):

| Script event | Neuron index | Action name    |
|--------------|--------------|----------------|
| 16           | 0            | Quiescent/Look |
| 17           | 1            | Activate1/Push |
| 18           | 2            | Activate2/Pull |
| 19           | 3            | Deactivate     |
| 20           | 4            | Approach       |
| 21           | 5            | Retreat        |
| 22           | 6            | Get/Pickup     |
| 23           | 7            | Drop           |
| 24           | 8            | Express        |
| 25           | 9            | Rest/Sleep     |
| 26           | 10           | Walk West      |
| 27           | 11           | Walk East      |
| 28           | 12           | Eat            |
| 29           | 13           | Hit            |

**Bad Action Script:** [13]: neuron 13 (Hit) is classified as a bad action. If a creature hits something, it receives punishment reinforcement.

**Good Action Scripts:** [1, 2]: neurons 1 and 2 (Activate1, Activate2) are good actions. Creatures are rewarded for pushing/pulling objects.

These classifications feed into the instinct gene system and the synchronous learning system when `engine_synchronous_learning` = 1.

---

## 36. NORN VOCABULARY SYSTEM

### Vocabulary Teaching (Scrolls of Learning)

The Learning Room contains "Scrolls of Learning" that teach norns vocabulary by:
1. Getting the norn to look at the scroll (`attn` = scroll category)
2. Playing the word audio
3. Calling `vocb`: this teaches the creature the word for `_it_`

### Vocab Slots

Creatures have 16 vocabulary slots (words they can learn). The `driv N` drive system maps to spoken needs:
- The highest-drive need becomes the creature's `sayn` output
- Creatures express this need verbally via script 24

### Word Orders (from textentry.cos)

`ordr shou word` sends word to all creatures that can hear. The creature then performs the associated drive-reduction behaviour. Known order words:
- "drop": creature drops held item
- "left", "right": navigation
- "push", "pull": interact with IT
- "come": approach the hand
- "no": punishment signal (injects punishment chemical)

---

## 37. COMPREHENSIVE STIM TABLE: ADDITIONS FROM PART 2 ANALYSIS

These supplement the base table in Section 6:

| Stim # | Meaning                              | Applied to | Intensity | Fired by                                 |
|--------|--------------------------------------|------------|-----------|------------------------------------------|
| 80     | Interacted with animal/critter       | self       | 1–5       | Critters/beasts on activation; graded    |
| 81     | Ate manky/rotten food                | self       | 1         | Manky food on eat                        |
| 82     | Patted another creature              | other      | 1         | When creature pats another               |
| 83     | Hit another creature (victim)        | other      | 1         | victim receives this on being hit        |
| 84     | Eaten another creature's food        | self       | 1         | Competing for food                       |
| 85     | Attempted to mate                    | self       | 1         | Mating attempt regardless of success     |
| 86     | Interacted with grazer               | self       | 1         | Grazer-specific STIM                     |
| 87     | Heard a creature speak               | self       | 1         | Creature nearby says a word              |
| 88     | Bitten by pest                       | self       | 1         | All pest classifiers (ants, wasps, etc.) |
| 89     | Touched a flower/plant proximity     | self       | 1         | Decorative plants, proximity trigger     |
| 90     | Activated a machine                  | self       | 1         | Machine event 1                          |
| 91     | Machine user feedback                | self       | 1         | Machine mid-use                          |
| 92     | Deactivated a machine                | self       | 1         | Machine event 2                          |
| 93     | Picked up an egg                     | self       | 1         | Egg pickup by creature                   |
| 94     | Riding a lift                        | self       | 1         | Lift passenger tick                      |
| 95     | Entered a door/passage               | self       | 1         | Door navigation agent                    |
| 96     | Exited a door/passage                | self       | 1         | Door navigation agent                    |
| 97     | Played with toy                      | self       | 1         | Toy event 1                              |

---

## 38. BIOCHEMICAL LOCI (for advanced bridge use)

`loci organ tissue locus_type id` reads a biochemical locus value.

Confirmed uses in Bootstrap:

| loci call            | Meaning                                    | Used by                |
|----------------------|--------------------------------------------|------------------------|
| `loci 1 1 4 9`       | Communication suppressed                   | Express need script    |
| `loci 0 0 0 0`       | (various muscle loci)                      | Involuntary scripts    |

Full loci address space is defined in the genome file format. The pattern is:
- organ: 0=body, 1=brain
- tissue: 0–N (varies by organ type)
- locus_type: 0=input, 1=output, 2–N=internal
- id: index within that type

---

## 39. PATCH SUMMARY (all 6 patches)

| Patch file                        | Bug fixed                                                              |
|-----------------------------------|------------------------------------------------------------------------|
| `aquatic_patches.cos`             | Man-O-War spore spawning could create agents at wrong classifier      |
| `dragonfly_patch.cos`             | Dragonflies eating mates: gender filter was missing in eat script    |
| `jungle_patches.cos`              | Mossie fly egg classifier check wrong: eggs weren't counted         |
| `meerk_fix.cos`                   | Meerk pickup mid-burrow caused physics glitch                         |
| `nature_patches.cos`              | Volcanic rocks not categorised as weather category (CA emissions off) |
| `wolf_patch.cos`                  | Wolf control divide-by-zero in frame rate (developer tool bug)        |
| `zzz_grendel_upgrade_c3.cos`      | Adds female grendel voice, sets `game "0kAy_GrEndELs_mAy-BE+_heR3"` = 1 |

The grendel upgrade GAME variable name is obfuscated intentionally. The `zzz_` prefix ensures it loads last.

---

## 40. SUMMARY: WHAT BOOTSTRAP NEVER DOES (safe bridge assumption list)

After reading all 320 Bootstrap files, these assumptions are **confirmed safe** for the bridge design:

1. **No Bootstrap script calls `SPNL`**: the command exists but is unused in Bootstrap. Bridge has exclusive use of it.
2. **No Bootstrap script calls `BRN:` commands**: brain structure is never modified by CAOS. Only the engine's internal tick modifies brain state.
3. **`lnn_` GAME variable prefix is unused**: confirmed no collision with any existing variable.
4. **`born` is called exactly once per creature**: only by Hatchery2.cos and creature import (`pray impo` pathway). Bridge must never call `born`.
5. **Decision scripts (events 16–29) are the exclusive action execution layer**: bridge should write to brain lobes, not bypass these scripts.
6. **Sleep lock cannot be broken by brain output**: when `aslp` = 1, the creature is locked. Bridge must detect and suppress outputs.
7. **Death cannot be prevented once `dead` = 1**: bridge must clean up and detach.
8. **Navigation drives (driv 15–19) are purely chemical**: driven by CA gradient chemicals 199–203. Bridge reads these but should not override them.
9. **Bioenergy is a shared economy**: bridge must not spawn food agents or consume bioenergy.
10. **Grendel upgrade marker**: `game "0kAy_GrEndELs_mAy-BE+_heR3"` = 1 in any world that has loaded the grendel upgrade patch.

