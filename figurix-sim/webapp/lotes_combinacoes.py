"""Combinações de IA x IA x Deck x Deck para "rodar tudo de uma vez"
(vários oponentes/decks de cada lado): funções puras de dados, sem tocar
banco/HTTP, pra poderem ser testadas sem precisar subir o FastAPI.

A quantidade de partidas pedida vale POR combinação (seção pedida pelo
usuário) — se há M IAs do lado A, N do lado B, P decks A e Q decks B,
isso gera M*N*P*Q lotes independentes, cada um com a quantidade de
partidas configurada.
"""
from __future__ import annotations

import itertools

PASSO_SEED_COMBINACAO = 10_000_000


def gerar_combinacoes(
    ia_a_chaves: list[str], ia_b_chaves: list[str], deck_a_ids: list[int], deck_b_ids: list[int]
) -> list[tuple]:
    """Produto cartesiano das 4 listas: (ia_a, ia_b, deck_a_id, deck_b_id)."""
    return list(itertools.product(ia_a_chaves, ia_b_chaves, deck_a_ids, deck_b_ids))


def nome_da_combinacao(nome_grupo: str | None, ia_a: str, ia_b: str, deck_a_nome: str, deck_b_nome: str) -> str:
    prefixo = f"{nome_grupo} — " if nome_grupo else ""
    return f"{prefixo}{ia_a} x {ia_b} — {deck_a_nome} x {deck_b_nome}"


def seed_da_combinacao(seed_base_grupo: int, indice: int, passo: int = PASSO_SEED_COMBINACAO) -> int:
    """Espaço de seeds bem separado por combinação — sem isso, duas
    combinações diferentes rodariam com as MESMAS seeds de partida (mesmas
    cartas compradas na mesma ordem em pontos equivalentes), quebrando a
    independência estatística entre elas."""
    return seed_base_grupo + indice * passo
