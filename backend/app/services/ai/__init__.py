"""
TradeAI - AI Service (Fase 6+)
Motor de inteligência artificial para geração de sinais de trading.

Implementação futura:
  - Modelos ML: RandomForest, XGBoost como baseline
  - Deep Learning: LSTM, Transformer para séries temporais
  - Reinforcement Learning para otimização de estratégia
  - Integração com LLMs para análise qualitativa

Interface esperada:
  AIService.generate_signal(symbol, candles, stats) → TradingSignal
  TradingSignal: { direction: BUY|SELL|HOLD, confidence: 0-100, reasoning: str }

Para integrar ao Market Score:
  Registrar no market_score.py como fator "ai".
"""
