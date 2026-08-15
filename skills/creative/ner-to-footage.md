# NER-to-Footage: Script → Entities → Stock Footage

> Turn any Chinese narration script/文案 into relevant stock B-roll by
> extracting named entities and driving footage search with them.
> Generic across pipelines (narration-montage, documentary-montage,
> cinematic, hybrid, explainer) — use whenever 文案 must become B-roll.

## When To Use

A script (or any narration text) needs concrete B-roll and the footage
must MATCH the subject. Two tools make the pipeline:

| Step | Tool | What it does |
|------|------|--------------|
| 1 | `ner_extractor` | Chinese NER: PER (人名) / LOC (地名) / ORG (机构名) from the script text |
| 2 | `ner_video_search` | Entity list → English stock queries → search + download → `manifest.json` with provenance |

`ner_video_search` already fetches and dedups clips. The skill's value
is the **query construction discipline** in between — this is where
footage relevance is won or lost.

## Core Idea

**Entities are fact; footage is vision.** An entity like "美国"/"Iran"
tells the search engine nothing visual by itself. You must translate
each entity into concrete, English, *filmable* nouns that match BOTH
the entity AND the script's subject domain (军事/金融/科技/民生…).

A generic fallback query ("city landscape", "business office") gives you
a generic clip — usually the wrong subject. Never let that happen on the
default path.

## Process

### 1. Collect The Text

Gather every script section's text:

- narration-montage/documentary: `script.sections[].text`
- any other pipeline: the narration lines / 旁白 in use

Join them into one string. Keep per-section linkage if scenes already
exist (see step 6).

### 2. Extract Entities

Call `ner_extractor` on the joined text:

```python
resp = ner_extractor.execute({"text": joined_text, "min_confidence": 0.5})
entities = resp.data["entities"]
```

### 3. Normalise Entities (CRITICAL — model output is noisy)

Before searching, fix the model's typical failure modes:

- **Merge single-character fragments.** The MSRA RaNER model often emits
  "美"/"伊"/"苏" instead of "美国"/"伊朗"/"苏联" when the text abbreviates
  country names (e.g. "美伊矛盾"). Expand by longest-matching a whitelist
  of known countries/regions found in the text.
- **Merge same-entity spans** (dedup by `(text, type)`, keep the highest
  confidence — the tool already does this, but re-check against your
  expanded set).
- **Drop fragments < 2 chars** unless they are a whitelisted country.
- **Keep the big three**: Trump / Rouhani-class PER names, country and
  region LOC names, military/party/government ORG names.

### 4. Derive The Subject Domain

Read the brief / script title / core section to name ONE subject domain,
e.g. `军事冲突` / `金融科技` / `医疗卫生`. The domain maps entities to
the filmable vocabulary below. Write the domain into the resulting
queries so adjacent scenes share a coherent visual world.

### 5. Build English Query Maps

For every kept entity, expand to a small list of English queries
(2-5 words each, concrete nouns first, 3-5 per entity). Per entity type:

| Type | Entity | Good query (filmmable, domain-aware) | Bad query (abstract/generic) |
|------|--------|--------------------------------------|------------------------------|
| PER 政要 | 特朗普 | `donald trump speech`, `white house briefing`, `us president press conference` | `person talking`, `interview closeup` |
| PER 政要 | 阿拉格齐 | `iran foreign minister meeting`, `diplomat handshake official` | `person portrait` |
| LOC | 伊朗 | `iran military parade`, `tehran city skyline` | `city landscape`, `landmark aerial` |
| LOC | 美国 | `us flag waving`, `washington dc capitol` | `city street people` |
| LOC | 海湾/中东 | `persian gulf warship`, `middle east map oil` | `ocean`, `map` |
| ORG | 伊朗革命卫队 | `soldiers marching`, `military vehicles convoy`, `army parade uniform` | `business office`, `corporate team` |
| ORG | 政府/国会 | `capitol building columns`, `government briefing room` | `official building` |

Rules:

- **Person → setting, not face.** Stock libraries have almost no footage
  of a *specific* person; searching "trump" yields junk. Instead map a
  PER to the *venue/occasion* where the person operates (speech, press
  conference, official meeting, flag).
