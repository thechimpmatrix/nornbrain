# Phase 4D: Language System: Vision Document

**Date:** 2026-03-30
**Branch:** `feature/multi-lobe-cfc`
**Depends on:** Phase 4A, 4B, 4C (all complete)
**Status:** Aspirational: architectural sketch, not implementation spec

---

## 0. Purpose

This document captures the long-term vision for norn language capabilities. It is NOT an implementation specification: it's a forward-looking architectural sketch to ensure Phases 4A-4C are designed with language in mind. No implementation plan will be created for this phase until 4A-4C are complete and validated.

---

## 1. Vision

Norns that can communicate meaningfully: expressing their internal states, needs, memories, and reactions through language. Starting with simple verb-object speech (matching the original C3 vocabulary), evolving toward natural language via bridge-side LLM translation, and eventually voice chat.

---

## 2. Three-Stage Roadmap

### Stage 1: Structured Speech Output

**What:** Add a speech output head to the Prefrontal CfC module. The norn produces structured utterances using its existing vocabulary.

**Architecture:**
```
Prefrontal CfC hidden state
    ├──→ decision motor neurons (17): what to DO     [existing]
    └──→ speech output (57+4 = 61): what to SAY      [new]
            ├── verb activation (17): action word
            ├── noun activation (40): object word
            └── tone (4): scared / happy / angry / neutral
```

**Output examples:**
- Norn is hungry, sees food: speech = "want food" (verb=get, noun=food, tone=neutral)
- Norn sees grendel, has trauma memory: speech = "scared grendel" (verb=retreat, noun=grendel, tone=scared)
- Norn is lonely, sees another norn: speech = "lonely norn" (verb=approach, noun=norn, tone=neutral)

**Key design points:**
- Speech output is driven by the PFC's current state, NOT just the action being taken. A norn can say "scared grendel" while performing "retreat": the speech expresses the WHY, not just the WHAT.
- The speech output is trained via behaviour cloning alongside the decision output. Observation data would need to include what the SVRule brain's verb/noun lobes produce.
- The speech is only generated when the norn has something meaningful to express (emotional intensity > threshold, or drives above a level, or LTM retrieval active).

**Bridge integration:**
- Bridge reads speech output alongside attention+decision
- Translates verb_idx + noun_idx + tone_idx into a text string
- Sends text string to dashboard for display
- Optionally sends to game as CAOS speech bubble (if C3 supports external creature speech)

### Stage 2: LLM-Translated Natural Language

**What:** The Python bridge uses a small language model to translate between the norn's structured internal state and natural language.

**Architecture:**
```
Norn internal state (structured)
    drives: {hunger: 0.8, fear: 0.9, ...}
    emotion: {tier: "HIGH", valence: -0.7}
    attention: "grendel"
    action: "retreat"
    speech: {verb: "retreat", noun: "grendel", tone: "scared"}
    ltm_active: {valence: -0.9, attention: "grendel"}
        │
        ▼
    Small LLM (local, e.g., Qwen3 via Ollama)
        │
        ▼
    Natural language: "No no no! Scary grendel! Run away!"
```

**Key design points:**
- The LLM receives a structured JSON summary of the norn's state, not raw tensors
- The LLM's system prompt establishes the norn's "voice": simple, childlike, emotional
- Temperature and output length are modulated by emotional tier: EXTREME = short, repetitive, panicked; LOW = longer, more descriptive
- The LLM runs in the bridge process: it does NOT affect brain inference timing
- Responses are cached: similar states produce cached responses to avoid repeated LLM calls

**Bidirectional (player → norn):**
```
Player types: "come here little norn"
        │
        ▼
    Small LLM parses intent:
    {verb: "approach", target: "hand", tone: "friendly"}
        │
        ▼
    Injected into brain as sensory input:
    - verb lobe: "approach" activation
    - noun lobe: "hand" activation
    - Amygdala receives positive valence signal
```

### Stage 3: Voice Chat

**What:** Text-to-speech and speech-to-text wrap the Stage 2 system.

**Architecture:**
```
Player speaks → Microphone → STT (Whisper) → text
    → LLM intent parsing → brain sensory injection

Norn state → LLM translation → natural text
    → TTS (local or API) → speaker
```

**Key design points:**
- STT and TTS run as separate async processes in the bridge
- The norn's "voice" should have character: pitch, speed, and emotional inflection vary with the emotional tier
- Latency budget: player speech → norn response in < 2 seconds (STT ~500ms, LLM ~500ms, TTS ~500ms)
- This is the highest-aspiration feature and may require hardware considerations (GPU for local LLM inference)

---

## 3. Architectural Implications for Phases 4A-4C

The language vision does NOT require changes to the Phase 4A-4C architecture. However, these design decisions ensure forward compatibility:

1. **PFC motor neurons are expandable.** Phase 4A defines 17 decision motor neurons. Stage 1 language adds 61 speech output neurons. The NCP wiring can accommodate additional motor neurons by increasing `motor_neurons` in the PFC genome config.

2. **Amygdala output is continuous, not argmax'd.** The 16-dimensional emotional state vector is exactly what Stage 2's LLM needs to translate "feelings" into words. If we argmax'd it into a single emotion label, we'd lose nuance.

3. **LTM retrieval results are accessible.** The bridge already has access to active LTM retrievals (Phase 4B). Stage 2's LLM can read these to generate memory-informed speech ("I remember bad grendel!").

4. **The verb/noun lobes are already brain inputs.** Stage 2's player→norn direction can inject parsed speech into the existing verb and noun input lobes. No new input channels needed.

5. **Emotional tier is computed every tick.** Stage 2 can read the current tier to modulate speech style without additional computation.

---

## 4. Open Questions (for future investigation)

1. **Which local LLM?** The user's system has Ollama with Qwen3 models and an RTX 3090 (24GB VRAM). A 7B-8B model should work for simple speech translation. Needs benchmarking.

2. **Speech frequency:** How often should the norn "speak"? Every tick is too much. Every emotional state change? Every LTM retrieval? Needs experimentation.

3. **Multi-creature conversation:** If two norns are near each other, can they "talk"? One norn's speech output would need to be injected into the other's brain as sensory input. This is architecturally possible but untested.

4. **C3 speech bubble integration:** Can we make the norn display a speech bubble in-game via CAOS? The `SAYN` command exists but may not work with externally-driven speech. Needs testing.

5. **Memory narration:** Can the norn describe its memories? "I remember scary grendel at waterfall." This requires the LTM retrieval to include enough metadata for the LLM to construct a narrative.
