"""Amazon Ads CSV import parser.

Accepts CSV exported from Amazon Advertising > Campaign Manager > Download Report.
Maps Amazon column names to Datacube Campaign + Performance fields.
"""

import csv
import io


def _clean_num(val: str) -> float:
    if not val or val == "--":
        return 0
    return float(str(val).replace(",", "").replace("$", "").strip())


def parse_amazon_ads_csv(file_content: str, brand_name: str) -> list[dict]:
    """Parse an Amazon Ads campaign report CSV into Datacube-compatible dicts."""
    reader = csv.DictReader(io.StringIO(file_content))

    campaigns = []
    for row in reader:
        name = row.get("Campaign Name", row.get("Campaign name", ""))
        if not name:
            continue

        cost = _clean_num(row.get("Spend", row.get("Cost", "0")))
        revenue = _clean_num(row.get("Sales", row.get("7 Day Total Sales", "0")))
        impressions = int(_clean_num(row.get("Impressions", "0")))
        clicks = int(_clean_num(row.get("Clicks", "0")))
        orders = int(_clean_num(row.get("Orders", row.get("7 Day Total Orders", "0"))))

        campaigns.append({
            "brand_name": brand_name,
            "campaign_name": name,
            "campaign_type": "paid_media",
            "context": {"channel": "amazon_ads", "funnel_stage": "conversion"},
            "performance": {
                "impressions": impressions,
                "clicks": clicks,
                "conversions": orders,
                "revenue": revenue,
                "cost": cost,
                "roas": round(revenue / cost, 2) if cost > 0 else 0,
                "cpc": round(cost / clicks, 2) if clicks > 0 else 0,
                "cpm": round(cost / impressions * 1000, 2) if impressions > 0 else 0,
                "engagement_rate": round(clicks / impressions * 100, 2) if impressions > 0 else 0,
            },
        })
    return campaigns
