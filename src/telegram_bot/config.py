import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]

ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)

BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
