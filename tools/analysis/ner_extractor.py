"""Chinese named-entity recognition (NER) extraction tool.

Given a script / 文案, extracts named entities — 人名 PER, 地名 LOC,
机构名 ORG — using the 通义实验室 RaNER model (StructBERT-base, MSRA
test F1 96.69) from ModelScope, loaded through standard HuggingFace
``transformers`` and decoded with the checkpoint's own CRF matrices
(Viterbi).

The model auto-downloads from ModelScope on first use (~409 MB) into
``.models/ner_raner_chinese/``. The model is cached per process, so
repeated calls in one run don't reload the weights.

Design
------
This is the analysis half of the script→footage flow: it extracts
entities only, with no network calls beyond the one-time model
download. Feed the returned ``entities`` list into ``ner_video_search``
to turn them into stock footage, or use them directly as input to any
other stage.
"""
from __future__ import annotations

import re
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

# ----------------------------------------------------------------------
# NER model configuration
# ----------------------------------------------------------------------

_MODEL_ID = "damo/nlp_raner_named-entity-recognition_chinese-base-news"
_DEFAULT_MODEL_DIR = (
    Path(__file__).resolve().parent.parent.parent / ".models" / "ner_raner_chinese"
)

# Minimum confidence for an entity to survive extraction (execute-level
# default; callers may lower it).
_DEFAULT_MIN_CONFIDENCE = 0.5


