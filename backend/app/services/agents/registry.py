"""
Agent Registry — Gerencia todos os agentes de trading.
Permite registrar, listar, ativar/desativar agentes.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.agents.base import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Registry central de agentes.
    Mantém a lista de agentes registrados e coordena execução.
    """

    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}
        self._results: dict[str, AgentResult] = {}

    def register(self, agent: BaseAgent) -> None:
        """Registra um agente no sistema."""
        if agent.name in self._agents:
            logger.warning(f"[AgentRegistry] Agente '{agent.name}' já registrado. Substituindo.")
        self._agents[agent.name] = agent
        logger.info(f"[AgentRegistry] Agente registrado: {agent.name}")

    def unregister(self, name: str) -> bool:
        """Remove um agente do registro."""
        if name in self._agents:
            del self._agents[name]
            self._results.pop(name, None)
            logger.info(f"[AgentRegistry] Agente removido: {name}")
            return True
        return False

    def get(self, name: str) -> BaseAgent | None:
        """Retorna um agente pelo nome."""
        return self._agents.get(name)

    def list_agents(self) -> list[dict]:
        """Lista todos os agentes registrados com status."""
        return [
            {
                "name": a.name,
                "description": a.description,
                "enabled": a.enabled,
                "last_execution": a.last_execution.isoformat() if a.last_execution else None,
            }
            for a in self._agents.values()
        ]

    def list_enabled(self) -> list[BaseAgent]:
        """Retorna apenas agentes habilitados."""
        return [a for a in self._agents.values() if a.enabled]

    @property
    def count(self) -> int:
        return len(self._agents)

    @property
    def enabled_count(self) -> int:
        return len(self.list_enabled())

    def enable(self, name: str) -> bool:
        """Ativa um agente."""
        agent = self.get(name)
        if agent:
            agent.enabled = True
            logger.info(f"[AgentRegistry] Agente ativado: {name}")
            return True
        return False

    def disable(self, name: str) -> bool:
        """Desativa um agente."""
        agent = self.get(name)
        if agent:
            agent.enabled = False
            logger.info(f"[AgentRegistry] Agente desativado: {name}")
            return True
        return False

    def store_result(self, agent_name: str, result: AgentResult) -> None:
        """Armazena o último resultado de um agente."""
        self._results[agent_name] = result

    def get_result(self, agent_name: str) -> AgentResult | None:
        """Retorna o último resultado de um agente."""
        return self._results.get(agent_name)

    def get_all_results(self) -> dict[str, AgentResult]:
        """Retorna todos os resultados recentes."""
        return dict(self._results)


# Singleton
agent_registry = AgentRegistry()
