"""Contract tests for the ner_video_search tool.

These tests are network-free: they cover registry discovery, the tool
contract fields, input validation, and the pure query-building helpers.
End-to-end tests (stock API + video download) live in scripts/ and are
run manually — they need network.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.base_tool import ToolRuntime, ToolStability, ToolTier
from tools.tool_registry import ToolRegistry
from tools.video.ner_video_search import (
    NerVideoSearch,
    _is_asciiish,
    _project_relative_path,
)


def _tool() -> NerVideoSearch:
    return NerVideoSearch()


# ----------------------------------------------------------------------
# Registry discovery & contract
# ----------------------------------------------------------------------


class TestContract:
    def test_registry_discovers_ner_video_search(self):
        reg = ToolRegistry()
        names = reg.discover("tools")
        assert "ner_video_search" in names
        assert reg.get("ner_video_search") is not None

    def test_contract_fields(self):
        t = _tool()
        assert t.name == "ner_video_search"
        assert t.capability == "ner_to_footage"
        assert t.provider == "openmontage"
        assert t.tier == ToolTier.SOURCE
        assert t.runtime == ToolRuntime.API
        assert t.stability == ToolStability.EXPERIMENTAL
        assert "stock_video_search" in t.capabilities
        assert "video_download" in t.capabilities
        # NER extraction is ner_extractor's job now.
        assert "ner_extraction" not in t.capabilities

    def test_input_schema_requires_entities(self):
        schema = _tool().input_schema
        assert "entities" in schema["required"]
        assert "text" not in schema["required"]
        props = schema["properties"]
        for key in ("entities", "project_dir", "output_dir", "scene_id", "sources",
                    "filters", "per_entity", "max_entities", "query_map"):
            assert key in props

    def test_get_info_exposes_sources(self):
        info = _tool().get_info()
        assert "source_provider_summary" in info
        # No model metadata: the NER model lives in ner_extractor.
        assert "ner_model_id" not in info


# ----------------------------------------------------------------------
# Input validation (no network)
# ----------------------------------------------------------------------


class TestInputValidation:
    def test_missing_entities_fails(self):
        res = _tool().execute({})
        assert not res.success
        assert "entities" in (res.error or "")

    def test_missing_output_target_fails(self):
        res = _tool().execute({"entities": [{"text": "深圳", "type": "LOC"}]})
        assert not res.success
        assert "project_dir" in (res.error or "")

    def test_output_dir_outside_projects_fails(self, tmp_path):
        res = _tool().execute({
            "entities": [{"text": "深圳", "type": "LOC"}],
            "output_dir": str(tmp_path / "elsewhere"),
        })
        assert not res.success
        assert "projects" in (res.error or "")


# ----------------------------------------------------------------------
# Pure helpers
# ----------------------------------------------------------------------


class TestHelpers:
    def test_is_asciiish(self):
        assert _is_asciiish("iPhone 15")
        assert _is_asciiish("NASA")
        assert not _is_asciiish("深圳")
        assert not _is_asciiish("阿里巴巴")

    def test_project_relative_path(self, tmp_path):
        rel = _project_relative_path(
            PROJECT_ROOT / "projects" / "demo" / "assets" / "video" / "ner" / "clip1.mp4"
        )
        assert rel == "assets/video/ner/clip1.mp4"

    def test_query_map_override(self):
        t = _tool()
        entity = {"text": "北京", "type": "LOC"}
        assert t._build_queries(entity, {"北京": "Beijing city aerial"}) == [
            "Beijing city aerial"
        ]
        assert t._build_queries(entity, {"北京": ["a", "b"]}) == ["a", "b"]

    def test_ascii_entity_used_verbatim(self):
        t = _tool()
        queries = t._build_queries({"text": "NASA", "type": "ORG"}, {})
        assert queries[0] == "NASA"

    def test_chinese_entity_falls_back_to_category(self):
        t = _tool()
        queries = t._build_queries({"text": "深圳", "type": "LOC"}, {})
        assert queries  # non-empty
        assert all(q.isascii() for q in queries)
        assert queries == [
            "city landscape", "landmark aerial", "city street people",
        ]
