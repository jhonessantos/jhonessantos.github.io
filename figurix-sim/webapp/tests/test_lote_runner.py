"""Integração do executor de lotes (Fase 3): roda algumas partidas de
verdade (sem thread, direto) e confere que o resultado gravado no banco
bate com o que as próprias partidas produziram."""
from card_view import serializar_carta
from cardpool import montar_deck
from lote_runner import _rodar_lote


def test_rodar_lote_grava_status_progresso_e_partidas(config, db_temporario):
    deck_a = montar_deck(config, faixa_forca="fraco", arquetipo="agro", seed=1)
    deck_b = montar_deck(config, faixa_forca="fraco", arquetipo="controle", seed=2)
    deck_a_cartas = [serializar_carta(c) for c in deck_a]
    deck_b_cartas = [serializar_carta(c) for c in deck_b]

    lote_id = db_temporario.criar_lote(
        nome="teste integração",
        ia_a_chave="aleatoria",
        ia_b_chave="aleatoria",
        deck_a_id=1,
        deck_b_id=2,
        deck_a_nome="Deck A",
        deck_b_nome="Deck B",
        n_partidas=6,
        seed_base=42,
    )

    _rodar_lote(
        lote_id=lote_id,
        config=config,
        deck_a_cartas=deck_a_cartas,
        deck_b_cartas=deck_b_cartas,
        ia_a_chave="aleatoria",
        ia_b_chave="aleatoria",
        n_partidas=6,
        seed_base=42,
    )

    lote = db_temporario.obter_lote(lote_id)
    assert lote["status"] == "concluido"
    assert lote["progresso"] == 6
    assert lote["concluido_em"] is not None

    partidas = db_temporario.listar_partidas_lote(lote_id, limit=100)
    assert len(partidas) == 6
    assert [p["indice"] for p in partidas] == list(range(6))
    # seeds usadas são seed_base + índice, garantindo reprodutibilidade individual
    assert [p["seed"] for p in partidas] == [42 + i for i in range(6)]
    # metade das partidas jogou com A como P1, metade com B (alternância)
    assert [p["papel_e_p1"] for p in partidas] == ["A", "B", "A", "B", "A", "B"]

    resumo = db_temporario.resumo_vitorias_lote(lote_id)
    assert resumo["total"] == 6
    assert resumo["vitorias_a"] + resumo["vitorias_b"] + resumo["indecisas"] == 6


def test_rodar_lote_marca_erro_em_ia_invalida(config, db_temporario):
    deck = montar_deck(config, faixa_forca="fraco", arquetipo="agro", seed=1)
    cartas = [serializar_carta(c) for c in deck]

    lote_id = db_temporario.criar_lote(
        nome="lote com erro",
        ia_a_chave="nao_existe",
        ia_b_chave="aleatoria",
        deck_a_id=1,
        deck_b_id=2,
        deck_a_nome="Deck A",
        deck_b_nome="Deck B",
        n_partidas=2,
        seed_base=1,
    )

    _rodar_lote(
        lote_id=lote_id,
        config=config,
        deck_a_cartas=cartas,
        deck_b_cartas=cartas,
        ia_a_chave="nao_existe",
        ia_b_chave="aleatoria",
        n_partidas=2,
        seed_base=1,
    )

    lote = db_temporario.obter_lote(lote_id)
    assert lote["status"] == "erro"
    assert lote["erro_mensagem"]
