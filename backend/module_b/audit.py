"""Case completeness auditor for DynaBridge case library.

Checks a case folder against the expected DynaBridge deliverable structure
and reports what's present, missing, and recommended.
"""
from module_b.taxonomy import classify_files, PHASE_ORDER

# Required deliverables per phase
EXPECTED_DELIVERABLES = {
    "discovery": {
        "discovery": {"required": True, "label": "Brand Discovery PPT"},
        "assessment": {"required": False, "label": "Brand Assessment"},
        "consumer_insights": {"required": False, "label": "Consumer Insights"},
        "competitor": {"required": False, "label": "Competitor Analysis"},
        "survey": {"required": False, "label": "Survey / Research Data"},
    },
    "strategy": {
        "strategy": {"required": True, "label": "Brand Strategy"},
        "naming": {"required": False, "label": "Naming Project"},
    },
    "design": {
        "visual_identity": {"required": False, "label": "Visual Identity"},
        "guidelines": {"required": False, "label": "Brand Guidelines / Book"},
    },
}


def audit_case(files: list[dict], brand_name: str = "") -> dict:
    """Audit a case folder for completeness.

    Args:
        files: List of file metadata dicts from GDriveClient.list_folder().
        brand_name: Brand name for the report header.

    Returns:
        {
            "brand_name": str,
            "total_files": int,
            "total_folders": int,
            "total_size_mb": float,
            "classified_files": [dict],
            "phase_coverage": {phase: {doc_type: {present, files, required}}},
            "completeness_score": float,  # 0.0-1.0
            "missing_required": [str],
            "missing_optional": [str],
            "recommendations": [str],
        }
    """
    non_folders = [f for f in files if not f.get("is_folder")]
    folders = [f for f in files if f.get("is_folder")]
    classified = classify_files(non_folders)

    total_size = sum(f.get("size", 0) for f in non_folders)

    # Build phase coverage map
    phase_coverage = {}
    for phase, deliverables in EXPECTED_DELIVERABLES.items():
        phase_coverage[phase] = {}
        for doc_type, spec in deliverables.items():
            matching = [f for f in classified if f["doc_type"] == doc_type]
            phase_coverage[phase][doc_type] = {
                "present": len(matching) > 0,
                "files": [f["name"] for f in matching],
                "required": spec["required"],
                "label": spec["label"],
            }

    # Calculate completeness
    required_items = []
    optional_items = []
    missing_required = []
    missing_optional = []

    for phase, deliverables in phase_coverage.items():
        for doc_type, info in deliverables.items():
            if info["required"]:
                required_items.append(doc_type)
                if not info["present"]:
                    missing_required.append(info["label"])
            else:
                optional_items.append(doc_type)
                if not info["present"]:
                    missing_optional.append(info["label"])

    required_score = (
        sum(1 for dt in required_items if phase_coverage.get(
            EXPECTED_DELIVERABLES_PHASE.get(dt, ""), {}
        ).get(dt, {}).get("present", False))
        / max(len(required_items), 1)
    ) if required_items else 1.0

    # Simpler scoring: count present vs total expected
    total_expected = len(required_items) + len(optional_items)
    total_present = total_expected - len(missing_required) - len(missing_optional)
    completeness_score = total_present / max(total_expected, 1)

    # Recommendations
    recommendations = []
    if missing_required:
        recommendations.append(
            f"Missing required deliverables: {', '.join(missing_required)}"
        )
    if not any(f["doc_type"] == "consumer_insights" for f in classified):
        recommendations.append(
            "No consumer insights document found — consider adding persona or segmentation research"
        )
    if not any(f["doc_type"] == "guidelines" for f in classified):
        recommendations.append(
            "No brand guidelines found — needed for design phase completion"
        )

    return {
        "brand_name": brand_name,
        "total_files": len(non_folders),
        "total_folders": len(folders),
        "total_size_mb": round(total_size / (1024 * 1024), 1),
        "classified_files": classified,
        "phase_coverage": phase_coverage,
        "completeness_score": round(completeness_score, 2),
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "recommendations": recommendations,
    }


# Helper: reverse lookup phase for a doc_type
EXPECTED_DELIVERABLES_PHASE = {}
for _phase, _deliverables in EXPECTED_DELIVERABLES.items():
    for _dt in _deliverables:
        EXPECTED_DELIVERABLES_PHASE[_dt] = _phase
