const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface DCCampaign {
  id: string;
  brand_name: string;
  campaign_name: string;
  campaign_type: string;
  status: string;
  channel: string;
  audience: string;
  content_theme: string;
  content_format: string;
  impressions: number;
  revenue: number;
  roas: number;
  created_at: string | null;
}

export interface DCCampaignDetail {
  id: string;
  brand_name: string;
  campaign_name: string;
  campaign_type: string;
  status: string;
  budget: number | null;
  notes: string | null;
  audience: Record<string, string>;
  content: Record<string, string>;
  context: Record<string, string>;
  performances: {
    date: string | null;
    impressions: number;
    clicks: number;
    engagement_rate: number;
    conversions: number;
    revenue: number;
    cost: number;
    roas: number;
    cpa: number;
  }[];
  insights: DCInsight[];
}

export interface DCInsight {
  id: number;
  brand_name: string;
  pattern_type: string;
  finding: string;
  evidence: string;
  confidence: string;
  action_type: string;
  action_recommendation: string;
  audience_segment: string | null;
  content_theme: string | null;
  channel: string | null;
  is_validated: boolean;
  created_at: string | null;
}

export interface DCLearning {
  id: number;
  brand_name: string;
  principle: string;
  evidence_count: number;
  first_observed: string | null;
  last_validated: string | null;
  applicable_audiences: string[];
  applicable_content: string[];
  applicable_channels: string[];
  applicable_geos: string[];
  status: string;
}

export interface DCStats {
  campaigns_count: number;
  total_impressions: number;
  total_revenue: number;
  total_cost: number;
  avg_roas: number;
  top_channels: { channel: string; roas: number; campaigns: number; revenue: number }[];
}

export interface DCAttribution {
  filter: Record<string, string | null>;
  campaigns_matched: number;
  aggregate_performance: {
    total_impressions: number;
    total_clicks: number;
    avg_engagement_rate: number;
    total_conversions: number;
    total_revenue: number;
    total_cost: number;
    avg_roas: number;
  };
  vs_average: {
    engagement_rate_diff: number;
    roas_diff: number;
  };
}

export interface TagOptions {
  audience: Record<string, string[]>;
  content: Record<string, string[]>;
  context: Record<string, string[]>;
}

export async function dcGetStats(): Promise<DCStats> {
  const res = await fetch(`${API_BASE}/api/datacube/stats`);
  return res.json();
}

export async function dcListCampaigns(params?: {
  brand?: string;
  channel?: string;
  audience?: string;
  status?: string;
}): Promise<DCCampaign[]> {
  const sp = new URLSearchParams();
  if (params?.brand) sp.set("brand", params.brand);
  if (params?.channel) sp.set("channel", params.channel);
  if (params?.audience) sp.set("audience", params.audience);
  if (params?.status) sp.set("status", params.status);
  const qs = sp.toString();
  const res = await fetch(`${API_BASE}/api/datacube/campaigns${qs ? `?${qs}` : ""}`);
  return res.json();
}

export async function dcGetCampaign(id: string): Promise<DCCampaignDetail> {
  const res = await fetch(`${API_BASE}/api/datacube/campaigns/${id}`);
  return res.json();
}

export async function dcCreateCampaign(body: Record<string, unknown>): Promise<{ id: string }> {
  const res = await fetch(`${API_BASE}/api/datacube/campaigns`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

export async function dcGetTagOptions(): Promise<TagOptions> {
  const res = await fetch(`${API_BASE}/api/datacube/tags/options`);
  return res.json();
}

export async function dcGetAttribution(params: {
  audience?: string;
  content_theme?: string;
  channel?: string;
}): Promise<DCAttribution> {
  const sp = new URLSearchParams();
  if (params.audience) sp.set("audience", params.audience);
  if (params.content_theme) sp.set("content_theme", params.content_theme);
  if (params.channel) sp.set("channel", params.channel);
  const res = await fetch(`${API_BASE}/api/datacube/attribution?${sp.toString()}`);
  return res.json();
}

export async function dcImportCSV(file: File): Promise<{ imported: number; errors: string[] }> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/api/datacube/import/csv`, {
    method: "POST",
    body: formData,
  });
  return res.json();
}

export async function dcImportPlatform(
  platform: string,
  brand: string,
  file: File,
): Promise<{ platform: string; imported: number; errors: string[] }> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(
    `${API_BASE}/api/datacube/import/${platform}?brand=${encodeURIComponent(brand)}`,
    { method: "POST", body: formData },
  );
  return res.json();
}

export async function dcGenerateInsights(brand: string): Promise<{ generated: number }> {
  const res = await fetch(`${API_BASE}/api/datacube/insights/generate?brand=${encodeURIComponent(brand)}`, {
    method: "POST",
  });
  return res.json();
}

export async function dcListInsights(params?: {
  brand?: string;
  action_type?: string;
}): Promise<DCInsight[]> {
  const sp = new URLSearchParams();
  if (params?.brand) sp.set("brand", params.brand);
  if (params?.action_type) sp.set("action_type", params.action_type);
  const res = await fetch(`${API_BASE}/api/datacube/insights?${sp.toString()}`);
  return res.json();
}

export async function dcGetRecommendations(brand: string): Promise<{
  scale: DCInsight[];
  stop: DCInsight[];
  test: DCInsight[];
}> {
  const res = await fetch(`${API_BASE}/api/datacube/recommendations?brand=${encodeURIComponent(brand)}`);
  return res.json();
}

export async function dcListLearnings(brand?: string): Promise<DCLearning[]> {
  const qs = brand ? `?brand=${encodeURIComponent(brand)}` : "";
  const res = await fetch(`${API_BASE}/api/datacube/learnings${qs}`);
  return res.json();
}

export async function dcConsolidateLearnings(brand: string): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/api/datacube/learnings/consolidate?brand=${encodeURIComponent(brand)}`, {
    method: "POST",
  });
  return res.json();
}

export async function dcPlanCampaign(body: Record<string, unknown>): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/api/datacube/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

export async function dcDebriefCampaign(campaignId: string): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/api/datacube/campaigns/${campaignId}/debrief`, {
    method: "POST",
  });
  return res.json();
}
