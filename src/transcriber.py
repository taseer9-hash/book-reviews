"""Extracts word-level timestamps from the generated narration audio.

We don't trust text-based duration estimates for word timing — TTS speed varies
by word/sentence. Instead we run the actual audio through faster-whisper, which
gives per-word start/end times we can hand straight to the subtitle renderer.
"""
from faster_whisper import WhisperModel

_MODEL = None


def _get_model():
    global _MODEL
    if _MODEL is None:
        # "small" is a good accuracy/speed tradeoff on GitHub Actions' CPU runners.
        # Use "base" for faster/cheaper runs, "medium" for better accuracy.
        _MODEL = WhisperModel("small", device="cpu", compute_type="int8")
    return _MODEL


def get_word_timestamps(audio_path: str, language: str = "en") -> list[dict]:
    """Returns a list of {"word": str, "start": float, "end": float}."""
    model = _get_model()
    segments, _info = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=True,
        vad_filter=True,
    )

    words = []
    for segment in segments:
        for w in segment.words:
            words.append({
                "word": w.word.strip(),
                "start": w.start,
                "end": w.end,
            })
    return words


if __name__ == "__main__":
    import sys
    import json
    result = get_word_timestamps(sys.argv[1])
    print(json.dumps(result, indent=2))
