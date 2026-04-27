"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import {
  ArrowLeft, FileText, ExternalLink, ChevronDown, ChevronUp,
  CheckCircle2, XCircle, Database, Loader2, Sparkles,
} from "lucide-react";
import {
  getCase, getSimilarCases, driveFileUrl, formatBytes,
  type CaseDetail, type SimilarCase,
} from "@/lib/knowledge-api";

const PHASE_ORDER = ["planning", "discovery", "strategy", "design", "marketing", "assets"];
const PHASE_STYLES: Record<string, string> = {
  planning: "bg-slate-100 text-slate-700",
  discovery: "bg-violet-100 text-violet-700",
  strategy: "bg-cyan-100 text-cyan-700",
  design: "bg-amber-100 text-amber-700",
  marketing: "bg-green-100 text-green-700",
  assets: "bg-neutral-100 text-neutral-600",
};

export default function CaseDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const caseId = Number(params.id);
  const highlightQuery = searchParams.get("highlight");
  const targetFileId = searchParams.get("file");

  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [similar, setSimilar] = useState<SimilarCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedPhases, setExpandedPhases] = useState<Set<string>>(new Set(PHASE_ORDER));

  useEffect(() => {
    if (!caseId) return;
    loadCase();
  }, [caseId]);

  useEffect(() => {
    if (targetFileId && caseData) {
      setTimeout(() => {
        const el = document.getElementById(`file-${targetFileId}`);
        if (el) {
          el.scrollIntoView({ behavior: "smooth", block: "center" });
          el.classList.add("bg-yellow-50");
        }
      }, 300);
    }
  }, [targetFileId, caseData]);

  const loadCase = async () => {
    try {
      const [data, similarData] = await Promise.all([
        getCase(caseId),
        getSimilarCases(caseId),
      ]);
      setCaseData(data);
      setSimilar(similarData);
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  };

  const togglePhase = (phase: string) => {
    setExpandedPhases((prev) => {
      const next = new Set(prev);
      if (next.has(phase)) next.delete(phase);
      else next.add(phase);
      return next;
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-neutral-400" />
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <p className="text-neutral-500">Case not found</p>
      </div>
    );
  }

  // Group files by phase
  const filesByPhase: Record<string, typeof caseData.files> = {};
  for (const f of caseData.files) {
    const phase = f.phase || "assets";
    if (!filesByPhase[phase]) filesByPhase[phase] = [];
    filesByPhase[phase].push(f);
  }

  const aiTags = caseData.ai_tags || {};
  const challenges = (aiTags.core_challenges as string[]) || [];
  const insights = (aiTags.key_insights as string[]) || [];
  const competitors = (aiTags.competitors_mentioned as string[]) || [];

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Header */}
      <header className="bg-white border-b border-neutral-200 px-6 py-4">
        <div className="max-w-5xl mx-auto">
          <Link
            href="/knowledge"
            className="flex items-center gap-1.5 text-sm text-neutral-500 hover:text-brand-500 mb-3 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Knowledge Base
          </Link>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold text-neutral-900">{caseData.brand_name}</h1>
              {caseData.brand_name_zh && (
                <p className="text-neutral-400 mt-0.5">{caseData.brand_name_zh}</p>
              )}
              <div className="flex items-center gap-2 mt-2">
                {caseData.industry && (
                  <span className="text-xs px-2 py-0.5 rounded bg-neutral-100 text-neutral-600">
                    {caseData.industry}
                  </span>
                )}
                {caseData.sub_category && (
                  <span className="text-xs px-2 py-0.5 rounded bg-neutral-100 text-neutral-600">
                    {caseData.sub_category}
                  </span>
                )}
              </div>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold text-brand-500">
                {Math.round(caseData.completeness_score * 100)}%
              </div>
              <p className="text-xs text-neutral-400 mt-0.5">completeness</p>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-6 space-y-6">
        {/* Overview Cards */}
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: "Files", value: caseData.total_files },
            { label: "Size", value: `${caseData.total_size_mb.toFixed(0)} MB` },
            { label: "Discovery", icon: caseData.has_discovery ? CheckCircle2 : XCircle, color: caseData.has_discovery ? "text-green-500" : "text-red-400" },
            { label: "Strategy", icon: caseData.has_strategy ? CheckCircle2 : XCircle, color: caseData.has_strategy ? "text-green-500" : "text-red-400" },
          ].map((item) => (
            <div key={item.label} className="bg-white rounded-xl border border-neutral-200 p-4">
              <p className="text-xs text-neutral-500">{item.label}</p>
              {"value" in item ? (
                <p className="text-xl font-semibold text-neutral-900 mt-1">{item.value}</p>
              ) : (
                <item.icon className={`w-6 h-6 mt-1 ${item.color}`} />
              )}
            </div>
          ))}
        </div>

        {/* Positioning Summary */}
        {caseData.positioning_summary && (
          <div className="bg-white rounded-xl border border-neutral-200 p-5">
            <h2 className="text-sm font-medium text-neutral-700 mb-2 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-brand-500" />
              Positioning Summary
            </h2>
            <p className="text-sm text-neutral-600 leading-relaxed">
              {caseData.positioning_summary}
            </p>
          </div>
        )}

        {/* AI Tags */}
        {(challenges.length > 0 || insights.length > 0 || competitors.length > 0) && (
          <div className="grid grid-cols-3 gap-4">
            {challenges.length > 0 && (
              <div className="bg-white rounded-xl border border-neutral-200 p-4">
                <h3 className="text-xs font-medium text-neutral-500 mb-2">Core Challenges</h3>
                <ul className="space-y-1.5">
                  {challenges.map((c, i) => (
                    <li key={i} className="text-sm text-neutral-700">{c}</li>
                  ))}
                </ul>
              </div>
            )}
            {insights.length > 0 && (
              <div className="bg-white rounded-xl border border-neutral-200 p-4">
                <h3 className="text-xs font-medium text-neutral-500 mb-2">Key Insights</h3>
                <ul className="space-y-1.5">
                  {insights.map((ins, i) => (
                    <li key={i} className="text-sm text-neutral-700">{ins}</li>
                  ))}
                </ul>
              </div>
            )}
            {competitors.length > 0 && (
              <div className="bg-white rounded-xl border border-neutral-200 p-4">
                <h3 className="text-xs font-medium text-neutral-500 mb-2">Competitors Mentioned</h3>
                <div className="flex flex-wrap gap-1.5">
                  {competitors.map((comp, i) => (
                    <span key={i} className="text-xs px-2 py-0.5 rounded bg-neutral-100 text-neutral-600">
                      {comp}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Files by Phase */}
        <div className="bg-white rounded-xl border border-neutral-200 overflow-hidden">
          <div className="px-5 py-3 border-b border-neutral-100">
            <h2 className="text-sm font-medium text-neutral-700 flex items-center gap-2">
              <FileText className="w-4 h-4 text-brand-500" />
              Files ({caseData.files.length})
            </h2>
          </div>

          {PHASE_ORDER.map((phase) => {
            const files = filesByPhase[phase];
            if (!files || files.length === 0) return null;
            const isExpanded = expandedPhases.has(phase);

            return (
              <div key={phase} className="border-b border-neutral-100 last:border-b-0">
                <button
                  onClick={() => togglePhase(phase)}
                  className="w-full flex items-center justify-between px-5 py-3 hover:bg-neutral-50 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] px-2 py-0.5 rounded font-medium ${PHASE_STYLES[phase] || PHASE_STYLES.assets}`}>
                      {phase.toUpperCase()}
                    </span>
                    <span className="text-sm text-neutral-600">{files.length} files</span>
                  </div>
                  {isExpanded ? (
                    <ChevronUp className="w-4 h-4 text-neutral-400" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-neutral-400" />
                  )}
                </button>

                {isExpanded && (
                  <div className="px-5 pb-3">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-xs text-neutral-400">
                          <th className="text-left py-1.5 font-medium">File</th>
                          <th className="text-left py-1.5 font-medium w-24">Type</th>
                          <th className="text-right py-1.5 font-medium w-20">Size</th>
                          <th className="text-right py-1.5 font-medium w-16">Words</th>
                          <th className="text-center py-1.5 font-medium w-16">Drive</th>
                        </tr>
                      </thead>
                      <tbody>
                        {files.map((f) => (
                          <tr key={f.id} id={`file-${f.drive_file_id}`} className="border-t border-neutral-50 hover:bg-neutral-50">
                            <td className="py-2 text-neutral-700 truncate max-w-[300px]">{f.filename}</td>
                            <td className="py-2">
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-neutral-100 text-neutral-500">
                                {f.doc_label}
                              </span>
                            </td>
                            <td className="py-2 text-right text-neutral-500 text-xs">
                              {f.size_bytes > 0 ? formatBytes(f.size_bytes) : "-"}
                            </td>
                            <td className="py-2 text-right text-neutral-500 text-xs">
                              {f.word_count > 0 ? f.word_count.toLocaleString() : "-"}
                            </td>
                            <td className="py-2 text-center">
                              {f.drive_file_id && (
                                <a
                                  href={driveFileUrl(f.drive_file_id)}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-brand-500 hover:text-brand-600"
                                >
                                  <ExternalLink className="w-3.5 h-3.5 inline" />
                                </a>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Similar Cases */}
        {similar.length > 0 && (
          <div className="bg-white rounded-xl border border-neutral-200 p-5">
            <h2 className="text-sm font-medium text-neutral-700 mb-3 flex items-center gap-2">
              <Database className="w-4 h-4 text-brand-500" />
              Similar Cases
            </h2>
            <div className="grid grid-cols-3 gap-4">
              {similar.map((s) => (
                <Link key={s.id} href={`/knowledge/${s.id}`}>
                  <div className="border border-neutral-200 rounded-lg p-4 hover:border-brand-300 hover:shadow-sm transition-all">
                    <h3 className="font-medium text-neutral-800">{s.brand_name}</h3>
                    {s.industry && (
                      <p className="text-xs text-neutral-400 mt-0.5">{s.industry}</p>
                    )}
                    <div className="flex items-center justify-between mt-2">
                      <span className="text-xs text-neutral-500">{s.total_files} files</span>
                      <span className="text-xs font-medium text-brand-500">
                        {Math.round(s.completeness_score * 100)}%
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
