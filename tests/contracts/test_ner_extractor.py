"""Contract tests for the ner_extractor tool.

These tests are network-free: they cover registry discovery, the tool
contract fields, input validation, and the pure helper functions
(chunking, dedup, Viterbi). End-to-end tests (model download + real
inference) live in scripts/ and are run manually — they need network
and ~410 MB of model download.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.base_tool import ToolRuntime, ToolStability, ToolTier
from tools.tool_registry import ToolRegistry
from tools.analysis.ner_extractor import (
    NerExtractor,
    _chunk_text,
    _dedupe_entities,
    _viterbi_decode,
)


def _tool() -> NerExtractor:
    return NerExtractor()


# ----------------------------------------------------------------------
# Registry discovery & contract
# ----------------------------------------------------------------------


class TestContract:
    def test_registry_discovers_ner_extractor(self):
        reg = ToolRegistry()
        names = reg.discover("tools")
        assert "ner_extractor" in names
        assert reg.get("ner_extractor") is not None

    def test_contract_fields(self):
        t = _tool()
        assert t.name == "ner_extractor"
        assert t.capability == "ner_extraction"
        assert t.provider == "openmontage"
        assert t.tier == ToolTier.ANALYZE
        assert t.runtime == ToolRuntime.LOCAL
        assert t.stability == ToolStability.EXPERIMENTAL
        assert "ner_extraction" in t.capabilities

    def test_input_schema_requires_text(self):
        schema = _tool().input_schema
        assert "text" in schema["required"]
        assert "min_confidence" in schema["properties"]

    def test_get_info_exposes_model(self):
        info = _tool().get_info()
        assert info["ner_model_id"].startswith("damo/")
        assert "ner_model_dir" in info


# ----------------------------------------------------------------------
# Input validation (no network, no model load)
# ----------------------------------------------------------------------


class TestInputValidation:
    def test_missing_text_fails(self):
        res = _tool().execute({})
        assert not res.success
        assert "text" in (res.error or "")

    def test_empty_text_fails(self):
        res = _tool().execute({"text": "   "})
        assert not res.success
        assert "text" in (res.error or "")


# ----------------------------------------------------------------------
# Pure helpers
# ----------------------------------------------------------------------


class TestHelpers:
    def test_chunk_text_short(self):
        text = "华为公司在深圳。"
        assert _chunk_text(text, max_chars=400) == [text]

    def test_chunk_text_long_split(self):
        text = "。".join(["第一句"] * 300)
        chunks = _chunk_text(text, max_chars=400)
        assert len(chunks) > 1
        assert all(len(c) <= 400 for c in chunks)
        assert "".join(chunks).replace("。", "") == "第一句" * 300

    def test_dedupe_entities(self):
        ents = [
            {"text": "北京", "type": "LOC", "confidence": 0.7, "positions": [[0, 2]]},
            {"text": "北京", "type": "LOC", "confidence": 0.9, "positions": [[10, 12]]},
            {"text": "华为", "type": "ORG", "confidence": 0.6, "positions": [[3, 5]]},
        ]
        merged = _dedupe_entities(ents)
        assert len(merged) == 2
        loc = next(e for e in merged if e["text"] == "北京")
        assert loc["confidence"] == 0.9
        assert loc["positions"] == [[0, 2], [10, 12]]
        assert merged[0]["text"] == "北京"  # highest confidence first

    def test_viterbi_falls_back_to_argmax_without_crf(self):
        import torch
        emissions = torch.tensor([[0.0, 10.0], [10.0, 0.0]], dtype=torch.float32)
        assert _viterbi_decode(emissions, None, None, None) == [1, 0]

    def test_viterbi_uses_crf_transitions(self):
        import torch
        emissions = torch.tensor([[0.0, 10.0], [10.0, 0.0]], dtype=torch.float32)
        trans = torch.zeros(2, 2)
        trans[0, 0] = 100.0
        path = _viterbi_decode(
            emissions,
            start_w=torch.zeros(2),
            trans_w=trans,
            end_w=torch.zeros(2),
        )
        assert path == [0, 0]
