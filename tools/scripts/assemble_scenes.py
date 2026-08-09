"""Assemble Plan A scenes from distinct Pexels clips (NO loop/repeat).

Each scene pulls time-slices from DIFFERENT clips so the same footage never
plays twice. Outputs one 1920x1080/30fps silent clip per scene, then concatenates
all scenes into the silent master planA_visuals.mp4.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

BASE = Path(r"C:\Users\mvs20\Documents\trae\videos\OpenMontage")
PROJ = BASE / r"projects\guofang-shikong-20260808"
VID = PROJ / "assets" / "video"

# scene -> [(file, in_sec, dur_sec), ...]  summed == target
SCENES = {
    1: [
        ("scenes/scene1/clip_news_studio_broadcast.mp4", 0.0, 12.78),
    ],
    2: [
        ("scenes/scene2/clip_armored_vehicle_military.mp4", 0.0, 3.3267),
        ("scenes/scene2/clip_hd_armored_transport_vehicle_military_r.mp4", 0.0, 7.04),
        ("scenes/scene2/clip_hd_tank_army_tracked_vehicles.mp4", 0.0, 7.04),
        ("scenes/scene2/clip_hd_military_convoy_trucks_driving.mp4", 0.0, 5.82),
    ],
    3: [
        ("scenes/scene3/clip_army_night_operation.mp4", 0.0, 20.375),
        ("scenes/scene3/clip_military_night_exercise_shooting.mp4", 0.3, 3.985),
    ],
    4: [
        ("scenes/scene4/clip_global_network_lines_map.mp4", 0.0, 10.0),
        ("scenes/scene4/clip_satellite_earth_globe.mp4", 0.0, 9.09),
    ],
    5: [
        ("scenes/scene5/clip_national_flag_wind.mp4", 4.0, 18.15),
    ],
}

VF = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
      "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p")


def run(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAILED: {' '.join(str(c) for c in cmd)}")
        print(r.stderr[-1500:])
        raise SystemExit(1)


def slice_clip(src: Path, offset: float, dur: float, dst: Path) -> None:
    run(
        ["ffmpeg", "-y", "-ss", f"{offset:.3f}", "-i", str(src),
         "-t", f"{dur:.4f}",
         "-vf", VF, "-an", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "22", "-pix_fmt", "yuv420p", str(dst)]
    )


def concat_parts(slices: list[tuple[str, float, float]], dst: Path) -> None:
    work = dst.parent
    pieces = []
    for i, (rel, off, dur) in enumerate(slices):
        p = work / f"{dst.stem}_p{i}.mp4"
        slice_clip(VID / rel, off, dur, p)
        pieces.append(p)
    lst = work / f"{dst.stem}.txt"
    lst.write_text(
        "".join(f"file '{p.as_posix()}'\n" for p in pieces), encoding="utf-8"
    )
    run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c", "copy", str(dst)]
    )


def main():
    work = VID / "prep2"
    work.mkdir(parents=True, exist_ok=True)

    for scene, slices in SCENES.items():
        flat = work / f"scene{scene}_flat.mp4"
        concat_parts(slices, flat)
        print(f"scene{scene} -> {flat}")

    # Concatenate the five scene flats into the silent master.
    master = VID / "planA_visuals.mp4"
    lst = work / "all.txt"
    lst.write_text(
        "".join(f"file '{ (work / f'scene{s}_flat.mp4').as_posix() }'\n"
                for s in range(1, 6)),
        encoding="utf-8",
    )
    run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c", "copy", str(master)]
    )
    print(f"master -> {master}")


if __name__ == "__main__":
    main()