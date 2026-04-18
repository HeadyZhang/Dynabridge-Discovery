const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface CaseSummary {
  id: number;
  brand_name: string;
  brand_name_zh: string;
  industry: string;
  sub_category: string;
  total_files: number;
  total_size_mb: number;
  completeness_score: number;
  has_discovery: boolean;
  has_strategy: boolean;
  has_guidelines: boolean;
  has_survey: boolean;
  last_synced_at: string | null;
}

export interface CaseFile {
  id: number;
  filename: string;
  drive_file_id: string;
  doc_type: string;
  doc_label: string;
  phase: string;
  size_bytes: number;
  word_count: number;
  language_hint: string;
  quality: string;
}

export interface CaseDetail extends CaseSummary {
  ai_tags: Record<string, unknown>;
  positioning_summary: string;
  files: CaseFile[];
}

export interface SimilarCase extends CaseSummary {
  similarity_score: number;
}

export interface SearchResult {
  source: string;
  doc_id: string;
  brand_name: string;
  filename: string;
  snippet: string;
  score: number;
}

export interface KnowledgeStats {
  total_cases: number;
  total_files: number;
  avg_completeness: number;
  industries: Record<string, number>;
  cases_with_discovery: number;
  cases_with_strategy: number;
  cases_with_guidelines: number;
}

export interface DashboardData {
  total_cases: number;
  total_files: number;
  phase_coverage: Record<string, number>;
  completeness_distribution: Record<string, number>;
  industries: Record<string, number>;
  doc_types: Record<string, number>;
  languages: Record<string, number>;
  top_cases: { brand_name: string; completeness: number; files: number }[];
}

export async function listCases(params?: {
  industry?: string;
  has_discovery?: boolean;
  has_strategy?: boolean;
}): Promise<CaseSummary[]> {
  const searchParams = new URLSearchParams();
  if (params?.industry) searchParams.set("industry", params.industry);
  if (params?.has_discovery !== undefined)
    searchParams.set("has_discovery", String(params.has_discovery));
  if (params?.has_strategy !== undefined)
    searchParams.set("has_strategy", String(params.has_strategy));
  const qs = searchParams.toString();
  const res = await fetch(`${API_BASE}/api/knowledge/cases${qs ? `?${qs}` : ""}`);
  return res.json();
}

export async function getCase(id: number): Promise<CaseDetail> {
  const res = await fetch(`${API_BASE}/api/knowledge/cases/${id}`);
  return res.json();
}

export async function getSimilarCases(id: number): Promise<SimilarCase[]> {
  const res = await fetch(`${API_BASE}/api/knowledge/cases/${id}/similar`);
  return res.json();
}

export async function searchKnowledge(
  query: string,
  mode: "fts" | "vector" | "hybrid" = "fts",
  limit: number = 20
): Promise<SearchResult[]> {
  const res = await fetch(
    `${API_BASE}/api/knowledge/search?q=${encodeURIComponent(query)}&mode=${mode}&limit=${limit}`
  );
  return res.json();
}

export async function getStats(): Promise<KnowledgeStats> {
  const res = await fetch(`${API_BASE}/api/knowledge/stats`);
  return res.json();
}

export async function getDashboardData(): Promise<DashboardData> {
  const res = await fetch(`${API_BASE}/api/knowledge/dashboard`);
  return res.json();
}

export function exportUrl(format: "csv" | "json" = "csv"): string {
  return `${API_BASE}/api/knowledge/export?format=${format}`;
}

export function driveFileUrl(driveFileId: string): string {
  return `https://drive.google.com/file/d/${driveFileId}/view`;
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}
