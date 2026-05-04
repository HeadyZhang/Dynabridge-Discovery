const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type SurveyMode = "simulated" | "real";

export interface Project {
  id: number;
  name: string;
  brand_url: string;
  competitor_urls: string[];
  status: string;
  language: string;
  phase: string;
  created_at: string;
  updated_at: string;
  has_pptx: boolean;
  slide_count: number;
  file_count: number;
  comment_count: number;
  survey_mode: SurveyMode;
  has_survey: boolean;
  has_survey_responses: boolean;
  slides?: SlidePreview[];
  comments?: Comment[];
}

export interface SlidePreview {
  order: number;
  type: string;
  content: Record<string, unknown>;
  preview_url: string;
}

export interface Comment {
  id: number;
  slide_order: number | null;
  author: string;
  content: string;
  feedback_type: string;
  phase: string;
  resolved: boolean;
  created_at?: string;
}

export type FeedbackType = "insight" | "image" | "data" | "text" | "layout" | "other";

export interface ProgressEvent {
  step: string;
  message: string;
  done?: boolean;
  competitors?: { name: string; source: string; confidence: number; category_role?: string; reason?: string }[];
}

/** Shared response checker — throws on non-OK responses */
async function assertOk(res: Response): Promise<Response> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || body.message || JSON.stringify(body);
    } catch { /* response wasn't JSON */ }
    throw new Error(`API ${res.status}: ${detail}`);
  }
  return res;
}

export async function listProjects(): Promise<Project[]> {
  const res = await fetch(`${API_BASE}/api/projects`);
  await assertOk(res);
  return res.json();
}

export async function getProject(id: number): Promise<Project> {
  const res = await fetch(`${API_BASE}/api/projects/${id}`);
  await assertOk(res);
  return res.json();
}

export async function createProject(data: {
  name: string;
  brand_url: string;
  competitor_urls: string[];
  language: string;
  phase?: string;
  survey_mode?: SurveyMode;
}): Promise<Project> {
  const form = new FormData();
  form.append("name", data.name);
  form.append("brand_url", data.brand_url);
  form.append("competitor_urls", JSON.stringify(data.competitor_urls));
  form.append("language", data.language);
  if (data.phase) form.append("phase", data.phase);
  if (data.survey_mode) form.append("survey_mode", data.survey_mode);
  const res = await fetch(`${API_BASE}/api/projects`, { method: "POST", body: form });
  await assertOk(res);
  return res.json();
}

export async function uploadFile(projectId: number, file: File) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/files`, {
    method: "POST",
    body: form,
  });
  await assertOk(res);
  return res.json();
}

export function generateReport(
  projectId: number,
  onProgress: (event: ProgressEvent) => void,
  onComplete: (data: { pptx_path: string; slide_count: number; phase?: string; next_phase?: string }) => void,
  onError: (msg: string) => void,
  phase: string = "full",
  checkpoint: boolean = false,
  onCheckpoint?: (data: { pptx_path: string; slide_count: number; phase: string; next_phase: string | null }) => void,
) {
  const form = new FormData();
  form.append("phase", phase);
  if (checkpoint) form.append("checkpoint", "true");

  const controller = new AbortController();
  // Overall timeout: 30 minutes for the entire pipeline
  const timeout = setTimeout(() => {
    controller.abort();
    onError("Generation timed out after 30 minutes");
  }, 30 * 60 * 1000);

  fetch(`${API_BASE}/api/projects/${projectId}/generate`, {
    method: "POST",
    body: form,
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        let detail = res.statusText;
        try {
          const body = await res.json();
          detail = body.detail || body.message || JSON.stringify(body);
        } catch { /* not JSON */ }
        onError(`Server error ${res.status}: ${detail}`);
        return;
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) {
        onError("No response stream");
        return;
      }

      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const block of lines) {
          const eventMatch = block.match(/^event: (\w+)/);
          const dataMatch = block.match(/^data: (.+)$/m);
          if (eventMatch && dataMatch) {
            const eventType = eventMatch[1];
            try {
              const data = JSON.parse(dataMatch[1]);
              if (eventType === "progress") onProgress(data);
              else if (eventType === "complete") onComplete(data);
              else if (eventType === "checkpoint") onCheckpoint?.(data);
              else if (eventType === "error") onError(data.message);
            } catch {
              // Malformed JSON in SSE event — skip this event
              console.warn("Malformed SSE data:", dataMatch[1]);
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name === "AbortError") return; // Already handled by timeout
      onError(err.message);
    })
    .finally(() => clearTimeout(timeout));
}

export async function getSlides(projectId: number): Promise<SlidePreview[]> {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/slides`);
  await assertOk(res);
  const slides: SlidePreview[] = await res.json();
  return slides.map((s) => ({
    ...s,
    preview_url: s.preview_url?.startsWith("/") ? `${API_BASE}${s.preview_url}` : s.preview_url,
  }));
}

