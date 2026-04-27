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
  case_id: number | null;
  file_id: string | null;
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
  has_guidelines?: boolean;
  has_survey?: boolean;
}): Promise<CaseSummary[]> {
  const searchParams = new URLSearchParams();
  if (params?.industry) searchParams.set("industry", params.industry);
  if (params?.has_discovery !== undefined)
    searchParams.set("has_discovery", String(params.has_discovery));
  if (params?.has_strategy !== undefined)
    searchParams.set("has_strategy", String(params.has_strategy));
  if (params?.has_guidelines !== undefined)
    searchParams.set("has_guidelines", String(params.has_guidelines));
  if (params?.has_survey !== undefined)
    searchParams.set("has_survey", String(params.has_survey));
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

export interface SurveyAnalytics {
  total_survey_files: number;
  cases_with_surveys: number;
  survey_files: { brand_name: string; filename: string; doc_type: string; size_bytes: number; word_count: number }[];
  questionnaire_count: number;
  total_responses: number;
  cross_tabulation_count: number;
  engagement_count: number;
  segment_count: number;
  cases_with_survey_data: string[];
}

export async function getSurveyAnalytics(): Promise<SurveyAnalytics> {
  const res = await fetch(`${API_BASE}/api/knowledge/survey-analytics`);
  return res.json();
}

export interface InsightData {
  total: number;
  insights: { case_id: number; brand_name: string; industry: string; insight: string; type: string }[];
}

export async function getInsights(q?: string): Promise<InsightData> {
  const params = q ? `?q=${encodeURIComponent(q)}` : "";
  const res = await fetch(`${API_BASE}/api/knowledge/insights${params}`);
  return res.json();
}

export function exportUrl(format: "csv" | "json" = "csv"): string {
  return `${API_BASE}/api/knowledge/export?format=${format}`;
}

export interface ConsumerInsightData {
  id: number;
  case_id: number;
  brand_name: string;
  industry: string;
  text: string;
  type: string;
  segment: string | null;
  source: string;
  geo: string;
  confidence: string;
}

export interface InsightsResponse {
  total: number;
  insights: ConsumerInsightData[];
}

export interface SynthesisResponse {
  synthesis: string;
  insights_count: number;
  filters: Record<string, string | null>;
}

export async function getConsumerInsights(params?: {
  q?: string;
  industry?: string;
  insight_type?: string;
  geo?: string;
  limit?: number;
}): Promise<InsightsResponse> {
  const sp = new URLSearchParams();
  if (params?.q) sp.set("q", params.q);
  if (params?.industry) sp.set("industry", params.industry);
  if (params?.insight_type) sp.set("insight_type", params.insight_type);
  if (params?.geo) sp.set("geo", params.geo);
  if (params?.limit) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  const res = await fetch(`${API_BASE}/api/knowledge/insights${qs ? `?${qs}` : ""}`);
  return res.json();
}

export async function getSynthesis(params?: {
  industry?: string;
  insight_type?: string;
  geo?: string;
  lang?: string;
}): Promise<SynthesisResponse> {
  const sp = new URLSearchParams();
  if (params?.industry) sp.set("industry", params.industry);
  if (params?.insight_type) sp.set("insight_type", params.insight_type);
  if (params?.geo) sp.set("geo", params.geo);
  if (params?.lang) sp.set("lang", params.lang);
  const qs = sp.toString();
  const res = await fetch(`${API_BASE}/api/knowledge/insights/synthesis${qs ? `?${qs}` : ""}`);
  return res.json();
}

export interface IndustryOverview {
  [industry: string]: {
    case_count: number;
    brands: string[];
    challenges: string[];
    insights_count: number;
  };
}

export interface IndustryDetail {
  industry: string;
  cases: {
    id: number;
    brand: string;
    completeness: number;
    has_discovery: boolean;
    has_strategy: boolean;
    challenges: string[];
  }[];
  insights: { text: string; type: string; brand: string }[];
  total_insights: number;
}

export async function getIndustries(): Promise<IndustryOverview> {
  const res = await fetch(`${API_BASE}/api/knowledge/industries`);
  return res.json();
}

export async function getIndustryDetail(industry: string): Promise<IndustryDetail> {
  const res = await fetch(`${API_BASE}/api/knowledge/industries/${encodeURIComponent(industry)}`);
  return res.json();
}

export async function getIndustryReport(industry: string): Promise<{ report: string; case_count: number; insight_count: number }> {
  const res = await fetch(`${API_BASE}/api/knowledge/industries/${encodeURIComponent(industry)}/report`);
  return res.json();
}

export async function compareIndustries(industries: string[]): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/api/knowledge/industries/compare?industries=${industries.join(",")}`);
  return res.json();
}

export interface MarketIntelligence {
  brand: string | null;
  industry: string | null;
  market: string;
  trends: Record<string, unknown>;
  insights: { brand: string; text: string; type: string }[];
  strategy: Record<string, unknown>;
}

export async function getMarketIntelligence(params: {
  brand?: string;
  industry?: string;
  market?: string;
  keywords?: string;
  lang?: string;
}): Promise<MarketIntelligence> {
  const sp = new URLSearchParams();
  if (params.brand) sp.set("brand", params.brand);
  if (params.industry) sp.set("industry", params.industry);
  if (params.market) sp.set("market", params.market);
  if (params.keywords) sp.set("keywords", params.keywords);
  if (params.lang) sp.set("lang", params.lang);
  const res = await fetch(`${API_BASE}/api/knowledge/market-intelligence?${sp.toString()}`);
  return res.json();
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
