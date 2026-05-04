"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Search, Filter, Lightbulb, Sparkles, Database, Loader2, Tag,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import {
  getConsumerInsights, getSynthesis, getStats,
  type ConsumerInsightData, type KnowledgeStats,
} from "@/lib/knowledge-api";
import KnowledgeNav from "@/components/KnowledgeNav";
import { useLanguage } from "@/lib/language-context";

const INSIGHT_TYPES = [
  "purchase_driver", "barrier", "need_state", "perception",
  "behavior", "attitude", "pricing", "channel",
];

const GEO_OPTIONS = ["us", "europe", "global", "china"];

const TYPE_COLORS: Record<string, string> = {
  purchase_driver: "bg-green-100 text-green-700",
  barrier: "bg-red-100 text-red-700",
  need_state: "bg-violet-100 text-violet-700",
  perception: "bg-blue-100 text-blue-700",
  behavior: "bg-amber-100 text-amber-700",
  attitude: "bg-cyan-100 text-cyan-700",
  pricing: "bg-orange-100 text-orange-700",
  channel: "bg-pink-100 text-pink-700",
};

export default function InsightsPage() {
  const { t, lang } = useLanguage();
  const [insights, setInsights] = useState<ConsumerInsightData[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [synthesis, setSynthesis] = useState("");
  const [loading, setLoading] = useState(true);
  const [synthLoading, setSynthLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterIndustry, setFilterIndustry] = useState("");
  const [filterType, setFilterType] = useState("");
  const [filterGeo, setFilterGeo] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  useEffect(() => {
    getStats().then(setStats).catch(() => {});
  }, []);

  const loadInsights = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getConsumerInsights({
        q: searchQuery || undefined,
        industry: filterIndustry || undefined,
        insight_type: filterType || undefined,
        geo: filterGeo || undefined,
        limit: 200,
      });
      setInsights(data.insights);
      setTotal(data.total);
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  }, [searchQuery, filterIndustry, filterType, filterGeo]);

  useEffect(() => {
    loadInsights();
  }, [loadInsights]);

  const loadSynthesis = async () => {
    setSynthLoading(true);
    try {
      const data = await getSynthesis({
        industry: filterIndustry || undefined,
        insight_type: filterType || undefined,
        geo: filterGeo || undefined,
        lang: lang === "en" ? "en" : "cn",
      });
      setSynthesis(data.synthesis);
    } catch {
      setSynthesis("Failed to generate synthesis.");
    } finally {
      setSynthLoading(false);
    }
  };

  const industries = stats ? Object.keys(stats.industries) : [];

  return (
    <div className="min-h-screen bg-neutral-50">
      <KnowledgeNav />

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Page title */}
        <div className="flex items-center gap-2 mb-6">
          <Lightbulb className="w-5 h-5 text-brand-500" />
          <h1 className="text-lg font-semibold text-neutral-900">
            {t("Consumer Insights", "\u6d88\u8d39\u8005\u6d1e\u5bdf")}
          </h1>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-xl border border-neutral-200 p-4">
            <p className="text-sm text-neutral-500">{t("Total Insights", "\u603b\u6d1e\u5bdf\u6570")}</p>
            <p className="text-2xl font-semibold text-neutral-900 mt-1">{total}</p>
          </div>
          <div className="bg-white rounded-xl border border-neutral-200 p-4">
            <p className="text-sm text-neutral-500">{t("Industries Covered", "\u8986\u76d6\u884c\u4e1a")}</p>
            <p className="text-2xl font-semibold text-neutral-900 mt-1">{industries.length}</p>
          </div>
          <div className="bg-white rounded-xl border border-neutral-200 p-4">
            <p className="text-sm text-neutral-500">{t("Insight Types", "\u6d1e\u5bdf\u7c7b\u578b")}</p>
            <p className="text-2xl font-semibold text-neutral-900 mt-1">{INSIGHT_TYPES.length}</p>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-6">
          {/* Left: Filters */}
          <div className="col-span-1 space-y-4">
            <div className="bg-white rounded-xl border border-neutral-200 p-4">
              <h3 className="text-sm font-medium text-neutral-700 mb-3 flex items-center gap-2">
                <Filter className="w-4 h-4" /> {t("Filters", "\u7b5b\u9009")}
              </h3>

              <div className="space-y-3">
                <div>
                  <label className="text-xs text-neutral-500 mb-1 block">{t("Industry", "\u884c\u4e1a")}</label>
                  <select
                    value={filterIndustry}
                    onChange={(e) => setFilterIndustry(e.target.value)}
                    className="w-full px-3 py-1.5 text-sm border border-neutral-200 rounded-lg bg-white"
                  >
                    <option value="">{t("All Industries", "\u6240\u6709\u884c\u4e1a")}</option>
                    {industries.map((ind) => (
                      <option key={ind} value={ind}>{ind}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs text-neutral-500 mb-1 block">{t("Insight Type", "\u6d1e\u5bdf\u7c7b\u578b")}</label>
                  <select
                    value={filterType}
                    onChange={(e) => setFilterType(e.target.value)}
                    className="w-full px-3 py-1.5 text-sm border border-neutral-200 rounded-lg bg-white"
                  >
                    <option value="">{t("All Types", "\u6240\u6709\u7c7b\u578b")}</option>
                    {INSIGHT_TYPES.map((t) => (
                      <option key={t} value={t}>{t.replace("_", " ")}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs text-neutral-500 mb-1 block">{t("Market", "\u5e02\u573a")}</label>
                  <select
                    value={filterGeo}
                    onChange={(e) => setFilterGeo(e.target.value)}
                    className="w-full px-3 py-1.5 text-sm border border-neutral-200 rounded-lg bg-white"
                  >
                    <option value="">{t("All Markets", "\u6240\u6709\u5e02\u573a")}</option>
                    {GEO_OPTIONS.map((g) => (
                      <option key={g} value={g}>{g.toUpperCase()}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* AI Synthesis button */}
            <button
              onClick={loadSynthesis}
              disabled={synthLoading}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-brand-500 text-white text-sm rounded-xl hover:bg-brand-600 disabled:opacity-50 transition-colors"
            >
              {synthLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
              {t("AI Synthesis", "AI \u7efc\u5408\u5206\u6790")}
            </button>
          </div>

          {/* Right: Content */}
          <div className="col-span-3 space-y-4">
            {/* Search */}
            <div className="bg-white rounded-xl border border-neutral-200 p-4">
              <div className="flex gap-3">
                <div className="flex-1 relative">
                  <Search className="absolute left-3 top-2.5 w-4 h-4 text-neutral-400" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder={t("Search insights by keyword...", "\u6309\u5173\u952e\u8bcd\u641c\u7d22\u6d1e\u5bdf...")}
                    className="w-full pl-9 pr-3 py-2 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                  />
                </div>
              </div>
            </div>

            {/* Synthesis */}
            {synthesis && (
              <div className="bg-brand-50 border border-brand-200 rounded-xl p-4">
                <h3 className="text-sm font-medium text-brand-700 mb-2 flex items-center gap-2">
                  <Sparkles className="w-4 h-4" /> {t("AI Cross-Case Synthesis", "AI \u8de8\u6848\u4f8b\u7efc\u5408\u5206\u6790")}
                </h3>
                <div className="prose prose-sm max-w-none text-neutral-700">
                  <ReactMarkdown>{synthesis}</ReactMarkdown>
                </div>
              </div>
            )}

            {/* Insights list */}
            {loading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="w-6 h-6 animate-spin text-neutral-400" />
              </div>
            ) : (
              <div className="space-y-3">
                {insights.map((insight) => (
                  <div
                    key={insight.id}
                    className="bg-white rounded-xl border border-neutral-200 p-4 hover:shadow-sm transition-shadow cursor-pointer"
                    onClick={() => setExpandedId(expandedId === insight.id ? null : insight.id)}
                  >
                    <p className="text-sm text-neutral-800 leading-relaxed mb-3">
                      {lang === "en" && insight.text_en ? insight.text_en : insight.text}
                    </p>
                    <div className="flex items-center gap-2 flex-wrap">
                      <Link
                        href={`/knowledge/${insight.case_id}`}
                        onClick={(e) => e.stopPropagation()}
                        className="text-xs px-2 py-0.5 rounded bg-neutral-100 text-brand-600 hover:bg-brand-50 transition-colors"
                      >
                        {insight.brand_name}
                      </Link>
                      <span className="text-xs px-2 py-0.5 rounded bg-neutral-100 text-neutral-600">
                        {insight.industry}
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded ${TYPE_COLORS[insight.type] || "bg-neutral-100 text-neutral-600"}`}>
                        {insight.type.replace("_", " ")}
                      </span>
                      {insight.geo && (
                        <span className="text-xs px-2 py-0.5 rounded bg-neutral-50 text-neutral-500">
                          {insight.geo.toUpperCase()}
                        </span>
                      )}
                      <span className="text-xs text-neutral-400">
                        {insight.confidence} confidence
                      </span>
                    </div>

                    {expandedId === insight.id && (
                      <div className="mt-3 p-3 bg-gray-50 rounded text-sm border-t border-neutral-100">
                        <p><strong>{t("Source", "\u6765\u6e90")}:</strong>{" "}
                          <Link
                            href={`/knowledge/${insight.case_id}`}
                            onClick={(e) => e.stopPropagation()}
                            className="text-brand-600 hover:underline"
                          >
                            {insight.brand_name}
                          </Link>
                        </p>
                        <p><strong>{t("Evidence", "\u8bc1\u636e\u7c7b\u578b")}:</strong> {insight.source}</p>
                        <p><strong>{t("Confidence", "\u7f6e\u4fe1\u5ea6")}:</strong> {insight.confidence}</p>
                        {insight.geo && <p><strong>{t("Market", "\u5e02\u573a")}:</strong> {insight.geo.toUpperCase()}</p>}
                        {insight.segment && <p><strong>{t("Segment", "\u4eba\u7fa4")}:</strong> {insight.segment}</p>}
                      </div>
                    )}
                  </div>
                ))}
                {insights.length === 0 && (
                  <div className="text-center py-12 text-neutral-400 text-sm">
                    No insights found for the current filters.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
