"""Extract structured ConsumerInsight records from all cases.

Sources (in priority order):
1. ai_tags_json → key_insights + core_challenges
2. extracted_text from case files → Claude generates insights

Falls back to keyword heuristics if Claude API is unavailable.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import DB_PATH
from models import Base
from module_b.models import CaseProject, CaseFile, ConsumerInsight

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Keyword-based fallback classifier
_TYPE_KEYWORDS = {
    "pricing": ["price", "cost", "afford", "premium", "budget", "cheap", "expensive", "value"],
    "purchase_driver": ["buy", "purchase", "choose", "prefer", "decide", "motivat", "driver"],
    "barrier": ["barrier", "obstacle", "concern", "trust", "hesitat", "risk", "fear", "challeng"],
    "channel": ["channel", "amazon", "retail", "online", "store", "platform", "dtc", "social media"],
    "behavior": ["behavior", "habit", "usage", "frequency", "repeat", "loyalty", "switch"],
    "perception": ["percei", "image", "brand", "reputation", "aware", "recogni"],
    "need_state": ["need", "want", "desire", "aspir", "goal", "pain point"],
    "attitude": ["attitude", "opinion", "sentiment", "feel", "believ", "expect"],
}


def _classify_fallback(text: str) -> str:
    text_lower = text.lower()
    for itype, keywords in _TYPE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return itype
    return "perception"


def _extract_with_claude(brand_name: str, industry: str, text_content: str) -> list[dict]:
    """Use Claude to extract and classify consumer insights from raw text."""
    import anthropic
    client = anthropic.Anthropic()

    prompt = f"""你是消费者研究分析师。以下是品牌 {brand_name}（{industry} 行业）的案例材料摘要。
请从中提取 3-8 条消费者洞察（consumer insights），包括购买驱动力、障碍、消费者需求、行为模式等。

材料:
{text_content[:3000]}

对每条洞察，输出 JSON 对象:
{{
  "insight_text": "洞察描述（简洁，1-2 句话）",
  "insight_type": "purchase_driver / barrier / need_state / perception / behavior / attitude / pricing / channel",
  "target_segment": "目标人群（null if not specific）",
  "evidence_source": "survey / review / social / interview / competitive",
  "confidence": "high / medium / low",
  "geo_market": "us / europe / global"
}}

输出一个 JSON 数组。只输出 JSON，不要其他内容。如果材料中没有消费者相关信息，输出空数组 []。"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(text)


def _extract_fallback(brand_name: str, industry: str, raw_items: list[str]) -> list[dict]:
    """Keyword-based fallback when Claude is unavailable."""
    results = []
    for text in raw_items:
        results.append({
            "insight_text": text,
            "insight_type": _classify_fallback(text),
            "target_segment": None,
            "evidence_source": "competitive",
            "confidence": "medium",
            "geo_market": "us",
        })
    return results


def _get_case_text(db, case_id: int) -> str:
    """Concatenate extracted text from a case's files."""
    files = (
        db.query(CaseFile)
        .filter(
            CaseFile.case_project_id == case_id,
            CaseFile.extracted_text != "",
            CaseFile.extracted_text.isnot(None),
        )
        .order_by(CaseFile.word_count.desc())
        .limit(5)
        .all()
    )
    parts = []
    total_chars = 0
    for f in files:
        chunk = f.extracted_text[:1000]
        parts.append(f"[{f.filename}]\n{chunk}")
        total_chars += len(chunk)
        if total_chars > 3000:
            break
    return "\n\n".join(parts)


def main():
    db = Session()

    existing = db.query(ConsumerInsight).count()
    if existing > 0:
        db.query(ConsumerInsight).delete()
        db.commit()
        print(f"Cleared {existing} existing insights")

    cases = db.query(CaseProject).all()
    total_created = 0

    for case in cases:
        # Source 1: ai_tags_json
        raw_insights = []
        if case.ai_tags_json and case.ai_tags_json != "{}":
            try:
                tags = json.loads(case.ai_tags_json) if isinstance(case.ai_tags_json, str) else case.ai_tags_json
                raw_insights.extend(tags.get("key_insights", []))
                raw_insights.extend(tags.get("core_challenges", []))
            except (json.JSONDecodeError, TypeError):
                pass

        structured = []

        if raw_insights:
            # Already have insights from tags — classify them
            try:
                structured = _extract_with_claude(
                    case.brand_name, case.industry or "other",
                    "\n".join(raw_insights),
                )
            except Exception as e:
                print(f"  {case.brand_name}: Claude classify failed ({e}), using fallback")
                structured = _extract_fallback(case.brand_name, case.industry or "other", raw_insights)
        else:
            # Source 2: Extract from file text
            case_text = _get_case_text(db, case.id)
            if not case_text:
                print(f"  {case.brand_name}: no text content, skipping")
                continue

            try:
                structured = _extract_with_claude(case.brand_name, case.industry or "other", case_text)
            except Exception as e:
                print(f"  {case.brand_name}: Claude extract failed ({e}), skipping")
                continue

        for item in structured:
            insight_text = item.get("insight_text", "")
            if not insight_text or len(insight_text) < 10:
                continue
            insight = ConsumerInsight(
                case_id=case.id,
                brand_name=case.brand_name,
                industry=case.industry or "other",
                insight_text=insight_text,
                insight_type=item.get("insight_type", "perception"),
                target_segment=item.get("target_segment"),
                evidence_source=item.get("evidence_source", "competitive"),
                confidence=item.get("confidence", "medium"),
                geo_market=item.get("geo_market", "us"),
            )
            db.add(insight)
            total_created += 1

        print(f"  {case.brand_name}: {len(structured)} insights")

    db.commit()
    print(f"\nTotal insights created: {total_created}")

    from sqlalchemy import func
    types = db.query(ConsumerInsight.insight_type, func.count()).group_by(ConsumerInsight.insight_type).all()
    for t, c in types:
        print(f"  {t}: {c}")

    db.close()


if __name__ == "__main__":
    main()
