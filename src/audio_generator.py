"""Generates narration audio from the script using Gemini's TTS output.
Writes a 16-bit PCM WAV file to disk.
"""
import wave
from pathlib import Path

from google import genai
from google.genai import types

from src.config import Secrets


def _save_wave(path: str, pcm_data: bytes, channels=1, rate=24000, sample_width=2):
    with wave.open(path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm_data)


def generate_audio(script_text: str, cfg: dict) -> str:
    """Returns the path to the generated narration.wav file."""
    client = genai.Client(api_key=Secrets.GEMINI_API_KEY)

    style_instruction = (
        f"Read the following in a {cfg['audio']['speaking_rate_hint']} tone, "
        f"suitable for a fast-paced short-form video narration:\n\n{script_text}"
    )

    response = client.models.generate_content(
        model=cfg["audio"]["gemini_tts_model"],
        contents=style_instruction,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=cfg["audio"]["voice_name"]
                    )
                )
            ),
        ),
    )

    audio_bytes = response.candidates[0].content.parts[0].inline_data.data

    out_path = str(Path(cfg["paths"]["work_dir"]) / "narration.wav")
    _save_wave(out_path, audio_bytes)
    return out_path


if __name__ == "__main__":
    from src.config import load_config
    cfg = load_config()
    path = generate_audio("This is a quick test of the narration voice.", cfg)
    print(f"Saved: {path}")