class NerExtractor(BaseTool):
    name = "ner_extractor"
    version = "0.1.0"
    tier = ToolTier.ANALYZE
    capability = "ner_extraction"
    provider = "openmontage"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.LOCAL  # local model inference; one-time model download

    dependencies = [
        "python:transformers",
        "python:torch",
        "python:modelscope",
    ]
    install_instructions = (
        "pip install transformers torch modelscope\n"
        "The NER model auto-downloads from ModelScope on first use "
        f"({_MODEL_ID}, ~409 MB) into {_DEFAULT_MODEL_DIR}."
    )
    agent_skills = []

    capabilities = [
        "ner_extraction",
        "chinese_entity_recognition",
    ]
    supports = {
        "entity_types": ["PER", "LOC", "ORG"],
        "bioes_decoding": True,
        "crf_viterbi": True,
        "confidence_filtering": True,
        "span_positions": True,
    }
    best_for = [
        "extracting people/places/organizations from Chinese scripts",
        "feeding entities into ner_video_search for footage gathering",
        "entity-level analysis of narration/文案 text",
    ]
    not_good_for = [
        "fine-grained 10-class entity types (use a CLUENER-style model)",
        "searching or downloading video (use ner_video_search)",
    ]
    fallback_tools = []

    input_schema = {
        "type": "object",
        "required": ["text"],
        "properties": {
            "text": {
                "type": "string",
                "description": "The script/文案 text to extract entities from.",
            },
            "min_confidence": {
                "type": "number",
                "default": 0.5,
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "Entities below this confidence are dropped.",
            },
            "model_dir": {
                "type": "string",
                "description": "Local NER model directory. Defaults to "
                               ".models/ner_raner_chinese and auto-downloads "
                               "from ModelScope on first use.",
            },
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=2, ram_mb=2048, vram_mb=0, disk_mb=600, network_required=False
    )
    side_effects = [
        "downloads NER model from ModelScope on first use (~409 MB)",
    ]
    user_visible_verification = [
        "Spot-check entity spans against the source text",
        "Check per-entity confidence values are plausible",
    ]

    def __init__(self) -> None:
        super().__init__()
        self._model: Optional[tuple[Any, Any]] = None  # (tokenizer, model) cache

    # ------------------------------------------------------------------
    # Status / info
    # ------------------------------------------------------------------

    def get_status(self) -> ToolStatus:
        try:
            self.check_dependencies()
        except Exception:
            return ToolStatus.UNAVAILABLE
        if not self._model_dir().exists():
            return ToolStatus.DEGRADED  # usable, but model download required first
        return ToolStatus.AVAILABLE

    def get_info(self) -> dict[str, Any]:
        info = super().get_info()
        info["ner_model_id"] = _MODEL_ID
        info["ner_model_dir"] = str(self._model_dir())
        return info

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0  # fully local inference

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        text = inputs.get("text", "").strip()
        if not text:
            return ToolResult(
                success=False,
                error="`text` is required — pass the script/文案 to analyze.",
            )
        min_confidence = float(inputs.get("min_confidence", _DEFAULT_MIN_CONFIDENCE))

        try:
            entities = self._extract_entities(text)
        except Exception as e:
            return ToolResult(
                success=False,
                error=(
                    f"NER model failed: {type(e).__name__}: {e}. "
                    + self.install_instructions
                ),
            )

        raw_spans = len(entities)
        entities = [
            e for e in entities if e["confidence"] >= min_confidence
        ]
        entities = _dedupe_entities(entities)

        return ToolResult(
            success=True,
            data={
                "entities": entities,
                "stats": {
                    "raw_spans": raw_spans,
                    "entities_after_filter": len(entities),
                    "min_confidence": min_confidence,
                    "model_id": _MODEL_ID,
                },
            },
        )

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _model_dir(self) -> Path:
        return Path(_DEFAULT_MODEL_DIR)

    def _ensure_model(self) -> Path:
        """Return a local model dir, downloading from ModelScope if needed."""
        model_dir = self._model_dir()
        if (model_dir / "config.json").exists():
            return model_dir
        try:
            from modelscope import snapshot_download
        except ImportError:
            raise RuntimeError(
                "modelscope is required to download the NER model. "
                "pip install modelscope"
            )
        model_dir.parent.mkdir(parents=True, exist_ok=True)
        snapshot_download(_MODEL_ID, local_dir=str(model_dir))
        if not (model_dir / "config.json").exists():
            raise RuntimeError(
                f"Model download from ModelScope did not yield config.json at "
                f"{model_dir}. Check network access to modelscope.cn."
            )
        return model_dir

    def _get_model(self) -> tuple[Any, Any]:
        """Lazily load (tokenizer, model) once per process.

        The RaNER checkpoint is trained with the Alibaba StructBERT +
        CRF training code, so its weight keys are ``encoder.*`` /
        ``linear.*`` / ``crf.*`` instead of the transformers-standard
        ``bert.*`` / ``classifier.*``. We remap the keys and load with
        ``strict=False``, keeping the CRF transition matrices on the
        model object for Viterbi decoding in `_extract_entities`.
        """
        if self._model is not None:
            return self._model
        model_dir = self._ensure_model()
        from transformers import BertForTokenClassification, AutoTokenizer
        import torch

        tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        config_path = Path(model_dir) / "config.json"
        config = BertForTokenClassification.config_class.from_json_file(
            str(config_path)
        )
        model = BertForTokenClassification(config)

        ckpt = torch.load(
            Path(model_dir) / "pytorch_model.bin",
            map_location="cpu",
            weights_only=True,
        )
        remapped: dict[str, Any] = {}
        for key, value in ckpt.items():
            if key.startswith("encoder."):
                remapped["bert." + key[len("encoder."):]] = value
            elif key == "linear.weight":
                remapped["classifier.weight"] = value
            elif key == "linear.bias":
                remapped["classifier.bias"] = value
            elif key.startswith("bert."):
                remapped[key] = value
        missing, _ = model.load_state_dict(remapped, strict=False)
        # The classifier head is what turns hidden states into labels —
        # if it didn't load, the model is random and NER is meaningless.
        if any("classifier" in m for m in missing):
            raise RuntimeError(
                "NER checkpoint incompatible: classifier head weights were "
                f"missing after key remap. Missing: {missing[:5]}"
            )
        model.eval()

        # Keep the CRF matrices (if present) for Viterbi decoding.
        crf: dict[str, Any] = {}
        for key, value in ckpt.items():
            if key.startswith("crf."):
                crf[key[len("crf."):]] = value
        model._crf_weights = crf  # type: ignore[attr-defined]

        self._model = (tokenizer, model)
        return self._model

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    def _extract_entities(self, text: str) -> list[dict[str, Any]]:
        """Run NER over the text (chunked) and return entity dicts.

        Each entity: {text, type, confidence, positions: [[start,end], ...]}.
        """
        tokenizer, model = self._get_model()
        import torch

        # config.id2label may use int keys or str keys depending on how the
        # checkpoint was saved. Normalise once to int -> label.
        raw_id2label = model.config.id2label or {}
        id2label: dict[int, str] = {}
        for k, v in raw_id2label.items():
            try:
                id2label[int(k)] = str(v)
            except (TypeError, ValueError):
                continue

        entities: list[dict[str, Any]] = []
        for chunk in _chunk_text(text, max_chars=400):
            encoding = tokenizer(
                chunk,
                return_tensors="pt",
                return_offsets_mapping=True,
                truncation=True,
                max_length=510,
            )
            offsets = encoding.pop("offset_mapping")[0].tolist()
            with torch.no_grad():
                logits = model(**encoding).logits[0]  # [seq_len, num_labels]
            probs = torch.softmax(logits, dim=-1)
            # Decode labels: CRF Viterbi when the checkpoint shipped CRF
            # matrices, plain argmax otherwise.
            crf = getattr(model, "_crf_weights", {}) or {}
            if crf.get("transitions") is not None:
                label_ids = _viterbi_decode(
                    logits,
                    crf.get("start_transitions"),
                    crf["transitions"],
                    crf.get("end_transitions"),
                )
            else:
                label_ids = logits.argmax(dim=-1).tolist()
            token_ids = encoding["input_ids"][0].tolist()

            seq_len = len(label_ids)
            i = 1  # skip [CLS]
            while i < seq_len - 1:  # [SEP] is last
                label = id2label.get(label_ids[i], "O")
                token = tokenizer.convert_ids_to_tokens(token_ids[i])
                # Skip sub-word continuations of an O token.
                if token.startswith("##"):
                    i += 1
                    continue
                if label == "O":
                    i += 1
                    continue

                parts = label.split("-", 1)
                tag = parts[-1]
                prefix = parts[0] if len(parts) == 2 else "S"
                if prefix == "S":
                    start_off, end_off = offsets[i]
                    entities.append({
                        "text": chunk[start_off:end_off],
                        "type": tag,
                        "confidence": float(probs[i, label_ids[i]].item()),
                        "positions": [[start_off, end_off]],
                    })
                    i += 1
                    continue
                if prefix == "B":
                    start_off = offsets[i][0]
                    toks: list[str] = [token]
                    confs: list[float] = [float(probs[i, label_ids[i]].item())]
                    j = i + 1
                    while j < seq_len - 1:
                        nlabel = id2label.get(label_ids[j], "O")
                        ntoken = tokenizer.convert_ids_to_tokens(token_ids[j])
                        if nlabel.startswith("I-") and nlabel.split("-", 1)[-1] == tag:
                            toks.append(ntoken)
                            confs.append(float(probs[j, label_ids[j]].item()))
                            j += 1
                        elif nlabel.startswith("E-") and nlabel.split("-", 1)[-1] == tag:
                            toks.append(ntoken)
                            confs.append(float(probs[j, label_ids[j]].item()))
                            end_off = offsets[j][1]
                            _append_entity(
                                entities,
                                text=_join_tokens(toks),
                                type=tag,
                                confidence=sum(confs) / len(confs),
                                start=start_off,
                                end=end_off,
                            )
                            i = j + 1
                            break
                        elif nlabel == "O":
                            # B with no E: treat as single token span.
                            end_off = offsets[i][1]
                            _append_entity(
                                entities,
                                text=token,
                                type=tag,
                                confidence=confs[0],
                                start=start_off,
                                end=end_off,
                            )
                            i = j
                            break
                        else:
                            end_off = offsets[i][1]
                            _append_entity(
                                entities,
                                text=_join_tokens(toks),
                                type=tag,
                                confidence=sum(confs) / len(confs),
                                start=start_off,
                                end=end_off,
                            )
                            i = j
                            break
                    else:
                        # Ran to sequence end without E.
                        end_off = offsets[j - 1][1] if j > i else offsets[i][1]
                        _append_entity(
                            entities,
                            text=_join_tokens(toks),
                            type=tag,
                            confidence=sum(confs) / len(confs),
                            start=start_off,
                            end=end_off,
                        )
                        i = j
                    continue
                # I-/E- without B (shouldn't happen with valid BIOES): skip.
                i += 1

        return entities


# ----------------------------------------------------------------------
# Module-level helpers
# ----------------------------------------------------------------------


def _dedupe_entities(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge same (text, type) entities, keeping the highest confidence and
    collecting all positions. Sorted by confidence desc."""
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for e in entities:
        key = (e["text"], e["type"])
        if key in merged:
            m = merged[key]
            m["positions"].extend(e["positions"])
            m["confidence"] = max(m["confidence"], e["confidence"])
        else:
            merged[key] = {
                "text": e["text"],
                "type": e["type"],
                "confidence": e["confidence"],
                "positions": list(e["positions"]),
            }
    return sorted(merged.values(), key=lambda e: e["confidence"], reverse=True)


def _append_entity(
    entities: list[dict[str, Any]],
    text: str,
    type: str,
    confidence: float,
    start: int,
    end: int,
) -> None:
    text = text.strip()
    if not text:
        return
    entities.append({
        "text": text,
        "type": type,
        "confidence": confidence,
        "positions": [[start, end]],
    })


def _join_tokens(tokens: list[str]) -> str:
    out = ""
    for t in tokens:
        if t.startswith("##"):
            out += t[2:]
        else:
            out += t
    return out


def _chunk_text(text: str, max_chars: int = 400) -> list[str]:
    """Split long text into chunks by sentence, each ≤ max_chars.

    Chinese text has no spaces; sentence boundaries (。！？；\n) are used.
    """
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    cur = ""
    for sent in re.split(r"(?<=[。！？；\n])", text):
        if not sent:
            continue
        if len(cur) + len(sent) <= max_chars:
            cur += sent
        else:
            if cur:
                chunks.append(cur)
            # A single sentence longer than max_chars gets hard-split.
            while len(sent) > max_chars:
                chunks.append(sent[:max_chars])
                sent = sent[max_chars:]
            cur = sent
    if cur:
        chunks.append(cur)
    return chunks


def _viterbi_decode(
    emissions: Any,
    start_w: Any,
    trans_w: Any,
    end_w: Any,
) -> list[int]:
    """Viterbi decode over emission scores with CRF transition matrices.

    ``emissions`` is a [seq_len, num_labels] tensor of raw logits.
    ``start_w``/``end_w``/``trans_w`` are the CRF matrices (optional —
    missing start/end default to zeros). Returns the best label path as
    a list of label ids. Falls back to argmax when ``trans_w`` is None.

    Pure-CPU implementation: a 512-token sequence over 13 labels is a
    handful of milliseconds, so there is no need to vectorise.
    """
    import torch

    if trans_w is None:
        return emissions.argmax(dim=-1).tolist()

    e = emissions.detach().cpu()
    num_labels = e.shape[1]
    seq_len = e.shape[0]
    start = start_w.detach().cpu() if start_w is not None else torch.zeros(num_labels)
    end = end_w.detach().cpu() if end_w is not None else torch.zeros(num_labels)
    trans = trans_w.detach().cpu()

    v = start + e[0]
    back: list[list[int]] = []
    for t in range(1, seq_len):
        scores = v[:, None] + trans + e[t][None, :]  # [L, L]
        best = scores.max(dim=0)
        back.append(best.indices.tolist())
        v = best.values
    v = v + end
    last = int(v.argmax().item())
    path = [last]
    for b in reversed(back):
        last = b[last]
        path.append(last)
    path.reverse()
    return path
