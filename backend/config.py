import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
TEMPLATE_DIR = BASE_DIR / "templates"
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
PREVIEW_DIR = BASE_DIR / "previews"
DB_PATH = BASE_DIR / "dynabridge.db"

# Ensure dirs exist
for d in [UPLOAD_DIR, OUTPUT_DIR, PREVIEW_DIR]:
    d.mkdir(exist_ok=True)

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")

# PPT Template
MASTER_TEMPLATE = TEMPLATE_DIR / "brand_discovery_master.pptx"

# Server
HOST = "0.0.0.0"
PORT = 8000