export function slidePreviewUrl(slideId: number): string {
  return `${API_BASE}/api/slides/${slideId}/preview`;
}

export async function addComment(
  projectId: number,
  data: { slide_order?: number; author: string; content: string; feedback_type?: string; phase?: string }
) {
  const form = new FormData();
  if (data.slide_order !== undefined) form.append("slide_order", String(data.slide_order));
  form.append("author", data.author);
  form.append("content", data.content);
  if (data.feedback_type) form.append("feedback_type", data.feedback_type);
  if (data.phase) form.append("phase", data.phase);
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/comments`, {
    method: "POST",
    body: form,
  });
  await assertOk(res);
  return res.json();
}

export async function approvePhase(
  projectId: number,
  phase: string,
  autoContinue: boolean = false,
): Promise<{ status: string; phase: string; next_phase: string | null; resolved_comments: number }> {
  const res = await fetch(
    `${API_BASE}/api/projects/${projectId}/phases/${phase}/approve?auto_continue=${autoContinue}`,
    { method: "POST" },
  );
  await assertOk(res);
  return res.json();
}

export function regeneratePhase(
  projectId: number,
  phase: string,
  onProgress: (event: ProgressEvent) => void,
  onComplete: (data: { pptx_path: string; slide_count: number; feedback_resolved: number }) => void,
  onError: (msg: string) => void,
) {
  fetch(`${API_BASE}/api/projects/${projectId}/phases/${phase}/regenerate`, {
    method: "POST",
  })
    .then(async (res) => {
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        onError(body.detail || body.message || `Error ${res.status}`);
        return;
      }
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) { onError("No response stream"); return; }

      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";
        for (const block of lines) {
          const eventMatch = block.match(/^event: (\w+)/);
          const dataMatch = block.match(/^data: (.+)$/m);
          if (eventMatch && dataMatch) {
            try {
              const data = JSON.parse(dataMatch[1]);
              if (eventMatch[1] === "progress") onProgress(data);
              else if (eventMatch[1] === "complete") onComplete(data);
              else if (eventMatch[1] === "error") onError(data.message);
            } catch { /* skip malformed */ }
          }
        }
      }
    })
    .catch((err) => onError(err.message));
}

export async function getComments(projectId: number): Promise<Comment[]> {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/comments`);
  await assertOk(res);
  return res.json();
}

export function downloadUrl(projectId: number): string {
  return `${API_BASE}/api/projects/${projectId}/download`;
}

// ── Survey endpoints ──────────────────────────────────────────

export async function designSurvey(projectId: number): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/survey`, { method: "POST" });
  await assertOk(res);
  return res.json();
}

export function surveyDownloadUrl(projectId: number): string {
  return `${API_BASE}/api/projects/${projectId}/survey/download`;
}

export async function uploadSurveyResponses(
  projectId: number,
  file: File
): Promise<{ status: string; sample_size: number; question_count: number }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/survey/responses`, {
    method: "POST",
    body: form,
  });
  await assertOk(res);
  return res.json();
}

export async function setSurveyMode(projectId: number, mode: SurveyMode): Promise<void> {
  const form = new FormData();
  form.append("mode", mode);
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/survey-mode`, {
    method: "PATCH",
    body: form,
  });
  await assertOk(res);
}

// ── PDF report endpoints ─────────────────────────────────────

export interface PdfReport {
  phase: string;
  filename: string;
  size: number;
  download_url: string;
}

export async function listPdfs(projectId: number): Promise<PdfReport[]> {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/pdfs`);
  await assertOk(res);
  return res.json();
}

export function pdfDownloadUrl(projectId: number, phase: string): string {
  return `${API_BASE}/api/projects/${projectId}/pdfs/${phase}`;
}

export function analysisDownloadUrl(projectId: number): string {
  return `${API_BASE}/api/projects/${projectId}/analysis`;
}

export async function deleteProject(projectId: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}`, { method: "DELETE" });
  await assertOk(res);
}

export async function updateProject(
  projectId: number,
  data: Partial<{ name: string; brand_url: string; competitor_urls: string; language: string; phase: string }>
): Promise<Project> {
  const form = new FormData();
  for (const [key, value] of Object.entries(data)) {
    if (value !== undefined) form.append(key, value);
  }
  const res = await fetch(`${API_BASE}/api/projects/${projectId}`, { method: "PATCH", body: form });
  await assertOk(res);
  return res.json();
}
