"""Interface comum das IAs (seção 4 da spec do simulador).

Toda IA recebe o estado da partida, o NOME do jogador que está decidindo
(necessário porque durante uma janela de barragem quem decide não é
necessariamente `estado.turno_de`), a lista de ações legais (produzida
pelo motor) e o config de regras vigente (necessário para prever dano
etc. — o mesmo config pode variar entre partidas de um experimento);
devolve UMA dessas ações — nunca inventa uma ação fora da lista. Isso
garante que nenhuma IA trapaceie e mantém MCTS simples de implementar
(mesma interface para simular rollouts).
"""
from __future__ import annotations

from typing import Protocol


class AI(Protocol):
    def escolher_acao(self, estado, jogador_nome: str, acoes_legais: list, config: dict):
        ...
