"""Google Ads CSV import parser.

Accepts CSV exported from Google Ads > Reports > Download CSV.
Maps Google Ads column names to Datacube Campaign + Performance fields.
"""

import csv
import io

GOOGLE_ADS_COLUMN_MAP = {
    "Campaign": "campaign_name",
    "Campaign type": "campaign_type",
    "Impressions": "impressions",
    "Clicks": "clicks",
    "Conversions": "conversions",
    "Cost": "cost",
    "Conv. value": "revenue",
    "CTR": "ctr",
    "CPC": "cpc",
}


def _clean_num(val: str) -> float:
    if not val or val == "--":
        return 0
    return float(str(val).replace(",", "").replace("$", "").replace("%", "").strip())


def parse_google_ads_csv(file_content: str, brand_name: str) -> list[dict]:
    """Parse a Google Ads campaign report CSV into Datacube-compatible dicts."""
    reader = csv.DictReader(io.StringIO(file_content))

    campaigns = []
    for row in reader:
        name = row.get("Campaign", row.get("Campaign name", ""))
        if not name or name.startswith("Total"):
            continue

        cost = _clean_num(row.get("Cost", "0"))
        revenue = _clean_num(row.get("Conv. value", row.get("Conversion value", "0")))
        impressions = int(_clean_num(row.get("Impressions", "0")))
        clicks = int(_clean_num(row.get("Clicks", "0")))
        conversions = int(_clean_num(row.get("Conversions", "0")))

        campaigns.append({
            "brand_name": brand_name,
            "campaign_name": name,
            "campaign_type": "paid_media",
            "context": {"channel": "google_ads", "funnel_stage": "conversion"},
            "performance": {
                "impressions": impressions,
                "clicks": clicks,
                "conversions": conversions,
                "revenue": revenue,
                "cost": cost,
                "roas": round(revenue / cost, 2) if cost > 0 else 0,
                "cpc": round(cost / clicks, 2) if clicks > 0 else 0,
                "cpm": round(cost / impressions * 1000, 2) if impressions > 0 else 0,
                "engagement_rate": round(clicks / impressions * 100, 2) if impressions > 0 else 0,
            },
        })
    return campaigns
