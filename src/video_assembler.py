"""Assembles the final video: trims/concats stock clips to cover the narration
length, scales+crops everything to the target resolution, burns in the .ass
subtitles, and mixes in the narration (+ optional background music).

Relies on the ffmpeg binary being available on PATH (installed via the
GitHub Actions workflow / apt).
"""
import itertools
import json
import subprocess
from pathlib import Path


def _run(cmd: list[str]):
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg command failed:\n{' '.join(cmd)}\n\n{result.stderr}")
    return result


def get_duration(path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", path,
    ]
    out = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return float(json.loads(out.stdout)["format"]["duration"])


def _prepare_clip(src: str, out_path: str, cfg: dict, take_seconds: float):
    """Scale+crop a clip to fill the target frame (center-crop) and trim to length."""
    w, h, fps = cfg["video"]["width"], cfg["video"]["height"], cfg["video"]["fps"]
    vf = (
        f"scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h},fps={fps},setsar=1"
    )
    cmd = [
        "ffmpeg", "-y", "-i", src, "-t", f"{take_seconds:.3f}",
        "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        out_path,
    ]
    _run(cmd)


def _build_broll_track(clip_paths: list[str], target_duration: float, cfg: dict, work_dir: Path) -> str:
    """Loops through clip_paths (repeating if needed) until target_duration is covered,
    trimming the final segment, then concatenates into one silent video track."""
    per_clip = max(cfg["video"]["clip_min_duration"], target_duration / max(len(clip_paths), 1))
    prepared = []
    remaining = target_duration

    for i, src in enumerate(itertools.cycle(clip_paths)):
        if remaining <= 0.05:
            break
        take = min(per_clip, remaining)
        out_path = work_dir / f"prepared_{i:02d}.mp4"
        _prepare_clip(src, str(out_path), cfg, take)
        prepared.append(str(out_path))
        remaining -= take
        if i > 200:  # safety valve against pathological loops
            break

    concat_list_path = work_dir / "concat_list.txt"
    with open(concat_list_path, "w") as f:
        for p in prepared:
            f.write(f"file '{p}'\n")

    broll_path = str(work_dir / "broll_track.mp4")
    _run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list_path),
        "-c", "copy", broll_path,
    ])
    return broll_path


def assemble_video(
    clip_paths: list[str],
    narration_path: str,
    ass_path: str,
    cfg: dict,
    out_filename: str = "final.mp4",
) -> str:
    work_dir = Path(cfg["paths"]["work_dir"])
    narration_duration = get_duration(narration_path)

    broll_path = _build_broll_track(clip_paths, narration_duration, cfg, work_dir)

    # ffmpeg needs subtitle paths escaped carefully, especially on Windows-style
    # paths; on Linux runners a straightforward path works, but colons still
    # need escaping for the filtergraph.
    ass_filter_path = ass_path.replace(":", r"\:")

    out_path = str(Path(cfg["paths"]["final_dir"]) / out_filename)

    inputs = ["-i", broll_path, "-i", narration_path]
    filter_complex = f"[0:v]ass='{ass_filter_path}'[vout]"
    map_args = ["-map", "[vout]", "-map", "1:a"]

    audio_filter = None
    bg_music = cfg["video"].get("background_music")
    if bg_music:
        inputs += ["-i", bg_music]
        vol = cfg["video"]["background_music_volume"]
        audio_filter = (
            f"[2:a]volume={vol},aloop=loop=-1:size=2e9[bg];"
            f"[1:a][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
        map_args = ["-map", "[vout]", "-map", "[aout]"]

    full_filter = filter_complex + (";" + audio_filter if audio_filter else "")

    cmd = [
        "ffmpeg", "-y", *inputs,
        "-filter_complex", full_filter,
        *map_args,
        "-c:v", "libx264", "-preset", "medium", "-crf", "19",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        out_path,
    ]
    _run(cmd)
    return out_path
