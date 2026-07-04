"""
TradeAI - WebSocket Connection Manager
Gerencia todas as conexões WebSocket ativas do frontend.
Responsável por aceitar, registrar, desconectar e transmitir mensagens.

Fase 2: broadcast de atualizações de preço.
Fase 3+: canais por símbolo, autenticação, rate limiting, compressão.
"""

import json
from fastapi import WebSocket
from app.logger import get_logger

logger = get_logger(__name__)


class WebSocketManager:
    """
    Singleton que mantém a lista de conexões WebSocket ativas.
    Thread-safe para o model single-threaded asyncio do FastAPI.
    """

    def __init__(self) -> None:
        # Lista de clientes conectados
        self._connections: list[WebSocket] = []

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    async def connect(self, websocket: WebSocket) -> None:
        """Aceita e registra uma nova conexão WebSocket."""
        await websocket.accept()
        self._connections.append(websocket)
        logger.info(
            f"WebSocket cliente conectado. "
            f"Total: {self.connection_count}"
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove uma conexão encerrada."""
        if websocket in self._connections:
            self._connections.remove(websocket)
        logger.info(
            f"WebSocket cliente desconectado. "
            f"Total: {self.connection_count}"
        )

    async def broadcast(self, data: dict) -> None:
        """
        Transmite um payload JSON para todos os clientes conectados.
        Clientes com falha são removidos da lista automaticamente.
        """
        if not self._connections:
            return

        message = json.dumps(data)
        dead: list[WebSocket] = []

        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws)

    async def send_to(self, websocket: WebSocket, data: dict) -> None:
        """Envia mensagem para um único cliente específico."""
        try:
            await websocket.send_text(json.dumps(data))
        except Exception as exc:
            logger.warning(f"Falha ao enviar para cliente: {exc}")
            self.disconnect(websocket)


# Instância singleton compartilhada entre endpoints e o scheduler
ws_manager = WebSocketManager()
