# military-photo-carousel

Landscape 1920×1080 HyperFrames scene generator: keyword-relevant Pexels **photo carousel** as background (crossfade + Ken Burns) with a dark gradient mask and title-card foreground. For narration-led Chinese military/political commentary videos that need real footage flowing under the copy instead of a static dark card.

Reuses `_military-shared/composition.mjs` (deterministic single paused GSAP timeline, 1920×1080 contract).

## When to use

A narration section needs 2–4 real stills (tankers, radars, warships, maps…) fading under a headline/keyword/number instead of the flat `#070b12` card. Paired with the Pexels fetch flow: `tools/graphics/pexels_image.py` (multi-download candidates) → agent curates by `alt` relevance → `pexels_manifest.json` → this builder renders each section.

## Inputs

| flag | meaning |
|---|---|
| `--project=<name>` | project dir under `projects/` |
| `--slug=<name>` | asset slug; local images are copied to `hyperframes/assets/images/<slug>/` so the renderer resolves them |
| `--title=<text>` | big headline (Chinese OK) |
| `--keyword=<text>` | amber keyword tag under headline (optional) |
| `--number=<val>:<label>` | count-up number + label (optional) |
| `--lower=<text>` | lower-third line (optional) |
| `--images=<a.jpg;b.jpg;c.jpg>` | semicolon-separated paths resolved relative to project root |
| `--duration=<sec>` | scene duration |
| `--accent=<hex>` | accent, default `#fbbf24` |
| `--no-carousel` | skip images → pure dark card (fallback for a section with no relevant photos) |

## Output & render

Writes `projects/<name>/hyperframes/index.html` (and copies local images under `hyperframes/assets/images/<slug>/`). Render:

```
npx hyperframes render projects/<name>/hyperframes -o projects/<name>/renders/<slug>.mp4 --fps 30 -q standard --workers 1 --quiet
```

`hyperframes check` will flag `missing_local_asset` for the `<img>` refs (it resolves project-relative, not hyperframes-relative) — that lint warning is a false positive; the runtime loads the copied images correctly. Trust a real render + frame sampling over the lint.

## Determinism

Same contract as military-title-card: no `Date.now` / `Math.random` / network; single `window.__timelines["main"]` paused timeline. Ken Burns scale + crossfade are explicit timeline tweens, so renders are reproducible.

## Carousel behaviour

- `N` images → each visible `perImg = duration/N` sec; neighbour crossfade 0.6s; first image fades in at t=0.
- Ken Burns per image: `scale 1 → 1.08`, alternate `transformOrigin` (50% 30% / 50% 70%).
- Dark gradient mask + inner vignette over the photos keep headline/numbers readable.
- `--no-carousel` emits the static dark card (used for sections that fell back).

## Verification

- Frame-sample 3-4 timestamps (ffmpeg `-ss`) and check: background is a photo (colour-set size large, not flat), headline white pixels present, and downsampled frame hashes differ between times (carousel moved).
- Check manifest `reason`/`alt` trace for relevance audit.