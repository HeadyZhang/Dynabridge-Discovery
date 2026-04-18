"""File taxonomy classifier for DynaBridge case library.

Classifies Drive files into standardized document types based on
filename patterns and MIME types.
"""
import re
from pathlib import Path

# Document type definitions
DOC_TYPES = {
    "discovery": {
        "label": "Brand Discovery",
        "patterns": [r"discovery", r"brand\s*discovery"],
        "phase": "discovery",
    },
    "strategy": {
        "label": "Brand Strategy",
        "patterns": [r"brand[_\s]*strategy", r"strategy[_\s]*workshop", r"strategy"],
        "phase": "strategy",
    },
    "assessment": {
        "label": "Brand Assessment",
        "patterns": [r"brand\s*assessment", r"brand\s*review", r"preliminary.*review"],
        "phase": "discovery",
    },
    "naming": {
        "label": "Naming / Renaming",
        "patterns": [r"naming", r"renaming", r"name\s*project"],
        "phase": "strategy",
    },
    "consumer_insights": {
        "label": "Consumer Insights",
        "patterns": [r"consumer\s*insight", r"persona", r"segmentation", r"customer.*persona"],
        "phase": "discovery",
    },
    "survey": {
        "label": "Survey / Research",
        "patterns": [r"survey", r"questionnaire", r"research\s*(report|data|section)"],
        "phase": "discovery",
    },
    "visual_identity": {
        "label": "Visual Identity",
        "patterns": [r"visual\s*id", r"vis[_\s]*id", r"logo[_\s]*concept", r"logo[_\s]*round", r"logo[_\s]*r\d"],
        "phase": "design",
    },
    "guidelines": {
        "label": "Brand Guidelines",
        "patterns": [r"guideline", r"brand\s*book", r"design\s*guideline"],
        "phase": "design",
    },
    "competitor": {
        "label": "Competitor Analysis",
        "patterns": [r"competitor", r"competitive", r"market\s*analysis"],
        "phase": "discovery",
    },
    "kickoff": {
        "label": "Kickoff / Meeting",
        "patterns": [r"kickoff", r"kick[\s-]*off", r"meeting\s*note"],
        "phase": "planning",
    },
    "social_media": {
        "label": "Social Media",
        "patterns": [r"social\s*media", r"content\s*calendar"],
        "phase": "marketing",
    },
    "product_image": {
        "label": "Product Image",
        "extensions": {".jpg", ".jpeg", ".png", ".svg", ".ai", ".psd", ".tif", ".tiff"},
        "phase": "assets",
    },
    "video": {
        "label": "Video Asset",
        "extensions": {".mp4", ".mov", ".avi", ".mkv"},
        "phase": "assets",
    },
    "design_file": {
        "label": "Design File",
        "extensions": {".ai", ".psd", ".stp", ".step"},
        "phase": "design",
    },
    "archive": {
        "label": "Archive",
        "extensions": {".zip", ".rar", ".7z"},
        "phase": "assets",
    },
}

# Phase ordering for pipeline
PHASE_ORDER = ["planning", "discovery", "strategy", "design", "marketing", "assets"]


def classify_file(filename: str, mime_type: str = "") -> dict:
    """Classify a file into a document type.

    Args:
        filename: The file name.
        mime_type: Optional MIME type string.

    Returns:
        {"doc_type": str, "label": str, "phase": str, "confidence": float}
    """
    name_lower = filename.lower()
    ext = Path(filename).suffix.lower()

    # Try name-pattern matching first (highest confidence)
    for doc_type, spec in DOC_TYPES.items():
        if "patterns" not in spec:
            continue
        for pattern in spec["patterns"]:
            if re.search(pattern, name_lower):
                return {
                    "doc_type": doc_type,
                    "label": spec["label"],
                    "phase": spec["phase"],
                    "confidence": 0.9,
                }

    # Try extension-based matching
    for doc_type, spec in DOC_TYPES.items():
        if "extensions" in spec and ext in spec["extensions"]:
            return {
                "doc_type": doc_type,
                "label": spec["label"],
                "phase": spec["phase"],
                "confidence": 0.7,
            }

    # Google Workspace type inference
    if "presentation" in mime_type:
        return {"doc_type": "presentation", "label": "Presentation", "phase": "strategy", "confidence": 0.5}
    if "document" in mime_type:
        return {"doc_type": "document", "label": "Document", "phase": "planning", "confidence": 0.5}
    if "spreadsheet" in mime_type:
        return {"doc_type": "spreadsheet", "label": "Spreadsheet", "phase": "planning", "confidence": 0.5}

    return {"doc_type": "other", "label": "Other", "phase": "assets", "confidence": 0.1}


def classify_files(files: list[dict]) -> list[dict]:
    """Classify a list of file metadata dicts, adding taxonomy fields.

    Each input dict should have 'name' and 'mimeType' keys.
    Returns new dicts with added doc_type, label, phase, confidence.
    """
    results = []
    for f in files:
        if f.get("is_folder"):
            continue
        classification = classify_file(f["name"], f.get("mimeType", ""))
        results.append({**f, **classification})
    return results
