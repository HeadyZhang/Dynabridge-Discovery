"use client";

import { useState, useRef } from "react";
import { Upload, FileText, Loader2, CheckCircle2 } from "lucide-react";
import { dcImportCSV } from "@/lib/datacube-api";
import KnowledgeNav from "@/components/KnowledgeNav";
import { useLanguage } from "@/lib/language-context";

export default function ImportPage() {
  const { t } = useLanguage();
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<{ imported: number; errors: string[] } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleImport = async (file: File) => {
    setImporting(true);
    setResult(null);
    try {
      const res = await dcImportCSV(file);
      setResult(res);
    } catch {
      setResult({ imported: 0, errors: ["Import failed"] });
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-50">
      <KnowledgeNav />
      <div className="max-w-3xl mx-auto px-6 py-6">
        <h1 className="text-lg font-semibold text-neutral-900 mb-6">{t("Import Campaign Data", "\u5bfc\u5165\u8425\u9500\u6570\u636e")}</h1>

        <div className="bg-white rounded-xl border border-neutral-200 p-5 space-y-4">
          <div
            onClick={() => fileRef.current?.click()}
            className="border-2 border-dashed border-neutral-200 rounded-xl p-8 text-center cursor-pointer hover:border-brand-300 hover:bg-brand-50/30 transition-all"
          >
            <Upload className="w-8 h-8 text-neutral-400 mx-auto mb-3" />
            <p className="text-sm text-neutral-500">{t("Click to upload CSV file", "\u70b9\u51fb\u4e0a\u4f20 CSV \u6587\u4ef6")}</p>
            <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={(e) => e.target.files?.[0] && handleImport(e.target.files[0])} />
          </div>

          <div className="bg-neutral-50 rounded-lg p-4">
            <h3 className="text-sm font-medium text-neutral-700 mb-2">{t("CSV Format", "CSV \u683c\u5f0f")}</h3>
            <code className="text-xs text-neutral-500 block whitespace-pre-wrap">
              campaign_name,brand,channel,audience_segment,content_theme,content_format,funnel_stage,geo,date,impressions,clicks,conversions,revenue,cost
            </code>
          </div>

          {importing && (
            <div className="flex items-center justify-center gap-2 py-4">
              <Loader2 className="w-5 h-5 animate-spin text-brand-500" />
              <span className="text-sm text-neutral-500">{t("Importing...", "\u5bfc\u5165\u4e2d...")}</span>
            </div>
          )}

          {result && (
            <div className={`rounded-lg p-4 ${result.errors.length > 0 ? "bg-amber-50" : "bg-green-50"}`}>
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle2 className="w-5 h-5 text-green-500" />
                <span className="text-sm font-medium">{t("Imported", "\u5df2\u5bfc\u5165")} {result.imported} {t("campaigns", "\u4e2a\u6d3b\u52a8")}</span>
              </div>
              {result.errors.length > 0 && (
                <div className="text-xs text-amber-700 space-y-1">
                  {result.errors.map((e, i) => <p key={i}>{e}</p>)}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
