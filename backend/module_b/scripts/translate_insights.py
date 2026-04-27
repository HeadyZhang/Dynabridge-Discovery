"""Batch translate Chinese consumer insights to English using Claude API.

Usage:
    python -m module_b.scripts.translate_insights [--limit N]
"""

import sys
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, ".")
from config import DB_PATH
from models import Base
from module_b.models import ConsumerInsight


def has_chinese(text: str) -> bool:
    return any("\u4e00" <= c <= "\u9fff" for c in text)


def translate_batch(insights: list, client, db) -> int:
    translated = 0
    for insight in insights:
        if insight.insight_text_en:
            continue
        if not has_chinese(insight.insight_text):
            # Already English - copy as-is
            insight.insight_text_en = insight.insight_text
            db.commit()
            translated += 1
            continue

        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Translate the following consumer insight to English. "
                        f"Keep brand names, technical terms, and numbers as-is. "
                        f"Output ONLY the translation, no explanations.\n\n"
                        f"{insight.insight_text}"
                    ),
                }],
            )
            insight.insight_text_en = response.content[0].text.strip()
            db.commit()
            translated += 1
            time.sleep(0.5)
        except Exception as e:
            print(f"  Error translating insight {insight.id}: {e}")
            time.sleep(2)

    return translated


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
    Session = sessionmaker(bind=engine)
    db = Session()

    total = db.query(ConsumerInsight).count()
    without_en = db.query(ConsumerInsight).filter(
        ConsumerInsight.insight_text_en.is_(None)
    ).count()

    print(f"Total insights: {total}")
    print(f"Without English: {without_en}")

    if without_en == 0:
        print("All insights already have English translations.")
        db.close()
        return

    try:
        import anthropic
        client = anthropic.Anthropic()
    except Exception as e:
        print(f"Cannot initialize Anthropic client: {e}")
        db.close()
        return

    insights = db.query(ConsumerInsight).filter(
        ConsumerInsight.insight_text_en.is_(None)
    ).limit(args.limit).all()

    print(f"Translating {len(insights)} insights...")
    translated = translate_batch(insights, client, db)
    print(f"Done! Translated {translated} insights.")

    db.close()


if __name__ == "__main__":
    main()
