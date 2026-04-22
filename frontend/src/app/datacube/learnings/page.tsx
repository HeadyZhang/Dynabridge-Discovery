"use client";

import { useState, useEffect } from "react";
import { BookOpen, Loader2, RefreshCw } from "lucide-react";
import { dcListLearnings, dcConsolidateLearnings, type DCLearning } from "@/lib/datacube-api";
import KnowledgeNav from "@/components/KnowledgeNav";
import { useLanguage } from "@/lib/language-context";

export default function LearningsPage() {
  const { t } = useLanguage();
  const [learnings, setLearnings] = useState<DCLearning[]>([]);
  const [loading, setLoading] = useState(true);
  const [consolidating, setConsolidating] = useState(false);
  const [brand, setBrand] = useState("AEKE");

  const loadData = () => {
    setLoading(true);
    dcListLearnings(brand).then(setLearnings).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, [brand]);

  const handleConsolidate = async () => {
    setConsolidating(true);
    try { await dcConsolidateLearnings(brand); loadData(); }
    catch { /* silently handle */ }
    finally { setConsolidating(false); }
  };

  return (
    <div className="min-h-screen bg-neutral-50">
      <KnowledgeNav />
      <div className="max-w-5xl mx-auto px-6 py-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-brand-500" />
            <h1 className="text-lg font-semibold text-neutral-900">{t("Cumulative Learnings", "\u7d2f\u79ef\u77e5\u8bc6")}</h1>
          </div>
          <div className="flex items-center gap-3">
            <input value={brand} onChange={(e) => setBrand(e.target.value)} className="px-3 py-1.5 text-sm border border-neutral-200 rounded-lg w-32" />
            <button onClick={handleConsolidate} disabled={consolidating} className="flex items-center gap-2 px-4 py-2 bg-brand-500 text-white text-sm rounded-xl hover:bg-brand-600 disabled:opacity-50">
              {consolidating ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              {t("Consolidate", "\u6c89\u6dc0\u77e5\u8bc6")}
            </button>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20"><Loader2 className="w-6 h-6 animate-spin text-neutral-400" /></div>
        ) : learnings.length === 0 ? (
          <div className="text-center py-20 text-neutral-400 text-sm">{t("No learnings yet. Generate insights first, then consolidate.", "\u6682\u65e0\u7d2f\u79ef\u77e5\u8bc6\u3002\u8bf7\u5148\u751f\u6210\u6d1e\u5bdf\uff0c\u518d\u6c89\u6dc0\u3002")}</div>
        ) : (
          <div className="space-y-4">
            {learnings.map((le) => (
              <div key={le.id} className="bg-white rounded-xl border border-neutral-200 p-5">
                <div className="flex items-start justify-between mb-2">
                  <p className="text-sm text-neutral-800 leading-relaxed flex-1">{le.principle}</p>
                  <span className="text-xs px-2 py-0.5 rounded bg-brand-50 text-brand-600 shrink-0 ml-3">
                    {le.evidence_count}x {t("validated", "\u5df2\u9a8c\u8bc1")}
                  </span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {le.applicable_audiences.map((a) => <span key={a} className="text-[10px] px-1.5 py-0.5 rounded bg-violet-50 text-violet-600">{a}</span>)}
                  {le.applicable_content.map((c) => <span key={c} className="text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-600">{c}</span>)}
                  {le.applicable_channels.map((ch) => <span key={ch} className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-600">{ch}</span>)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
