"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Loader2, Tag } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { dcGetCampaign, type DCCampaignDetail } from "@/lib/datacube-api";
import KnowledgeNav from "@/components/KnowledgeNav";
import { useLanguage } from "@/lib/language-context";

export default function CampaignDetailPage() {
  const { t } = useLanguage();
  const params = useParams();
  const [data, setData] = useState<DCCampaignDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dcGetCampaign(String(params.id)).then(setData).catch(() => {}).finally(() => setLoading(false));
  }, [params.id]);

  if (loading) return <div className="min-h-screen bg-neutral-50"><KnowledgeNav /><div className="flex items-center justify-center py-20"><Loader2 className="w-6 h-6 animate-spin text-neutral-400" /></div></div>;
  if (!data) return <div className="min-h-screen bg-neutral-50"><KnowledgeNav /><div className="text-center py-20 text-neutral-500">Campaign not found</div></div>;

  const tagBadge = (label: string, value: string, color: string) => value ? (
    <span className={`text-xs px-2 py-0.5 rounded ${color}`}>{label}: {value}</span>
  ) : null;

  return (
    <div className="min-h-screen bg-neutral-50">
      <KnowledgeNav />
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="flex items-center gap-3 mb-6">
          <Link href="/datacube/campaigns" className="text-neutral-400 hover:text-neutral-600"><ArrowLeft className="w-5 h-5" /></Link>
          <h1 className="text-lg font-semibold text-neutral-900">{data.campaign_name}</h1>
          <span className="text-sm text-neutral-400">{data.brand_name}</span>
        </div>

        {/* Tags */}
        <div className="bg-white rounded-xl border border-neutral-200 p-5 mb-6">
          <h2 className="text-sm font-medium text-neutral-700 mb-3 flex items-center gap-2"><Tag className="w-4 h-4" /> {t("Tags", "\u6807\u7b7e")}</h2>
          <div className="flex flex-wrap gap-2">
            {Object.entries(data.audience).map(([k, v]) => tagBadge(k, v, "bg-violet-50 text-violet-600"))}
            {Object.entries(data.content).map(([k, v]) => tagBadge(k, v, "bg-amber-50 text-amber-600"))}
            {Object.entries(data.context).map(([k, v]) => tagBadge(k, v, "bg-blue-50 text-blue-600"))}
          </div>
        </div>

        {/* Performance chart */}
        {data.performances.length > 0 && (
          <div className="bg-white rounded-xl border border-neutral-200 p-5 mb-6">
            <h2 className="text-sm font-medium text-neutral-700 mb-3">{t("Performance", "\u6548\u679c\u6570\u636e")}</h2>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.performances}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(v: string) => v ? v.slice(5, 10) : ""} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="impressions" stroke="#f97316" strokeWidth={2} dot={false} name="Impressions" />
                  <Line type="monotone" dataKey="revenue" stroke="#10b981" strokeWidth={2} dot={false} name="Revenue" />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="grid grid-cols-4 gap-4 mt-4">
              {[
                { label: t("Total Impressions", "\u603b\u66dd\u5149"), value: data.performances.reduce((s, p) => s + p.impressions, 0).toLocaleString() },
                { label: t("Total Revenue", "\u603b\u6536\u5165"), value: `$${data.performances.reduce((s, p) => s + p.revenue, 0).toLocaleString()}` },
                { label: t("Total Cost", "\u603b\u6210\u672c"), value: `$${data.performances.reduce((s, p) => s + p.cost, 0).toLocaleString()}` },
                { label: "ROAS", value: `${(data.performances.reduce((s, p) => s + p.revenue, 0) / (data.performances.reduce((s, p) => s + p.cost, 0) || 1)).toFixed(1)}x` },
              ].map((m) => (
                <div key={m.label} className="text-center">
                  <p className="text-xs text-neutral-500">{m.label}</p>
                  <p className="text-lg font-semibold text-neutral-900">{m.value}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Related insights */}
        {data.insights.length > 0 && (
          <div className="bg-white rounded-xl border border-neutral-200 p-5">
            <h2 className="text-sm font-medium text-neutral-700 mb-3">{t("Related Insights", "\u76f8\u5173\u6d1e\u5bdf")}</h2>
            <div className="space-y-2">
              {data.insights.map((ins) => (
                <div key={ins.id} className="p-3 rounded-lg bg-neutral-50">
                  <p className="text-sm text-neutral-800">{ins.finding}</p>
                  <span className={`text-xs px-2 py-0.5 rounded mt-1 inline-block ${ins.action_type === "scale" ? "bg-green-50 text-green-600" : ins.action_type === "stop" ? "bg-red-50 text-red-600" : "bg-blue-50 text-blue-600"}`}>
                    {ins.action_type}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
