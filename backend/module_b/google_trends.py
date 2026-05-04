"""Google Trends integration using pytrends.

Provides search interest data, related queries, and regional breakdowns.
Includes retry logic, caching (24h TTL), and graceful degradation on 429.
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

CACHE_DIR = "/tmp/trends_cache"
CACHE_TTL_HOURS = 24


class GoogleTrendsClient:
    def __init__(self):
        os.makedirs(CACHE_DIR, exist_ok=True)

    def _cache_key(self, method: str, keywords: list, geo: str) -> str:
        return f"{method}_{'_'.join(keywords)}_{geo}".replace(" ", "_").replace("/", "_")

    def _get_cached(self, key: str) -> dict | None:
        path = os.path.join(CACHE_DIR, f"{key}.json")
        if os.path.exists(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                cached_at = datetime.fromisoformat(data.get("_cached_at", "2000-01-01"))
                if datetime.now() - cached_at < timedelta(hours=CACHE_TTL_HOURS):
                    return data
            except (json.JSONDecodeError, ValueError):
                pass
        return None

    def _set_cache(self, key: str, data: dict):
        data_with_ts = {**data, "_cached_at": datetime.now().isoformat()}
        path = os.path.join(CACHE_DIR, f"{key}.json")
        with open(path, "w") as f:
            json.dump(data_with_ts, f)

    def _get_pytrends(self):
        from pytrends.request import TrendReq
        return TrendReq(hl="en-US", tz=360, timeout=(10, 25))

    def get_interest_over_time(
        self,
        keywords: list[str],
        geo: str = "US",
        timeframe: str = "today 12-m",
    ) -> dict:
        """Search interest over time for up to 5 keywords."""
        kw_list = keywords[:5]
        cache_key = self._cache_key("iot", kw_list, geo)

        cached = self._get_cached(cache_key)
        if cached:
            cached.pop("_cached_at", None)
            return {**cached, "source": "cache"}

        for attempt in range(3):
            try:
                pytrends = self._get_pytrends()
                pytrends.build_payload(kw_list, timeframe=timeframe, geo=geo)
                df = pytrends.interest_over_time()

                if df.empty:
                    result = {"data": [], "averages": {}, "source": "google_trends"}
                else:
                    records = []
                    for idx, row in df.iterrows():
                        entry = {"date": idx.isoformat()}
                        for kw in kw_list:
                            if kw in df.columns:
                                entry[kw] = int(row[kw])
                        records.append(entry)

                    averages = {kw: int(df[kw].mean()) for kw in kw_list if kw in df.columns}
                    result = {"data": records, "averages": averages, "source": "google_trends"}

                self._set_cache(cache_key, result)
                return result

            except Exception as e:
                if "429" in str(e) and attempt < 2:
                    wait = (attempt + 1) * 30
                    time.sleep(wait)
                else:
                    return {"data": [], "averages": {}, "error": str(e), "source": "error"}

        return {"data": [], "averages": {}, "error": "Max retries exceeded", "source": "error"}

    def get_related_queries(self, keyword: str, geo: str = "US") -> dict:
        """Top and rising related queries for a keyword."""
        cache_key = self._cache_key("rq", [keyword], geo)

        cached = self._get_cached(cache_key)
        if cached:
            cached.pop("_cached_at", None)
            return cached

        for attempt in range(3):
            try:
                pytrends = self._get_pytrends()
                pytrends.build_payload([keyword], timeframe="today 12-m", geo=geo)
                related = pytrends.related_queries()
                result_raw = related.get(keyword, {})

                top_df = result_raw.get("top")
                rising_df = result_raw.get("rising")

                result = {
                    "top": top_df.to_dict(orient="records") if isinstance(top_df, pd.DataFrame) and not top_df.empty else [],
                    "rising": rising_df.to_dict(orient="records") if isinstance(rising_df, pd.DataFrame) and not rising_df.empty else [],
                }

                self._set_cache(cache_key, result)
                return result

            except Exception as e:
                if "429" in str(e) and attempt < 2:
                    wait = (attempt + 1) * 30
                    time.sleep(wait)
                else:
                    return {"top": [], "rising": [], "error": str(e)}

        return {"top": [], "rising": [], "error": "Max retries exceeded"}

    def get_interest_by_region(self, keyword: str, geo: str = "US") -> list[dict]:
        """Regional interest breakdown."""
        cache_key = self._cache_key("ibr", [keyword], geo)

        cached = self._get_cached(cache_key)
        if cached:
            cached.pop("_cached_at", None)
            return cached.get("regions", [])

        for attempt in range(3):
            try:
                pytrends = self._get_pytrends()
                pytrends.build_payload([keyword], timeframe="today 12-m", geo=geo)
                df = pytrends.interest_by_region(resolution="REGION")

                if df.empty:
                    return []

                filtered = df[df[keyword] > 0].sort_values(keyword, ascending=False).head(15)
                regions = filtered.reset_index().to_dict(orient="records")

                self._set_cache(cache_key, {"regions": regions})
                return regions

            except Exception as e:
                if "429" in str(e) and attempt < 2:
                    wait = (attempt + 1) * 30
                    time.sleep(wait)
                else:
                    return []

        return []
