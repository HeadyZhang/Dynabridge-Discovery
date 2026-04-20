"""Classify all unclassified cases by industry using Claude API.

Dynabridge's clients are primarily Chinese brands going global.
This script uses Claude to infer industry from brand name, file names, and content.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

import anthropic

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import DB_PATH
from models import Base
from module_b.models import CaseProject, CaseFile

ALLOWED_INDUSTRIES = [
    "fitness", "electronics", "beauty", "home", "food_beverage",
    "fashion", "jewelry", "baby_maternity", "toys", "cleaning",
    "pet_care", "outdoor", "automotive", "healthcare", "other",
]

client = anthropic.Anthropic()
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


def classify_case(case: CaseProject, files: list[CaseFile]) -> str:
    """Use Claude to infer the industry for a single case."""
    file_names = [f.filename for f in files[:20]]
    extracted_samples = [
        f.extracted_text[:200]
        for f in files
        if f.extracted_text
    ][:5]

    prompt = f"""Based on this brand case information, classify the industry into exactly ONE of these categories:

Categories: {', '.join(ALLOWED_INDUSTRIES)}

Brand name: {case.brand_name}
Files: {json.dumps(file_names, ensure_ascii=False)}
Content samples: {json.dumps(extracted_samples, ensure_ascii=False)}
AI tags: {case.ai_tags_json[:500] if case.ai_tags_json else 'none'}

Reply with ONLY the category name, nothing else."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}],
        )
        industry = response.content[0].text.strip().lower()
        return industry if industry in ALLOWED_INDUSTRIES else "other"
    except Exception as e:
        print(f"  AI classification failed for {case.brand_name}: {e}")
        return "other"


def main():
    db = Session()
    cases = db.query(CaseProject).all()
    classified = 0

    for case in cases:
        if case.industry and case.industry != "Unclassified":
            print(f"  skip {case.brand_name}: already {case.industry}")
            continue

        files = db.query(CaseFile).filter(CaseFile.case_project_id == case.id).all()
        industry = classify_case(case, files)
        case.industry = industry
        classified += 1
        print(f"  {case.brand_name} -> {industry}")

    db.commit()

    # Summary
    industries: dict[str, int] = {}
    for case in db.query(CaseProject).all():
        ind = case.industry or "Unclassified"
        industries[ind] = industries.get(ind, 0) + 1

    print(f"\nClassified {classified} cases")
    print(f"Industry distribution: {json.dumps(industries, indent=2)}")

    unclassified = industries.get("Unclassified", 0) + industries.get("", 0)
    if unclassified == 0:
        print("All cases classified")
    else:
        print(f"WARNING: {unclassified} still unclassified")

    db.close()


if __name__ == "__main__":
    main()
