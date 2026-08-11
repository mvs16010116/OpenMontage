# Script Director - Narration Montage Pipeline

## When To Use

The brief exists and carries the raw source script. You now shape that
text into the `script` artifact: a sequence of timed sections, each
sized to the target duration and ready for TTS generation at the asset
stage. This stage produces the WORDS contract — everything downstream
(scene plan, assets, edit, compose) obeys these section boundaries.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/script.schema.json` | Artifact validation |
| Prior artifact | `state.artifacts["idea"]["brief"]` | source_script, tone, target_duration_seconds |
| Reference | `skills/pipelines/narration-montage/executive-producer.md` | Cross-stage rules |

## Mental Model

You are not writing a new script from thin air (unless the user gave no
text — then you draft one from the brief's `key_points`). You are
**structuring** the user's words into TTS-friendly sections.

Two forces pull on every section boundary:

1. **Meaning** — a section is one coherent thought. Never split
   mid-sentence, never merge two thoughts.
2. **Duration** — each section must be short enough to stay a single
   visual beat (~5-15s of speech) and long enough to be worth a scene.

If the user's script is a single block, you MUST split it into sections.
If it's already structured, validate the boundaries and add timings.

## Process

### 1. Estimate Total Duration

Use the brief's `target_duration_seconds` as the target. Sanity-check
it against the speaking-rate math (from the idea-director):

| Language | Rate |
|----------|------|
| Chinese (mandarin) | ~4-5 chars/sec |
| English | ~2.5-3 words/sec |

`total_duration_seconds` must land within ±10% of the brief's target.
If the raw text is too long, flag it to the user BEFORE trimming —
never silently cut the user's script.

### 2. Split Into Sections

Divide the text at thought boundaries. Each section:

- `text` — the exact narration line(s) TTS will speak. No stage
  directions, no markdown.
- `id` — `section_01`, `section_02`, ...
- `start_seconds` / `end_seconds` — estimated placement. These are
  PROVISIONAL. The asset stage force-aligns real audio and the compose
  stage burns subtitles from aligned timings, so these estimates only
  drive the scene plan and the edit grid.

Section length guidance:

| Section speech length | Feels like |
|----------------------|------------|
| 3-8s | a quick beat — fine for punchy lines |
| 8-15s | the sweet spot for one scene |
| 15-25s | a long beat — split if there's a natural pause |
| >25s | too long — the scene will feel static |

Use the schema's `delivery_cues` when the line needs performance
emphasis (pace, energy, pauses). Keep `delivery_cues.pause_before/after`
for natural breathing room — TTS pauses make force-alignment more
robust, not less.

### 3. Assign Enhancement Cues

For each section, note what the footage should show via
`enhancement_cues`. These are hints to the scene director — concrete
nouns, not moods:

```json
{
  "type": "broll",
  "description": "server racks with blinking LEDs in a dim data center",
  "timestamp_seconds": 4.2
}
```

`type` values the schema allows: `overlay`, `broll`, `diagram`,
`stat_card`, `code_snippet`, `animation`. For this pipeline, `broll` is
the workhorse; `overlay`/`stat_card` are for supporting text on screen
(optional, keep minimal — this pipeline is B-roll led).

### 4. Handle Source Claims

Every factual claim should carry `source_ref` (the schema field) —
a URL or the research_brief data point that supports it. This keeps the
explainer honest and gives the asset stage a hook for verification.

### 5. Record The Script

Canonical shape:

```json
{
  "version": "1.0",
  "title": "How The Cloud Actually Works",
  "total_duration_seconds": 78,
  "voice_performance": {
    "performance_intent": "calm, authoritative tech explainer",
    "pacing_profile": "technical",
    "energy_curve": "steady, slight lift on the payoff line",
    "pause_policy": "pause between sections, brief pause before the key line",
    "sample_section_id": "section_04",
    "provider_notes": {
      "zh-CN": "Use natural mandarin prosody; avoid overly dramatic emphasis."
    }
  },
  "sections": [
    {
      "id": "section_01",
      "label": "Hook",
      "text": "The internet doesn't run on servers. It runs on permission.",
      "start_seconds": 0.0,
      "end_seconds": 5.0,
      "delivery_cues": {
        "pace": "measured",
        "emphasis_words": ["permission"],
        "pause_after_seconds": 0.4
      },
      "enhancement_cues": [
        { "type": "broll", "description": "server racks blinking in a dim data center" }
      ],
      "source_ref": ""
    },
    {
      "id": "section_02",
      "label": "Physical reality",
      "text": "Every file you've ever saved lives on a physical hard drive in a physical building, usually far from you.",
      "start_seconds": 5.0,
      "end_seconds": 16.0,
      "delivery_cues": { "pace": "conversational" },
      "enhancement_cues": [
        { "type": "broll", "description": "aerial shot of a large data center campus at dusk" },
        { "type": "broll", "description": "close up of stacked hard drives inside a server" }
      ],
      "source_ref": ""
    }
  ],
  "metadata": {
    "pipeline": "narration-montage",
    "language": "zh-CN",
    "section_count": 7,
    "estimated_speaking_rate_chars_per_sec": 4.5
  }
}
```

### 6. Quality Gate

- Every section has non-empty `text`, `id`, `start_seconds`,
  `end_seconds`.
- No section's estimated speech length exceeds ~25s.
- `sum(end - start)` is within ±10% of the brief's
  `target_duration_seconds`.
- Section boundaries fall at sentence/thought boundaries — never
  mid-sentence.
- `voice_performance` is present (it drives TTS generation).
- Every factual claim has a `source_ref` or an explicit empty string.
- If the script was user-supplied, no wording was silently changed —
  any edit is flagged to the user at the gate.

## Common Pitfalls

- **Not splitting a monolithic script.** One 78-second section is
  unproducible — the scene director needs boundaries to assign scenes.
- **Splitting mid-sentence.** The section text is spoken as-is by TTS.
  A mid-sentence split produces a clipped audio file.
- **Writing performance directions into `text`.** "(dramatic pause)"
  inside the narration string gets spoken literally. Use
  `delivery_cues`, never inline stage directions.
- **Estimating timing from gut feeling.** Use the speaking-rate math;
  under-estimating compresses the whole edit later.
- **Cutting user wording silently.** Any trim/rewrite is a change to
  the user's script — surface it at the gate, don't smuggle it.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true`). After review passes:
checkpoint with `status="awaiting_human"`, present the summary (the Backlot board renders
the artifact), and **END YOUR TURN**. Do not start the next stage in the same response.
Approval is per-gate — an earlier "go ahead" does not cover this gate.
