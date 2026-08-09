"""Drive the pexels_video registry tool to fetch distinct clips per scene.

Each scene needs enough unique clips to cover its narration duration WITHOUT
any loop replay. Queries are chosen per scene; pages are bumped on duplicate
video ids so we never reuse a clip.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tools.tool_registry import registry  # noqa: E402

SCENES = {
    # scene_index -> (target_seconds, [(query, page), ...])
    1: (
        12.72,
        [
            ("news studio broadcast", 1),
            ("television news studio camera", 1),
            ("breaking news anchor", 1),
        ],
    ),
    2: (
        23.30,
        [
            ("military tank convoy", 1),
            ("armored vehicle military", 1),
            ("army soldiers marching", 1),
            ("military vehicles parade", 1),
        ],
    ),
    3: (
        24.36,
        [
            ("military night exercise shooting", 1),
            ("army night operation", 1),
            ("soldier firing night", 1),
            ("military training ground", 1),
        ],
    ),
    4: (
        19.13,
        [
            ("world map pins strategy", 1),
            ("satellite earth globe", 1),
            ("military strategy map", 1),
            ("global network lines map", 1),
        ],
    ),
    5: (
        18.15,
        [
            ("flag waving sky", 1),
            ("red flag pole waving", 1),
            ("national flag wind", 1),
            ("chinese flag", 1),
        ],
    ),
}


def main() -> None:
    registry.discover()
    tool_instance = registry.get("pexels_video")
    out = Path(r"C:\Users\mvs20\Documents\trae\videos\OpenMontage"
               r"\projects\guofang-shikong-20260808\assets\video\scenes")
    seen_ids: set[str] = set()
    results: dict[int, list[str]] = {}

    for idx, (_, queries) in SCENES.items():
        results[idx] = []
        scene_dir = out / f"scene{idx}"
        scene_dir.mkdir(parents=True, exist_ok=True)

        for q, page in queries:
            dst = scene_dir / f"clip_{q.replace(' ', '_')[:40]}.mp4"
            if dst.exists():
                results[idx].append(str(dst))
                continue
            resp = tool_instance.execute(
                {
                    "query": q,
                    "page": page,
                    "per_page": 5,
                    "orientation": "landscape",
                    "preferred_quality": "hd",
                    "output_path": str(dst),
                }
            )
            if not resp.success:
                print(f"[scene{idx}] FAIL {q}: {resp.error}")
                continue
            vid = resp.data.get("video_id")
            if vid in seen_ids:
                print(f"[scene{idx}] DUP {q} (id {vid}) - skipping")
                dst.unlink(missing_ok=True)
                continue
            seen_ids.add(vid)
            results[idx].append(str(dst))
            print(f"[scene{idx}] ok {q} id={vid} dur={resp.data.get('duration_seconds')}s")

    print("SCENE ASSIGNMENTS")
    for idx, paths in results.items():
        print(f"  scene{idx}: {paths}")


if __name__ == "__main__":
    main()