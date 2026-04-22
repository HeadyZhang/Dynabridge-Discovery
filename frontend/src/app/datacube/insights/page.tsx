"use client";

import { useState, useEffect } from "react";
import { Sparkles, Loader2, ArrowUpCircle, StopCircle, FlaskConical } from "lucide-react";
import { dcListInsights, dcGenerateInsights, dcGetRecommendations, type DCInsight } from "@/lib/datacube-api";
import KnowledgeNav from "@/components/KnowledgeNav";
import { useLanguage } from "@/lib/language-context";

const ACTION_CONFIG = {
  scale: { icon: ArrowUpCircle, color: "border-green-200 bg-green-50", badge: "bg-green-100 text-green-700", label_en: "Scale", label_cn: "\u6269\u5927" },
  stop: { icon: StopCircle, color: "border-red-200 bg-red-50", badge: "bg-red-100 text-red-700", label_en: "Stop", label_cn: "\u505c\u6b62" },
  test: { icon: FlaskConical, color: "border-blue-200 bg-blue-50", badge: "bg-blue-100 text-blue-700", label_en: "Test", label_cn: "\u6d4b\u8bd5" },
};

export default function InsightsPage() {
  const { t } = useLanguage();
  const [recs, setRecs] = useState<{ scale: DCInsight[]; stop: DCInsight[]; test: DCInsight[] }>({ scale: [], stop: [], test: [] });
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [brand, setBrand] = useState("AEKE");

  const loadData = () => {
    setLoading(true);
    dcGetRecommendations(brand).then(setRecs).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, [brand]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await dcGenerateInsights(brand);
      loadData();
    } catch { /* silently handle */ }
    finally { setGenerating(false); }
  };

  return (
    <div className="min-h-screen bg-neutral-50">
      <KnowledgeNav />
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-lg font-semibold text-neutral-900">{t("AI Insights", "AI \u6d1e\u5bdf")}</h1>
          <div className="flex items-center gap-3">
            <input value={brand} onChange={(e) => setBrand(e.target.value)} placeholder="Brand" className="px-3 py-1.5 text-sm border border-neutral-200 rounded-lg w-32" />
            <button onClick={handleGenerate} disabled={generating} className="flex items-center gap-2 px-4 py-2 bg-brand-500 text-white text-sm rounded-xl hover:bg-brand-600 disabled:opacity-50">
              {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
              {t("Generate Insights", "\u751f\u6210\u6d1e\u5bdf")}
            </button>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20"><Loader2 className="w-6 h-6 animate-spin text-neutral-400" /></div>
        ) : (
          <div className="grid grid-cols-3 gap-4">
            {(["scale", "stop", "test"] as const).map((type) => {
              const config = ACTION_CONFIG[type];
              const Icon = config.icon;
              return (
                <div key={type}>
                  <h2 className="text-sm font-medium text-neutral-700 mb-3 flex items-center gap-2">
                    <Icon className="w-4 h-4" /> {t(config.label_en, config.label_cn)} ({recs[type].length})
                  </h2>
                  <div className="space-y-3">
                    {recs[type].map((ins) => (
                      <div key={ins.id} className={`rounded-xl border p-4 ${config.color}`}>
                        <p className="text-sm text-neutral-800 mb-2">{ins.finding}</p>
                        {ins.action_recommendation && (
                          <p className="text-xs text-neutral-600 mb-2">{ins.action_recommendation}</p>
                        )}
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] px-2 py-0.5 rounded ${config.badge}`}>{ins.action_type}</span>
                          <span className="text-[10px] px-2 py-0.5 rounded bg-neutral-100 text-neutral-500">{ins.confidence}</span>
                        </div>
                      </div>
                    ))}
                    {recs[type].length === 0 && (
                      <p className="text-sm text-neutral-400 text-center py-6">{t("No insights", "\u6682\u65e0\u6d1e\u5bdf")}</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
