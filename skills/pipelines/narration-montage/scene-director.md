# Scene Director - Narration Montage Pipeline

## When To Use

The script exists with timed sections. You now turn each section into a
SCENE: a window of time with a concrete visual description and the
Pexels queries that will find footage for it. The asset director fetches
per scene; the edit director cuts within each scene's window.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/scene_plan.schema.json` | Artifact validation |
| Prior artifact | `state.artifacts["script"]["script"]` | Sections, timings, enhancement cues |
| Prior artifact | `state.artifacts["idea"]["brief"]` | tone, narration_plan, shot_cadence_seconds |
| Reference | `skills/pipelines/narration-montage/executive-producer.md` | Cross-stage rules |

## Mental Model

In a narration montage, the scene director is a **sight-reader**: they
translate spoken words into the images a listener would picture. The
scene must do four jobs:

1. **Cover the section window** — scene `start/end` match the section's.
2. **Underline the meaning** — the visuals are concrete and noun-led,
   the same way the narration is.
3. **Give the editor enough material** — each scene must yield
   `ceil(section_duration / shot_cadence) + 3` distinct clips so the
   edit never reuses a clip and never flashes a clip too short.
4. **Vary the language** — adjacent scenes never reuse the same query
   vocabulary, so the cut never looks repetitive.

## Process

### 1. One Scene Per Section

Walk `script.sections[]` in order. For each section, create one scene
with:

- `id` — `scene_01`, `scene_02`, ...
- `script_section_id` — the section this scene serves.
- `start_seconds` / `end_seconds` — COPIED from the section. Scene
  windows equal section windows. Do not invent offsets yet; the edit
  stage aligns to real audio.

### 2. Write The Scene Description

`description` is the contract text the asset director reads when
fetching. It is also what a human reviewer sees on the Backlot board.
Write it as a **concrete stock-footage tag string** — nouns and
adjectives, no emotion words, no verbs of intention.

**Template:** `<subject>, <action/pose>, <environment>, <lighting>`

| Section line | Good description | Bad description |
|--------------|------------------|-----------------|
| "the internet runs on permission" | "server racks with blinking LEDs in a dim data center, wide shot" | "the concept of permission" |
| "every file lives on a physical drive" | "stacked hard drives inside an open server, shallow focus" | "technology and data" |
| "a city far from you" | "aerial view of a suburban data center campus at dusk" | "a big building" |

Rule of thumb: if you can't imagine a specific Pexels clip from the
description, the asset director can't fetch one either.

### 3. Write 3+ Pexels Queries Per Scene

Put them in `metadata.queries` (per-scene) — the asset director fans
them out through `pexels_video`. Rules:

- **English queries.** Pexels' search works best in English, regardless
  of the narration language.
- **2-5 words each.** Short queries beat long ones on stock APIs.
- **3+ per scene** — variety protects against dead ends and gives the
  dedup rule room to work.
- **Concrete nouns first.** `"data center server racks night"` beats
  `"internet"`.

Example for a scene about the cloud's physical reality:

```json
"queries": [
  "data center server racks",
  "server room blinking lights",
  "aerial data center campus",
  "hard drives close up"
]
```

### 4. Set Shot Language Per Scene

Use the scene schema's `framing` and `movement` fields — do not leave
them default. The edit stage reads these to enforce variety:

| Field | Values |
|-------|--------|
| `framing` | `wide`, `medium`, `close`, `extreme_close`, `aerial` |
| `movement` | `static`, `pan`, `tilt`, `dolly_in`, `dolly_out`, `handheld` |

Adjacent scenes must not share `framing` AND `movement` (a wide static
shot followed by a wide static shot reads as one long clip).

### 5. Flag Hero Moments

Mark at most 1-2 scenes per piece as `hero_moment: true` — the hook
scene and (optionally) the payoff scene. Hero scenes get:

- longer holds at edit time (the cadence may stretch on a hero),
- more queries at asset time (4-5 instead of 3),
- priority treatment if a fetch fails.

### 6. Record The Scene Plan

Canonical shape:

```json
{
  "version": "1.0",
  "scenes": [
    {
      "id": "scene_01",
      "type": "broll",
      "description": "server racks with blinking LEDs in a dim data center, wide shot",
      "start_seconds": 0.0,
      "end_seconds": 5.0,
      "script_section_id": "section_01",
      "framing": "wide",
      "movement": "static",
      "transition_in": "fade_in",
      "transition_out": "cut",
      "shot_language": "establishing_wide",
      "shot_intent": "establish the physical scale of the cloud",
      "narrative_role": "hook",
      "hero_moment": true,
      "texture_keywords": ["server", "LED", "dim", "rack"],
      "required_assets": [
        { "type": "video", "description": "server room wide shot", "source": "pexels" }
      ]
    }
  ],
  "metadata": {
    "pipeline": "narration-montage",
    "tone": "authoritative",
    "shot_cadence_seconds": 3.0,
    "queries": {
      "scene_01": ["data center server racks", "server room blinking lights", "aerial data center campus", "server racks close up"],
      "scene_02": ["stacked hard drives server", "hard drive close up", "data storage technology"]
    }
  }
}
```

### 7. Quality Gate

- One scene per script section (count matches).
- Every scene's `start/end` matches its section's window.
- Every scene `description` uses concrete noun-and-adjective language.
- Every scene has 3+ English Pexels queries in `metadata.queries`.
- `framing` and `movement` are set per scene; no two adjacent scenes
  share both.
- `sum(end - start)` is within ±10% of `script.total_duration_seconds`.
- At most 2 scenes are marked `hero_moment`.

## Common Pitfalls

- **Writing one scene per thought instead of per section.** The section
  is the unit. One scene per section, no more, no less.
- **Abstract descriptions.** "the feeling of control" is not fetchable.
  "a hand turning off a breaker switch" is.
- **Chinese-language queries.** Translate to English — Pexels ranking
  collapses on non-English queries.
- **Two adjacent scenes with identical framing + movement.** The cut
  looks like a single clip. Enforce variety at the source.
- **Forgetting query variety.** Three queries that are the same sentence
  reordered return the same clips. Write genuinely different angles.
- **Padding scenes with extra seconds.** Scene windows equal section
  windows. Extra time belongs to the edit stage's cadence, not the
  scene plan.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true`). After review passes:
checkpoint with `status="awaiting_human"`, present the summary (the Backlot board renders
the artifact), and **END YOUR TURN**. Do not start the next stage in the same response.
Approval is per-gate — an earlier "go ahead" does not cover this gate.
