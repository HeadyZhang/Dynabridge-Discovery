"""Meta Ads (Facebook / Instagram) CSV import parser.

Accepts CSV exported from Meta Ads Manager > Export.
Maps Meta column names to Datacube Campaign + Performance fields.
"""

import csv
import io


def _clean_num(val: str) -> float:
    if not val or val == "--":
        return 0
    return float(str(val).replace(",", "").replace("$", "").strip())


def parse_meta_ads_csv(file_content: str, brand_name: str) -> list[dict]:
    """Parse a Meta Ads Manager export CSV into Datacube-compatible dicts."""
    reader = csv.DictReader(io.StringIO(file_content))

    campaigns = []
    for row in reader:
        name = row.get("Campaign name", row.get("Campaign Name", ""))
        if not name:
            continue

        cost = _clean_num(row.get("Amount spent (USD)", row.get("Amount spent", "0")))
        clicks = int(_clean_num(row.get("Link clicks", row.get("Clicks (all)", "0"))))
        impressions = int(_clean_num(row.get("Impressions", "0")))
        conversions = int(_clean_num(row.get("Results", row.get("Purchases", "0"))))

        roas_val = _clean_num(row.get("Purchase ROAS (return on ad spend)", row.get("ROAS", "0")))
        revenue = round(cost * roas_val, 2) if roas_val > 0 else 0

        placement = row.get("Placement", row.get("Platform", "")).lower()
        channel = "instagram" if "instagram" in placement else "facebook"

        campaigns.append({
            "brand_name": brand_name,
            "campaign_name": name,
            "campaign_type": "paid_media",
            "context": {"channel": channel, "funnel_stage": "awareness"},
            "performance": {
                "impressions": impressions,
                "clicks": clicks,
                "conversions": conversions,
                "revenue": revenue,
                "cost": cost,
                "roas": round(roas_val, 2),
                "engagement_rate": round(clicks / impressions * 100, 2) if impressions > 0 else 0,
                "cpc": round(cost / clicks, 2) if clicks > 0 else 0,
                "cpm": round(cost / impressions * 1000, 2) if impressions > 0 else 0,
            },
        })
    return campaigns
