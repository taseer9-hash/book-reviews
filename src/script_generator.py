"""Generates the video script, title, description, and b-roll search keywords
using the Gemini API. Returns structured JSON so downstream steps don't have
to re-parse free text.

BOOK REVIEW VERSION: tuned for reviewing real, published books about wealth,
business, and success. Every script follows a fixed structure: hook, book
title+author, what it's about, who it's best for, the best takeaway, and one
honest critique.

Also tracks previously-used books in used_books.json (at the repo root) so
the pipeline doesn't repeat the same title run after run.
"""
import json
from pathlib import Path

from google import genai

from src.config import Secrets

ROOT = Path(__file__).resolve().parent.parent
USED_BOOKS_PATH = ROOT / "used_books.json"


TOPIC_POOL_PROMPT = """You are picking ONE specific, real, published, well-known book
that fits this description: "{niche}"

The book MUST be real — an actual published book with a real title and a real author.
Do not invent a title or author under any circumstances. If you are not fully certain
a book is real, pick a different, more famous one instead.

Do NOT pick any of these books — they have already been covered recently:
{used_books_list}

Return ONLY the book's title and author, in this exact format and nothing else:
"Book Title" by Author Name"""

SCRIPT_PROMPT = """Write a script for a fast-paced, engaging short-form YouTube video
reviewing this REAL, published book: {topic}

The book MUST be real and the details you state about it MUST be accurate — do not
invent facts, quotes, or claims about the book's content. If unsure of a specific
detail, keep that part general rather than stating something that might be wrong.

Structure the script in this exact order:
1. HOOK (first line, 1 sentence): a punchy hook tied to the book's core promise —
   e.g. "If you want to build real wealth, this book has the blueprint."
2. State the book's exact title and the author's full name clearly and naturally.
3. WHAT IT'S ABOUT: 1-2 sentences on the book's core idea or thesis.
4. WHO IT'S FOR: 1 sentence on who gets the most value from this book (e.g. "best if
   you're just starting to invest" or "perfect for first-time founders").
5. BEST TAKEAWAY: the single most actionable idea from the book, stated concretely.
6. WHAT COULD BE BETTER: one honest, specific, fair critique or limitation.
7. A punchy natural closing line (not "subscribe", no calls to action).

Requirements:
- About {word_count} words total, spoken narration only, no stage directions or headers.
- Conversational, confident tone. {rate_hint}.

Also produce:
- A punchy YouTube title that includes the book's real title. {title_hint}
- A short YouTube description (2-3 sentences, must include the real book title and
  real author name, plus relevant hashtags).
- A list of {keyword_count} short visual search phrases (2-4 words each) describing
  stock footage that would visually match different moments of the review — concrete
  and visual (e.g. "person reading book", "stack of money", "writing notes desk"),
  not abstract concepts.

Return ONLY valid JSON, no markdown fences, in this exact shape:
{{
  "title": "...",
  "description": "...",
  "script": "...",
  "visual_keywords": ["...", "..."],
  "book_title": "...",
  "book_author": "..."
}}
"""


def _client() -> genai.Client:
    return genai.Client(api_key=Secrets.GEMINI_API_KEY)


def load_used_books() -> list[str]:
    """Returns a list of 'Title by Author' strings already covered."""
    if not USED_BOOKS_PATH.exists():
        return []
    try:
        with open(USED_BOOKS_PATH, "r") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_used_book(book_title: str, book_author: str) -> None:
    """Appends a newly-covered book to used_books.json (creates it if needed)."""
    if not book_title:
        return
    used = load_used_books()
    entry = f"{book_title} by {book_author}" if book_author else book_title
    if entry not in used:
        used.append(entry)
    with open(USED_BOOKS_PATH, "w") as f:
        json.dump(used, f, indent=2)


def pick_topic(cfg: dict) -> str:
    if cfg["content"]["fixed_topic"]:
        return cfg["content"]["fixed_topic"]

    client = _client()
    used_books = load_used_books()
    # Keep the avoid-list from growing the prompt unreasonably large — the
    # most recent ~40 are plenty to steer Gemini away from repeats.
    recent = used_books[-40:]
    used_books_list = "\n".join(f"- {b}" for b in recent) if recent else "(none yet)"

    prompt = TOPIC_POOL_PROMPT.format(
        niche=cfg["content"]["niche"],
        used_books_list=used_books_list,
    )
    resp = client.models.generate_content(
        model=cfg["content"]["gemini_text_model"],
        contents=prompt,
    )
    return resp.text.strip().strip('"')


def generate_script(cfg: dict) -> dict:
    """Returns dict with keys: title, description, script, visual_keywords,
    book_title, book_author, topic."""
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

    if len(data.get("visual_keywords", [])) < 2:
        data["visual_keywords"] = [topic]

    return data


if __name__ == "__main__":
    from src.config import load_config
    result = generate_script(load_config())
    print(json.dumps(result, indent=2))
