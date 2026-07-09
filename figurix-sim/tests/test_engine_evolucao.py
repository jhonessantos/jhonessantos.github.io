"""Seção 6, caso 5: evolução de herói."""
import pytest

from cardpool import CardPool
from engine import EstadoHeroiCampo, aplicar_evolucao, custo_evolucao, pode_evoluir


def test_nao_pode_evoluir_na_mesma_rodada_sem_item_raro(config):
    pool = CardPool(config, seed=1)
    comum = pool.novo_heroi("comum", variacao_id=1, participante_id=1)
    destino = pool.novo_heroi("rara", variacao_id=1, participante_id=1)
    campo = EstadoHeroiCampo.entrar_em_campo(comum, rodada_atual=3)

    pode, motivo = pode_evoluir(campo, destino, rodada_atual=3, item_raro_anexado=False, config=config)
    assert pode is False
    assert "rodada seguinte" in motivo


def test_pode_evoluir_na_mesma_rodada_com_item_raro(config):
    pool = CardPool(config, seed=2)
    comum = pool.novo_heroi("comum", variacao_id=1, participante_id=1)
    destino = pool.novo_heroi("ultra_rara", variacao_id=1, participante_id=1)
    campo = EstadoHeroiCampo.entrar_em_campo(comum, rodada_atual=3)

    pode, _ = pode_evoluir(campo, destino, rodada_atual=3, item_raro_anexado=True, config=config)
    assert pode is True
    assert custo_evolucao(item_raro_anexado=True, config=config) == 0


def test_pode_pular_estagios(config):
    pool = CardPool(config, seed=3)
    comum = pool.novo_heroi("comum", variacao_id=1, participante_id=1)
    destino_ultra = pool.novo_heroi("ultra_rara", variacao_id=1, participante_id=1)
    campo = EstadoHeroiCampo.entrar_em_campo(comum, rodada_atual=1)

    pode, _ = pode_evoluir(campo, destino_ultra, rodada_atual=2, item_raro_anexado=False, config=config)
    assert pode is True


def test_evolucao_exige_mesmo_participante(config):
    pool = CardPool(config, seed=4)
    comum = pool.novo_heroi("comum", variacao_id=1, participante_id=1)
    destino_outro_participante = pool.novo_heroi("rara", variacao_id=2, participante_id=99)
    campo = EstadoHeroiCampo.entrar_em_campo(comum, rodada_atual=1)

    pode, motivo = pode_evoluir(
        campo, destino_outro_participante, rodada_atual=2, item_raro_anexado=False, config=config
    )
    assert pode is False
    assert "mesmo participante" in motivo


def test_evolucao_restaura_forca_cheia(config):
    pool = CardPool(config, seed=5)
    comum = pool.novo_heroi("comum", variacao_id=1, participante_id=1, forca=60)
    destino = pool.novo_heroi("ultra_rara", variacao_id=1, participante_id=1, forca=400)
    campo = EstadoHeroiCampo.entrar_em_campo(comum, rodada_atual=1)
    campo.forca_atual = 10  # tomou dano antes de evoluir

    novo_campo = aplicar_evolucao(campo, destino, rodada_atual=2, item_raro_anexado=False, config=config)
    assert novo_campo.forca_atual == 400
    assert novo_campo.evoluiu is True


def test_evolucao_acontece_uma_unica_vez(config):
    pool = CardPool(config, seed=6)
    comum = pool.novo_heroi("comum", variacao_id=1, participante_id=1)
    rara = pool.novo_heroi("rara", variacao_id=1, participante_id=1)
    ultra = pool.novo_heroi("ultra_rara", variacao_id=1, participante_id=1)
    campo = EstadoHeroiCampo.entrar_em_campo(comum, rodada_atual=1)

    evoluido = aplicar_evolucao(campo, rara, rodada_atual=2, item_raro_anexado=False, config=config)

    pode, motivo = pode_evoluir(evoluido, ultra, rodada_atual=3, item_raro_anexado=False, config=config)
    assert pode is False
    assert "já evoluiu" in motivo

    with pytest.raises(ValueError):
        aplicar_evolucao(evoluido, ultra, rodada_atual=3, item_raro_anexado=False, config=config)
