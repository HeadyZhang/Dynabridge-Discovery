"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Box, TrendingUp, Users, BarChart3, Lightbulb, Loader2 } from "lucide-react";
import { dcGetStats, dcListInsights, type DCStats, type DCInsight } from "@/lib/datacube-api";
import KnowledgeNav from "@/components/KnowledgeNav";
import { useLanguage } from "@/lib/language-context";

export default function DatacubeDashboard() {
  const { t } = useLanguage();
  const [stats, setStats] = useState<DCStats | null>(null);
  const [insights, setInsights] = useState<DCInsight[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([dcGetStats(), dcListInsights({ brand: undefined })])
      .then(([s, i]) => { setStats(s); setInsights(i.slice(0, 5)); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-50">
        <KnowledgeNav />
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 animate-spin text-neutral-400" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-50">
      <KnowledgeNav />
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="flex items-center gap-2 mb-6">
          <Box className="w-5 h-5 text-brand-500" />
          <h1 className="text-lg font-semibold text-neutral-900">Datacube</h1>
          <span className="text-sm text-neutral-400">{t("Decision-Making Engine", "\u51b3\u7b56\u5f15\u64ce")}</span>
        </div>

        {/* Key Metrics */}
        {stats && (
          <div className="grid grid-cols-4 gap-4 mb-6">
            {[
              { label: t("Campaigns", "\u8425\u9500\u6d3b\u52a8"), value: stats.campaigns_count },
              { label: t("Total Revenue", "\u603b\u6536\u5165"), value: `$${stats.total_revenue.toLocaleString()}` },
              { label: t("Avg ROAS", "\u5e73\u5747 ROAS"), value: `${stats.avg_roas}x` },
              { label: t("Total Impressions", "\u603b\u66dd\u5149"), value: stats.total_impressions.toLocaleString() },
            ].map((s) => (
              <div key={s.label} className="bg-white rounded-xl border border-neutral-200 p-4">
                <p className="text-sm text-neutral-500">{s.label}</p>
                <p className="text-2xl font-semibold text-neutral-900 mt-1">{s.value}</p>
              </div>
            ))}
          </div>
        )}

        {/* Four core questions */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          {[
            { icon: TrendingUp, q: t("What works?", "\u4ec0\u4e48\u6709\u6548\uff1f"), desc: t("Top performing content types", "\u6548\u679c\u6700\u597d\u7684\u5185\u5bb9\u7c7b\u578b"), href: "/datacube/attribution" },
            { icon: Users, q: t("For whom?", "\u9488\u5bf9\u8c01\uff1f"), desc: t("Best audience-content matches", "\u6700\u4f73\u53d7\u4f17-\u5185\u5bb9\u5339\u914d"), href: "/datacube/attribution" },
            { icon: BarChart3, q: t("In which channels?", "\u54ea\u4e2a\u6e20\u9053\uff1f"), desc: t("Channel ROAS ranking", "\u6e20\u9053 ROAS \u6392\u540d"), href: "/datacube/attribution" },
            { icon: Lightbulb, q: t("Why?", "\u4e3a\u4ec0\u4e48\uff1f"), desc: t("AI-powered explanations", "AI \u667a\u80fd\u89e3\u91ca"), href: "/datacube/insights" },
          ].map(({ icon: Icon, q, desc, href }) => (
            <Link key={q} href={href}>
              <div className="bg-white rounded-xl border border-neutral-200 p-5 hover:shadow-md hover:border-brand-300 transition-all cursor-pointer group">
                <div className="flex items-center gap-3 mb-2">
                  <Icon className="w-5 h-5 text-brand-500" />
                  <h3 className="font-semibold text-neutral-900 group-hover:text-brand-500">{q}</h3>
                </div>
                <p className="text-sm text-neutral-500">{desc}</p>
              </div>
            </Link>
          ))}
        </div>

        {/* Top channels */}
        {stats && stats.top_channels.length > 0 && (
          <div className="bg-white rounded-xl border border-neutral-200 p-5 mb-6">
            <h2 className="text-sm font-medium text-neutral-700 mb-3">{t("Top Channels by ROAS", "\u6e20\u9053 ROAS \u6392\u540d")}</h2>
            <div className="space-y-2">
              {stats.top_channels.map((ch) => (
                <div key={ch.channel} className="flex items-center justify-between py-2 border-b border-neutral-50">
                  <span className="text-sm font-medium text-neutral-800">{ch.channel}</span>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="text-neutral-500">{ch.campaigns} {t("campaigns", "\u4e2a\u6d3b\u52a8")}</span>
                    <span className="text-neutral-500">${ch.revenue.toLocaleString()}</span>
                    <span className="font-semibold text-brand-600">{ch.roas.toFixed(1)}x ROAS</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Quick links */}
        <div className="grid grid-cols-4 gap-4">
          {[
            { href: "/datacube/campaigns", label: t("Campaigns", "\u6d3b\u52a8\u5217\u8868") },
            { href: "/datacube/import", label: t("Import Data", "\u5bfc\u5165\u6570\u636e") },
            { href: "/datacube/insights", label: t("AI Insights", "AI \u6d1e\u5bdf") },
            { href: "/datacube/plan", label: t("Plan Campaign", "\u89c4\u5212\u6d3b\u52a8") },
          ].map((link) => (
            <Link key={link.href} href={link.href}>
              <div className="bg-white rounded-xl border border-neutral-200 p-4 text-center hover:shadow-md hover:border-brand-300 transition-all cursor-pointer">
                <p className="text-sm font-medium text-brand-600">{link.label}</p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
