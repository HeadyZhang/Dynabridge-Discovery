"use client";

import { useState } from "react";
import { Sparkles, Loader2, Target } from "lucide-react";
import { dcPlanCampaign } from "@/lib/datacube-api";
import KnowledgeNav from "@/components/KnowledgeNav";
import { useLanguage } from "@/lib/language-context";

export default function PlanPage() {
  const { t } = useLanguage();
  const [form, setForm] = useState({ brand: "AEKE", objective: "", budget: "50000", target_audience: "self_disciplined_achiever" });
  const [plan, setPlan] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);

  const handlePlan = async () => {
    setLoading(true);
    try {
      const result = await dcPlanCampaign({ ...form, budget: Number(form.budget) });
      setPlan(result);
    } catch { /* silently handle */ }
    finally { setLoading(false); }
  };

  const renderSection = (title: string, data: unknown) => {
    if (!data || typeof data !== "object") return null;
    return (
      <div className="bg-white rounded-xl border border-neutral-200 p-5">
        <h3 className="text-sm font-medium text-neutral-700 mb-3">{title}</h3>
        <pre className="text-xs text-neutral-600 whitespace-pre-wrap bg-neutral-50 rounded-lg p-3">
          {JSON.stringify(data, null, 2)}
        </pre>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-neutral-50">
      <KnowledgeNav />
      <div className="max-w-5xl mx-auto px-6 py-6">
        <div className="flex items-center gap-2 mb-6">
          <Target className="w-5 h-5 text-brand-500" />
          <h1 className="text-lg font-semibold text-neutral-900">{t("Campaign Planner", "\u6d3b\u52a8\u89c4\u5212\u52a9\u624b")}</h1>
        </div>

        <div className="grid grid-cols-3 gap-6">
          <div className="col-span-1">
            <div className="bg-white rounded-xl border border-neutral-200 p-5 space-y-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">{t("Brand", "\u54c1\u724c")}</label>
                <input value={form.brand} onChange={(e) => setForm({ ...form, brand: e.target.value })} className="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">{t("Objective", "\u76ee\u6807")}</label>
                <input value={form.objective} onChange={(e) => setForm({ ...form, objective: e.target.value })} placeholder={t("e.g. Q2 awareness campaign", "\u5982: Q2 \u54c1\u724c\u77e5\u540d\u5ea6\u6d3b\u52a8")} className="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">{t("Budget ($)", "\u9884\u7b97 ($)")}</label>
                <input value={form.budget} onChange={(e) => setForm({ ...form, budget: e.target.value })} type="number" className="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">{t("Target Audience", "\u76ee\u6807\u53d7\u4f17")}</label>
                <input value={form.target_audience} onChange={(e) => setForm({ ...form, target_audience: e.target.value })} className="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm" />
              </div>
              <button onClick={handlePlan} disabled={loading || !form.brand} className="w-full py-3 bg-brand-500 text-white font-medium rounded-xl hover:bg-brand-600 disabled:opacity-50 flex items-center justify-center gap-2">
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                {t("Generate Plan", "\u751f\u6210\u8ba1\u5212")}
              </button>
            </div>
          </div>

          <div className="col-span-2 space-y-4">
            {loading && (
              <div className="flex items-center justify-center py-20">
                <div className="text-center">
                  <Loader2 className="w-8 h-8 animate-spin text-brand-500 mx-auto mb-3" />
                  <p className="text-sm text-neutral-500">{t("Analyzing learnings and trends...", "\u5206\u6790\u7d2f\u79ef\u77e5\u8bc6\u548c\u8d8b\u52bf...")}</p>
                </div>
              </div>
            )}

            {plan && !loading && (
              <>
                {plan.executive_summary && (
                  <div className="bg-brand-50 rounded-xl border border-brand-200 p-5">
                    <p className="text-sm text-neutral-800 leading-relaxed">{String(plan.executive_summary)}</p>
                  </div>
                )}
                {renderSection(t("Channel Allocation", "\u6e20\u9053\u5206\u914d"), plan.channel_allocation || plan.recommended_plan)}
                {renderSection(t("Content Recommendations", "\u5185\u5bb9\u5efa\u8bae"), plan.content_recommendations)}
                {renderSection(t("What to Test", "\u5efa\u8bae\u6d4b\u8bd5"), plan.what_to_test)}
                {plan.past_learnings_applied && renderSection(t("Applied Learnings", "\u5e94\u7528\u7684\u7d2f\u79ef\u77e5\u8bc6"), plan.past_learnings_applied)}
              </>
            )}

            {!plan && !loading && (
              <div className="text-center py-20 text-neutral-400 text-sm">
                {t("Fill in the form and click Generate Plan", "\u586b\u5199\u8868\u5355\u5e76\u70b9\u51fb\u751f\u6210\u8ba1\u5212")}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
