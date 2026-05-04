import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend directory (ensures keys are always available)
load_dotenv(Path(__file__).parent / ".env")

# Paths
BASE_DIR = Path(__file__).parent.parent
# DATA_DIR holds runtime-mutable artifacts (DBs, vectors, watcher state, drive
# downloads). On Railway, mount a Volume here via DATA_DIR=/data.
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR))
TEMPLATE_DIR = BASE_DIR / "templates"
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", BASE_DIR / "uploads"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "output"))
PREVIEW_DIR = Path(os.getenv("PREVIEW_DIR", BASE_DIR / "previews"))
DB_PATH = Path(os.getenv("DB_PATH", DATA_DIR / "dynabridge.db"))

# Ensure dirs exist
for d in [DATA_DIR, UPLOAD_DIR, OUTPUT_DIR, PREVIEW_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")

# AI Model Versions (centralized — change here, applies everywhere)
MODEL_OPUS = "claude-opus-4-6"
MODEL_SONNET = "claude-sonnet-4-20250514"
MODEL_HAIKU = "claude-haiku-4-5-20251001"

# PPT Template
MASTER_TEMPLATE = TEMPLATE_DIR / "brand_discovery_master.pptx"

# Server
HOST = "0.0.0.0"
PORT = 8000
