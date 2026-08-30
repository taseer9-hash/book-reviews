"""Fetches stock b-roll clips from Pexels matching the script's visual keywords."""
from pathlib import Path

import requests

from src.config import Secrets

PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"


def _pick_best_file(video: dict, cfg: dict) -> str | None:
    """Choose the video file variant closest to our target resolution/orientation."""
    target_w, target_h = cfg["video"]["width"], cfg["video"]["height"]
    want_portrait = target_h > target_w

    candidates = video.get("video_files", [])
    scored = []
    for f in candidates:
        w, h = f.get("width") or 0, f.get("height") or 0
        if w == 0 or h == 0:
            continue
        is_portrait = h > w
        if is_portrait != want_portrait:
            continue
        # prefer resolutions close to (but not wildly above) our target
        score = abs(w - target_w) + abs(h - target_h)
        scored.append((score, f["link"]))

    if not scored:
        # fall back to any orientation if nothing matches (better than failing)
        for f in candidates:
            if f.get("link"):
                return f["link"]
        return None

    scored.sort(key=lambda x: x[0])
    return scored[0][1]


def search_clip(query: str, cfg: dict, min_duration: float) -> dict | None:
    headers = {"Authorization": Secrets.PEXELS_API_KEY}
    params = {"query": query, "per_page": 5, "orientation":
              "portrait" if cfg["video"]["orientation"] == "vertical" else "landscape"}

    resp = requests.get(PEXELS_SEARCH_URL, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    videos = resp.json().get("videos", [])

    for video in videos:
        if video.get("duration", 0) >= min_duration:
            file_url = _pick_best_file(video, cfg)
            if file_url:
                return {"url": file_url, "duration": video["duration"], "query": query}

    return None


def download_clips(keywords: list[str], cfg: dict) -> list[str]:
    """Searches each keyword on Pexels, downloads the best match, returns local paths."""
    work_dir = Path(cfg["paths"]["work_dir"])
    min_dur = cfg["video"]["clip_min_duration"]
    paths = []

    for i, keyword in enumerate(keywords):
        result = search_clip(keyword, cfg, min_dur)
        if result is None:
            print(f"[pexels] no match for '{keyword}', trying a broader fallback query")
            result = search_clip(keyword.split()[0], cfg, min_dur)
        if result is None:
            print(f"[pexels] skipping '{keyword}' — no usable clip found")
            continue

        out_path = work_dir / f"clip_{i:02d}.mp4"
        with requests.get(result["url"], stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    f.write(chunk)

        paths.append(str(out_path))

    if not paths:
        raise RuntimeError("No stock clips could be downloaded for any keyword.")

    return paths


if __name__ == "__main__":
    from src.config import load_config
    cfg = load_config()
    clips = download_clips(["ocean waves aerial", "city timelapse night"], cfg)
    print(clips)
