"use client";

import type { NewsArticle } from "@/types";

interface Props {
  articles: NewsArticle[];
  loading?: boolean;
}

const SENTIMENT_STYLE = {
  POSITIVE: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
  NEUTRAL:  "text-[#9ca3af] bg-[#1f2937] border-[#374151]",
  NEGATIVE: "text-red-400 bg-red-500/10 border-red-500/20",
};

const SENTIMENT_DOT = {
  POSITIVE: "bg-emerald-400",
  NEUTRAL:  "bg-[#6b7280]",
  NEGATIVE: "bg-red-400",
};

function fmtDate(iso: string) {
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 3600)  return `${Math.floor(diff / 60)}m atrás`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h atrás`;
  return `${Math.floor(diff / 86400)}d atrás`;
}

export function NewsFeed({ articles, loading }: Props) {
  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-[#f9fafb]">News Feed</h3>
        <span className="text-xs text-[#4b5563]">{articles.length} notícias</span>
      </div>

      {loading ? (
        <div className="h-40 flex items-center justify-center">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : articles.length === 0 ? (
        <div className="h-40 flex flex-col items-center justify-center gap-2">
          <p className="text-sm text-[#6b7280]">Sem notícias recentes</p>
          <p className="text-xs text-[#4b5563]">Aguardando primeira sincronização (~30s)</p>
        </div>
      ) : (
        <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
          {articles.map((a) => (
            <a
              key={a.id}
              href={a.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block p-3 rounded-lg bg-[#0a0e1a] border border-[#1f2937] hover:border-[#374151] transition-colors group"
            >
              <div className="flex items-start justify-between gap-2 mb-1">
                <p className="text-xs font-medium text-[#f9fafb] group-hover:text-blue-300 line-clamp-2 transition-colors">
                  {a.title}
                </p>
                <span className={`shrink-0 text-[10px] px-1.5 py-0.5 rounded border ${
                  SENTIMENT_STYLE[a.sentiment]
                }`}>
                  {a.sentiment === "POSITIVE" ? "POS" : a.sentiment === "NEGATIVE" ? "NEG" : "NEU"}
                </span>
              </div>
              <div className="flex items-center gap-2 mt-1">
                <div className={`w-1.5 h-1.5 rounded-full ${SENTIMENT_DOT[a.sentiment]}`} />
                <span className="text-[10px] text-[#6b7280]">{a.source}</span>
                <span className="text-[10px] text-[#4b5563]">·</span>
                <span className="text-[10px] text-[#4b5563]">{fmtDate(a.published_at)}</span>
                <span className="text-[10px] text-[#4b5563]">·</span>
                <span className="text-[10px] text-[#6b7280]">{a.asset}</span>
                <span className="text-[10px] text-[#4b5563] ml-auto">
                  Impacto: {a.impact_score.toFixed(0)}
                </span>
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
