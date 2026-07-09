"""Interface comum das IAs (seção 4 da spec do simulador).

Toda IA recebe o estado da partida e a lista de ações legais (produzida
pelo motor) e devolve UMA dessas ações — nunca inventa uma ação fora da
lista. Isso garante que nenhuma IA trapaceie e mantém MCTS simples de
implementar (mesma interface para simular rollouts).
"""
from __future__ import annotations

from typing import Protocol


class AI(Protocol):
    def escolher_acao(self, estado, acoes_legais: list):
        ...
