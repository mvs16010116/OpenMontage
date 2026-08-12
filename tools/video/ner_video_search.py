"""Entity-driven stock video search and acquisition tool.

Given a list of named entities (people PER / places LOC / organizations
ORG — typically the output of ``ner_extractor``), this tool:

1. **Builds search queries** from the entities. Stock APIs rank English
   queries far better than Chinese ones, so the tool maps each entity to
   English queries (ASCII-containing entities are used verbatim; pure-Chinese
   entities fall back to a per-category English shot vocabulary). A
   ``query_map`` input lets the caller override any entity → queries.
2. **Searches stock sources** (default ``pexels``, same adapters the
   corpus builder uses) for footage matching each entity.
3. **Downloads** matching clips into the project and writes an
   ``asset_manifest``-compatible ``manifest.json`` next to them, with
   full provenance (provider, original_url, license, duration,
   resolution) and the entity → clip linkage.

This is the footage-gathering half of the script→footage flow. The
analysis half — turning a script/文案 into entities — lives in
``ner_extractor``. Feed its ``entities`` output directly into the
``entities`` input here.

Design notes
------------
- Global dedup across the whole run: a stock ``video_id`` is downloaded
  at most once, even if several entities' queries surface it.
- Per-candidate errors are collected, never fatal: one flaky URL must
  not poison the whole fetch.
- All outputs land under a project: pass ``project_dir`` (writes to
  ``assets/video/<scene_id>/``) or an explicit ``output_dir``.

Agent surface
-------------
Keep the agent's decisions at the top of the input schema: WHICH
entities to fetch footage for, WHERE to put the footage, HOW MANY clips
per entity, and any entity→query overrides. Everything else has sensible
defaults.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Optional

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)

# Entity category → English fallback shot vocabulary. Pexels-style stock
# APIs rank English queries far above Chinese ones, so pure-Chinese
# entities map to one of these generic-but-relevant query sets. The
# caller can override per entity with `query_map`.
_CATEGORY_FALLBACK_QUERIES: dict[str, list[str]] = {
    "PER": ["person portrait", "interview closeup", "person talking"],
    "LOC": ["city landscape", "landmark aerial", "city street people"],
    "ORG": ["business office", "corporate team", "office building"],
    "OTHER": ["stock footage", "abstract background"],
}

# Minimum clip duration (seconds) — clips shorter than the shot cadence
# flash-cut when composed, so we filter them at search time.
_DEFAULT_MIN_DURATION = 3.0
_DEFAULT_MAX_ENTITIES = 10
_DEFAULT_PER_ENTITY = 2


def _is_asciiish(text: str) -> bool:
    """True when the entity contains ASCII letters/digits (brands, IDs).

    Such entities can be searched verbatim on English-first stock APIs.
    """
    return bool(re.search(r"[A-Za-z0-9]", text))


class NerVideoSearch(BaseTool):
    name = "ner_video_search"
    version = "0.2.0"
    tier = ToolTier.SOURCE
    capability = "ner_to_footage"
    provider = "openmontage"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.API  # network stock APIs (no local model)

    dependencies = [
        "python:requests",
    ]
    install_instructions = (
        "pip install requests\n"
        "At least one stock source must be configured, e.g. "
        "PEXELS_API_KEY (free at https://www.pexels.com/api/).\n"
        "Feed it the `entities` output of ner_extractor."
    )
    agent_skills = []

    capabilities = [
        "stock_video_search",
        "video_download",
        "asset_manifest_writing",
    ]
    supports = {
        "entity_to_query_mapping": True,
        "global_clip_dedup": True,
        "project_output": True,
        "landscape_default": True,
    }
    best_for = [
        "script/文案-driven footage gathering (narration-montage style)",
        "turning named entities (people/places/organizations) into B-roll",
        "automating the scene_plan → assets gap for Chinese scripts",
    ]
    not_good_for = [
        "custom/AI-generated scenes (use video generation tools)",
        "semantic retrieval over an existing corpus (use clip_search)",
        "extracting entities from text (use ner_extractor)",
    ]
    fallback_tools = []

    input_schema = {
        "type": "object",
        "required": ["entities"],
        "properties": {
            "entities": {
                "type": "array",
                "minItems": 1,
                "description": "Entity list from ner_extractor (or any "
                               "[{text, type}, ...] list). Items need at least "
                               "`text`; `type` defaults to OTHER.",
                "items": {
                    "type": "object",
                    "required": ["text"],
                    "properties": {
                        "text": {"type": "string"},
                        "type": {"type": "string"},
                        "confidence": {"type": "number"},
                    },
                },
            },
            "project_dir": {
                "type": "string",
                "description": "Project workspace (projects/<project-id>). "
                               "Footage lands in <project_dir>/assets/video/<scene_id>/.",
            },
            "output_dir": {
                "type": "string",
                "description": "Explicit output directory (overrides project_dir "
                               "layout). Must be under projects/ per workspace rules.",
            },
            "scene_id": {
                "type": "string",
                "default": "ner",
                "description": "Scene label used as the sub-directory and in "
                               "the manifest asset linkage.",
            },
            "sources": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Stock source names to search, e.g. ['pexels']. "
                               "Defaults to all configured sources.",
            },
            "filters": {
                "type": "object",
                "properties": {
                    "min_duration": {"type": "number", "description": "Seconds floor."},
                    "max_duration": {"type": "number", "description": "Seconds ceiling."},
                    "orientation": {
                        "type": "string",
                        "enum": ["landscape", "portrait", "square"],
                    },
                    "min_width": {"type": "integer"},
                },
            },
            "per_entity": {
                "type": "integer",
                "default": 2,
                "minimum": 1,
                "maximum": 10,
                "description": "Clips to download per entity (before global dedup).",
            },
            "max_entities": {
                "type": "integer",
                "default": 10,
                "minimum": 1,
                "maximum": 100,
                "description": "Cap on how many entities to fetch footage for.",
            },
            "query_map": {
                "type": "object",
                "description": "Optional entity-text → English query overrides, "
                               "e.g. {\"北京\": \"Beijing Forbidden City aerial\"}. "
                               "Value may be a string or a list of strings.",
            },
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=512, vram_mb=0, disk_mb=1000, network_required=True
    )
    side_effects = [
        "searches configured stock APIs (e.g. Pexels)",
        "downloads video clips into the project output directory",
        "writes manifest.json describing downloaded assets",
    ]
    user_visible_verification = [
        "Inspect <output_dir>/manifest.json for provenance fields",
        "Play a downloaded clip to confirm it matches the entity",
    ]

    # ------------------------------------------------------------------
    # Status / info
    # ------------------------------------------------------------------

    def get_status(self) -> ToolStatus:
        try:
            self.check_dependencies()
        except Exception:
            return ToolStatus.UNAVAILABLE
        if not _any_source_available():
            return ToolStatus.UNAVAILABLE
        return ToolStatus.AVAILABLE

    def get_info(self) -> dict[str, Any]:
        info = super().get_info()
        try:
            from tools.video.stock_sources import source_summary
            info["source_provider_summary"] = source_summary()
        except Exception:
            info["source_provider_summary"] = {
                "configured": 0, "total": 0,
                "available_source_names": [], "unavailable_source_names": [],
            }
        return info

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0  # free-tier stock sources

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        start = time.time()
        entities_in = inputs.get("entities")
        if not entities_in:
            return ToolResult(
                success=False,
                error="`entities` is required — pass the entity list from "
                      "ner_extractor (or any [{text, type}, ...] list).",
            )

        try:
            out_dir = self._resolve_output_dir(inputs)
        except ValueError as e:
            return ToolResult(success=False, error=str(e))

        requested_sources = inputs.get("sources")
        sources = self._resolve_sources(requested_sources)
        if not sources:
            from tools.video.stock_sources import source_summary
            summary = source_summary()
            hint = (
                f"Configured now: "
                f"{', '.join(summary['available_source_names']) or 'none'}. "
                "See the tool's install_instructions."
            )
            if requested_sources:
                hint = (
                    f"Requested sources unavailable or unknown: "
                    f"{', '.join(requested_sources)}. "
                    f"Configured now: "
                    f"{', '.join(summary['available_source_names']) or 'none'}."
                )
            return ToolResult(
                success=False,
                error="No stock sources available for video search. " + hint,
            )

        filters = dict(inputs.get("filters") or {})
        # Landscape by default: narration-montage composes to a 1920x1080
        # canvas and portrait stock clips would letterbox or crop badly.
        filters.setdefault("orientation", "landscape")
        min_duration = filters.get("min_duration", _DEFAULT_MIN_DURATION)
        per_entity = int(inputs.get("per_entity", _DEFAULT_PER_ENTITY))
        max_entities = int(inputs.get("max_entities", _DEFAULT_MAX_ENTITIES))
        query_map: dict = inputs.get("query_map") or {}
        scene_id = inputs.get("scene_id") or "ner"

        # Normalise the entity list. Every item needs `text`; `type` is
        # used for query building and defaults to OTHER. Confidence is
        # informational here — filtering is ner_extractor's job.
        entities: list[dict[str, Any]] = []
        for raw in entities_in:
            if not isinstance(raw, dict):
                continue
            text = str(raw.get("text", "")).strip()
            if not text:
                continue
            entities.append({
                "text": text,
                "type": str(raw.get("type") or "OTHER").strip().upper(),
                "confidence": float(raw.get("confidence") or 1.0),
            })
        entities = entities[:max_entities]
        if not entities:
            return ToolResult(
                success=True,
                data={
                    "entities": [],
                    "assets": [],
                    "output_dir": str(out_dir),
                    "manifest_path": str(out_dir / "manifest.json"),
                    "stats": {
                        "entities_found": 0,
                        "entities_with_footage": 0,
                        "clips_downloaded": 0,
                        "errors": [],
                    },
                },
            )

        # Per entity: build queries → search → download → record.
        assets: list[dict[str, Any]] = []
        used_clip_ids: set[str] = set()          # global dedup
        used_video_ids: set[str] = set()          # provenance-level dedup
        errors: list[dict[str, Any]] = []
        per_entity_counts: dict[str, int] = {}
        entity_footage: dict[str, list[str]] = {}

        for entity in entities:
            queries = self._build_queries(entity, query_map)
            picked: list[tuple[str, Any]] = []    # (filename, asset_dict)
            for query in queries:
                if len(picked) >= per_entity:
                    break
                for cand in _search_all(sources, query, filters):
                    if len(picked) >= per_entity:
                        break
                    if cand.clip_id in used_clip_ids:
                        continue
                    if cand.kind != "video":
                        continue
                    if min_duration and cand.duration and cand.duration < min_duration:
                        continue
                    # Accept this candidate: download it.
                    try:
                        fname, asset = self._download_candidate(
                            cand, out_dir, scene_id, query, entity
                        )
                    except Exception as e:
                        errors.append({
                            "clip_id": cand.clip_id,
                            "entity": entity["text"],
                            "error": f"{type(e).__name__}: {e}",
                        })
                        continue
                    used_clip_ids.add(cand.clip_id)
                    if cand.source_id:
                        used_video_ids.add(f"{cand.source}_{cand.source_id}")
                    picked.append((fname, asset))

            if picked:
                entity_footage[entity["text"]] = [f for f, _ in picked]
                per_entity_counts[entity["text"]] = len(picked)
                assets.extend(a for _, a in picked)

        # Write the manifest.
        manifest_path = out_dir / "manifest.json"
        manifest = {
            "version": "1.0",
            "assets": assets,
            "total_cost_usd": 0.0,
            "metadata": {
                "tool": self.name,
                "generated_by": "ner_video_search",
                "scene_id": scene_id,
                "entities": [
                    {
                        "text": e["text"],
                        "type": e["type"],
                        "confidence": round(e["confidence"], 4),
                        "queries": self._build_queries(e, query_map),
                        "footage": entity_footage.get(e["text"], []),
                    }
                    for e in entities
                ],
                "stats": {
                    "entities_found": len(entities),
                    "entities_with_footage": len(entity_footage),
                    "clips_downloaded": len(assets),
                    "used_video_ids": len(used_video_ids),
                    "errors": errors,
                },
            },
        }
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            return ToolResult(
                success=False,
                error=f"Failed to write manifest at {manifest_path}: {e}",
            )

        return ToolResult(
            success=True,
            data={
                "entities": manifest["metadata"]["entities"],
                "assets": assets,
                "output_dir": str(out_dir),
                "manifest_path": str(manifest_path),
                "stats": manifest["metadata"]["stats"],
            },
            artifacts=[str(manifest_path)],
            duration_seconds=round(time.time() - start, 2),
        )

    # ------------------------------------------------------------------
    # Output resolution
    # ------------------------------------------------------------------

    def _resolve_output_dir(self, inputs: dict[str, Any]) -> Path:
        """Resolve the footage output directory.

        Precedence: explicit ``output_dir`` > ``project_dir``-based layout.
        Both must end up under a ``projects/`` workspace per AGENT_GUIDE.
        """
        out = inputs.get("output_dir")
        project_dir = inputs.get("project_dir")
        if out:
            path = Path(out)
            if not _is_under_projects(path):
                raise ValueError(
                    "output_dir must live under projects/ (workspace contract). "
                    f"Got: {path}"
                )
            return path
        if project_dir:
            path = Path(project_dir) / "assets" / "video" / (inputs.get("scene_id") or "ner")
            if not _is_under_projects(path):
                raise ValueError(
                    "project_dir must live under projects/ (workspace contract). "
                    f"Got: {path}"
                )
            return path
        raise ValueError(
            "Pass either `project_dir` (projects/<project-id>) or `output_dir` "
            "(under projects/) to tell the tool where to put the footage."
        )

    def _resolve_sources(self, names: Optional[list[str]]) -> list[Any]:
        from tools.video.stock_sources import (
            all_sources, available_sources, get_source,
        )
        if not names:
            # Default to Pexels only: it is the fastest, highest-quality
            # general B-roll source and matches the narration-montage
            # pipeline convention. Other no-key sources (NASA, Wikimedia,
            # ...) are niche and noisy — enable them explicitly via
            # `sources` when the topic calls for them.
            pexels = all_sources()
            pexels = [s for s in pexels if s.name == "pexels" and s.is_available()]
            if pexels:
                return pexels
            return available_sources()
        requested: list[Any] = []
        known = {s.name: s for s in all_sources()}
        for name in names:
            s = known.get(name)
            if s is None:
                try:
                    s = get_source(name)
                except KeyError:
                    continue
            if s.is_available():
                requested.append(s)
        return requested

    # ------------------------------------------------------------------
    # Query building
    # ------------------------------------------------------------------

    def _build_queries(
        self, entity: dict[str, Any], query_map: dict
    ) -> list[str]:
        """Map an entity to English search queries (deduped, in order)."""
        text = entity["text"]
        if query_map and text in query_map:
            override = query_map[text]
            if isinstance(override, str):
                return [override]
            return list(override)
        queries: list[str] = []
        if _is_asciiish(text):
            queries.append(text)
        for fb in _CATEGORY_FALLBACK_QUERIES.get(entity["type"], _CATEGORY_FALLBACK_QUERIES["OTHER"]):
            queries.append(fb)
        seen: set[str] = set()
        out: list[str] = []
        for q in queries:
            q = q.strip()
            if q and q not in seen:
                seen.add(q)
                out.append(q)
        return out or [entity["type"]]

    # ------------------------------------------------------------------
    # Search & download
    # ------------------------------------------------------------------

    def _download_candidate(
        self,
        cand: Any,
        out_dir: Path,
        scene_id: str,
        query: str,
        entity: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        """Download one candidate; returns (filename, asset_dict).

        Raises on download failure — the caller records the error.
        """
        out_dir.mkdir(parents=True, exist_ok=True)
        idx = len(list(out_dir.glob("clip*.mp4"))) + 1
        fname = f"clip{idx}.mp4"
        from tools.video.stock_sources import get_source
        src = get_source(cand.source)
        src.download(cand, out_dir / fname)

        asset = {
            "id": cand.clip_id,
            "type": "video",
            "path": _project_relative_path(out_dir / fname),
            "source_tool": self.name,
            "scene_id": scene_id,
            "provider": cand.source,
            "license": cand.license,
            "original_url": cand.source_url,
            "duration_seconds": cand.duration,
            "resolution": (
                f"{cand.width}x{cand.height}" if cand.width and cand.height else ""
            ),
            "query": query,
            "subtype": "stock",
            "generation_summary": (
                f"NER entity '{entity['text']}' ({entity['type']}) → "
                f"stock query '{query}'"
            ),
        }
        return fname, asset


# ----------------------------------------------------------------------
# Module-level helpers
# ----------------------------------------------------------------------


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _is_under_projects(path: Path) -> bool:
    try:
        Path(path).resolve().relative_to(_project_root().resolve() / "projects")
        return True
    except ValueError:
        return False


def _project_relative_path(path: Path) -> str:
    """Return a path relative to the owning project root.

    The asset_manifest contract wants ``path`` relative to the pipeline
    project directory (e.g. ``assets/video/ner/clip1.mp4``, no
    ``projects/<id>/`` prefix). We walk up to the first ``projects/<id>``
    segment; if none exists, fall back to the raw path string. Always
    uses forward slashes so the manifest is portable across platforms.
    """
    resolved = Path(path).resolve()
    root = _project_root().resolve()
    try:
        rel = resolved.relative_to(root)
        parts = rel.parts
        if len(parts) >= 2 and parts[0] == "projects":
            return str(Path(*parts[2:])).replace("\\", "/")
    except ValueError:
        pass
    return str(path).replace("\\", "/")


def _any_source_available() -> bool:
    try:
        from tools.video.stock_sources import available_sources
        return bool(available_sources())
    except Exception:
        return False


def _search_all(
    sources: list[Any], query: str, filters: dict
) -> list[Any]:
    from tools.video.stock_sources import SearchFilters
    f = SearchFilters(
        kind="video",
        min_duration=filters.get("min_duration"),
        max_duration=filters.get("max_duration"),
        orientation=filters.get("orientation"),
        min_width=filters.get("min_width"),
        per_page=int(filters.get("per_page", 10)),
    )
    out: list[Any] = []
    for src in sources:
        try:
            out.extend(src.search(query, f))
        except Exception:
            continue  # per-source tolerance
    return out
