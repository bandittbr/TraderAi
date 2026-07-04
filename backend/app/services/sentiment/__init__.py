"""
TradeAI - Sentiment Service (Fase 4+)
Análise de sentimento de mercado a partir de notícias e redes sociais.

Implementação futura:
  - VADER Sentiment Analysis (rápido, sem GPU)
  - HuggingFace FinBERT (precisão maior para textos financeiros)
  - Twitter/X API para sentiment social
  - Fear & Greed Index

Para integrar ao Market Score:
  Implementar SentimentService.get_score(symbol) → float (0.0 a 1.0)
  Registrar no market_score.py como fator "sentiment".
"""
