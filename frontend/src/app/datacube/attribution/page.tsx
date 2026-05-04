"use client";

import { useState, useEffect } from "react";
import { Search, Loader2, TrendingUp, TrendingDown } from "lucide-react";
import { dcGetAttribution, dcGetTagOptions, type DCAttribution, type TagOptions } from "@/lib/datacube-api";
import KnowledgeNav from "@/components/KnowledgeNav";
import { useLanguage } from "@/lib/language-context";

export default function AttributionPage() {
  const { t } = useLanguage();
  const [tags, setTags] = useState<TagOptions | null>(null);
  const [audience, setAudience] = useState("");
  const [contentTheme, setContentTheme] = useState("");
  const [channel, setChannel] = useState("");
  const [result, setResult] = useState<DCAttribution | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { dcGetTagOptions().then(setTags).catch(() => {}); }, []);

  const handleSearch = async () => {
    setLoading(true);
    try {
      const data = await dcGetAttribution({ audience: audience || undefined, content_theme: contentTheme || undefined, channel: channel || undefined });
      setResult(data);
    } catch { /* silently handle */ }
    finally { setLoading(false); }
  };

  const DiffBadge = ({ value, label }: { value: number; label: string }) => {
    const positive = value >= 0;
    return (
      <div className="flex items-center gap-2 p-3 rounded-lg bg-neutral-50">
        {positive ? <TrendingUp className="w-4 h-4 text-green-500" /> : <TrendingDown className="w-4 h-4 text-red-500" />}
        <div>
          <span className={`text-sm font-semibold ${positive ? "text-green-600" : "text-red-600"}`}>{positive ? "+" : ""}{value}</span>
          <p className="text-xs text-neutral-500">{label}</p>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-neutral-50">
      <KnowledgeNav />
      <div className="max-w-7xl mx-auto px-6 py-6">
        <h1 className="text-lg font-semibold text-neutral-900 mb-6">{t("Attribution Analysis", "\u5f52\u56e0\u5206\u6790")}</h1>

        {/* Filters */}
        <div className="bg-white rounded-xl border border-neutral-200 p-5 mb-6">
          <div className="grid grid-cols-4 gap-3">
            <select value={audience} onChange={(e) => setAudience(e.target.value)} className="px-3 py-2 text-sm border border-neutral-200 rounded-lg">
              <option value="">{t("All Audiences", "\u6240\u6709\u53d7\u4f17")}</option>
              {tags?.audience.segment?.map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
            <select value={contentTheme} onChange={(e) => setContentTheme(e.target.value)} className="px-3 py-2 text-sm border border-neutral-200 rounded-lg">
              <option value="">{t("All Content", "\u6240\u6709\u5185\u5bb9")}</option>
              {tags?.content.theme?.map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
            <select value={channel} onChange={(e) => setChannel(e.target.value)} className="px-3 py-2 text-sm border border-neutral-200 rounded-lg">
              <option value="">{t("All Channels", "\u6240\u6709\u6e20\u9053")}</option>
              {tags?.context.channel?.map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
            <button onClick={handleSearch} disabled={loading} className="flex items-center justify-center gap-2 px-4 py-2 bg-brand-500 text-white text-sm rounded-lg hover:bg-brand-600 disabled:opacity-50">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              {t("Analyze", "\u5206\u6790")}
            </button>
          </div>
        </div>

        {result && (
          <div className="space-y-4">
            <div className="bg-white rounded-xl border border-neutral-200 p-5">
              <p className="text-sm text-neutral-500 mb-4">{t("Matched", "\u5339\u914d")} <span className="font-semibold text-neutral-900">{result.campaigns_matched}</span> {t("campaigns", "\u4e2a\u6d3b\u52a8")}</p>
              <div className="grid grid-cols-4 gap-4">
                {[
                  { label: t("Impressions", "\u66dd\u5149"), value: result.aggregate_performance.total_impressions.toLocaleString() },
                  { label: t("Revenue", "\u6536\u5165"), value: `$${result.aggregate_performance.total_revenue.toLocaleString()}` },
                  { label: t("Engagement Rate", "\u4e92\u52a8\u7387"), value: `${result.aggregate_performance.avg_engagement_rate}%` },
                  { label: "ROAS", value: `${result.aggregate_performance.avg_roas}x` },
                ].map((m) => (
                  <div key={m.label} className="bg-neutral-50 rounded-lg p-4 text-center">
                    <p className="text-xs text-neutral-500">{m.label}</p>
                    <p className="text-xl font-semibold text-neutral-900 mt-1">{m.value}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white rounded-xl border border-neutral-200 p-5">
              <h3 className="text-sm font-medium text-neutral-700 mb-3">{t("vs. Average", "\u4e0e\u5e73\u5747\u503c\u5bf9\u6bd4")}</h3>
              <div className="grid grid-cols-2 gap-4">
                <DiffBadge value={result.vs_average.engagement_rate_diff} label={t("Engagement Rate vs Avg", "\u4e92\u52a8\u7387 vs \u5e73\u5747")} />
                <DiffBadge value={result.vs_average.roas_diff} label={t("ROAS vs Avg", "ROAS vs \u5e73\u5747")} />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
