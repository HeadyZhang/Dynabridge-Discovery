"use client";

import { useState, useRef, useCallback } from "react";
import {
  Upload,
  Globe,
  Plus,
  X,
  ChevronLeft,
  ChevronRight,
  Download,
  Send,
  CheckCircle2,
  Loader2,
  Circle,
  FileText,
  MessageSquare,
} from "lucide-react";
import { t, type Locale } from "@/lib/i18n";
import {
  createProject,
  uploadFile,
  generateReport,
  getSlides,
  addComment,
  getComments,
  downloadUrl,
  type SlidePreview,
  type Comment,
  type ProgressEvent,
} from "@/lib/api";

type Step = "scraping" | "parsing" | "analyzing" | "generating";

const STEPS: Step[] = ["scraping", "parsing", "analyzing", "generating"];

export default function Home() {
  const [locale, setLocale] = useState<Locale>("en");

  // Form state
  const [projectName, setProjectName] = useState("");
  const [brandUrl, setBrandUrl] = useState("");
  const [competitors, setCompetitors] = useState<string[]>([]);
  const [competitorInput, setCompetitorInput] = useState("");
  const [language, setLanguage] = useState("en");
  const [files, setFiles] = useState<File[]>([]);

  // Pipeline state
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentStep, setCurrentStep] = useState<Step | null>(null);
  const [completedSteps, setCompletedSteps] = useState<Set<Step>>(new Set());
  const [projectId, setProjectId] = useState<number | null>(null);

  // Preview state
  const [slides, setSlides] = useState<SlidePreview[]>([]);
  const [currentSlide, setCurrentSlide] = useState(0);

  // Review state
  const [comments, setComments] = useState<Comment[]>([]);
  const [commentText, setCommentText] = useState("");
  const [authorName, setAuthorName] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleAddCompetitor = () => {
    if (competitorInput.trim()) {
      setCompetitors((prev) => [...prev, competitorInput.trim()]);
      setCompetitorInput("");
    }
  };

  const handleRemoveCompetitor = (index: number) => {
    setCompetitors((prev) => prev.filter((_, i) => i !== index));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles((prev) => [...prev, ...Array.from(e.target.files!)]);
    }
  };

  const handleRemoveFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files) {
      setFiles((prev) => [...prev, ...Array.from(e.dataTransfer.files)]);
    }
  }, []);

  const handleGenerate = async () => {
    if (!projectName.trim()) return;

    setIsGenerating(true);
    setCompletedSteps(new Set());
    setCurrentStep(null);
    setSlides([]);

    try {
      // Create project
      const project = await createProject({
        name: projectName,
        brand_url: brandUrl,
        competitor_urls: competitors,
        language,
      });
      setProjectId(project.id);

      // Upload files
      for (const file of files) {
        await uploadFile(project.id, file);
      }

      // Generate report with SSE progress
      generateReport(
        project.id,
        (event: ProgressEvent) => {
          setCurrentStep(event.step as Step);
          if (event.done) {
            setCompletedSteps((prev) => new Set([...prev, event.step as Step]));
          }
        },
        async () => {
          setIsGenerating(false);
          setCurrentStep(null);
          // Load slide previews
          const slideData = await getSlides(project.id);
          setSlides(slideData);
          setCurrentSlide(0);
          // Load comments
          const commentData = await getComments(project.id);
          setComments(commentData);
        },
        (msg: string) => {
          setIsGenerating(false);
          console.error("Generation error:", msg);
        }
      );
    } catch (err) {
      setIsGenerating(false);
      console.error(err);
    }
  };

  const handleSubmitComment = async () => {
    if (!commentText.trim() || !authorName.trim() || projectId === null) return;
    const comment = await addComment(projectId, {
      slide_order: currentSlide,
      author: authorName,
      content: commentText,
    });
    setComments((prev) => [...prev, comment]);
    setCommentText("");
  };

  const slideComments = comments.filter(
    (c) => c.slide_order === currentSlide || c.slide_order === null
  );

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <header className="flex items-center justify-between px-6 h-14 border-b border-neutral-200 bg-white">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-brand-500 flex items-center justify-center">
            <span className="text-white font-bold text-sm">db</span>
          </div>
          <h1 className="text-lg font-semibold text-neutral-900">
            {t("app.title", locale)}
          </h1>
          <span className="text-sm text-neutral-400 hidden sm:inline">
            {t("app.subtitle", locale)}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setLocale(locale === "en" ? "zh" : "en")}
            className="px-3 py-1.5 text-sm font-medium text-neutral-600 hover:text-brand-500 rounded-lg hover:bg-brand-50 transition-colors"
          >
            {locale === "en" ? "中文" : "EN"}
          </button>
        </div>
      </header>

      {/* Main: dual-panel layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Panel — Input & Controls */}
        <aside className="w-[380px] border-r border-neutral-200 bg-white flex flex-col overflow-y-auto">
          <div className="p-5 space-y-5">
            {/* Project Name */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                {t("form.name", locale)}
              </label>
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder={t("form.name.placeholder", locale)}
                className="w-full px-3 py-2 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all"
              />
            </div>

            {/* Brand URL */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                {t("form.url", locale)}
              </label>
              <div className="relative">
                <Globe className="absolute left-3 top-2.5 w-4 h-4 text-neutral-400" />
                <input
                  type="url"
                  value={brandUrl}
                  onChange={(e) => setBrandUrl(e.target.value)}
                  placeholder={t("form.url.placeholder", locale)}
                  className="w-full pl-9 pr-3 py-2 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all"
                />
              </div>
            </div>

            {/* File Upload */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                {t("form.files", locale)}
              </label>
              <div
                onDrop={handleDrop}
                onDragOver={(e) => e.preventDefault()}
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-neutral-200 rounded-xl p-4 text-center cursor-pointer hover:border-brand-300 hover:bg-brand-50/30 transition-all"
              >
                <Upload className="w-6 h-6 text-neutral-400 mx-auto mb-2" />
                <p className="text-sm text-neutral-500">
                  {t("form.files.hint", locale)}
                </p>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".pdf,.docx,.doc,.pptx,.png,.jpg,.jpeg"
                  onChange={handleFileChange}
                  className="hidden"
                />
              </div>
              {files.length > 0 && (
                <div className="mt-2 space-y-1">
                  {files.map((f, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between px-3 py-1.5 bg-neutral-50 rounded-lg text-sm"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <FileText className="w-4 h-4 text-brand-500 shrink-0" />
                        <span className="truncate">{f.name}</span>
                      </div>
                      <button
                        onClick={() => handleRemoveFile(i)}
                        className="text-neutral-400 hover:text-red-500 shrink-0"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Competitors */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                {t("form.competitors", locale)}
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={competitorInput}
                  onChange={(e) => setCompetitorInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAddCompetitor()}
                  placeholder={t("form.competitors.placeholder", locale)}
                  className="flex-1 px-3 py-2 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all"
                />
                <button
                  onClick={handleAddCompetitor}
                  className="px-3 py-2 bg-neutral-100 hover:bg-neutral-200 rounded-xl transition-colors"
                >
                  <Plus className="w-4 h-4 text-neutral-600" />
                </button>
              </div>
              {competitors.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {competitors.map((c, i) => (
                    <span
                      key={i}
                      className="inline-flex items-center gap-1 px-2.5 py-1 bg-brand-50 text-brand-700 rounded-lg text-sm"
                    >
                      {c}
                      <button
                        onClick={() => handleRemoveCompetitor(i)}
                        className="hover:text-red-500"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Language */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                {t("form.language", locale)}
              </label>
              <div className="flex gap-2">
                {[
                  { value: "en", label: t("form.language.en", locale) },
                  { value: "zh", label: t("form.language.zh", locale) },
                  { value: "en+zh", label: t("form.language.both", locale) },
                ].map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setLanguage(opt.value)}
                    className={`flex-1 py-2 text-sm rounded-xl transition-all ${
                      language === opt.value
                        ? "bg-brand-500 text-white shadow-sm"
                        : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Divider */}
            <div className="border-t border-neutral-100" />

            {/* Progress */}
            {(isGenerating || completedSteps.size > 0) && (
              <div className="space-y-2.5">
                {STEPS.map((step) => {
                  const isDone = completedSteps.has(step);
                  const isCurrent = currentStep === step;
                  return (
                    <div key={step} className="flex items-center gap-2.5">
                      {isDone ? (
                        <CheckCircle2 className="w-5 h-5 text-green-500" />
                      ) : isCurrent ? (
                        <Loader2 className="w-5 h-5 text-brand-500 animate-spin" />
                      ) : (
                        <Circle className="w-5 h-5 text-neutral-300" />
                      )}
                      <span
                        className={`text-sm ${
                          isDone
                            ? "text-green-600"
                            : isCurrent
                              ? "text-brand-500 font-medium"
                              : "text-neutral-400"
                        }`}
                      >
                        {t(`progress.${step}`, locale)}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Generate Button */}
            <button
              onClick={handleGenerate}
              disabled={isGenerating || !projectName.trim()}
              className="w-full py-3 bg-brand-500 text-white font-medium rounded-xl hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm hover:shadow-md flex items-center justify-center gap-2"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {t("form.generating", locale)}
                </>
              ) : (
                t("form.generate", locale)
              )}
            </button>

            {/* Download Buttons */}
            {projectId && slides.length > 0 && (
              <div className="flex gap-2">
                <a
                  href={downloadUrl(projectId)}
                  className="flex-1 py-2.5 flex items-center justify-center gap-2 border border-brand-500 text-brand-500 font-medium rounded-xl hover:bg-brand-50 transition-all text-sm"
                >
                  <Download className="w-4 h-4" />
                  {t("download.pptx", locale)}
                </a>
              </div>
            )}
          </div>
        </aside>

        {/* Right Panel — Preview & Review */}
        <main className="flex-1 flex flex-col bg-neutral-50 overflow-hidden">
          {slides.length === 0 ? (
            /* Empty state */
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="w-20 h-20 rounded-2xl bg-brand-50 flex items-center justify-center mx-auto mb-4">
                  <FileText className="w-10 h-10 text-brand-300" />
                </div>
                <p className="text-neutral-400 text-lg">
                  {t("preview.empty", locale)}
                </p>
              </div>
            </div>
          ) : (
            <>
              {/* Slide Preview Area */}
              <div className="flex-1 flex items-center justify-center p-6 min-h-0">
                <div className="relative w-full max-w-4xl aspect-[16/9]">
                  {/* Slide image */}
                  <div className="w-full h-full bg-white rounded-xl shadow-lg overflow-hidden border border-neutral-200">
                    {slides[currentSlide]?.preview_url ? (
                      <img
                        src={slides[currentSlide].preview_url}
                        alt={`Slide ${currentSlide + 1}`}
                        className="w-full h-full object-contain"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-neutral-400">
                        {t("preview.slide", locale)} {currentSlide + 1}
                      </div>
                    )}
                  </div>

                  {/* Navigation arrows */}
                  <button
                    onClick={() => setCurrentSlide((s) => Math.max(0, s - 1))}
                    disabled={currentSlide === 0}
                    className="absolute left-[-48px] top-1/2 -translate-y-1/2 w-10 h-10 flex items-center justify-center rounded-full bg-white shadow-md hover:bg-neutral-50 disabled:opacity-30 transition-all"
                  >
                    <ChevronLeft className="w-5 h-5 text-neutral-600" />
                  </button>
                  <button
                    onClick={() =>
                      setCurrentSlide((s) =>
                        Math.min(slides.length - 1, s + 1)
                      )
                    }
                    disabled={currentSlide === slides.length - 1}
                    className="absolute right-[-48px] top-1/2 -translate-y-1/2 w-10 h-10 flex items-center justify-center rounded-full bg-white shadow-md hover:bg-neutral-50 disabled:opacity-30 transition-all"
                  >
                    <ChevronRight className="w-5 h-5 text-neutral-600" />
                  </button>
                </div>
              </div>

              {/* Slide counter + slide strip */}
              <div className="px-6 pb-2">
                <div className="flex items-center justify-center gap-2 text-sm text-neutral-500 mb-3">
                  <span>
                    {t("preview.slide", locale)} {currentSlide + 1}{" "}
                    {t("preview.of", locale)} {slides.length}
                  </span>
                </div>
                <div className="flex gap-1.5 overflow-x-auto pb-2 justify-center">
                  {slides.map((_, i) => (
                    <button
                      key={i}
                      onClick={() => setCurrentSlide(i)}
                      className={`w-16 h-10 rounded-md border-2 transition-all shrink-0 flex items-center justify-center text-xs ${
                        i === currentSlide
                          ? "border-brand-500 bg-brand-50 text-brand-500 font-medium"
                          : "border-neutral-200 bg-white text-neutral-400 hover:border-neutral-300"
                      }`}
                    >
                      {i + 1}
                    </button>
                  ))}
                </div>
              </div>

              {/* Comment section */}
              <div className="border-t border-neutral-200 bg-white px-6 py-4">
                <div className="flex items-center gap-2 mb-3">
                  <MessageSquare className="w-4 h-4 text-brand-500" />
                  <h3 className="text-sm font-medium text-neutral-700">
                    {t("review.title", locale)}
                  </h3>
                  {slideComments.length > 0 && (
                    <span className="text-xs bg-brand-50 text-brand-500 px-2 py-0.5 rounded-full">
                      {slideComments.length}
                    </span>
                  )}
                </div>

                {/* Existing comments */}
                {slideComments.length > 0 && (
                  <div className="space-y-2 mb-3 max-h-32 overflow-y-auto">
                    {slideComments.map((c) => (
                      <div
                        key={c.id}
                        className={`flex items-start gap-2 px-3 py-2 rounded-lg text-sm ${
                          c.resolved
                            ? "bg-green-50 text-green-700"
                            : "bg-neutral-50 text-neutral-700"
                        }`}
                      >
                        <span className="font-medium shrink-0">
                          {c.author}:
                        </span>
                        <span className="flex-1">{c.content}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* New comment input */}
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={authorName}
                    onChange={(e) => setAuthorName(e.target.value)}
                    placeholder={t("review.author", locale)}
                    className="w-24 px-3 py-2 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                  />
                  <input
                    type="text"
                    value={commentText}
                    onChange={(e) => setCommentText(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSubmitComment()}
                    placeholder={t("review.placeholder", locale)}
                    className="flex-1 px-3 py-2 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
                  />
                  <button
                    onClick={handleSubmitComment}
                    disabled={!commentText.trim() || !authorName.trim()}
                    className="px-4 py-2 bg-brand-500 text-white rounded-xl hover:bg-brand-600 disabled:opacity-50 transition-all"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
