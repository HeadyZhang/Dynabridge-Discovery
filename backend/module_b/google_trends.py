"""Google Trends integration using pytrends.

Provides search interest data, related queries, and regional breakdowns.
All methods have try/except wrappers — Google may rate-limit or block requests.
"""

import time
from typing import Optional

import pandas as pd
from pytrends.request import TrendReq


class GoogleTrendsClient:
    def __init__(self):
        self.pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))

    def get_interest_over_time(
        self,
        keywords: list[str],
        geo: str = "US",
        timeframe: str = "today 12-m",
    ) -> dict:
        """Search interest over time for up to 5 keywords."""
        kw_list = keywords[:5]
        self.pytrends.build_payload(kw_list, timeframe=timeframe, geo=geo)
        df = self.pytrends.interest_over_time()
        if df.empty:
            return {"data": [], "averages": {}}

        records = []
        for idx, row in df.iterrows():
            entry = {"date": idx.isoformat()}
            for kw in kw_list:
                if kw in df.columns:
                    entry[kw] = int(row[kw])
            records.append(entry)

        averages = {kw: int(df[kw].mean()) for kw in kw_list if kw in df.columns}
        return {"data": records, "averages": averages}

    def get_related_queries(self, keyword: str, geo: str = "US") -> dict:
        """Top and rising related queries for a keyword."""
        self.pytrends.build_payload([keyword], timeframe="today 12-m", geo=geo)
        related = self.pytrends.related_queries()
        result = related.get(keyword, {})

        top_df = result.get("top")
        rising_df = result.get("rising")

        return {
            "top": top_df.to_dict(orient="records") if isinstance(top_df, pd.DataFrame) and not top_df.empty else [],
            "rising": rising_df.to_dict(orient="records") if isinstance(rising_df, pd.DataFrame) and not rising_df.empty else [],
        }

    def get_interest_by_region(self, keyword: str, geo: str = "US") -> list[dict]:
        """Regional interest breakdown."""
        self.pytrends.build_payload([keyword], timeframe="today 12-m", geo=geo)
        df = self.pytrends.interest_by_region(resolution="REGION")
        if df.empty:
            return []
        filtered = df[df[keyword] > 0].sort_values(keyword, ascending=False).head(15)
        return filtered.reset_index().to_dict(orient="records")
