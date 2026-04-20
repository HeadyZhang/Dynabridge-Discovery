"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Search, Filter, FileText, CheckCircle2, XCircle,
  Database, ArrowRight, Download, Loader2,
} from "lucide-react";
import {
  listCases, searchKnowledge, getStats, exportUrl,
  type CaseSummary, type SearchResult, type KnowledgeStats,
} from "@/lib/knowledge-api";
import KnowledgeNav from "@/components/KnowledgeNav";
import { useLanguage } from "@/lib/language-context";

export default function KnowledgePage() {
  const { t } = useLanguage();
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [loading, setLoading] = useState(true);
  const [filterIndustry, setFilterIndustry] = useState("");
  const [filterPhase, setFilterPhase] = useState("");

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [casesData, statsData] = await Promise.all([listCases(), getStats()]);
      setCases(casesData);
      setStats(statsData);
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    setIsSearching(true);
    try {
      const results = await searchKnowledge(searchQuery, "fts", 20);
      setSearchResults(results);
    } catch {
      // silently handle
    } finally {
      setIsSearching(false);
    }
  }, [searchQuery]);

  const handleFilter = async () => {
    setLoading(true);
    try {
      const params: Parameters<typeof listCases>[0] = {
        industry: filterIndustry || undefined,
      };
      if (filterPhase === "has_discovery") params.has_discovery = true;
      if (filterPhase === "has_strategy") params.has_strategy = true;
      if (filterPhase === "has_guidelines") params.has_guidelines = true;
      if (filterPhase === "has_survey") params.has_survey = true;
      const data = await listCases(params);
      setCases(data);
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleFilter();
  }, [filterIndustry, filterPhase]);

  const industries = stats ? Object.keys(stats.industries) : [];

  return (
    <div className="min-h-screen bg-neutral-50">
      <KnowledgeNav />

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Page title + export */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-brand-500" />
            <h1 className="text-lg font-semibold text-neutral-900">
              {t("Knowledge Base", "\u6848\u4f8b\u77e5\u8bc6\u5e93")}
            </h1>
          </div>
          <a
            href={exportUrl("csv")}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-neutral-200 rounded-lg hover:bg-neutral-50 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            {t("Export CSV", "\u5bfc\u51fa CSV")}
          </a>
        </div>

        {/* Stats Bar */}
        {stats && (
          <div className="grid grid-cols-4 gap-4 mb-6">
            {[
              { label: t("Total Cases", "\u603b\u6848\u4f8b\u6570"), value: stats.total_cases },
              { label: t("Total Files", "\u603b\u6587\u4ef6\u6570"), value: stats.total_files.toLocaleString() },
              { label: t("Avg Completeness", "\u5e73\u5747\u5b8c\u6574\u5ea6"), value: `${Math.round(stats.avg_completeness * 100)}%` },
              { label: t("With Discovery", "\u542b\u54c1\u724c\u63a2\u7d22"), value: stats.cases_with_discovery },
            ].map((s) => (
              <div key={s.label} className="bg-white rounded-xl border border-neutral-200 p-4">
                <p className="text-sm text-neutral-500">{s.label}</p>
                <p className="text-2xl font-semibold text-neutral-900 mt-1">{s.value}</p>
              </div>
            ))}
          </div>
        )}

        {/* Search + Filters */}
        <div className="bg-white rounded-xl border border-neutral-200 p-4 mb-6">
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-neutral-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder={t("Search cases by keyword, brand name, or insight...", "\u6309\u5173\u952e\u8bcd\u3001\u54c1\u724c\u540d\u6216\u6d1e\u5bdf\u641c\u7d22\u6848\u4f8b...")}
                className="w-full pl-9 pr-3 py-2 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
              />
            </div>
            <button
              onClick={handleSearch}
              disabled={isSearching}
              className="px-4 py-2 bg-brand-500 text-white text-sm rounded-xl hover:bg-brand-600 disabled:opacity-50 transition-colors"
            >
              {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : t("Search", "\u641c\u7d22")}
            </button>
          </div>

          <div className="flex items-center gap-3 mt-3">
            <Filter className="w-4 h-4 text-neutral-400" />
            <select
              value={filterIndustry}
              onChange={(e) => setFilterIndustry(e.target.value)}
              className="px-3 py-1.5 text-sm border border-neutral-200 rounded-lg bg-white"
            >
              <option value="">{t("All Industries", "\u6240\u6709\u884c\u4e1a")}</option>
              {industries.map((ind) => (
                <option key={ind} value={ind}>{ind}</option>
              ))}
            </select>
            <select
              value={filterPhase}
              onChange={(e) => setFilterPhase(e.target.value)}
              className="px-3 py-1.5 text-sm border border-neutral-200 rounded-lg bg-white"
            >
              <option value="">{t("All Phases", "\u6240\u6709\u9636\u6bb5")}</option>
              <option value="has_discovery">{t("Has Discovery", "\u542b\u54c1\u724c\u63a2\u7d22")}</option>
              <option value="has_strategy">{t("Has Strategy", "\u542b\u54c1\u724c\u6218\u7565")}</option>
              <option value="has_guidelines">{t("Has Guidelines", "\u542b\u54c1\u724c\u6307\u5357")}</option>
              <option value="has_survey">{t("Has Survey", "\u542b\u8c03\u7814")}</option>
            </select>
          </div>
        </div>

        {/* Search Results */}
        {searchResults.length > 0 && (
          <div className="bg-white rounded-xl border border-neutral-200 p-4 mb-6">
            <h2 className="text-sm font-medium text-neutral-700 mb-3">
              {t("Search Results", "\u641c\u7d22\u7ed3\u679c")} ({searchResults.length})
            </h2>
            <div className="space-y-2">
              {searchResults.map((r, i) => (
                <Link
                  key={i}
                  href={r.case_id ? `/knowledge/${r.case_id}` : "#"}
                  className="flex items-start gap-3 p-3 rounded-lg hover:bg-brand-50 cursor-pointer transition-colors border border-transparent hover:border-brand-200"
                >
                  <FileText className="w-4 h-4 text-brand-500 mt-0.5 shrink-0" />
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-neutral-800">{r.brand_name}</span>
                      <span className="text-xs text-neutral-400">{r.filename}</span>
                    </div>
                    {r.snippet && (
                      <p
                        className="text-xs text-neutral-500 mt-1 line-clamp-2"
                        dangerouslySetInnerHTML={{ __html: r.snippet }}
                      />
                    )}
                  </div>
                  <ArrowRight className="w-4 h-4 text-neutral-300 mt-0.5 shrink-0" />
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Case Grid */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-6 h-6 animate-spin text-neutral-400" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {cases.map((c) => (
              <Link key={c.id} href={`/knowledge/${c.id}`}>
                <div className="bg-white rounded-xl border border-neutral-200 p-5 hover:shadow-md hover:border-brand-300 transition-all cursor-pointer group">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-semibold text-neutral-900 group-hover:text-brand-500 transition-colors">
                        {c.brand_name}
                      </h3>
                      {c.brand_name_zh && (
                        <p className="text-xs text-neutral-400">{c.brand_name_zh}</p>
                      )}
                    </div>
                    <ArrowRight className="w-4 h-4 text-neutral-300 group-hover:text-brand-500 transition-colors" />
                  </div>

                  {c.industry && (
                    <span className="inline-block text-[10px] px-2 py-0.5 rounded bg-neutral-100 text-neutral-600 mb-3">
                      {c.industry}
                    </span>
                  )}

                  <div className="mb-3">
                    <div className="flex items-center justify-between text-xs text-neutral-500 mb-1">
                      <span>{t("Completeness", "\u5b8c\u6574\u5ea6")}</span>
                      <span className="font-medium">{Math.round(c.completeness_score * 100)}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-brand-500 rounded-full transition-all"
                        style={{ width: `${c.completeness_score * 100}%` }}
                      />
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-1.5 mb-3">
                    {c.has_discovery && (
                      <span className="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-violet-50 text-violet-600">
                        <CheckCircle2 className="w-3 h-3" /> Discovery
                      </span>
                    )}
                    {c.has_strategy && (
                      <span className="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-cyan-50 text-cyan-600">
                        <CheckCircle2 className="w-3 h-3" /> Strategy
                      </span>
                    )}
                    {c.has_guidelines && (
                      <span className="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-600">
                        <CheckCircle2 className="w-3 h-3" /> Guidelines
                      </span>
                    )}
                    {!c.has_discovery && !c.has_strategy && (
                      <span className="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-red-50 text-red-500">
                        <XCircle className="w-3 h-3" /> {t("Incomplete", "\u4e0d\u5b8c\u6574")}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-4 text-[11px] text-neutral-400">
                    <span>{c.total_files} {t("files", "\u4e2a\u6587\u4ef6")}</span>
                    <span>{c.total_size_mb.toFixed(0)} MB</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
