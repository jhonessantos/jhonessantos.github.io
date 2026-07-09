"""Seção 6, caso 8: mulligan.

Convenção: ordem_decisao = [perdedor, vencedor] — o vencedor do par ou
ímpar pergunta primeiro ao adversário (perdedor) se mantém a mão
(seção 3, item 5). titular_inicial é quem detém a prioridade (vencedor).
"""
from cardpool import CardPool
from engine import quem_age_primeiro, resolver_mulligan


def test_mao_aceita_na_primeira_tentativa_nao_gera_penalidade(config):
    resultado = resolver_mulligan(
        jogadores_e_maos=[("P1", []), ("P2", [])],
        ordem_decisao=["P2", "P1"],
        titular_inicial="P1",
        decisoes={"P1": [True], "P2": [True]},
        config=config,
    )
    assert resultado.compras_extra == {"P1": 0, "P2": 0}
    assert resultado.pontos == {"P1": 0, "P2": 0}
    assert resultado.titular_prioridade == "P1"


def test_primeira_desistencia_so_da_compra_extra_sem_ponto(config):
    resultado = resolver_mulligan(
        jogadores_e_maos=[("P1", []), ("P2", [])],
        ordem_decisao=["P2", "P1"],
        titular_inicial="P1",
        decisoes={"P2": [False, True], "P1": [True]},
        config=config,
    )
    assert resultado.compras_extra["P1"] == 1
    assert resultado.pontos["P1"] == 0


def test_penalidades_progressivas_a_partir_da_2a_desistencia(config):
    resultado = resolver_mulligan(
        jogadores_e_maos=[("P1", []), ("P2", [])],
        ordem_decisao=["P2", "P1"],
        titular_inicial="P1",
        decisoes={"P2": [False, False, True], "P1": [True]},
        config=config,
    )
    assert resultado.compras_extra["P1"] == 2
    assert resultado.pontos["P1"] == 1  # só a partir da 2ª desistência


def test_virada_de_titularidade_quando_perdedor_mantem_e_vencedor_desiste(config):
    # P1 é o vencedor (titular inicial); P2 é o perdedor e decide primeiro.
    # P2 mantém a mão logo de cara; P1 (titular) desiste depois -> vira para P2.
    resultado = resolver_mulligan(
        jogadores_e_maos=[("P1", []), ("P2", [])],
        ordem_decisao=["P2", "P1"],
        titular_inicial="P1",
        decisoes={"P2": [True], "P1": [False, True]},
        config=config,
    )
    assert resultado.titular_prioridade == "P2"


def test_sem_virada_quando_perdedor_tambem_desiste_antes(config):
    # Se o perdedor (P2) ainda não aceitou quando o titular (P1) desiste,
    # não há virada (a condição exige que o perdedor já tenha mantido).
    resultado = resolver_mulligan(
        jogadores_e_maos=[("P1", []), ("P2", [])],
        ordem_decisao=["P2", "P1"],
        titular_inicial="P1",
        decisoes={"P2": [False, True], "P1": [False, True]},
        config=config,
    )
    assert resultado.titular_prioridade == "P1"


def test_comum_de_menor_forca_age_primeiro(config):
    pool = CardPool(config, seed=1)
    fraca = pool.novo_heroi("comum", variacao_id=1, forca=60)
    forte = pool.novo_heroi("comum", variacao_id=2, forca=120)
    assert quem_age_primeiro(("P1", fraca), ("P2", forte), titular_prioridade="P2") == "P1"
    assert quem_age_primeiro(("P1", forte), ("P2", fraca), titular_prioridade="P2") == "P2"


def test_empate_de_forca_vale_a_prioridade(config):
    pool = CardPool(config, seed=2)
    h1 = pool.novo_heroi("comum", variacao_id=1, forca=90)
    h2 = pool.novo_heroi("comum", variacao_id=2, forca=90)
    assert quem_age_primeiro(("P1", h1), ("P2", h2), titular_prioridade="P2") == "P2"
