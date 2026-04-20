"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  BarChart3, PieChart, TrendingUp, Download, Loader2, ArrowLeft, Database,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart as RechartsPie, Pie, Cell, Legend,
} from "recharts";
import {
  getDashboardData, getSurveyAnalytics, exportUrl,
  type DashboardData, type SurveyAnalytics,
} from "@/lib/knowledge-api";
import KnowledgeNav from "@/components/KnowledgeNav";
import { useLanguage } from "@/lib/language-context";

const COLORS = ["#E8652D", "#00A8B5", "#F09E72", "#585752", "#D6D3D1", "#8B6D52", "#D4B89C", "#A08B75"];

export default function DashboardPage() {
  const { t } = useLanguage();
  const [data, setData] = useState<DashboardData | null>(null);
  const [survey, setSurvey] = useState<SurveyAnalytics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const [result, surveyResult] = await Promise.all([
        getDashboardData(),
        getSurveyAnalytics(),
      ]);
      setData(result);
      setSurvey(surveyResult);
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-neutral-400" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <p className="text-neutral-500">Failed to load dashboard data</p>
      </div>
    );
  }

  // Transform data for charts
  const phaseCoverageData = Object.entries(data.phase_coverage).map(([key, value]) => ({
    name: key.charAt(0).toUpperCase() + key.slice(1),
    count: value,
  }));

  const completenessData = Object.entries(data.completeness_distribution).map(([key, value]) => ({
    name: key,
    count: value,
  }));

  const docTypeData = Object.entries(data.doc_types)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([key, value]) => ({
      name: key.replace(/_/g, " "),
      count: value,
    }));

  const languageData = Object.entries(data.languages).map(([key, value]) => ({
    name: key === "en+zh" ? "Bilingual" : key === "en" ? "English" : key === "zh" ? "Chinese" : key,
    value: value,
  }));

  const industryData = Object.entries(data.industries)
    .sort((a, b) => b[1] - a[1])
    .map(([key, value]) => ({
      name: key,
      value: value,
    }));

  return (
    <div className="min-h-screen bg-neutral-50">
      <KnowledgeNav />

      {/* Sub-header with title + export */}
      <div className="bg-white border-b border-neutral-100 px-6 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-brand-500" />
            <h1 className="text-lg font-semibold text-neutral-900">
              {t("Discovery Dashboard", "\u6570\u636e\u770b\u677f")}
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <a
              href={exportUrl("csv")}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-neutral-200 rounded-lg hover:bg-neutral-50 transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              {t("Export CSV", "\u5bfc\u51fa CSV")}
            </a>
            <a
              href={exportUrl("json")}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-neutral-200 rounded-lg hover:bg-neutral-50 transition-colors"
            >
              <Database className="w-3.5 h-3.5" />
              JSON
            </a>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Top Stats */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          {[
            { label: "Total Cases", value: data.total_cases, icon: Database },
            { label: "Total Files", value: data.total_files.toLocaleString(), icon: BarChart3 },
            { label: "With Discovery", value: data.phase_coverage.discovery || 0, icon: PieChart },
            { label: "With Strategy", value: data.phase_coverage.strategy || 0, icon: TrendingUp },
          ].map((s) => (
            <div key={s.label} className="bg-white rounded-xl border border-neutral-200 p-5">
              <div className="flex items-center justify-between">
                <p className="text-sm text-neutral-500">{s.label}</p>
                <s.icon className="w-4 h-4 text-neutral-300" />
              </div>
              <p className="text-3xl font-bold text-neutral-900 mt-2">{s.value}</p>
            </div>
          ))}
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-2 gap-6 mb-6">
          {/* Phase Coverage */}
          <div className="bg-white rounded-xl border border-neutral-200 p-5">
            <h2 className="text-sm font-medium text-neutral-700 mb-4">Phase Coverage</h2>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={phaseCoverageData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#E8652D" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Completeness Distribution */}
          <div className="bg-white rounded-xl border border-neutral-200 p-5">
            <h2 className="text-sm font-medium text-neutral-700 mb-4">Completeness Distribution</h2>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={completenessData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#00A8B5" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Document Types */}
          <div className="bg-white rounded-xl border border-neutral-200 p-5">
            <h2 className="text-sm font-medium text-neutral-700 mb-4">Document Types</h2>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={docTypeData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis type="number" tick={{ fontSize: 12 }} />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={100} />
                <Tooltip />
                <Bar dataKey="count" fill="#F09E72" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Language Distribution */}
          <div className="bg-white rounded-xl border border-neutral-200 p-5">
            <h2 className="text-sm font-medium text-neutral-700 mb-4">Language Distribution</h2>
            <ResponsiveContainer width="100%" height={250}>
              <RechartsPie>
                <Pie
                  data={languageData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                >
                  {languageData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </RechartsPie>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Bottom Section: Top Cases + Industry */}
        <div className="grid grid-cols-2 gap-6">
          {/* Top Cases by Completeness */}
          <div className="bg-white rounded-xl border border-neutral-200 p-5">
            <h2 className="text-sm font-medium text-neutral-700 mb-4">Top Cases by Completeness</h2>
            <div className="space-y-3">
              {data.top_cases.map((c, i) => (
                <div key={i} className="flex items-center gap-3">
                  <span className="text-xs text-neutral-400 w-5">{i + 1}</span>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-neutral-800">{c.brand_name}</span>
                      <span className="text-xs text-neutral-500">
                        {Math.round(c.completeness * 100)}% | {c.files} files
                      </span>
                    </div>
                    <div className="w-full h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-brand-500 rounded-full"
                        style={{ width: `${c.completeness * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Industry Breakdown */}
          <div className="bg-white rounded-xl border border-neutral-200 p-5">
            <h2 className="text-sm font-medium text-neutral-700 mb-4">Industry Breakdown</h2>
            {industryData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <RechartsPie>
                  <Pie
                    data={industryData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    label={({ name, value }) => `${name} (${value})`}
                  >
                    {industryData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </RechartsPie>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-neutral-400 py-10 text-center">
                Industry data will appear after AI tagging
              </p>
            )}
          </div>
        </div>

        {/* Survey Analytics Section */}
        {survey && (
          <div className="grid grid-cols-3 gap-4 mt-6">
            <div className="bg-white rounded-xl border border-neutral-200 p-5">
              <h2 className="text-sm font-medium text-neutral-700 mb-3">Survey Analytics</h2>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-neutral-500">Survey Files</span>
                  <span className="font-medium text-neutral-900">{survey.total_survey_files}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-neutral-500">Cases with Surveys</span>
                  <span className="font-medium text-neutral-900">{survey.cases_with_surveys}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-neutral-500">Questionnaires</span>
                  <span className="font-medium text-neutral-900">{survey.questionnaire_count}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-neutral-500">Total Responses</span>
                  <span className="font-medium text-neutral-900">{survey.total_responses}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-neutral-500">Engagements</span>
                  <span className="font-medium text-neutral-900">{survey.engagement_count}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-neutral-500">Consumer Segments</span>
                  <span className="font-medium text-neutral-900">{survey.segment_count}</span>
                </div>
              </div>
            </div>

            <div className="col-span-2 bg-white rounded-xl border border-neutral-200 p-5">
              <h2 className="text-sm font-medium text-neutral-700 mb-3">
                Cases with Survey Data ({survey.cases_with_survey_data.length})
              </h2>
              {survey.cases_with_survey_data.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {survey.cases_with_survey_data.map((name) => (
                    <span
                      key={name}
                      className="text-xs px-2.5 py-1 rounded-lg bg-violet-50 text-violet-700"
                    >
                      {name}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-neutral-400 py-4 text-center">
                  No survey data ingested yet
                </p>
              )}
              {survey.survey_files.length > 0 && (
                <div className="mt-4 max-h-40 overflow-y-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-neutral-400 border-b border-neutral-100">
                        <th className="text-left py-1.5">Brand</th>
                        <th className="text-left py-1.5">File</th>
                        <th className="text-left py-1.5">Type</th>
                      </tr>
                    </thead>
                    <tbody>
                      {survey.survey_files.slice(0, 20).map((f, i) => (
                        <tr key={i} className="border-b border-neutral-50">
                          <td className="py-1.5 text-neutral-600">{f.brand_name}</td>
                          <td className="py-1.5 text-neutral-800 truncate max-w-[200px]">{f.filename}</td>
                          <td className="py-1.5 text-neutral-500">{f.doc_type}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
