"""Seção 6, caso 6: entrada do Juiz."""
import pytest

from cardpool import CardPool
from engine import (
    EstadoGuardiaoCampo,
    EstadoHeroiCampo,
    EstadoJogador,
    EstadoLocal,
    EstadoMestreCampo,
    EstadoPartida,
    resolver_entrada_juiz,
)


def _jogador_com_heroi(pool, nome, raridade, forca):
    heroi = pool.novo_heroi(raridade, variacao_id=hash(nome) % 100 + 1, forca=forca)
    campo = EstadoHeroiCampo.entrar_em_campo(heroi, rodada_atual=1)
    return EstadoJogador(nome=nome, heroi_ativo=campo)


def test_equalizacao_so_se_adversario_tiver_mais_forca(config):
    pool = CardPool(config, seed=1)
    p1 = _jogador_com_heroi(pool, "P1", "comum", 100)
    p2 = _jogador_com_heroi(pool, "P2", "rara", 250)
    partida = EstadoPartida(jogadores={"P1": p1, "P2": p2}, turno_de="P1")

    resolver_entrada_juiz(p1, p2, partida, escolhas_remocao=[], config=config)
    assert p2.heroi_ativo.forca_atual == 100  # equalizado para a força do próprio (p1)


def test_equalizacao_nao_ocorre_se_adversario_tem_menos_forca(config):
    pool = CardPool(config, seed=2)
    p1 = _jogador_com_heroi(pool, "P1", "rara", 250)
    p2 = _jogador_com_heroi(pool, "P2", "comum", 80)
    partida = EstadoPartida(jogadores={"P1": p1, "P2": p2}, turno_de="P1")

    resolver_entrada_juiz(p1, p2, partida, escolhas_remocao=[], config=config)
    assert p2.heroi_ativo.forca_atual == 80  # inalterado


def test_cura_com_cap_na_forca_impressa(config):
    pool = CardPool(config, seed=3)
    p1 = _jogador_com_heroi(pool, "P1", "comum", 60)
    p1.heroi_ativo.forca_atual = 30  # tomou dano
    p2 = _jogador_com_heroi(pool, "P2", "comum", 60)
    partida = EstadoPartida(jogadores={"P1": p1, "P2": p2}, turno_de="P1")

    resolver_entrada_juiz(p1, p2, partida, escolhas_remocao=[], config=config)
    # 30 + cura_juiz(100) = 130, mas cap é a força impressa (60)
    assert p1.heroi_ativo.forca_atual == 60


def test_limpeza_seletiva_remove_so_do_adversario(config):
    pool = CardPool(config, seed=4)
    p1 = _jogador_com_heroi(pool, "P1", "comum", 100)
    p2 = _jogador_com_heroi(pool, "P2", "comum", 100)

    item_adversario = pool.novo_item()
    p2.heroi_ativo.item_anexado = item_adversario
    guardiao_adversario = pool.novo_guardiao()
    p2.guardioes.append(EstadoGuardiaoCampo(carta=guardiao_adversario, forca_atual=guardiao_adversario.forca_impressa))
    mestre_adversario = pool.novo_mestre("comum")
    p2.mestre = EstadoMestreCampo(carta=mestre_adversario, rodadas_restantes=1)
    local = pool.novo_local()
    partida = EstadoPartida(jogadores={"P1": p1, "P2": p2}, local=EstadoLocal(carta=local), turno_de="P1")

    resolver_entrada_juiz(
        p1, p2, partida,
        escolhas_remocao=[item_adversario, guardiao_adversario, mestre_adversario, local],
        config=config,
    )

    assert p2.heroi_ativo.item_anexado is None
    assert p2.guardioes == []
    assert p2.mestre is None
    assert partida.local is None
    assert item_adversario in p2.descarte
    assert guardiao_adversario in p2.descarte
    assert mestre_adversario in p2.descarte
    assert local in p2.descarte


def test_limpeza_seletiva_e_parcial_pode_manter_cartas(config):
    pool = CardPool(config, seed=5)
    p1 = _jogador_com_heroi(pool, "P1", "comum", 100)
    p2 = _jogador_com_heroi(pool, "P2", "comum", 100)
    item_adversario = pool.novo_item()
    p2.heroi_ativo.item_anexado = item_adversario
    local = pool.novo_local()
    partida = EstadoPartida(jogadores={"P1": p1, "P2": p2}, local=EstadoLocal(carta=local), turno_de="P1")

    # jogador escolhe remover só o item, mantendo o local (que o favorece)
    resolver_entrada_juiz(p1, p2, partida, escolhas_remocao=[item_adversario], config=config)

    assert p2.heroi_ativo.item_anexado is None
    assert partida.local is not None
    assert partida.local.carta is local


def test_invocacoes_nunca_sao_tocadas(config):
    pool = CardPool(config, seed=6)
    p1 = _jogador_com_heroi(pool, "P1", "comum", 100)
    p2 = _jogador_com_heroi(pool, "P2", "comum", 100)
    invocacao = pool.nova_invocacao()
    partida = EstadoPartida(jogadores={"P1": p1, "P2": p2}, turno_de="P1")

    with pytest.raises(ValueError):
        resolver_entrada_juiz(p1, p2, partida, escolhas_remocao=[invocacao], config=config)


def test_juiz_vai_para_descarte_ao_fim_do_turno(config):
    from engine import juiz_vai_para_descarte

    pool = CardPool(config, seed=7)
    juiz = pool.novo_juiz()
    jogador = EstadoJogador(nome="P1")
    juiz_vai_para_descarte(juiz, jogador)
    assert juiz in jogador.descarte
