"""
TradeAI - News Service (Fase 3+)
Coleta e normalização de notícias financeiras de múltiplas fontes.

Implementação futura:
  - NewsAPI, Finnhub, CryptoPanic
  - Normalização de conteúdo
  - Cache de artigos lidos
  - Deduplicação por URL/hash

Para integrar ao Market Score:
  Implementar NewsService.get_score(symbol) → float (0.0 a 1.0)
  Registrar no market_score.py como fator "news".
"""
