"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Building2, ArrowRight, Lightbulb, Database, Loader2, Tag,
} from "lucide-react";
import { getIndustries, type IndustryOverview } from "@/lib/knowledge-api";

export default function IndustriesPage() {
  const [industries, setIndustries] = useState<IndustryOverview>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getIndustries()
      .then(setIndustries)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const sorted = Object.entries(industries).sort(
    ([, a], [, b]) => b.case_count - a.case_count,
  );

  return (
    <div className="min-h-screen bg-neutral-50">
      <header className="bg-white border-b border-neutral-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/knowledge" className="text-neutral-400 hover:text-neutral-600 text-sm">
              Knowledge Base
            </Link>
            <span className="text-neutral-300">/</span>
            <div className="flex items-center gap-2">
              <Building2 className="w-5 h-5 text-brand-500" />
              <h1 className="text-lg font-semibold text-neutral-900">Industry Intelligence</h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/insights" className="px-3 py-1.5 text-sm text-neutral-600 hover:text-brand-500 hover:bg-brand-50 rounded-lg transition-colors">
              Insights
            </Link>
            <Link href="/marketing" className="px-3 py-1.5 text-sm text-neutral-600 hover:text-brand-500 hover:bg-brand-50 rounded-lg transition-colors">
              Marketing
            </Link>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-xl border border-neutral-200 p-4">
            <p className="text-sm text-neutral-500">Industries</p>
            <p className="text-2xl font-semibold text-neutral-900 mt-1">{sorted.length}</p>
          </div>
          <div className="bg-white rounded-xl border border-neutral-200 p-4">
            <p className="text-sm text-neutral-500">Total Brands</p>
            <p className="text-2xl font-semibold text-neutral-900 mt-1">
              {sorted.reduce((sum, [, v]) => sum + v.case_count, 0)}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-neutral-200 p-4">
            <p className="text-sm text-neutral-500">Total Insights</p>
            <p className="text-2xl font-semibold text-neutral-900 mt-1">
              {sorted.reduce((sum, [, v]) => sum + v.insights_count, 0)}
            </p>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-6 h-6 animate-spin text-neutral-400" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {sorted.map(([industry, data]) => (
              <Link key={industry} href={`/industries/${encodeURIComponent(industry)}`}>
                <div className="bg-white rounded-xl border border-neutral-200 p-5 hover:shadow-md hover:border-brand-300 transition-all cursor-pointer group">
                  <div className="flex items-start justify-between mb-3">
                    <h3 className="font-semibold text-neutral-900 group-hover:text-brand-500 transition-colors capitalize">
                      {industry.replace("_", " ")}
                    </h3>
                    <ArrowRight className="w-4 h-4 text-neutral-300 group-hover:text-brand-500 transition-colors" />
                  </div>

                  <div className="flex items-center gap-4 text-sm text-neutral-500 mb-3">
                    <span className="flex items-center gap-1">
                      <Database className="w-3.5 h-3.5" /> {data.case_count} cases
                    </span>
                    <span className="flex items-center gap-1">
                      <Lightbulb className="w-3.5 h-3.5" /> {data.insights_count} insights
                    </span>
                  </div>

                  <div className="flex flex-wrap gap-1 mb-3">
                    {data.brands.slice(0, 4).map((brand) => (
                      <span key={brand} className="text-[10px] px-2 py-0.5 rounded bg-brand-50 text-brand-600">
                        {brand}
                      </span>
                    ))}
                    {data.brands.length > 4 && (
                      <span className="text-[10px] px-2 py-0.5 rounded bg-neutral-100 text-neutral-500">
                        +{data.brands.length - 4} more
                      </span>
                    )}
                  </div>

                  {data.challenges.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {data.challenges.slice(0, 2).map((ch, i) => (
                        <span key={i} className="text-[10px] px-2 py-0.5 rounded bg-red-50 text-red-600 line-clamp-1">
                          {typeof ch === "string" ? ch.slice(0, 40) : ""}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
