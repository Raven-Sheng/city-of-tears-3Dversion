"""Pure Stage 6 frame-planning, identity, and PNG validation helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

FRAME_RE = re.compile(r"^f(\d+)\.png$")
IDENTITY_FILE = "sequence_identity.json"


def expected_take_frames(config: dict[str, Any]) -> dict[str, list[int]]:
    return {
        take["id"]: list(
            range(
                int(take["frame_start"]) - int(take["handle_in"]),
                int(take["frame_end"]) + int(take["handle_out"]) + 1,
            )
        )
        for take in config["takes"]
    }


def light_regions_for_take(config: dict[str, Any], take_id: str, always_regions: Iterable[str]) -> list[str]:
    """Return the stable region set whose lights stay enabled for one take.

    Geometry is never culled.  The set is intentionally the union of every beat
    in the take so that lighting cannot jump at an internal beat boundary.
    """
    take = next((item for item in config["takes"] if item["id"] == take_id), None)
    if take is None:
        raise ValueError(f"unknown take: {take_id}")
    regions = {str(region) for region in always_regions}
    regions.update(str(beat["region"]) for beat in take.get("beats", []))
    return sorted(regions)


def build_compose_map(config: dict[str, Any]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for take in config["takes"]:
        for frame in range(int(take["frame_start"]), int(take["frame_end"]) + 1):
            if frame in result:
                raise ValueError(f"owned frame overlap at {frame}")
            result[frame] = {"owner": take["id"]}

    expected = list(range(1, 4273))
    if sorted(result) != expected:
        raise ValueError("owned timeline must cover frames 1-4272 exactly")

    for transition in config["transitions"]:
        start, end = (int(v) for v in transition["frames"])
        length = end - start + 1
        for frame in range(start, end + 1):
            x = (frame - start + 0.5) / length
            weight = x * x * (3.0 - 2.0 * x)
            result[frame] = {
                "owner": result[frame]["owner"],
                "mix": [transition["from_take"], transition["to_take"]],
                "weight": weight,
            }
    return result


def bind_identity(folder: Path, identity: dict[str, Any], resume: bool) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / IDENTITY_FILE
    existing_frames = list(folder.glob("f*.png"))
    if path.exists():
        current = json.loads(path.read_text(encoding="utf-8"))
        if current != identity:
            raise ValueError("sequence identity changed; use a new output directory")
        return
    if resume and existing_frames:
        raise ValueError("sequence has frames but no verified identity")
    path.write_text(json.dumps(identity, ensure_ascii=False, indent=2), encoding="utf-8")


def validate_sequence(folder: Path, expected_frames: Iterable[int], resolution: tuple[int, int]) -> dict[str, Any]:
    from PIL import Image

    expected = set(int(frame) for frame in expected_frames)
    actual: dict[int, Path] = {}
    names: dict[int, list[str]] = {}
    unexpected_names = []
    for path in folder.glob("f*.png"):
        match = FRAME_RE.match(path.name)
        if match:
            frame = int(match.group(1))
            names.setdefault(frame, []).append(path.name)
            actual[frame] = path
        else:
            unexpected_names.append(path.name)
    duplicates = [{"frame": frame, "files": sorted(files)} for frame, files in sorted(names.items()) if len(files) > 1]

    missing = sorted(expected - actual.keys())
    extra = sorted(actual.keys() - expected)
    corrupt: list[int] = []
    wrong_size: list[dict[str, Any]] = []
    for frame in sorted(expected & actual.keys()):
        try:
            with Image.open(actual[frame]) as image:
                size = image.size
                image.load()
            if size != resolution:
                wrong_size.append({"frame": frame, "actual": list(size)})
        except Exception:
            corrupt.append(frame)

    return {
        "folder": str(folder),
        "expected_count": len(expected),
        "actual_count": len(actual),
        "missing": missing,
        "extra": extra,
        "corrupt": corrupt,
        "wrong_size": wrong_size,
        "duplicates": duplicates,
        "unexpected_names": sorted(unexpected_names),
        "pass": not (missing or extra or corrupt or wrong_size or duplicates or unexpected_names),
    }
