"""Fila com concorrência limitada (lote_runner.iniciar_lote_em_background):
diferente de _rodar_lote (chamado direto, síncrono, testado em
test_lote_runner.py), aqui a submissão é assíncrona — o teste precisa
esperar (polling com timeout) o worker pegar o job da fila e terminar."""
import time

from card_view import serializar_carta
from cardpool import montar_deck
from lote_runner import iniciar_lote_em_background


def _esperar_conclusao(db_temporario, lote_id, timeout=10):
    fim = time.time() + timeout
    while time.time() < fim:
        lote = db_temporario.obter_lote(lote_id)
        if lote["status"] in ("concluido", "erro"):
            return lote
        time.sleep(0.05)
    raise AssertionError(f"lote {lote_id} não concluiu em {timeout}s (status={lote['status']!r})")


def test_iniciar_lote_em_background_processa_via_fila(config, db_temporario):
    deck = montar_deck(config, faixa_forca="fraco", arquetipo="agro", seed=1)
    cartas = [serializar_carta(c) for c in deck]

    lote_id = db_temporario.criar_lote(
        nome="fila teste", ia_a_chave="aleatoria", ia_b_chave="aleatoria",
        deck_a_id=1, deck_b_id=2, deck_a_nome="A", deck_b_nome="B",
        n_partidas=3, seed_base=1,
    )
    iniciar_lote_em_background(
        lote_id=lote_id, config=config, deck_a_cartas=cartas, deck_b_cartas=cartas,
        ia_a_chave="aleatoria", ia_b_chave="aleatoria", n_partidas=3, seed_base=1,
    )

    lote = _esperar_conclusao(db_temporario, lote_id)
    assert lote["status"] == "concluido"
    assert lote["progresso"] == 3
    assert len(db_temporario.listar_partidas_lote(lote_id)) == 3


def test_varios_lotes_enfileirados_processam_todos(config, db_temporario):
    """Simula o cenário de "rodar todas as combinações": vários lotes
    submetidos de uma vez, processados por um número fixo de workers (não
    1 thread por lote) — todos precisam terminar mesmo assim."""
    deck = montar_deck(config, faixa_forca="fraco", arquetipo="agro", seed=1)
    cartas = [serializar_carta(c) for c in deck]

    lote_ids = []
    for i in range(6):
        lote_id = db_temporario.criar_lote(
            nome=f"combo {i}", ia_a_chave="aleatoria", ia_b_chave="aleatoria",
            deck_a_id=1, deck_b_id=2, deck_a_nome="A", deck_b_nome="B",
            n_partidas=2, seed_base=i,
        )
        iniciar_lote_em_background(
            lote_id=lote_id, config=config, deck_a_cartas=cartas, deck_b_cartas=cartas,
            ia_a_chave="aleatoria", ia_b_chave="aleatoria", n_partidas=2, seed_base=i,
        )
        lote_ids.append(lote_id)

    for lote_id in lote_ids:
        lote = _esperar_conclusao(db_temporario, lote_id, timeout=15)
        assert lote["status"] == "concluido"
        assert lote["progresso"] == 2
