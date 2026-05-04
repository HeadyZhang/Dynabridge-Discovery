"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Plus, Loader2, BarChart3 } from "lucide-react";
import { dcListCampaigns, type DCCampaign } from "@/lib/datacube-api";
import KnowledgeNav from "@/components/KnowledgeNav";
import { useLanguage } from "@/lib/language-context";

export default function CampaignsPage() {
  const { t } = useLanguage();
  const [campaigns, setCampaigns] = useState<DCCampaign[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dcListCampaigns().then(setCampaigns).catch(() => {}).finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-neutral-50">
      <KnowledgeNav />
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-brand-500" />
            <h1 className="text-lg font-semibold text-neutral-900">{t("Campaigns", "\u8425\u9500\u6d3b\u52a8")}</h1>
          </div>
          <Link href="/datacube/campaigns/new" className="flex items-center gap-1.5 px-4 py-2 bg-brand-500 text-white text-sm rounded-xl hover:bg-brand-600 transition-colors">
            <Plus className="w-4 h-4" /> {t("New Campaign", "\u65b0\u5efa\u6d3b\u52a8")}
          </Link>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-6 h-6 animate-spin text-neutral-400" />
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-neutral-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-neutral-50">
                <tr className="text-left text-neutral-500">
                  <th className="px-4 py-3 font-medium">{t("Campaign", "\u6d3b\u52a8")}</th>
                  <th className="px-4 py-3 font-medium">{t("Brand", "\u54c1\u724c")}</th>
                  <th className="px-4 py-3 font-medium">{t("Channel", "\u6e20\u9053")}</th>
                  <th className="px-4 py-3 font-medium">{t("Audience", "\u53d7\u4f17")}</th>
                  <th className="px-4 py-3 font-medium">{t("Content", "\u5185\u5bb9")}</th>
                  <th className="px-4 py-3 font-medium text-right">{t("Impressions", "\u66dd\u5149")}</th>
                  <th className="px-4 py-3 font-medium text-right">ROAS</th>
                </tr>
              </thead>
              <tbody>
                {campaigns.map((c) => (
                  <tr key={c.id} className="border-t border-neutral-100 hover:bg-neutral-50">
                    <td className="px-4 py-3">
                      <Link href={`/datacube/campaigns/${c.id}`} className="text-brand-600 hover:underline font-medium">
                        {c.campaign_name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-neutral-600">{c.brand_name}</td>
                    <td className="px-4 py-3"><span className="text-xs px-2 py-0.5 rounded bg-blue-50 text-blue-600">{c.channel}</span></td>
                    <td className="px-4 py-3"><span className="text-xs px-2 py-0.5 rounded bg-violet-50 text-violet-600">{c.audience}</span></td>
                    <td className="px-4 py-3"><span className="text-xs px-2 py-0.5 rounded bg-amber-50 text-amber-600">{c.content_theme}</span></td>
                    <td className="px-4 py-3 text-right text-neutral-600">{c.impressions.toLocaleString()}</td>
                    <td className="px-4 py-3 text-right font-semibold text-brand-600">{c.roas}x</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {campaigns.length === 0 && (
              <div className="text-center py-12 text-neutral-400 text-sm">{t("No campaigns yet.", "\u6682\u65e0\u6d3b\u52a8\u6570\u636e\u3002")}</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
