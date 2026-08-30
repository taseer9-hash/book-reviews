"""Loads config.yaml and environment/secret variables into one place."""
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()  # no-op in CI, useful for local runs

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH, "r") as f:
        cfg = yaml.safe_load(f)

    # Resolve output paths to absolute, and make sure they exist
    work_dir = ROOT / cfg["paths"]["work_dir"]
    final_dir = ROOT / cfg["paths"]["final_dir"]
    work_dir.mkdir(parents=True, exist_ok=True)
    final_dir.mkdir(parents=True, exist_ok=True)
    cfg["paths"]["work_dir"] = str(work_dir)
    cfg["paths"]["final_dir"] = str(final_dir)

    return cfg


class Secrets:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
    YOUTUBE_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID")
    YOUTUBE_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET")
    YOUTUBE_REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN")

    @classmethod
    def validate(cls):
        missing = [k for k, v in vars(cls).items()
                   if not k.startswith("_") and not callable(v) and v is None
                   and not isinstance(v, classmethod)]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables/secrets: {missing}"
            )
