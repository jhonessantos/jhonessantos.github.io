"""Executor de lotes de simulação em segundo plano.

Roda numa thread daemon (não bloqueia a API) e grava os resultados
direto no SQLite em lotes de escrita (não 1 INSERT por partida — isso
seria o gargalo real em lotes de milhões de partidas). O progresso fica
visível via `db.obter_lote` a qualquer momento, mesmo com o lote ainda
rodando.

Cada partida é reprodutível individualmente a partir do que fica salvo
na linha de `lotes` (decks, IAs) + a seed daquela partida específica —
é o que vai permitir o replay passo a passo (próxima fase) sem precisar
guardar o log completo de cada uma das milhões de partidas.
"""
from __future__ import annotations

import sys
import threading
import traceback
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import db  # noqa: E402
from ai.personas_catalogo import criar_ia  # noqa: E402
from card_view import desserializar_carta  # noqa: E402
from match import jogar_partida  # noqa: E402
from tournament import resumir_resultado  # noqa: E402

TAMANHO_LOTE_ESCRITA = 200  # quantas partidas acumular antes de gravar no banco


def iniciar_lote_em_background(
    lote_id: int,
    config: dict,
    deck_a_cartas: list[dict],
    deck_b_cartas: list[dict],
    ia_a_chave: str,
    ia_b_chave: str,
    n_partidas: int,
    seed_base: int,
) -> None:
    thread = threading.Thread(
        target=_rodar_lote,
        args=(lote_id, config, deck_a_cartas, deck_b_cartas, ia_a_chave, ia_b_chave, n_partidas, seed_base),
        daemon=True,
    )
    thread.start()


def _rodar_lote(
    lote_id: int,
    config: dict,
    deck_a_cartas: list[dict],
    deck_b_cartas: list[dict],
    ia_a_chave: str,
    ia_b_chave: str,
    n_partidas: int,
    seed_base: int,
) -> None:
    try:
        db.atualizar_status_lote(lote_id, "rodando")
        deck_a = [desserializar_carta(d) for d in deck_a_cartas]
        deck_b = [desserializar_carta(d) for d in deck_b_cartas]

        buffer: list[dict] = []
        for i in range(n_partidas):
            seed = seed_base + i
            papel_e_p1 = "A" if i % 2 == 0 else "B"  # alterna lado (métrica de 1º jogador não fica viesada)

            ai_a = criar_ia(ia_a_chave, seed=seed)
            ai_b = criar_ia(ia_b_chave, seed=seed + 1)
            if papel_e_p1 == "A":
                deck1, deck2, ai1, ai2 = deck_a, deck_b, ai_a, ai_b
            else:
                deck1, deck2, ai1, ai2 = deck_b, deck_a, ai_b, ai_a

            resultado = jogar_partida(config, deck1, deck2, ai1, ai2, seed=seed)
            resumo = resumir_resultado(resultado, papel_e_p1)
            resumo["indice"] = i
            resumo["seed"] = seed
            resumo["papel_e_p1"] = papel_e_p1
            buffer.append(resumo)

            if len(buffer) >= TAMANHO_LOTE_ESCRITA or i == n_partidas - 1:
                db.inserir_partidas(lote_id, buffer)
                db.atualizar_progresso_lote(lote_id, i + 1)
                buffer = []

        db.marcar_lote_concluido(lote_id)
    except Exception:
        db.marcar_lote_erro(lote_id, traceback.format_exc(limit=5))
