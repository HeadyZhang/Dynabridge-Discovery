"use client";

import { useState, useRef, useEffect } from "react";
import { Upload, Loader2, CheckCircle2 } from "lucide-react";
import { dcImportCSV, dcImportPlatform, dcListCampaigns } from "@/lib/datacube-api";
import KnowledgeNav from "@/components/KnowledgeNav";
import { useLanguage } from "@/lib/language-context";

const PLATFORMS = [
  {
    id: "csv",
    label: "Generic CSV",
    label_cn: "\u901a\u7528 CSV",
    instructions_en: "Upload a CSV with columns: campaign_name, brand, channel, audience_segment, content_theme, content_format, funnel_stage, geo, date, impressions, clicks, conversions, revenue, cost",
    instructions_cn: "\u4e0a\u4f20 CSV\uff0c\u5305\u542b\u5217\uff1acampaign_name, brand, channel, audience_segment, content_theme, content_format, funnel_stage, geo, date, impressions, clicks, conversions, revenue, cost",
  },
  {
    id: "google_ads",
    label: "Google Ads",
    label_cn: "Google \u5e7f\u544a",
    instructions_en: "Export from Google Ads: Reports \u2192 Campaigns \u2192 Download CSV. Required columns: Campaign, Impressions, Clicks, Conversions, Cost, Conv. value",
    instructions_cn: "\u4ece Google Ads \u5bfc\u51fa\uff1a\u62a5\u544a \u2192 \u5e7f\u544a\u7cfb\u5217 \u2192 \u4e0b\u8f7d CSV\u3002\u9700\u8981\u5217\uff1aCampaign, Impressions, Clicks, Conversions, Cost, Conv. value",
  },
  {
    id: "meta_ads",
    label: "Meta Ads",
    label_cn: "Meta \u5e7f\u544a",
    instructions_en: "Export from Meta Ads Manager: Select campaigns \u2192 Export \u2192 CSV. Required columns: Campaign name, Impressions, Link clicks, Results, Amount spent (USD)",
    instructions_cn: "\u4ece Meta Ads Manager \u5bfc\u51fa\uff1a\u9009\u62e9\u5e7f\u544a\u7cfb\u5217 \u2192 \u5bfc\u51fa \u2192 CSV\u3002\u9700\u8981\u5217\uff1aCampaign name, Impressions, Link clicks, Results, Amount spent (USD)",
  },
  {
    id: "amazon_ads",
    label: "Amazon Ads",
    label_cn: "Amazon \u5e7f\u544a",
    instructions_en: "Export from Amazon Advertising: Campaign Manager \u2192 Download Report. Required columns: Campaign Name, Impressions, Clicks, Spend, Sales, Orders",
    instructions_cn: "\u4ece Amazon Advertising \u5bfc\u51fa\uff1aCampaign Manager \u2192 \u4e0b\u8f7d\u62a5\u544a\u3002\u9700\u8981\u5217\uff1aCampaign Name, Impressions, Clicks, Spend, Sales, Orders",
  },
];

export default function ImportPage() {
  const { t } = useLanguage();
  const [platform, setPlatform] = useState("csv");
  const [brand, setBrand] = useState("");
  const [brands, setBrands] = useState<string[]>([]);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<{ imported: number; errors: string[] } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    dcListCampaigns()
      .then((campaigns) => {
        const unique = [...new Set(campaigns.map((c) => c.brand_name))];
        setBrands(unique);
        if (unique.length > 0) setBrand(unique[0]);
      })
      .catch(() => {});
  }, []);

  const handleImport = async (file: File) => {
    setImporting(true);
    setResult(null);
    try {
      if (platform === "csv") {
        const res = await dcImportCSV(file);
        setResult(res);
      } else {
        const res = await dcImportPlatform(platform, brand, file);
        setResult({ imported: res.imported, errors: res.errors });
      }
    } catch {
      setResult({ imported: 0, errors: ["Import failed"] });
    } finally {
      setImporting(false);
    }
  };

  const currentPlatform = PLATFORMS.find((p) => p.id === platform) || PLATFORMS[0];

  return (
    <div className="min-h-screen bg-neutral-50">
      <KnowledgeNav />
      <div className="max-w-3xl mx-auto px-6 py-6">
        <h1 className="text-lg font-semibold text-neutral-900 mb-6">
          {t("Import Campaign Data", "\u5bfc\u5165\u8425\u9500\u6570\u636e")}
        </h1>

        {/* Platform tabs */}
        <div className="flex gap-1 mb-4 bg-neutral-100 rounded-lg p-1">
          {PLATFORMS.map((p) => (
            <button
              key={p.id}
              onClick={() => { setPlatform(p.id); setResult(null); }}
              className={`flex-1 px-3 py-2 text-sm rounded-md transition-colors ${
                platform === p.id
                  ? "bg-white text-neutral-900 font-medium shadow-sm"
                  : "text-neutral-500 hover:text-neutral-700"
              }`}
            >
              {t(p.label, p.label_cn)}
            </button>
          ))}
        </div>

        <div className="bg-white rounded-xl border border-neutral-200 p-5 space-y-4">
          {/* Brand selector for platform imports */}
          {platform !== "csv" && (
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                {t("Brand", "\u54c1\u724c")}
              </label>
              <div className="flex gap-2">
                <select
                  value={brand}
                  onChange={(e) => setBrand(e.target.value)}
                  className="flex-1 px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white"
                >
                  {brands.map((b) => (
                    <option key={b} value={b}>{b}</option>
                  ))}
                </select>
                <input
                  type="text"
                  value={brand}
                  onChange={(e) => setBrand(e.target.value)}
                  placeholder={t("Or type new brand", "\u6216\u8f93\u5165\u65b0\u54c1\u724c")}
                  className="flex-1 px-3 py-2 text-sm border border-neutral-200 rounded-lg"
                />
              </div>
            </div>
          )}

          {/* Instructions */}
          <div className="bg-neutral-50 rounded-lg p-4">
            <h3 className="text-sm font-medium text-neutral-700 mb-2">
              {t("Instructions", "\u5bfc\u5165\u8bf4\u660e")}
            </h3>
            <p className="text-xs text-neutral-500">
              {t(currentPlatform.instructions_en, currentPlatform.instructions_cn)}
            </p>
          </div>

          {/* Upload area */}
          <div
            onClick={() => fileRef.current?.click()}
            className="border-2 border-dashed border-neutral-200 rounded-xl p-8 text-center cursor-pointer hover:border-brand-300 hover:bg-brand-50/30 transition-all"
          >
            <Upload className="w-8 h-8 text-neutral-400 mx-auto mb-3" />
            <p className="text-sm text-neutral-500">
              {t("Click to upload CSV file", "\u70b9\u51fb\u4e0a\u4f20 CSV \u6587\u4ef6")}
            </p>
            <input
              ref={fileRef}
              type="file"
              accept=".csv"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleImport(e.target.files[0])}
            />
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
                <span className="text-sm font-medium">
                  {t("Imported", "\u5df2\u5bfc\u5165")} {result.imported} {t("campaigns", "\u4e2a\u6d3b\u52a8")}
                </span>
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
