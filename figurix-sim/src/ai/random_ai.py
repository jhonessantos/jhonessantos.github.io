"""Nível 1: RandomAI — escolhe uniformemente entre as ações legais.

Baseline e teste de robustez do motor (seção 4 da spec do simulador).
"""
from __future__ import annotations

import random


class RandomAI:
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)

    def escolher_acao(self, estado, jogador_nome: str, acoes_legais: list, config: dict):
        return self.rng.choice(acoes_legais)
