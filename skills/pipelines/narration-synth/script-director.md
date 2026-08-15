# Script Director - Narration Synth Pipeline

## When To Use

The brief exists. You shape the user's raw text into the timed `script` artifact:
sections with `start_seconds`/`end_seconds`, each mapped to a section id, sized so
Chinese narration lands at ~4-5 chars/sec. The script is the spine; the scene plan
will give every section a generated visual.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/script.schema.json` | Artifact validation |
| Prior artifact | `state.artifacts["idea"]["brief"]` | hook, tone, target_duration_seconds |
| Meta | `skills/meta/reviewer.md` | Self-review pass |

## Process

### 1. Shape The Sections

Cut the narration into sections that each carry ONE idea — the section is the unit
the scene plan will visualize one-for-one. Rules:

- **Hook → body → closing arc.** The first section states the thesis; the middle
  sections build evidence (equipment, numbers, strategy); the final section lands
  the 意义/结论.
- **Meaningful boundaries only.** Never split mid-sentence; prefer paragraph-level
  cuts at idea transitions.
- **Section length.** Chinese ≈ 4-5 chars/sec. Cap any single section at ~90s of
  narration. A 400-char paragraph ≈ 80-90s.

### 2. Time The Sections

`start_seconds`/`end_seconds` are ESTIMATES (the doc cadence). Sequence them
contiguously from `0.0`; each gets a `delivery_cue_wait`/pause allowance. Record
`total_duration_seconds` = sum + pauses.

### 3. Mark Delivery Cues

For 军政 narration the voice performance matters: mark pauses after number-heavy
lines (`delivery_cue: "pause_after"`), emphasis on proper nouns
(`emphasis: "句子快慢"`), and pace notes where a technical read is needed. These
flow into TTS generation at the assets stage.

### 4. Keep The Visual Contract In Mind

While writing, note the visual anchor each section implies (the scene director
will read it): a "驱逐舰下水" section → warship; "弹道覆盖" → missile;
"地区力量对比" → data-viz or map. Do NOT write the generation_spec here — that's
the scene plan's job — but leave enough concrete nouns that the mapping is obvious.

### 5. Emit The Script

Canonical shape:

```json
{
  "version": "1.0",
  "title": "新型驱逐舰：改写西太平洋",
  "sections": [
    {
      "id": "section_01",
      "text": "这艘驱逐舰，正在改写西太平洋的版图。",
      "start_seconds": 0.0,
      "end_seconds": 5.5,
      "delivery_cue": "hook_landing",
      "visual_anchor": "warship_at_sea"
    },
    {
      "id": "section_02",
      "text": "满载排水量一万两千吨，搭载四十八单元垂发系统。",
      "start_seconds": 5.5,
      "end_seconds": 14.0,
      "delivery_cue": "pause_after",
      "visual_anchor": "warship_specs_countup"
    }
  ],
  "total_duration_seconds": 90.0,
  "voice_performance": {
    "performance_intent": "calm authoritative",
    "pacing_profile": "documentary-broadcast",
    "chinese_speaking_rate": 4.5
  },
  "metadata": {
    "pipeline": "narration-synth"
  }
}
```

### 6. Quality Gate

- Sections ordered hook → body → closing.
- Every section has non-empty `text` + concrete `start/end`.
- `total_duration_seconds` within ±10% of `brief.target_duration_seconds`.
- No section exceeds ~90s of narration text.
- Every section leaves a clear `visual_anchor` (or the section is too vague to
  visualize).
- All fields validate against the script schema.

## Common Pitfalls

- Splitting mid-sentence to hit an arbitrary section count.
- Writing sections so dense the visuals can only hold a wall of text.
- One 120s monolith that blows past the 90s ceiling.
- Omitting `visual_anchor` — then the scene director guesses.
- Trusting section timings for the final burn — compose force-aligns anyway; these
  are the planning cadence, not the contract.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true`). After review passes:
checkpoint with `status="awaiting_human"`, present the summary (the Backlot board renders
the artifact), and **END YOUR TURN**. Do not start the next stage in the same response.
Approval is per-gate — an earlier "go ahead" does not cover this gate.