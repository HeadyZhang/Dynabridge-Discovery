"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft, Building2, Lightbulb, Sparkles, Loader2, FileText,
  CheckCircle2, XCircle,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import {
  getIndustryDetail, getIndustryReport, type IndustryDetail,
} from "@/lib/knowledge-api";
import KnowledgeNav from "@/components/KnowledgeNav";
import { useLanguage } from "@/lib/language-context";

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

export default function IndustryDetailPage() {
  const { t } = useLanguage();
  const params = useParams();
  const industry = decodeURIComponent(String(params.industry));

  const [detail, setDetail] = useState<IndustryDetail | null>(null);
  const [report, setReport] = useState("");
  const [reportLoading, setReportLoading] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getIndustryDetail(industry)
      .then(setDetail)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [industry]);

  const handleGenerateReport = async () => {
    setReportLoading(true);
    try {
      const data = await getIndustryReport(industry);
      setReport(data.report);
    } catch {
      setReport("Failed to generate report.");
    } finally {
      setReportLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-neutral-400" />
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <p className="text-neutral-500">Industry not found.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-50">
      <KnowledgeNav />

      {/* Sub-header */}
      <div className="bg-white border-b border-neutral-100 px-6 py-3">
        <div className="max-w-7xl mx-auto flex items-center gap-3">
          <Link href="/industries" className="text-neutral-400 hover:text-neutral-600">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <Building2 className="w-5 h-5 text-brand-500" />
          <h1 className="text-lg font-semibold text-neutral-900 capitalize">
            {industry.replace("_", " ")} {t("Industry", "\u884c\u4e1a")}
          </h1>
          <span className="text-sm text-neutral-400">
            {detail.cases.length} {t("brands", "\u4e2a\u54c1\u724c")} | {detail.total_insights} {t("insights", "\u6761\u6d1e\u5bdf")}
          </span>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        {/* Cases table */}
        <div className="bg-white rounded-xl border border-neutral-200 p-5">
          <h2 className="text-sm font-medium text-neutral-700 mb-4">{t("Brand Cases", "\u54c1\u724c\u6848\u4f8b")}</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-100 text-left text-neutral-500">
                  <th className="pb-2 font-medium">Brand</th>
                  <th className="pb-2 font-medium">Completeness</th>
                  <th className="pb-2 font-medium">Discovery</th>
                  <th className="pb-2 font-medium">Strategy</th>
                  <th className="pb-2 font-medium">Challenges</th>
                </tr>
              </thead>
              <tbody>
                {detail.cases.map((c) => (
                  <tr key={c.id} className="border-b border-neutral-50 hover:bg-neutral-50">
                    <td className="py-2.5">
                      <Link href={`/knowledge/${c.id}`} className="text-brand-600 hover:underline font-medium">
                        {c.brand}
                      </Link>
                    </td>
                    <td className="py-2.5">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                          <div className="h-full bg-brand-500 rounded-full" style={{ width: `${c.completeness * 100}%` }} />
                        </div>
                        <span className="text-xs text-neutral-500">{Math.round(c.completeness * 100)}%</span>
                      </div>
                    </td>
                    <td className="py-2.5">
                      {c.has_discovery ? (
                        <CheckCircle2 className="w-4 h-4 text-green-500" />
                      ) : (
                        <XCircle className="w-4 h-4 text-neutral-300" />
                      )}
                    </td>
                    <td className="py-2.5">
                      {c.has_strategy ? (
                        <CheckCircle2 className="w-4 h-4 text-green-500" />
                      ) : (
                        <XCircle className="w-4 h-4 text-neutral-300" />
                      )}
                    </td>
                    <td className="py-2.5">
                      <div className="flex flex-wrap gap-1">
                        {c.challenges.slice(0, 2).map((ch, i) => (
                          <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-red-50 text-red-600">
                            {typeof ch === "string" ? ch.slice(0, 30) : ""}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* AI Report */}
        <div className="bg-white rounded-xl border border-neutral-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-medium text-neutral-700 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-brand-500" />
              {t("AI Industry Experience Report", "AI \u884c\u4e1a\u7ecf\u9a8c\u62a5\u544a")}
            </h2>
            <button
              onClick={handleGenerateReport}
              disabled={reportLoading}
              className="flex items-center gap-2 px-4 py-2 bg-brand-500 text-white text-sm rounded-xl hover:bg-brand-600 disabled:opacity-50 transition-colors"
            >
              {reportLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
              {t("Generate Report", "\u751f\u6210\u62a5\u544a")}
            </button>
          </div>
          {report ? (
            <div className="prose prose-sm max-w-none text-neutral-700 bg-neutral-50 rounded-lg p-4 max-h-[600px] overflow-y-auto">
              <ReactMarkdown>{report}</ReactMarkdown>
            </div>
          ) : (
            <p className="text-sm text-neutral-400">
              Click &quot;Generate Report&quot; to create an AI-powered industry analysis.
            </p>
          )}
        </div>

        {/* Insights */}
        <div className="bg-white rounded-xl border border-neutral-200 p-5">
          <h2 className="text-sm font-medium text-neutral-700 mb-4 flex items-center gap-2">
            <Lightbulb className="w-4 h-4 text-brand-500" />
            Consumer Insights ({detail.total_insights})
          </h2>
          <div className="space-y-2">
            {detail.insights.map((ins, i) => (
              <div key={i} className="flex items-start gap-3 p-3 rounded-lg hover:bg-neutral-50">
                <FileText className="w-4 h-4 text-neutral-400 mt-0.5 shrink-0" />
                <div className="min-w-0">
                  <p className="text-sm text-neutral-800">{ins.text}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs px-2 py-0.5 rounded bg-brand-50 text-brand-600">
                      {ins.brand}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded ${TYPE_COLORS[ins.type] || "bg-neutral-100 text-neutral-600"}`}>
                      {ins.type.replace("_", " ")}
                    </span>
                  </div>
                </div>
              </div>
            ))}
            {detail.insights.length === 0 && (
              <p className="text-sm text-neutral-400 text-center py-6">
                No insights extracted for this industry yet.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
