"""Stock image acquisition from Pexels API (free)."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    RetryPolicy,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)


class PexelsImage(BaseTool):
    name = "pexels_image"
    version = "0.1.0"
    tier = ToolTier.SOURCE
    capability = "image_generation"
    provider = "pexels"
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.API

    dependencies = []
    install_instructions = (
        "Set PEXELS_API_KEY to your Pexels API key.\n"
        "  Get one free at https://www.pexels.com/api/"
    )
    agent_skills = []

    capabilities = ["search_image", "download_image", "stock_image"]
    supports = {
        "orientation_filter": True,
        "size_filter": True,
        "color_filter": True,
        "locale": True,
        "free_commercial_use": True,
    }
    best_for = [
        "real-world photography (cities, nature, people, objects)",
        "establishing shots and B-roll stills",
        "free stock images — no cost, no attribution required",
    ]
    not_good_for = [
        "custom/specific compositions",
        "abstract or stylized graphics",
        "offline use",
    ]

    input_schema = {
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {"type": "string", "description": "Search term"},
            "orientation": {
                "type": "string",
                "enum": ["landscape", "portrait", "square"],
            },
            "size": {
                "type": "string",
                "enum": ["large", "medium", "small"],
                "description": "large=24MP+, medium=12MP+, small=4MP+",
            },
            "color": {
                "type": "string",
                "description": "Hex without # (e.g. FF0000) or color name (red, blue, etc.)",
            },
            "per_page": {"type": "integer", "default": 5, "minimum": 1, "maximum": 80},
            "page": {"type": "integer", "default": 1},
            "download_size": {
                "type": "string",
                "enum": ["original", "large2x", "large", "medium"],
                "default": "large2x",
            },
            "output_path": {"type": "string"},
            "output_dir": {
                "type": "string",
                "description": "Directory to download N candidate images into. Requires `count`. When set, multiple photos are downloaded and the candidate list is returned; `output_path` is ignored.",
            },
            "count": {
                "type": "integer",
                "default": 1,
                "minimum": 1,
                "maximum": 20,
                "description": "Number of photos to download (first N results). Only meaningful with `output_dir`; default 1 preserves legacy single-download behaviour.",
            },
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=256, vram_mb=0, disk_mb=50, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["rate_limit", "timeout"])
    idempotency_key_fields = ["query", "orientation", "size", "color", "page"]
    side_effects = ["writes image file to output_path", "calls Pexels API"]
    user_visible_verification = ["Check that downloaded image matches the intended scene"]

    def get_status(self) -> ToolStatus:
        if os.environ.get("PEXELS_API_KEY"):
            return ToolStatus.AVAILABLE
        return ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0  # Pexels is free

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        api_key = os.environ.get("PEXELS_API_KEY")
        if not api_key:
            return ToolResult(
                success=False,
                error="PEXELS_API_KEY not set. " + self.install_instructions,
            )

        import requests

        start = time.time()
        query = inputs["query"]

        params: dict[str, Any] = {
            "query": query,
            "per_page": inputs.get("per_page", 5),
            "page": inputs.get("page", 1),
        }
        if inputs.get("orientation"):
            params["orientation"] = inputs["orientation"]
        if inputs.get("size"):
            params["size"] = inputs["size"]
        if inputs.get("color"):
            params["color"] = inputs["color"]

        try:
            search_response = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": api_key},
                params=params,
                timeout=30,
            )
            search_response.raise_for_status()
            data = search_response.json()

            photos = data.get("photos", [])
            if not photos:
                return ToolResult(
                    success=False,
                    error=f"No images found for query: {query}",
                    data={"total_results": data.get("total_results", 0)},
                )

            download_size = inputs.get("download_size", "large2x")
            output_dir = inputs.get("output_dir")
            count = inputs.get("count", 1)

            candidates = []
            downloaded = []
            selected = photos[:count]

            if output_dir and count > 1:
                # multi-download: fetch `count` photos into output_dir (photo_id-named files)
                for idx, photo in enumerate(selected):
                    image_url = photo["src"].get(download_size, photo["src"]["large2x"])
                    image_response = requests.get(image_url, timeout=60)
                    image_response.raise_for_status()
                    out_path = Path(output_dir) / f"{photo['id']}.jpg"
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_bytes(image_response.content)
                    downloaded.append(str(out_path))
                    candidates.append(_to_candidate(query, photo, str(out_path)))
            else:
                # legacy single-download path
                photo = selected[0]
                image_url = photo["src"].get(download_size, photo["src"]["large2x"])
                image_response = requests.get(image_url, timeout=60)
                image_response.raise_for_status()
                output_path = Path(inputs.get("output_path", f"pexels_{photo['id']}.jpg"))
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(image_response.content)
                candidates.append(_to_candidate(query, photo, str(output_path)))

        except Exception as e:
            return ToolResult(success=False, error=f"Pexels image search failed: {e}")

        primary = candidates[0]
        return ToolResult(
            success=True,
            data={
                "provider": "pexels",
                "photo_id": primary["photo_id"],
                "photographer": primary.get("photographer", "Unknown"),
                "photographer_url": primary.get("photographer_url", ""),
                "alt": primary.get("alt", ""),
                "width": primary.get("width"),
                "height": primary.get("height"),
                "query": query,
                "output": str(primary.get("output", "")),
                "outputs": downloaded if downloaded else [str(primary.get("output", ""))],
                "total_results": data.get("total_results", 0),
                "results_returned": len(photos),
                "candidates": candidates,
                "license": "Pexels License (free, no attribution required)",
                "pexels_url": primary.get("url", ""),
            },
            artifacts=downloaded if downloaded else [str(primary.get("output", ""))],
            cost_usd=0.0,
            duration_seconds=round(time.time() - start, 2),
        )


def _to_candidate(query: str, photo: dict, output_path: str = "") -> dict[str, Any]:
    """Normalize a Pexels photo into a candidate descriptor for agent-side curation."""
    return {
        "query": query,
        "photo_id": photo["id"],
        "photographer": photo.get("photographer", "Unknown"),
        "photographer_url": photo.get("photographer_url", ""),
        "alt": photo.get("alt", ""),
        "width": photo.get("width"),
        "height": photo.get("height"),
        "url": photo.get("url", ""),
        "src": photo["src"].get("large2x", photo["src"].get("original", "")),
        "output": output_path,
    }
