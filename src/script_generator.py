"""Generates the video script, title, description, and b-roll search keywords
using the Gemini API. Returns structured JSON so downstream steps don't have
to re-parse free text.
"""
import json
import random

from google import genai

from src.config import Secrets


TOPIC_POOL_PROMPT = """You are picking ONE specific, narrow topic for a {word_count}-word
short-form video script in the niche: "{niche}".
Return ONLY the topic as a short phrase, nothing else."""

SCRIPT_PROMPT = """Write a script for a fast-paced, engaging short-form YouTube video
(like a YouTube Short / TikTok) about: "{topic}"

Requirements:
- About {word_count} words, spoken narration only (no stage directions, no headers).
- Hook the viewer in the first sentence.
- Punchy, simple sentences. Conversational tone. {rate_hint}.
- End with a satisfying final line (not "subscribe" / no calls to action).

Also produce:
- A punchy YouTube title. {title_hint}
- A short YouTube description (2-3 sentences + relevant hashtags).
- A list of {keyword_count} short visual search phrases (2-4 words each) describing
  stock footage that would visually match different moments of the script, in order.
  These will be used to search a stock video library, so keep them concrete and visual
  (e.g. "ocean waves aerial", "scientist microscope lab") — not abstract concepts.

Return ONLY valid JSON, no markdown fences, in this exact shape:
{{
  "title": "...",
  "description": "...",
  "script": "...",
  "visual_keywords": ["...", "..."]
}}
"""


def _client() -> genai.Client:
    return genai.Client(api_key=Secrets.GEMINI_API_KEY)


def pick_topic(cfg: dict) -> str:
    if cfg["content"]["fixed_topic"]:
        return cfg["content"]["fixed_topic"]

    client = _client()
    prompt = TOPIC_POOL_PROMPT.format(
        word_count=cfg["content"]["script_word_count"],
        niche=cfg["content"]["niche"],
    )
    resp = client.models.generate_content(
        model=cfg["content"]["gemini_text_model"],
        contents=prompt,
    )
    return resp.text.strip().strip('"')


def generate_script(cfg: dict) -> dict:
    """Returns dict with keys: title, description, script, visual_keywords."""
    topic = pick_topic(cfg)
    client = _client()

    prompt = SCRIPT_PROMPT.format(
        topic=topic,
        word_count=cfg["content"]["script_word_count"],
        rate_hint=cfg["audio"]["speaking_rate_hint"],
        title_hint=cfg["youtube"]["title_prompt_hint"],
        keyword_count=cfg["video"]["pexels_query_count"],
    )

    resp = client.models.generate_content(
        model=cfg["content"]["gemini_text_model"],
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )

    data = json.loads(resp.text)
    data["topic"] = topic

    # basic sanity fallback in case the model returns fewer keywords than requested
    if len(data.get("visual_keywords", [])) < 2:
        data["visual_keywords"] = [topic]

    return data


if __name__ == "__main__":
    from src.config import load_config
    result = generate_script(load_config())
    print(json.dumps(result, indent=2))
