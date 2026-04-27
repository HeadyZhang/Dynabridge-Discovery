"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  TrendingUp, Search, Lightbulb, Sparkles, Loader2, MapPin,
  BarChart3, Target, Clock, Globe, Tag,
} from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar,
} from "recharts";
import {
  getMarketIntelligence, listCases, getStats,
  type MarketIntelligence, type CaseSummary, type KnowledgeStats,
} from "@/lib/knowledge-api";
import KnowledgeNav from "@/components/KnowledgeNav";
import { useLanguage } from "@/lib/language-context";

const MARKETS = [
  { value: "US", label: "United States" },
  { value: "GB", label: "United Kingdom" },
  { value: "DE", label: "Germany" },
  { value: "JP", label: "Japan" },
  { value: "", label: "Global" },
];

export default function MarketingPage() {
  const { t, lang } = useLanguage();
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [selectedBrand, setSelectedBrand] = useState("");
  const [selectedIndustry, setSelectedIndustry] = useState("");
  const [selectedMarket, setSelectedMarket] = useState("US");
  const [keywords, setKeywords] = useState("");
  const [data, setData] = useState<MarketIntelligence | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    Promise.all([listCases(), getStats()])
      .then(([c, s]) => { setCases(c); setStats(s); })
      .catch(() => {});
  }, []);

  const industries = stats ? Object.keys(stats.industries) : [];

  const handleAnalyze = async () => {
    setLoading(true);
    try {
      const result = await getMarketIntelligence({
        brand: selectedBrand || undefined,
        industry: selectedIndustry || undefined,
        market: selectedMarket,
        keywords: keywords || undefined,
        lang: lang === "en" ? "en" : "cn",
      });
      setData(result);
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  };

  const trendsData = data?.trends as Record<string, unknown> | undefined;
  const interestData = (trendsData?.interest_over_time as Record<string, unknown>)?.data as Record<string, unknown>[] | undefined;
  const relatedQueries = trendsData?.related_queries as Record<string, unknown[]> | undefined;
  const regionalData = trendsData?.regional_interest as Record<string, unknown>[] | undefined;
  const strategy = data?.strategy as Record<string, unknown> | undefined;

  return (
    <div className="min-h-screen bg-neutral-50">
      <KnowledgeNav />

      <div className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        {/* Page title */}
        <div className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-brand-500" />
          <h1 className="text-lg font-semibold text-neutral-900">
            {t("Marketing Intelligence", "\u8425\u9500\u60c5\u62a5")}
          </h1>
        </div>
        {/* Input Controls */}
        <div className="bg-white rounded-xl border border-neutral-200 p-5">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <select
              value={selectedBrand}
              onChange={(e) => setSelectedBrand(e.target.value)}
              className="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white"
            >
              <option value="">{t("Select Brand", "\u9009\u62e9\u54c1\u724c")}</option>
              {cases.map((c) => (
                <option key={c.id} value={c.brand_name}>{c.brand_name}</option>
              ))}
            </select>

            <select
              value={selectedIndustry}
              onChange={(e) => setSelectedIndustry(e.target.value)}
              className="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white"
            >
              <option value="">{t("Select Industry", "\u9009\u62e9\u884c\u4e1a")}</option>
              {industries.map((ind) => (
                <option key={ind} value={ind}>{ind}</option>
              ))}
            </select>

            <select
              value={selectedMarket}
              onChange={(e) => setSelectedMarket(e.target.value)}
              className="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white"
            >
              {MARKETS.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>

            <input
              type="text"
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              placeholder="Keywords (comma separated)"
              className="px-3 py-2 text-sm border border-neutral-200 rounded-lg"
            />

            <button
              onClick={handleAnalyze}
              disabled={loading}
              className="flex items-center justify-center gap-2 px-4 py-2 bg-brand-500 text-white text-sm rounded-lg hover:bg-brand-600 disabled:opacity-50 transition-colors"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              {t("Analyze", "\u5206\u6790")}
            </button>
          </div>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <Loader2 className="w-8 h-8 animate-spin text-brand-500 mx-auto mb-3" />
              <p className="text-sm text-neutral-500">Fetching Google Trends + generating AI strategy...</p>
              <p className="text-xs text-neutral-400">This may take 10-15 seconds</p>
            </div>
          </div>
        )}

        {data && !loading && (
          <>
            {/* Trends + Insights row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Google Trends */}
              <div className="bg-white rounded-xl border border-neutral-200 p-5">
                <h2 className="text-sm font-medium text-neutral-700 mb-4 flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-brand-500" /> Google Trends
                </h2>

                {interestData && interestData.length > 0 ? (
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={interestData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                        <XAxis
                          dataKey="date"
                          tick={{ fontSize: 10 }}
                          tickFormatter={(v: string) => v.slice(5, 10)}
                        />
                        <YAxis tick={{ fontSize: 10 }} />
                        <Tooltip />
                        {Object.keys(interestData[0] || {})
                          .filter((k) => k !== "date")
                          .map((key, i) => (
                            <Line
                              key={key}
                              type="monotone"
                              dataKey={key}
                              stroke={["#f97316", "#3b82f6", "#10b981", "#8b5cf6", "#ec4899"][i % 5]}
                              strokeWidth={2}
                              dot={false}
                            />
                          ))}
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <p className="text-sm text-neutral-400 text-center py-8">
                    {trendsData?.error ? `Trends unavailable: ${trendsData.error}` : "No trend data available."}
                  </p>
                )}

                {/* Regional interest */}
                {regionalData && regionalData.length > 0 && (
                  <div className="mt-4">
                    <h3 className="text-xs font-medium text-neutral-500 mb-2 flex items-center gap-1">
                      <MapPin className="w-3 h-3" /> Top Regions
                    </h3>
                    <div className="h-40">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={regionalData.slice(0, 8)} layout="vertical">
                          <XAxis type="number" tick={{ fontSize: 10 }} />
                          <YAxis dataKey="geoName" type="category" tick={{ fontSize: 10 }} width={100} />
                          <Tooltip />
                          <Bar dataKey={Object.keys(regionalData[0]).find((k) => k !== "geoName") || ""} fill="#f97316" radius={[0, 4, 4, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}

                {/* Related queries */}
                {relatedQueries?.top && (relatedQueries.top as unknown[]).length > 0 && (
                  <div className="mt-4">
                    <h3 className="text-xs font-medium text-neutral-500 mb-2">Related Searches</h3>
                    <div className="flex flex-wrap gap-1">
                      {(relatedQueries.top as Array<Record<string, unknown>>).slice(0, 10).map((q, i) => (
                        <span key={i} className="text-[10px] px-2 py-0.5 rounded bg-neutral-100 text-neutral-600">
                          {String(q.query || "")}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Consumer Insights */}
              <div className="bg-white rounded-xl border border-neutral-200 p-5">
                <h2 className="text-sm font-medium text-neutral-700 mb-4 flex items-center gap-2">
                  <Lightbulb className="w-4 h-4 text-brand-500" /> Consumer Insights ({data.insights.length})
                </h2>
                <div className="space-y-2 max-h-[400px] overflow-y-auto">
                  {data.insights.map((ins, i) => (
                    <div key={i} className="p-3 rounded-lg bg-neutral-50">
                      <p className="text-sm text-neutral-800 mb-1">{ins.text}</p>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-brand-50 text-brand-600">
                          {ins.brand}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-neutral-200 text-neutral-600">
                          {ins.type}
                        </span>
                      </div>
                    </div>
                  ))}
                  {data.insights.length === 0 && (
                    <p className="text-sm text-neutral-400 text-center py-8">
                      No insights found for this industry.
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* AI Strategy */}
            {strategy && !strategy.error && (
              <div className="bg-white rounded-xl border border-neutral-200 p-5">
                <h2 className="text-sm font-medium text-neutral-700 mb-4 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-brand-500" /> AI Marketing Strategy
                </h2>

                {strategy.executive_summary ? (
                  <div className="bg-brand-50 rounded-lg p-4 mb-4">
                    <p className="text-sm text-neutral-800 leading-relaxed">
                      {String(strategy.executive_summary)}
                    </p>
                  </div>
                ) : null}

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {[
                    { key: "content_strategy", icon: Tag, label: t("Content Strategy", "\u5185\u5bb9\u7b56\u7565") },
                    { key: "channel_strategy", icon: BarChart3, label: t("Channel Strategy", "\u6e20\u9053\u7b56\u7565") },
                    { key: "timing_strategy", icon: Clock, label: t("Timing Strategy", "\u65f6\u673a\u7b56\u7565") },
                    { key: "geo_strategy", icon: Globe, label: t("Geo Strategy", "\u5730\u57df\u7b56\u7565") },
                    { key: "keyword_strategy", icon: Target, label: t("Keyword Strategy", "\u5173\u952e\u8bcd\u7b56\u7565") },
                  ].map(({ key, icon: Icon, label }) => {
                    const section = strategy[key] as Record<string, unknown> | undefined;
                    if (!section) return null;
                    return (
                      <div key={key} className="border border-neutral-200 rounded-lg p-4">
                        <h3 className="text-sm font-medium text-neutral-700 mb-2 flex items-center gap-2">
                          <Icon className="w-4 h-4 text-brand-500" /> {label}
                        </h3>
                        {(() => {
                          const items = (section.recommended || section.primary || section.peak_months || section.priority_regions) as string[] | undefined;
                          if (!items || !Array.isArray(items)) return null;
                          return (
                            <div className="mb-2">
                              <p className="text-[10px] text-green-600 font-medium mb-1">{t("RECOMMENDED", "\u63a8\u8350")}</p>
                              <div className="flex flex-wrap gap-1">
                                {items.map((item, i) => (
                                  <span key={i} className="text-xs px-2 py-0.5 rounded bg-green-50 text-green-700">
                                    {String(item)}
                                  </span>
                                ))}
                              </div>
                            </div>
                          );
                        })()}
                        {(() => {
                          const items = section.avoid as string[] | undefined;
                          if (!items || !Array.isArray(items)) return null;
                          return (
                            <div className="mb-2">
                              <p className="text-[10px] text-red-600 font-medium mb-1">{t("AVOID", "\u907f\u514d")}</p>
                              <div className="flex flex-wrap gap-1">
                                {items.map((item, i) => (
                                  <span key={i} className="text-xs px-2 py-0.5 rounded bg-red-50 text-red-700">
                                    {String(item)}
                                  </span>
                                ))}
                              </div>
                            </div>
                          );
                        })()}
                        {(() => {
                          const items = section.long_tail as string[] | undefined;
                          if (!items || !Array.isArray(items)) return null;
                          return (
                            <div className="mb-2">
                              <p className="text-[10px] text-blue-600 font-medium mb-1">{t("LONG TAIL", "\u957f\u5c3e\u8bcd")}</p>
                              <div className="flex flex-wrap gap-1">
                                {items.map((item, i) => (
                                  <span key={i} className="text-xs px-2 py-0.5 rounded bg-blue-50 text-blue-700">
                                    {String(item)}
                                  </span>
                                ))}
                              </div>
                            </div>
                          );
                        })()}
                        {section.rationale ? (
                          <p className="text-xs text-neutral-500 mt-2">{String(section.rationale)}</p>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {strategy?.error && (
              <div className="bg-white rounded-xl border border-neutral-200 p-5">
                <h2 className="text-sm font-medium text-neutral-700 mb-2 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-brand-500" /> AI Strategy
                </h2>
                <p className="text-sm text-neutral-400">
                  AI strategy generation unavailable. Check API key configuration.
                </p>
              </div>
            )}
          </>
        )}

        {!data && !loading && (
          <div className="text-center py-20 text-neutral-400">
            <TrendingUp className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">Select a brand, industry, or keywords and click Analyze</p>
          </div>
        )}
      </div>
    </div>
  );
}
