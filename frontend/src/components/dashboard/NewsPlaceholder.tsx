/**
 * TradeAI - Componente: Placeholder de Notícias de Mercado
 * Área reservada para feed de notícias com análise de sentimento.
 * Fase 2: integrar com APIs de notícias financeiras + NLP.
 */

export function NewsPlaceholder() {
  const mockNews = [
    { title: "Banco Central mantém Selic em 10,5%",   sentiment: "neutral",  time: "há 2h" },
    { title: "PETR4 sobe 3% após resultado trimestral", sentiment: "positive", time: "há 4h" },
    { title: "Dólar recua frente ao real",             sentiment: "positive", time: "há 6h" },
  ];

  const sentimentStyle: Record<string, string> = {
    positive: "text-emerald-400",
    negative: "text-red-400",
    neutral:  "text-[#9ca3af]",
  };

  const sentimentLabel: Record<string, string> = {
    positive: "↑ Positivo",
    negative: "↓ Negativo",
    neutral:  "● Neutro",
  };

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-[#f9fafb]">Notícias de Mercado</h3>
          <p className="text-xs text-[#6b7280] mt-0.5">Análise de sentimento — Fase 2</p>
        </div>
        <span className="text-xs px-2 py-0.5 rounded-full bg-[#1f2937] text-[#6b7280]">
          Preview
        </span>
      </div>

      <div className="flex flex-col gap-2">
        {mockNews.map((news, i) => (
          <div
            key={i}
            className="p-3 rounded-lg bg-[#0a0e1a] border border-[#1f2937] opacity-50 cursor-not-allowed"
          >
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm text-[#d1d5db] leading-snug flex-1">{news.title}</p>
              <span className={`text-xs shrink-0 ${sentimentStyle[news.sentiment]}`}>
                {sentimentLabel[news.sentiment]}
              </span>
            </div>
            <p className="text-xs text-[#4b5563] mt-1.5">{news.time}</p>
          </div>
        ))}
      </div>

      <p className="text-xs text-center text-[#4b5563] pt-2 border-t border-[#1f2937]">
        Feed real de notícias disponível na Fase 2
      </p>
    </div>
  );
}
