# Idea Director - Narration Montage Pipeline

## When To Use

You are turning a user prompt and/or their written script (口播文案)
into the `brief` artifact that every downstream stage reads. The brief
is the contract: what the video says, who says it, how long it runs,
and what supports it.

## Runtime Selection (MANDATORY — present the constraint, don't silently pick)

Lock `render_runtime = "ffmpeg"`. **Remotion and HyperFrames are NOT
valid runtimes on this pipeline** — narration-montage is a
narration-led stock-cut pipeline: ffmpeg burns static subtitle lines,
cuts B-roll on a fixed cadence, and muxes narration + music. Neither
Remotion's scene-type stack nor HyperFrames' HTML/GSAP composition
applies to this deliverable.

Per AGENT_GUIDE.md → "Present Both Composition Runtimes (HARD RULE)":
do NOT silently default. If `video_compose.get_info()["render_engines"]`
lists remotion/hyperframes as available on the machine, still present
them but explain why neither is viable here, then record a
`render_runtime_selection` decision in `decision_log` listing both
runtimes in `options_considered`, with `rejected_because: "narration-montage is a script-led stock-cut pipeline; subtitle burn + narration mux are ffmpeg-native"`.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/brief.schema.json` | Artifact validation |
| User input | Conversation history + written script | The raw ask |
| Meta | `skills/meta/reviewer.md` | Self-review pass |

## Process

### 1. Ingest The Script

The user's text is the seed. If they provided a written script, this
stage's job is to understand it, not rewrite it (that's the script
stage). Capture:

- **The raw text** — store it verbatim in `reference_material` and in
  `metadata.source_script` so later stages can quote it.
- **The intended register** — is this a product pitch, an educational
  explainer, a tech deep-dive, a storytelling piece? The tone of the
  VIDEO follows the tone of the WORDS.
- **The intended audience** — who needs to follow this?
- **Any explicit constraints** — brand, banned topics, required phrases,
  platform, length.

### 2. Name The Hook

Write the ONE line that opens the video — the attention grabber. It is
usually the first sentence of the script, sharpened. A good hook is
specific, concrete, and makes the viewer need the next line.

- Good: "The internet doesn't run on servers. It runs on permission."
- Bad: "Today we're going to talk about how the internet works."

### 3. Fix The Tone

Choose ONE emotional/register word. Everything downstream keys off it.
For a narration-led explainer the tone usually mirrors the script's
voice:

- **authoritative** — expert framing, technical (product, finance, science)
- **conversational** — friendly, direct-address (social, lifestyle, teaching)
- **urgent** — pressing, high-stakes (news, security, launches)
- **aspirational** — inspiring, big-picture (brand, vision, motivation)
- **storytelling** — narrative, warm (documentary-adjacent, personal)

Write the tone in `brief.tone`.

### 4. Pick A Duration

Duration is driven by script length. Use these speaking-rate estimates:

| Language | Speaking rate | Estimate |
|----------|---------------|----------|
| Chinese (mandarin) | ~4-5 chars/sec | `chars / 4.5` |
| English | ~2.5-3 words/sec | `words / 2.7` |

Example: a 350-char Chinese script ≈ 75-80s of narration. Round up to
allow for pauses; record the number in `brief.target_duration_seconds`.

**Rule:** never let a single narration section run past ~90s — if the
script would, it must be split into multiple sections at the script
stage, not crammed into one.

### 5. Choose The Narration Voice (MANDATORY)

Narration is the spine of this pipeline. You MUST record a narration
plan. If the user has a preferred voice or provider, record it. If not,
query `registry.get_by_capability("tts")`, list the configured
providers, and propose a voice with a register matching `brief.tone`.

Record in `brief.metadata.narration_plan`:

```json
{
  "narration_plan": {
    "enabled": true,
    "provider": "openai_tts",
    "model": "gpt-4o-mini-tts",
    "voice": "alloy",
    "language": "zh-CN",
    "register": "authoritative",
    "notes": "Matched to the technical tone of the script."
  }
}
```

Every major voice choice — provider, model, voice — is a MAJOR
production decision. Log it in `decision_log` with
`category: "voice_selection"`, `subject: "Narration TTS provider"`, and
list alternatives in `options_considered`. If the voice changes later,
APPEND a new decision entry with the SAME category + subject (see
AGENT_GUIDE.md → "Re-log Changed Decisions").

The ONLY way out of narration is an explicit user opt-out, recorded as:

```json
{
  "narration_plan": {
    "enabled": false,
    "opt_out_reason": "user wants a silent text-driven montage"
  }
}
```

Do not silently drop narration because "the visuals will carry it" —
on this pipeline they won't.

### 6. Note Music Intent (MANDATORY)

Music supports the narration; it does not replace it. **Music is
MANDATORY by default.** The ONLY way out is an explicit user opt-out
recorded as `music_plan.source = "none"` with a `music_plan.opt_out_reason`.

If the user hasn't mentioned music, ASSUME THEY WANT IT and pick from
(per AGENT_GUIDE.md → "Music Plan (Mandatory)"):

- user-provided track (put path in `music_plan.source_path`),
- music library pick (query `registry.get_by_capability("music_library")` and list tracks),
- royalty-free search (query `registry.get_by_capability("music_search")`, report provider and license),
- generated (name the tool and prompt seed with register),
- explicit opt-out (`source: "none"` + `opt_out_reason`).

Record it:

```json
{
  "music_plan": {
    "source": "generated",
    "provider": "suno_music",
    "prompt_seed": "understated electronic underscore, no vocals, 75s, warm pads, low tempo"
  }
}
```

Warn the user if no music source is available. Do not defer this to the
asset stage where it becomes an expensive surprise.

### 7. Record The Brief

Minimum fields the brief must carry:

```json
{
  "version": "1.0",
  "title": "How The Cloud Actually Works",
  "hook": "The internet doesn't run on servers. It runs on permission.",
  "key_points": [
    "Cloud data is stored in physical data centers",
    "Availability is the real product, not hardware",
    "Redundancy is why it never 'runs out'"
  ],
  "core_message": "The cloud is a network of physical machines engineered to never appear to go down.",
  "cta": "Follow for more tech explained in a minute.",
  "tone": "authoritative",
  "style": "clean-professional",
  "target_audience": "general tech-curious viewers",
  "target_platform": "youtube",
  "target_duration_seconds": 78,
  "reference_material": ["<path to user script>"],
  "metadata": {
    "source_script": "<verbatim user script>",
    "pipeline": "narration-montage",
    "narration_plan": {
      "enabled": true,
      "provider": "openai_tts",
      "model": "gpt-4o-mini-tts",
      "voice": "alloy",
      "language": "zh-CN",
      "register": "authoritative"
    },
    "music_plan": {
      "source": "generated",
      "provider": "suno_music",
      "prompt_seed": "understated electronic underscore, no vocals, 75s, warm pads, low tempo"
    },
    "shot_cadence_seconds": 3.0,
    "subtitle_style": {
      "font_size": 56,
      "position": "bottom-center",
      "color": "#FFFFFF",
      "outline_color": "#000000",
      "mode": "static_whole_line"
    }
  }
}
```

`metadata.shot_cadence_seconds` and `metadata.subtitle_style` are
narration-montage-specific defaults the edit stage may refine.

### 8. Quality Gate

- Hook is ONE concrete line, not a topic summary.
- Tone is ONE word from the register list.
- `target_duration_seconds` is a concrete number consistent with the
  script length estimate.
- `metadata.narration_plan` is present AND either names a real provider
  + voice OR has `enabled: false` + `opt_out_reason` (explicit user
  decision).
- `metadata.music_plan` is present AND either names a real source OR has
  `source: "none"` + `opt_out_reason` (explicit user decision).
- `source_script` is present so the script stage has the raw text.

## Common Pitfalls

- Rewriting the user's script at the idea stage. The brief carries it
  verbatim; the script stage shapes it.
- Stating multiple tones ("authoritative AND conversational"). Pick one.
- Forgetting to ask about the narration voice. The user usually has an
  opinion, and swapping it later is a logged decision churn.
- Forgetting to ask about music. See AGENT_GUIDE.md.
- Ignoring script length when choosing duration. The math in step 4
  exists for a reason.
- Recording `narration_plan` without `source_script` — later stages
  then can't quote the exact words.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true`). After review passes:
checkpoint with `status="awaiting_human"`, present the summary (the Backlot board renders
the artifact), and **END YOUR TURN**. Do not start the next stage in the same response.
Approval is per-gate — an earlier "go ahead" does not cover this gate.
