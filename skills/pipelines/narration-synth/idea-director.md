# Idea Director - Narration Synth Pipeline

## When To Use

You turn a user prompt and/or their written script (口播文案) into the `brief`
artifact every downstream stage reads. Same mission as the narration-montage idea
director, but the visuals will be **self-generated** — so the brief also shapes
the available visual register (which `military-*` skills are fair game).

## Runtime Selection (MANDATORY — present the constraint, don't silently pick)

Lock `render_runtime = "ffmpeg"` — the **finisher**. HyperFrames is the *asset
generator*, not the final-compose runtime. Per AGENT_GUIDE.md → "Present Both
Composition Runtimes (HARD RULE)":

1. Present both runtimes plainly:
   - **HyperFrames** — smart for this brief because every scene is a
     deterministic HTML/GSAP composition authored by the `military-*` skills and
     rendered to MP4 at the assets stage.
   - **Remotion** — would work for hand-authored React scenes, but there is no
     military scene-type stack, so it would cost extra authoring tokens with no
     visual gain.
2. Explain the composition: HyperFrames *produces the scene clips*; **ffmpeg
   finishes the master** (scene concat + ASS subtitle burn + narration/music mux).
   `render_runtime="ffmpeg"` is the recorded single runtime in
   `edit_decisions`; the HyperFrames step happens *inside* the assets stage.
3. Record a `render_runtime_selection` decision in `decision_log` listing
   `options_considered: [hyperframes, remotion, ffmpeg]`, with
   `rejected_because` for the non-chosen generation+runtime combo.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/brief.schema.json` | Artifact validation |
| User input | Conversation history + written script | The raw ask |
| Layer 3 | `.agents/skills/military-*/SKILL.md` | Visual register available |
| Meta | `skills/meta/reviewer.md` | Self-review pass |

## Process

### 1. Ingest The Script

Same as narration-montage: store the raw text verbatim in `reference_material`
and `metadata.source_script`. Capture register, audience, and any constraints.

### 2. Name The Hook

One concrete, specific line that opens the video — the attention grabber.

- Good: "这艘驱逐舰，正在改写西太平洋的版图。"
- Bad: "今天我们来聊聊海军装备发展。"

### 3. Fix The Tone

One word. For 军政 commentary the register is usually **authoritative** or
**urgent**; occasionally **aspirational** for strategy/exercise pieces. Record it
in `brief.tone`.

### 4. Pick A Duration

Chinese narration maps at ~4-5 chars/sec → `chars / 4.5`. No single section may
exceed ~90s of narration; split at the script stage.

### 5. Choose The Narration Voice (MANDATORY)

Narration is the spine. Record `metadata.narration_plan` with provider/model/voice
matched to the tone (authoritative register → a steady, mid-low voice). Log the
choice as a `voice_selection` decision with `options_considered`. The ONLY way out
of narration is an explicit user opt-out (`enabled: false` + `opt_out_reason`).

### 6. Note Music Intent (MANDATORY)

Music supports the narration. Per AGENT_GUIDE.md "Music Plan": user-provided track,
music library, royalty-free search, generated, or explicit opt-out. For 军政, an
underscored tension bed (low brass/pulse, no vocals) fits the register.

### 7. Record The brief + Visual Register

The brief carries the CORE creative promise that the scene plan will deliver:

```json
{
  "version": "1.0",
  "title": "新型驱逐舰：改写西太平洋",
  "hook": "这艘驱逐舰，正在改写西太平洋的版图。",
  "key_points": [
    "新型驱逐舰的吨位与作能能力",
    "区域防空与反舰体系的构成",
    "列装后的战略意义"
  ],
  "core_message": "一艘国产驱逐舰如何重塑区域力量平衡。",
  "cta": "关注后续装备深度分析。",
  "tone": "authoritative",
  "style": "clean-professional",
  "target_audience": "军事爱好者、时政评论观众",
  "target_platform": "youtube",
  "target_duration_seconds": 90,
  "reference_material": ["<path to user script>"],
  "metadata": {
    "source_script": "<verbatim user script>",
    "pipeline": "narration-synth",
    "visual_register": {
      "allowed_skills": ["military-warship", "military-missile", "military-map-deduction", "military-data-viz", "military-title-card", "military-seal"],
      "default_palette": "dark",
      "default_accent": "#fbbf24",
      "style_note": "dark naval background, amber accents, archival-bold headlines — 军政 objectivity over decorative flash"
    },
    "bookend_plan": {
      "opener": { "skill": "military-title-card", "mode": "center" },
      "chapter_breaks": { "skill": "military-title-card", "mode": "lower" }
    },
    "narration_plan": {
      "enabled": true,
      "provider": "openai_tts",
      "model": "gpt-4o-mini-tts",
      "voice": "onyx",
      "language": "zh-CN",
      "register": "authoritative"
    },
    "music_plan": {
      "source": "generated",
      "provider": "suno_music",
      "prompt_seed": "understated military-pulse underscore, no vocals, 90s, low brass + sub-bass, tense but restrained"
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

`visual_register.allowed_skills` becomes the whitelist the scene director may
route to. `bookend_plan` tells the scene plan to open with a center title card and
use lower title cards at chapter breaks. Inside the allowed set, prefer roughly:
warship/missile for equipment, map-deduction for 战略/态势, data-viz for 军费/装备
对比, title-card for 章节/强调, seal for 文书/指令.

### 8. Quality Gate

- Hook is one concrete line, not a topic summary.
- Tone is one word from the register list.
- `target_duration_seconds` concrete and consistent with script length.
- `metadata.visual_register.allowed_skills` — non-empty whitelist of real
  `military-*` skills, default palette + accent set.
- `metadata.bookend_plan` — opener + chapter_breaks defined.
- `metadata.narration_plan` present (provider + voice) OR explicit opt-out.
- `metadata.music_plan` present OR explicit opt-out.
- `source_script` present.

## Common Pitfalls

- Rewriting the script at the idea stage — carry it verbatim.
- Leaving `allowed_skills` empty or naming a skill that doesn't exist.
- Picking an accent/palette that fights the 军政 register (neon cyan over archival
  amber is a visual-identity fail).
- Forgetting the bookend plan — chapterless cuts drift.
- Recording narration/music plans without `source_script`.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true`). After review passes:
checkpoint with `status="awaiting_human"`, present the summary (the Backlot board renders
the artifact), and **END YOUR TURN**. Do not start the next stage in the same response.
Approval is per-gate — an earlier "go ahead" does not cover this gate.