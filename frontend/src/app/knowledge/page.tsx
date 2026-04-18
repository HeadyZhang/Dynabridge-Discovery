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

const PHASE_COLORS: Record<string, string> = {
  discovery: "bg-violet-100 text-violet-700",
  strategy: "bg-cyan-100 text-cyan-700",
  design: "bg-amber-100 text-amber-700",
  marketing: "bg-green-100 text-green-700",
};

export default function KnowledgePage() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [loading, setLoading] = useState(true);
  const [filterIndustry, setFilterIndustry] = useState("");
  const [filterDiscovery, setFilterDiscovery] = useState<boolean | undefined>(undefined);

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
      const data = await listCases({
        industry: filterIndustry || undefined,
        has_discovery: filterDiscovery,
      });
      setCases(data);
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleFilter();
  }, [filterIndustry, filterDiscovery]);

  const industries = stats ? Object.keys(stats.industries) : [];

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Header */}
      <header className="bg-white border-b border-neutral-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="text-neutral-400 hover:text-neutral-600 text-sm">
              Home
            </Link>
            <span className="text-neutral-300">/</span>
            <div className="flex items-center gap-2">
              <Database className="w-5 h-5 text-brand-500" />
              <h1 className="text-lg font-semibold text-neutral-900">Knowledge Base</h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="px-3 py-1.5 text-sm text-neutral-600 hover:text-brand-500 hover:bg-brand-50 rounded-lg transition-colors"
            >
              Dashboard
            </Link>
            <a
              href={exportUrl("csv")}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-neutral-200 rounded-lg hover:bg-neutral-50 transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              Export CSV
            </a>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Stats Bar */}
        {stats && (
          <div className="grid grid-cols-4 gap-4 mb-6">
            {[
              { label: "Total Cases", value: stats.total_cases },
              { label: "Total Files", value: stats.total_files.toLocaleString() },
              { label: "Avg Completeness", value: `${Math.round(stats.avg_completeness * 100)}%` },
              { label: "With Discovery", value: stats.cases_with_discovery },
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
            {/* Search */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-neutral-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder="Search cases by keyword, brand name, or insight..."
                className="w-full pl-9 pr-3 py-2 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
              />
            </div>
            <button
              onClick={handleSearch}
              disabled={isSearching}
              className="px-4 py-2 bg-brand-500 text-white text-sm rounded-xl hover:bg-brand-600 disabled:opacity-50 transition-colors"
            >
              {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : "Search"}
            </button>
          </div>

          {/* Filters */}
          <div className="flex items-center gap-3 mt-3">
            <Filter className="w-4 h-4 text-neutral-400" />
            <select
              value={filterIndustry}
              onChange={(e) => setFilterIndustry(e.target.value)}
              className="px-3 py-1.5 text-sm border border-neutral-200 rounded-lg bg-white"
            >
              <option value="">All Industries</option>
              {industries.map((ind) => (
                <option key={ind} value={ind}>{ind}</option>
              ))}
            </select>
            <select
              value={filterDiscovery === undefined ? "" : String(filterDiscovery)}
              onChange={(e) =>
                setFilterDiscovery(e.target.value === "" ? undefined : e.target.value === "true")
              }
              className="px-3 py-1.5 text-sm border border-neutral-200 rounded-lg bg-white"
            >
              <option value="">All Phases</option>
              <option value="true">Has Discovery</option>
              <option value="false">No Discovery</option>
            </select>
          </div>
        </div>

        {/* Search Results */}
        {searchResults.length > 0 && (
          <div className="bg-white rounded-xl border border-neutral-200 p-4 mb-6">
            <h2 className="text-sm font-medium text-neutral-700 mb-3">
              Search Results ({searchResults.length})
            </h2>
            <div className="space-y-2">
              {searchResults.map((r, i) => (
                <div key={i} className="flex items-start gap-3 p-3 rounded-lg hover:bg-neutral-50">
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
                </div>
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
                  {/* Brand name */}
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

                  {/* Industry tag */}
                  {c.industry && (
                    <span className="inline-block text-[10px] px-2 py-0.5 rounded bg-neutral-100 text-neutral-600 mb-3">
                      {c.industry}
                    </span>
                  )}

                  {/* Completeness bar */}
                  <div className="mb-3">
                    <div className="flex items-center justify-between text-xs text-neutral-500 mb-1">
                      <span>Completeness</span>
                      <span className="font-medium">{Math.round(c.completeness_score * 100)}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-brand-500 rounded-full transition-all"
                        style={{ width: `${c.completeness_score * 100}%` }}
                      />
                    </div>
                  </div>

                  {/* Phase badges */}
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
                        <XCircle className="w-3 h-3" /> Incomplete
                      </span>
                    )}
                  </div>

                  {/* Meta */}
                  <div className="flex items-center gap-4 text-[11px] text-neutral-400">
                    <span>{c.total_files} files</span>
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