- **Location → landmark + domain.** Add the subject's key objects:
  海湾 → warship/missile/destroyer; 中东 → oil field/map/desert.
- **ORG → its people and equipment.** A military ORG maps to soldiers /
  vehicles / parades, not a boardroom.
- **Domain overlay.** Every query gets a filmable noun from the subject
  domain so ALL scenes read as the same story.

Pass these as `query_map` to `ner_video_search` (entity text → query or
list). The tool's fallback vocabulary only exists for unidentified
entities — treat any hit that uses fallback queries as an alert that
step 3/5 missed something.

### 6. Wire Into Scene Queries

If the pipeline has a `scene_plan` (`metadata.queries` per scene),
regenerate the scene-level queries FROM the entity query maps, not by
hand-freewriting. Also:

- Prefer ~4 queries per scene, adjacent scenes with disjoint vocabulary.
- If a scene has no clear entity, reuse the nearest entity's domain
  vocabulary (scene about 美伊对抗 with no PER → `parade`, `warship`,
  `negotation table`, `flags`).

This keeps `run_assets.py`-style fetchers (which read
`scene_plan.metadata.queries`) on the NER-derived path.

### 7. Fetch (via ner_video_search, optional per-pipeline)

```python
resp = ner_video_search.execute({
    "entities": normalised_entities,      # from step 3
    "project_dir": "projects/<project-id>",
    "scene_id": "ner",
    "filters": {"orientation": "landscape", "min_duration": 3.0},
    "per_entity": 3,
    "query_map": english_query_map,        # from step 5
})
```

Per-scene fetchers (existing narration-montage flow) may instead
consume `scene_plan.metadata.queries` directly — either path is NER-driven
as long as the queries came from step 5.

## Quality Gate

- ≥90% of kept entities have a non-fallback, filmable English query map.
- No single-character entities survive step 3.
- No scene query contains: an abstract word on its own (`conflict`,
  `tension`, `negotiation`), a bare country name without a filmable noun,
  or any query from `_CATEGORY_FALLBACK_QUERIES`.
- Adjacent scenes in a `scene_plan` do not share more than one query
  token.
- Spot-check 2+ downloaded clips visually against the section text.

## Common Pitfalls

- **Trusting the model's bare output.** "美/伊/苏" fragments become
  garbage queries. Expand first.
- **Generic fallback silently winning.** If `ner_video_search` stats show
  fallback queries being used, pause and write real `query_map` entries.
- **Chinese queries.** Translate to English — stock APIs rank English far
  higher.
- **Searching a specific person's name.** Use the person's venue/occasion
  instead. Stock has no footage of named individuals.
- **One shared vocabulary across all scenes.** Vary per scene; a parade
  scene and a map scene should not both query "military".
- **Hand-writing queries without the NER step.** The whole point is that
  entities anchor the search to the script's actual subject.

## Example (Jun Zheng / 美伊矛盾 commentary)

Script entities (NER output, normalised):
`特朗普(PER), 阿拉格齐(PER), 美国(LOC), 伊朗(LOC), 中东(LOC), 苏联(LOC), 伊朗革命卫队(ORG), 美国军队/国会(ORG)`

Subject domain: `军事冲突 / 政治博弈`.

Query map:

```json
{
  "特朗普": ["donald trump speech", "us president press conference", "white house briefing"],
  "阿拉格齐": ["iran foreign minister meeting", "diplomat handshake official"],
  "美国": ["us flag waving", "washington dc capitol", "united states army soldiers"],
  "伊朗": ["iran military parade", "tehran skyline", "persian culture architecture"],
  "中东": ["middle east map oil", "desert aerial", "persian gulf warship"],
  "苏联": ["cold war map", "old warship navy"],
  "伊朗革命卫队": ["soldiers marching uniform", "military vehicles convoy", "army parade"],
  "美国军队": ["us marines marching", "military tanks convoy"],
  "国会": ["capitol building columns", "government briefing room"]
}
```

## Reference

- Tool: `tools/analysis/ner_extractor.py` — Chinese NER (MSRA RaNER).
- Tool: `tools/video/ner_video_search.py` — entity→query→download→manifest.
- Research: `docs/ner-research.md` — model selection rationale.