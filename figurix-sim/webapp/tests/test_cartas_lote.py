"""Preenchimento em lote do Deck Builder (cartas_lote.py): geração por
regra dinâmica ("X cartas de Y tipo de Z categoria") e o cuidado de não
duplicar variação de herói dentro da mesma raridade sem necessidade."""
from types import SimpleNamespace

import pytest

from cardpool import CardPool
from cards import Heroi, Invocacao
from cartas_lote import gerar_lote, gerar_uma_carta, variacoes_usadas_de_cartas_existentes


def _regra(tipo_carta="heroi", quantidade=1, **campos):
    base = dict(
        tipo_carta=tipo_carta,
        raridade=None,
        categoria=None,
        variacao_id=None,
        participante_id=None,
        tipo_heroi_dominado=None,
        tipo_guardiao=None,
        tipo_heroi=None,
        forca=None,
        quantidade=quantidade,
    )
    base.update(campos)
    return SimpleNamespace(**base)


def test_gerar_uma_carta_invocacao(config):
    pool = CardPool(config, seed=1)
    carta = gerar_uma_carta(pool, _regra(tipo_carta="invocacao", categoria="Acao"))
    assert isinstance(carta, Invocacao)
    assert carta.categoria == "Acao"


def test_gerar_uma_carta_tipo_desconhecido_lanca_value_error(config):
    pool = CardPool(config, seed=1)
    with pytest.raises(ValueError):
        gerar_uma_carta(pool, _regra(tipo_carta="nao_existe"))


def test_gerar_lote_quantidade_invalida_lanca_value_error(config):
    with pytest.raises(ValueError):
        gerar_lote(config, [_regra(quantidade=0)], [], seed=1)


def test_gerar_lote_respeita_quantidade_por_regra(config):
    regras = [
        _regra(tipo_carta="heroi", raridade="comum", quantidade=5),
        _regra(tipo_carta="invocacao", categoria="Mente", quantidade=3),
    ]
    cartas = gerar_lote(config, regras, [], seed=7)
    assert len(cartas) == 8
    assert sum(isinstance(c, Heroi) for c in cartas) == 5
    assert sum(isinstance(c, Invocacao) for c in cartas) == 3


def test_gerar_lote_nao_duplica_variacao_de_heroi_na_mesma_raridade(config):
    regra = _regra(tipo_carta="heroi", raridade="comum", quantidade=30)
    cartas = gerar_lote(config, [regra], [], seed=123)
    variacoes = [c.variacao_id for c in cartas]
    assert len(variacoes) == len(set(variacoes))


def test_gerar_lote_permite_mesma_variacao_em_raridades_diferentes(config):
    # 1 comum + 1 rara da MESMA variação fixada é uma família válida (evolução)
    regras = [
        _regra(tipo_carta="heroi", raridade="comum", variacao_id=10, quantidade=1),
        _regra(tipo_carta="heroi", raridade="rara", variacao_id=10, quantidade=1),
    ]
    cartas = gerar_lote(config, regras, [], seed=1)
    assert {c.variacao_id for c in cartas} == {10}
    assert {c.raridade for c in cartas} == {"comum", "rara"}


def test_gerar_lote_considera_cartas_existentes_para_nao_duplicar(config):
    pool = CardPool(config, seed=1)
    existente = pool.novo_heroi("comum", variacao_id=42)
    from card_view import serializar_carta

    regra = _regra(tipo_carta="heroi", raridade="comum", quantidade=10)
    cartas = gerar_lote(config, [regra], [serializar_carta(existente)], seed=99)
    assert all(c.variacao_id != 42 for c in cartas)


def test_variacoes_usadas_de_cartas_existentes_ignora_outros_tipos(config):
    pool = CardPool(config, seed=1)
    from card_view import serializar_carta

    heroi = pool.novo_heroi("comum", variacao_id=5)
    invocacao = pool.nova_invocacao(categoria="Acao")
    dados = [serializar_carta(heroi), serializar_carta(invocacao)]
    usadas = variacoes_usadas_de_cartas_existentes(dados, config)
    assert usadas == {"comum": {5}}


def test_gerar_lote_esgota_variacoes_livres_lanca_value_error(config):
    regra = _regra(tipo_carta="heroi", raridade="comum", quantidade=106)
    with pytest.raises(ValueError):
        gerar_lote(config, [regra], [], seed=1)
