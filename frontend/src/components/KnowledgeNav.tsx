"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Menu, X } from "lucide-react";
import { useLanguage } from "@/lib/language-context";

const NAV_ITEMS = [
  { href: "/", label_en: "Home", label_cn: "\u9996\u9875" },
  { href: "/knowledge", label_en: "Knowledge Base", label_cn: "\u6848\u4f8b\u5e93" },
  { href: "/insights", label_en: "Consumer Insights", label_cn: "\u6d88\u8d39\u8005\u6d1e\u5bdf" },
  { href: "/industries", label_en: "Industries", label_cn: "\u884c\u4e1a\u5206\u6790" },
  { href: "/marketing", label_en: "Marketing Intelligence", label_cn: "\u8425\u9500\u60c5\u62a5" },
  { href: "/dashboard", label_en: "Dashboard", label_cn: "\u6570\u636e\u770b\u677f" },
];

export default function KnowledgeNav() {
  const pathname = usePathname();
  const { lang, setLang, t } = useLanguage();
  const [mobileOpen, setMobileOpen] = useState(false);

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <header className="sticky top-0 z-40 bg-white border-b border-neutral-200">
      <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-14">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 shrink-0">
          <span className="text-lg font-bold text-brand-500">DynaBridge</span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-1">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                isActive(item.href)
                  ? "bg-brand-50 text-brand-600 font-medium"
                  : "text-neutral-600 hover:text-brand-500 hover:bg-neutral-50"
              }`}
            >
              {lang === "en" ? item.label_en : item.label_cn}
            </Link>
          ))}
        </nav>

        {/* Right: language toggle + mobile menu */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setLang(lang === "en" ? "cn" : "en")}
            className="px-3 py-1 text-sm border border-neutral-200 rounded-full hover:bg-neutral-50 transition-colors"
          >
            {lang === "en" ? "\u4e2d\u6587" : "EN"}
          </button>

          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="md:hidden p-1.5 rounded-lg hover:bg-neutral-100 transition-colors"
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile nav */}
      {mobileOpen && (
        <nav className="md:hidden border-t border-neutral-100 bg-white px-4 py-2">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMobileOpen(false)}
              className={`block px-3 py-2 text-sm rounded-lg ${
                isActive(item.href)
                  ? "bg-brand-50 text-brand-600 font-medium"
                  : "text-neutral-600 hover:bg-neutral-50"
              }`}
            >
              {lang === "en" ? item.label_en : item.label_cn}
            </Link>
          ))}
        </nav>
      )}
    </header>
  );
}
