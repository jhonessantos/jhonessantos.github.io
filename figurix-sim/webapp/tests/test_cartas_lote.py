"""Preenchimento em lote do Deck Builder (cartas_lote.py): geração por
regra dinâmica ("X cartas de Y tipo de Z categoria") e o cuidado de não
duplicar variação de herói dentro da mesma raridade sem necessidade."""
from types import SimpleNamespace

import pytest

from cardpool import CardPool, categorias_da_variacao
from cards import Guardiao, Heroi, ItemHeroi, Invocacao, Juiz, Local, Mestre
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


def test_gerar_uma_carta_heroi_com_categoria(config):
    pool = CardPool(config, seed=5)
    carta = gerar_uma_carta(pool, _regra(tipo_carta="heroi", raridade="comum", categoria="Coracao"))
    assert carta.categoria_principal == "Coracao"


def test_gerar_lote_heroi_com_categoria_respeita_filtro(config):
    regra = _regra(tipo_carta="heroi", raridade="comum", categoria="Mente", quantidade=15)
    cartas = gerar_lote(config, [regra], [], seed=42)
    assert len(cartas) == 15
    assert all(c.categoria_principal == "Mente" for c in cartas)
    # e ainda assim sem duplicar variação dentro da mesma raridade
    assert len({c.variacao_id for c in cartas}) == 15


def test_gerar_lote_heroi_categoria_inexistente_lanca_value_error(config):
    regra = _regra(tipo_carta="heroi", raridade="comum", categoria="Categoria_Fake", quantidade=1)
    with pytest.raises(ValueError):
        gerar_lote(config, [regra], [], seed=1)


def test_gerar_lote_heroi_categoria_esgota_variacoes_da_categoria(config):
    # cada categoria tem só ~21 variações (105 / 5); pedir 22 da mesma
    # categoria e raridade estoura o teto disponível.
    n_na_categoria = sum(
        1 for v in range(1, 106) if categorias_da_variacao(v, config)[0] == "Acao"
    )
    regra = _regra(tipo_carta="heroi", raridade="comum", categoria="Acao", quantidade=n_na_categoria + 1)
    with pytest.raises(ValueError):
        gerar_lote(config, [regra], [], seed=1)


def test_gerar_lote_misto_respeita_quantidade_total(config):
    regra = _regra(tipo_carta="misto", quantidade=40)
    cartas = gerar_lote(config, [regra], [], seed=3)
    assert len(cartas) == 40


def test_gerar_lote_misto_distribui_por_varios_tipos(config):
    regra = _regra(tipo_carta="misto", quantidade=64)
    cartas = gerar_lote(config, [regra], [], seed=3)
    tipos_presentes = {type(c) for c in cartas}
    # com 64 cartas (o tamanho de um deck cheio), a mistura deve produzir
    # pelo menos heróis e invocações — os dois maiores pesos da distribuição
    assert Heroi in tipos_presentes
    assert Invocacao in tipos_presentes


def test_gerar_lote_misto_nao_duplica_variacao_de_heroi(config):
    regra = _regra(tipo_carta="misto", quantidade=64)
    cartas = gerar_lote(config, [regra], [], seed=9)
    variacoes_por_raridade: dict[str, list[int]] = {}
    for c in cartas:
        if isinstance(c, Heroi):
            variacoes_por_raridade.setdefault(c.raridade, []).append(c.variacao_id)
    for raridade, variacoes in variacoes_por_raridade.items():
        assert len(variacoes) == len(set(variacoes)), f"duplicata na raridade {raridade}"


def test_gerar_lote_misto_combinado_com_regra_fixa(config):
    regras = [
        _regra(tipo_carta="invocacao", categoria="Acao", quantidade=10),
        _regra(tipo_carta="misto", quantidade=20),
    ]
    cartas = gerar_lote(config, regras, [], seed=11)
    assert len(cartas) == 30
    invocacoes_acao = [c for c in cartas if isinstance(c, Invocacao) and c.categoria == "Acao"]
    assert len(invocacoes_acao) >= 10  # a regra fixa + possivelmente mais vindas do misto


def test_gerar_lote_misto_produz_apenas_tipos_conhecidos(config):
    regra = _regra(tipo_carta="misto", quantidade=64)
    cartas = gerar_lote(config, [regra], [], seed=17)
    tipos_validos = (Heroi, Mestre, Guardiao, Juiz, ItemHeroi, Local, Invocacao)
    assert all(isinstance(c, tipos_validos) for c in cartas)
