"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Plus, Loader2 } from "lucide-react";
import { dcCreateCampaign, dcGetTagOptions, type TagOptions } from "@/lib/datacube-api";
import KnowledgeNav from "@/components/KnowledgeNav";
import { useLanguage } from "@/lib/language-context";

export default function NewCampaignPage() {
  const { t } = useLanguage();
  const router = useRouter();
  const [tags, setTags] = useState<TagOptions | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    campaign_name: "", brand_name: "", campaign_type: "paid_media",
    audience: { segment: "", motivation: "", geo_market: "" },
    content: { theme: "", format: "", message_type: "" },
    context: { channel: "", placement: "", funnel_stage: "" },
  });

  useEffect(() => { dcGetTagOptions().then(setTags).catch(() => {}); }, []);

  const handleSubmit = async () => {
    if (!form.campaign_name || !form.brand_name) return;
    setSaving(true);
    try {
      const result = await dcCreateCampaign(form);
      router.push(`/datacube/campaigns/${result.id}`);
    } catch { setSaving(false); }
  };

  const updateField = (section: "audience" | "content" | "context", key: string, value: string) => {
    setForm({ ...form, [section]: { ...form[section], [key]: value } });
  };

  return (
    <div className="min-h-screen bg-neutral-50">
      <KnowledgeNav />
      <div className="max-w-3xl mx-auto px-6 py-6">
        <h1 className="text-lg font-semibold text-neutral-900 mb-6">{t("New Campaign", "\u65b0\u5efa\u8425\u9500\u6d3b\u52a8")}</h1>

        <div className="bg-white rounded-xl border border-neutral-200 p-5 space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">{t("Campaign Name", "\u6d3b\u52a8\u540d\u79f0")}</label>
              <input value={form.campaign_name} onChange={(e) => setForm({ ...form, campaign_name: e.target.value })} className="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">{t("Brand", "\u54c1\u724c")}</label>
              <input value={form.brand_name} onChange={(e) => setForm({ ...form, brand_name: e.target.value })} className="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm" />
            </div>
          </div>

          {tags && (
            <>
              <div>
                <h3 className="text-sm font-medium text-neutral-700 mb-2">{t("Audience Tags", "\u53d7\u4f17\u6807\u7b7e")}</h3>
                <div className="grid grid-cols-3 gap-3">
                  {(["segment", "motivation", "geo_market"] as const).map((key) => (
                    <select key={key} value={form.audience[key]} onChange={(e) => updateField("audience", key, e.target.value)} className="px-3 py-1.5 text-sm border border-neutral-200 rounded-lg">
                      <option value="">{key}</option>
                      {tags.audience[key]?.map((v) => <option key={v} value={v}>{v}</option>)}
                    </select>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="text-sm font-medium text-neutral-700 mb-2">{t("Content Tags", "\u5185\u5bb9\u6807\u7b7e")}</h3>
                <div className="grid grid-cols-3 gap-3">
                  {(["theme", "format", "message_type"] as const).map((key) => (
                    <select key={key} value={form.content[key]} onChange={(e) => updateField("content", key, e.target.value)} className="px-3 py-1.5 text-sm border border-neutral-200 rounded-lg">
                      <option value="">{key}</option>
                      {tags.content[key]?.map((v) => <option key={v} value={v}>{v}</option>)}
                    </select>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="text-sm font-medium text-neutral-700 mb-2">{t("Context Tags", "\u573a\u666f\u6807\u7b7e")}</h3>
                <div className="grid grid-cols-3 gap-3">
                  {(["channel", "placement", "funnel_stage"] as const).map((key) => (
                    <select key={key} value={form.context[key]} onChange={(e) => updateField("context", key, e.target.value)} className="px-3 py-1.5 text-sm border border-neutral-200 rounded-lg">
                      <option value="">{key}</option>
                      {tags.context[key]?.map((v) => <option key={v} value={v}>{v}</option>)}
                    </select>
                  ))}
                </div>
              </div>
            </>
          )}

          <button onClick={handleSubmit} disabled={saving || !form.campaign_name} className="w-full py-3 bg-brand-500 text-white font-medium rounded-xl hover:bg-brand-600 disabled:opacity-50 transition-colors flex items-center justify-center gap-2">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            {t("Create Campaign", "\u521b\u5efa\u6d3b\u52a8")}
          </button>
        </div>
      </div>
    </div>
  );
}
