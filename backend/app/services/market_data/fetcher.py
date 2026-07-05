"""
TradeAI - MarketDataFetcher
Cliente HTTP para a API pública da Binance (sem autenticação).
Responsável exclusivamente por buscar dados externos — sem lógica de negócio.

Fase 2: REST API para candles e estatísticas 24h.
Fase 3+: adicionar suporte a outras exchanges, WebSocket de klines.
"""

import httpx
from app.logger import get_logger

logger = get_logger(__name__)

# Base URL da Binance REST API pública
BINANCE_BASE = "https://data-api.binance.vision"

# Timeframes nativos da Binance
# O timeframe "45m" NÃO existe na Binance — é calculado por resampling de 15m
NATIVE_INTERVALS = {"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"}


class MarketDataFetcher:
    """
    Encapsula todas as chamadas à Binance REST API.
    Stateless — pode ser instanciado múltiplas vezes sem efeitos colaterais.
    """

    # ── Candles ───────────────────────────────────────────────────────────────

    async def fetch_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 100,
    ) -> list[list]:
        """
        Busca candles OHLCV da Binance.
        Para o timeframe '45m' (não nativo), busca candles de 15m e faz resampling.

        Retorna lista de candles no formato Binance:
        [open_time_ms, open, high, low, close, volume, close_time_ms, ...]
        """
        if interval == "45m":
            return await self._fetch_45m(symbol, limit)

        if interval not in NATIVE_INTERVALS:
            raise ValueError(f"Timeframe '{interval}' não suportado.")

        return await self._fetch_raw_klines(symbol, interval, limit)

    async def _fetch_raw_klines(
        self,
        symbol: str,
        interval: str,
        limit: int,
    ) -> list[list]:
        """Busca candles diretamente da Binance."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{BINANCE_BASE}/api/v3/klines",
                params={
                    "symbol": symbol.upper(),
                    "interval": interval,
                    "limit": min(limit, 1000),
                },
            )
            response.raise_for_status()
            return response.json()

    async def _fetch_45m(self, symbol: str, limit: int) -> list[list]:
        """
        Calcula candles de 45m a partir de 3 candles de 15m.
        Binance não oferece 45m nativamente — resampling obrigatório.
        """
        raw_15m = await self._fetch_raw_klines(symbol, "15m", limit * 3)
        return self._resample_45m(raw_15m)

    @staticmethod
    def _resample_45m(candles_15m: list[list]) -> list[list]:
        """
        Agrupa candles de 15m em blocos de 3 → 1 candle de 45m.
        Cada grupo:
          open  = primeiro candle do grupo
          close = último candle do grupo
          high  = máxima do grupo
          low   = mínima do grupo
          volume= soma do grupo
        """
        result = []
        for i in range(0, len(candles_15m) - 2, 3):
            group = candles_15m[i : i + 3]
            if len(group) < 3:
                break
            result.append([
                group[0][0],                                   # open_time_ms
                group[0][1],                                   # open
                str(max(float(c[2]) for c in group)),          # high
                str(min(float(c[3]) for c in group)),          # low
                group[2][4],                                   # close
                str(sum(float(c[5]) for c in group)),          # volume
                group[2][6],                                   # close_time_ms
            ])
        return result

    # ── Estatísticas 24h ──────────────────────────────────────────────────────

    async def fetch_ticker_24h(self, symbol: str) -> dict:
        """
        Busca estatísticas de 24h para um símbolo.
        Retorna: lastPrice, priceChangePercent, volume, highPrice, lowPrice, etc.
        """
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(
                f"{BINANCE_BASE}/api/v3/ticker/24hr",
                params={"symbol": symbol.upper()},
            )
            response.raise_for_status()
            return response.json()

    async def fetch_price(self, symbol: str) -> float:
        """Busca apenas o preço atual de um símbolo (endpoint leve)."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{BINANCE_BASE}/api/v3/ticker/price",
                params={"symbol": symbol.upper()},
            )
            response.raise_for_status()
            return float(response.json()["price"])


# Instância singleton reutilizável
fetcher = MarketDataFetcher()
