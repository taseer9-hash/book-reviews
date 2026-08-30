"""Builds an .ass subtitle file that displays words one-at-a-time (or in small
groups), styled per config.yaml. This is the file to look at / extend if you
want different caption styles — it's deliberately self-contained.

All visual knobs (font, size, colors, outline, position, pop animation,
highlight color) come from cfg["subtitles"]. Nothing here is hardcoded.
"""
from pathlib import Path

_ALIGNMENT = {"bottom": 2, "middle": 5, "top": 8}


def _group_words(words: list[dict], group_size: int) -> list[dict]:
    """Merges consecutive word-timestamp dicts into groups of `group_size`,
    keeping each word's own start/end so we can still highlight per-word."""
    groups = []
    for i in range(0, len(words), group_size):
        chunk = words[i:i + group_size]
        groups.append({
            "words": chunk,
            "start": chunk[0]["start"],
            "end": chunk[-1]["end"],
        })
    return groups


def _clamp_duration(start: float, end: float, sub_cfg: dict) -> tuple[float, float]:
    dur = end - start
    min_d, max_d = sub_cfg["min_word_duration"], sub_cfg["max_word_duration"]
    if dur < min_d:
        end = start + min_d
    elif dur > max_d:
        end = start + max_d
    return start, end


def _fmt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


def _build_header(cfg: dict) -> str:
    s = cfg["subtitles"]
    v = cfg["video"]
    align = _ALIGNMENT.get(s["position"], 2)

    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {v['width']}
PlayResY: {v['height']}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Word,{s['font_name']},{s['font_size']},{s['primary_color']},{s['primary_color']},{s['outline_color']},&H00000000,{-1 if s['bold'] else 0},{-1 if s['italic'] else 0},0,0,100,100,0,0,1,{s['outline_width']},{s['shadow_depth']},{align},{s['horizontal_margin']},{s['horizontal_margin']},{s['vertical_margin']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _word_text(word: str, sub_cfg: dict, is_group_display: bool, highlight: bool) -> str:
    """Builds the {\\tags}Text portion for a single dialogue line."""
    tags = ""
    if sub_cfg["pop_scale_start"] and sub_cfg["pop_duration_ms"] > 0:
        start_scale = sub_cfg["pop_scale_start"]
        dur = sub_cfg["pop_duration_ms"]
        tags += f"\\fscx{start_scale}\\fscy{start_scale}\\t(0,{dur},\\fscx100\\fscy100)"

    if highlight and sub_cfg["highlight_enabled"]:
        tags += f"\\c{sub_cfg['highlight_color']}"

    return f"{{{tags}}}{word}" if tags else word


def build_ass(words: list[dict], cfg: dict, out_path: str) -> str:
    """Writes the .ass file and returns its path.

    words: list of {"word": str, "start": float, "end": float} from transcriber.py
    """
    sub_cfg = cfg["subtitles"]
    group_size = max(1, sub_cfg["max_words_per_group"])
    groups = _group_words(words, group_size)

    lines = [_build_header(cfg)]

    for group in groups:
        if group_size == 1:
            # single_word mode: one dialogue event per word, simplest + cleanest
            w = group["words"][0]
            start, end = _clamp_duration(w["start"], w["end"], sub_cfg)
            text = _word_text(w["word"], sub_cfg, is_group_display=False, highlight=False)
            lines.append(
                f"Dialogue: 0,{_fmt_time(start)},{_fmt_time(end)},Word,,0,0,0,,{text}"
            )
        else:
            # n_word mode: show the whole group, but emit one Dialogue event per
            # highlighted-word window so the "current" word can pop/highlight
            # while the rest of the group stays visible and static.
            full_words = [w["word"] for w in group["words"]]
            for idx, w in enumerate(group["words"]):
                start, end = _clamp_duration(w["start"], w["end"], sub_cfg)
                rendered = []
                for j, token in enumerate(full_words):
                    rendered.append(
                        _word_text(token, sub_cfg, is_group_display=True, highlight=(j == idx))
                    )
                text = " ".join(rendered)
                lines.append(
                    f"Dialogue: 0,{_fmt_time(start)},{_fmt_time(end)},Word,,0,0,0,,{text}"
                )

    Path(out_path).write_text("\n".join(lines), encoding="utf-8")
    return out_path


if __name__ == "__main__":
    # quick manual smoke test
    from src.config import load_config
    fake_words = [
        {"word": "This", "start": 0.0, "end": 0.3},
        {"word": "is", "start": 0.3, "end": 0.45},
        {"word": "a", "start": 0.45, "end": 0.55},
        {"word": "test", "start": 0.55, "end": 0.9},
    ]
    cfg = load_config()
    path = build_ass(fake_words, cfg, "test_subs.ass")
    print(f"Wrote {path}")
