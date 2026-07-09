"""Seção 6, caso 7: Guardião do Descanso."""
import pytest

from cardpool import CardPool
from engine import EstadoHeroiCampo, EstadoJogador, aplicar_descanso, resolver_retorno_descanso


def test_isca_precisa_ser_comum(config):
    pool = CardPool(config, seed=1)
    titular = pool.novo_heroi("rara", variacao_id=1)
    jogador = EstadoJogador(nome="P1", heroi_ativo=EstadoHeroiCampo.entrar_em_campo(titular, 1))
    isca_nao_comum = pool.novo_heroi("rara", variacao_id=2)

    with pytest.raises(ValueError):
        aplicar_descanso(jogador, isca_nao_comum, rodada_atual=1, config=config)


def test_descanso_devolve_titular_a_mao_e_poe_isca_por_1_rodada(config):
    pool = CardPool(config, seed=2)
    titular = pool.novo_heroi("rara", variacao_id=1, forca=250)
    jogador = EstadoJogador(nome="P1", heroi_ativo=EstadoHeroiCampo.entrar_em_campo(titular, 1))
    isca = pool.novo_heroi("comum", variacao_id=2, forca=80)

    descanso = aplicar_descanso(jogador, isca, rodada_atual=5, config=config)

    assert titular in jogador.mao
    assert jogador.heroi_ativo.carta is isca
    assert descanso.rodada_retorno == 6


def test_ponto_ao_adversario_se_a_isca_cair(config):
    pool = CardPool(config, seed=3)
    titular = pool.novo_heroi("rara", variacao_id=1, forca=250)
    jogador = EstadoJogador(nome="P1", heroi_ativo=EstadoHeroiCampo.entrar_em_campo(titular, 1))
    adversario = EstadoJogador(nome="P2")
    isca = pool.novo_heroi("comum", variacao_id=2, forca=80)
    aplicar_descanso(jogador, isca, rodada_atual=1, config=config)

    resolver_retorno_descanso(jogador, adversario, isca_foi_derrotada=True, config=config)

    assert adversario.pontos == config["pontos_por_raridade"]["comum"]
    assert jogador.heroi_ativo is None
    assert jogador.descanso is None


def test_heroi_descansado_recupera_ate_30_cap_na_forca_impressa(config):
    pool = CardPool(config, seed=4)
    titular = pool.novo_heroi("rara", variacao_id=1, forca=250)
    jogador = EstadoJogador(nome="P1", heroi_ativo=EstadoHeroiCampo.entrar_em_campo(titular, 1))
    jogador.heroi_ativo.forca_atual = 240  # já tinha tomado um pouco de dano antes de descansar
    adversario = EstadoJogador(nome="P2")
    isca = pool.novo_heroi("comum", variacao_id=2, forca=80)
    aplicar_descanso(jogador, isca, rodada_atual=1, config=config)

    resolver_retorno_descanso(jogador, adversario, isca_foi_derrotada=False, config=config)

    # 240 + cura_descanso(30) = 270, mas cap é a força impressa (250)
    assert jogador.heroi_ativo.forca_atual == 250
    assert jogador.heroi_ativo.carta is titular
    assert titular not in jogador.mao


def test_heroi_descansado_recupera_sem_ultrapassar_impressa_quando_baixo(config):
    pool = CardPool(config, seed=5)
    titular = pool.novo_heroi("rara", variacao_id=1, forca=250)
    jogador = EstadoJogador(nome="P1", heroi_ativo=EstadoHeroiCampo.entrar_em_campo(titular, 1))
    jogador.heroi_ativo.forca_atual = 100
    adversario = EstadoJogador(nome="P2")
    isca = pool.novo_heroi("comum", variacao_id=2, forca=80)
    aplicar_descanso(jogador, isca, rodada_atual=1, config=config)

    resolver_retorno_descanso(jogador, adversario, isca_foi_derrotada=False, config=config)
    assert jogador.heroi_ativo.forca_atual == 130
