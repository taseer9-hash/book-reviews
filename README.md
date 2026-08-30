# YouTube Automation Pipeline

Generates a short-form video (script + narration via Gemini, b-roll via Pexels,
fast word-by-word subtitles) and uploads it to YouTube. Runs on GitHub Actions
3 times a day.

## Pipeline

```
script_generator.py  -> Gemini writes script + title + description + visual keywords
audio_generator.py   -> Gemini TTS renders narration.wav
transcriber.py        -> faster-whisper gets word-level timestamps from the actual audio
pexels_fetcher.py    -> downloads b-roll clips matching the visual keywords
subtitles.py          -> builds an .ass file: one word at a time, timed to the audio
video_assembler.py   -> ffmpeg stitches clips + burns subtitles + mixes audio
youtube_uploader.py  -> uploads the final mp4 via the YouTube Data API
main.py               -> runs all of the above in order
```

## One-time setup

1. **Gemini API key** — from [Google AI Studio](https://aistudio.google.com/apikey).
2. **Pexels API key** — free, from the [Pexels API](https://www.pexels.com/api/).
3. **YouTube OAuth**:
   - Create an OAuth Client ID (type: Desktop app) in Google Cloud Console, with
     the YouTube Data API v3 enabled.
   - Run locally: `YOUTUBE_CLIENT_ID=... YOUTUBE_CLIENT_SECRET=... python get_refresh_token.py`
   - This opens a browser once for consent, then prints a refresh token.
4. Add all five values as **GitHub repo Secrets** (Settings → Secrets and variables → Actions):
   `GEMINI_API_KEY`, `PEXELS_API_KEY`, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`
5. Push this repo to GitHub. The workflow at `.github/workflows/pipeline.yml`
   is already scheduled — no further action needed. You can also trigger a run
   manually from the Actions tab (`workflow_dispatch`).

For local testing, copy `.env.example` to `.env` and fill in the same values,
then run `python main.py` directly.

## Customizing the subtitles

Everything is in `config.yaml` under `subtitles:` — you shouldn't need to touch
`src/subtitles.py` for normal tweaks:

| Setting | What it does |
|---|---|
| `max_words_per_group` | `1` = one word at a time (default). `2`-`3` = short phrases, with the "active" word highlighted. |
| `font_name` | Must be installed in the render environment. Default `Roboto Black`; the workflow installs `fonts-roboto` via apt. For other fonts, add an `apt-get install` step or vendor a `.ttf` and point `font_name` at it. |
| `font_size` | In ASS pt units, relative to the video's resolution (`video.width`/`video.height`). |
| `primary_color` / `outline_color` | ASS hex format `&HAABBGGRR` (alpha, blue, green, red — note the reversed order vs. normal hex). `&H00FFFFFF` = opaque white, `&H00000000` = opaque black. |
| `outline_width` | Stroke thickness in px. Set higher (e.g. `10-12`) for an even bolder look. |
| `position` | `top`, `middle`, or `bottom`. |
| `pop_scale_start` / `pop_duration_ms` | Each word animates in from this % size down to 100% over this many ms — the "pop" effect. Set `pop_duration_ms: 0` to disable. |
| `highlight_enabled` / `highlight_color` | Only used when `max_words_per_group > 1` — colors the currently-spoken word differently from the rest of the phrase. |
| `min_word_duration` / `max_word_duration` | Clamps per-word screen time so very short/long words don't look glitchy or dragging. |

Because subtitle timing comes from actually transcribing the generated audio
(not estimating from text), captions stay in sync even if the TTS speeds up or
slows down mid-sentence.

To go beyond styling — e.g. a different animation curve, per-word color
cycling, or emoji injection — edit `_word_text()` in `src/subtitles.py`; it's
the single function that turns one word into an ASS-tagged string.

## Customizing content / video

Also in `config.yaml`:
- `content.niche` / `content.fixed_topic` — what the videos are about.
- `content.script_word_count` — roughly controls final video length.
- `video.orientation` — `vertical` (1080x1920, Shorts) or `horizontal` (1920x1080).
- `video.background_music` — path to an mp3 to mix under the narration.
- `youtube.privacy_status` — set to `private` while testing so nothing goes live by accident.

## Notes / things to verify before relying on this in production

- **Gemini TTS model name** (`audio.gemini_tts_model`) and available voice names
  change as Google updates the API — double check current values in the Gemini
  API docs before your first real run.
- **YouTube upload quota**: the default YouTube Data API quota is 10,000 units/day
  and an upload costs ~1,600 units, so 3 uploads/day fits comfortably, but check
  your quota if you add more runs.
- **Copyright**: Pexels clips are free to use per their license, but always spot
  check generated scripts before going fully unattended — nothing here reviews
  content for accuracy or platform policy compliance before upload. Consider
  starting with `youtube.privacy_status: "private"` or `"unlisted"` and a manual
  review step until you trust the output.
- `faster-whisper` downloads its model on first run — the first CI run will be
  slower than subsequent ones.
