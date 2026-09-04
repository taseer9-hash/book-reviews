"""Entry point: runs the full pipeline end to end.

    script -> audio -> word timestamps -> stock clips -> subtitles -> assemble -> upload
"""
import sys
import traceback
from pathlib import Path

from src.config import Secrets, load_config
from src.script_generator import generate_script, save_used_book
from src.audio_generator import generate_audio
from src.transcriber import get_word_timestamps
from src.pexels_fetcher import download_clips
from src.subtitles import build_ass
from src.video_assembler import assemble_video, get_duration
from src.youtube_uploader import upload_video


def run():
    Secrets.validate()
    cfg = load_config()

    print("== 1/6 Generating script ==")
    script_data = generate_script(cfg)
    print(f"Topic: {script_data['topic']}")
    print(f"Title: {script_data['title']}")

    # Record this book immediately so even if a later step fails, we don't
    # risk regenerating the exact same book on the very next run.
    save_used_book(script_data.get("book_title"), script_data.get("book_author"))

    print("== 2/6 Generating narration audio ==")
    narration_path = generate_audio(script_data["script"], cfg)
    narration_duration = get_duration(narration_path)

    print("== 3/6 Transcribing for word-level timestamps ==")
    words = get_word_timestamps(narration_path, language=cfg["content"]["language"])
    if not words:
        raise RuntimeError("Transcription returned no words — aborting before upload.")

    print("== 4/6 Fetching stock b-roll from Pexels ==")
    clip_paths = download_clips(script_data["visual_keywords"], cfg)

    print("== 5/6 Building subtitles + assembling video ==")
    ass_path = str(Path(cfg["paths"]["work_dir"]) / "subs.ass")
    build_ass(
        words, cfg, ass_path,
        book_title=script_data.get("book_title"),
        book_author=script_data.get("book_author"),
        title_card_duration=narration_duration,
    )
    final_video_path = assemble_video(clip_paths, narration_path, ass_path, cfg)
    print(f"Final video: {final_video_path}")

    print("== 6/6 Uploading to YouTube ==")
    video_id = upload_video(
        final_video_path, script_data["title"], script_data["description"], cfg
    )
    print(f"Done. https://youtube.com/watch?v={video_id}")


if __name__ == "__main__":
    try:
        run()
    except Exception:
        # Print full traceback so it's visible in the GitHub Actions log,
        # and exit non-zero so the workflow run is marked failed.
        traceback.print_exc()
        sys.exit(1)
