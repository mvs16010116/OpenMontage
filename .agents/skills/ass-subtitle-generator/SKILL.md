---
name: ass-subtitle-generator
description: Generate and burn short-line ASS subtitles for narration-led videos (narration-montage and similar ffmpeg pipelines). Use when creating or restyling subtitles from a narration script — splitting Chinese narration into sentence-per-event short lines, sizing the font, setting white-on-black ASS colors, writing subtitles.ass, or burning subtitles into an existing render with the correct ASS force_style colors. Triggers: subtitle, 字幕, subtitles.ass, 字幕太小, 字幕黑色, white subtitle, force_style, burn subtitles.
---

# ASS Subtitle Generator

Generate a **short-line** ASS subtitle file from a narration script + per-section narration durations, sized and styled for ffmpeg burn, then burn it into the render. This is the pipeline's standard subtitle path — every narration-led video uses it so subtitles look consistent (white text, black outline, one short sentence per event) instead of paragraph-blocks that come out black or too small.

## The script — one source for splitting · styling · timing

Do NOT hand-write the ASS file. One generator, `scripts/build_ass.py`, reads the script artifact and the asset_manifest (narration durations) and writes the whole `.ass`:

```bash
python <SKILL_DIR>/scripts/build_ass.py \
  --script <project>/script.json \
  --manifest <project>/asset_manifest.json \
  --output <project>/assets/subtitles.ass \
  --font-size 68 \
  --max-chars 16 \
  --primary "&H00FFFFFF" \
  --outline "&H00000000" \
  --outline-width 3 \
  --margin-v 55 \
  --alignment 2 \
  --font "MS YaHei"
```

- **Inputs**: `--script` (must have `sections[]` with `id/text/start_seconds/end_seconds`); `--manifest` (optional — provides real narration durations; falls back to script section windows). Asset manifest narration entries use `scene_id` like `scene_01` (zero-padded) joined to `section_01`.
- **Output**: a `.ass` with one `Dialogue` event per short line, timed proportionally to character count across the section's narration window.
- **Style switches** (all CLI flags): `--font-size` (default 68), `--max-chars` (default 16), `--primary`/`--outline` ASS colors, `--outline-width`, `--margin-v`, `--alignment`, `--font`.

## What the generator guarantees

- **Sentence-per-event lines**: splits Chinese narration on `。，！？、；：` punctuation, merges tiny chunks up to `--max-chars`, hard-splits oversized chunks. Normal subtitle display — no paragraph blocks.
- **Proportional timing**: each line's display time = its char share × the section's real narration duration, so text lands on the words being spoken.
- **Readable styling**: default white `&H00FFFFFF` on black outline `&H00000000` at font 68 — large, legible, forced static whole-line.

## The black-text trap — ASS colors, NOT HTML hex

ffmpeg's `subtitles` filter `force_style` (via `video_compose._build_subtitle_style`) passes color values straight through to libass. libass parses **`&HAABBGGRR`** form and silently fails on HTML hex like `#FFFFFF` — a subtitle that renders **black**. Any restyle must carry the ASS-format codes:

| What | HTML (WRONG) | ASS (correct) |
| ---- | ------------ | ------------- |
| white text | `#FFFFFF` | `&H00FFFFFF` |
| black outline | `#000000` | `&H00000000` |
| translucent box | `#00000080` | `&H80000000` |

The `.ass` **Style** line uses the same ASS codes, so the file is correct even without `force_style`.

## Burn into the render

Restyling an existing render? Do NOT re-run the whole compose — re-burn the new `.ass` into the finished video, preserving the audio track. Run via the `video_compose` tool `burn_subtitles` operation, or the same ffmpeg command it builds:

```
-vf "subtitles='<sub_path>':force_style='FontName=MS YaHei,FontSize=68,Bold=0,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=0,MarginV=55,Alignment=2'"
```

- The burn needs a distinct input and output path — ffmpeg cannot edit a file in place (same input/output → "same as Input #0 - exiting"). Copy the source first, then replace.
- Pass the **ASS codes** in `subtitle_style` (`primary_color`/`outline_color`/`back_color`), never HTML hex.
- Keep the burn crf reasonable (~20) so one re-encode doesn't degrade the footage.

## Completion criterion

- `subtitles.ass` regenerated with the requested `--font-size` / `--max-chars`, schema-clean ASS header, and one Dialogue per short line.
- Render re-burned with ASS-format colors; **pixel-check** the subtitle band (~lower third, center) shows a strong white-pixel share (a black-text regression shows ~0).
- Render's verification artifacts (`render_report.json`, `checkpoint_compose.json`, `final_review.json`) updated with the new file size, font size, event count, and a note recording the restyle.
