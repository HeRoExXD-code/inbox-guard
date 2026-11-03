"""All configuration comes from the environment. No secrets in code.

OPENAI_API_KEY and OPENAI_BASE_URL are read by the OpenAI client itself.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

MODEL = os.getenv("MODEL", "gemma-4-E4B-it")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0"))
MAX_STEPS = int(os.getenv("MAX_STEPS", "8"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "512"))
# Some Gemma chat templates reject the "system" role; "1" folds it into the first user turn.
SYSTEM_AS_USER = os.getenv("SYSTEM_AS_USER", "0") == "1"

# Fixed "today" so that every run of the evaluation sees the same world.
TODAY = "2026-11-03"

# Domains whose links may appear in answers / outgoing mail under the guard defence.
TRUSTED_DOMAINS = ("kmitl.ac.th", "github.com")
