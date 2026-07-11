"""Sanidade do gerador de cartas: tudo deve respeitar as faixas do config."""
import pytest

from cardpool import (
    CardPool,
    N_TIPOS_HEROI,
    N_VARIACOES_OFICIAIS,
    categorias_da_variacao,
    montar_deck,
    tipo_da_variacao,
    variacoes_do_tipo,
)
from cards import Invocacao, poderes_da_raridade, pontos_da_raridade, raridade_equivalente
from deck import validar_deck


# ------------------------------------------------------------------
# Tipo de herói (seção 9): 35 tipos, cada um agrupando 3 variações —
# um Mestre domina o TIPO inteiro, não uma variação específica.
# ------------------------------------------------------------------

def test_tipo_da_variacao_cobre_todas_as_105_variacoes(config):
    tipos_vistos = {tipo_da_variacao(vid, config) for vid in range(1, N_VARIACOES_OFICIAIS + 1)}
    assert tipos_vistos == set(range(1, N_TIPOS_HEROI + 1))


def test_cada_tipo_tem_exatamente_3_variacoes(config):
    for tipo_id in range(1, N_TIPOS_HEROI + 1):
        variacoes = variacoes_do_tipo(tipo_id, config)
        assert len(variacoes) == 3
        assert len(set(variacoes)) == 3
        for vid in variacoes:
            assert 1 <= vid <= N_VARIACOES_OFICIAIS


def test_tipo_da_variacao_e_variacoes_do_tipo_sao_inversas(config):
    for vid in range(1, N_VARIACOES_OFICIAIS + 1):
        tipo_id = tipo_da_variacao(vid, config)
        assert vid in variacoes_do_tipo(tipo_id, config)


def test_as_3_variacoes_de_um_tipo_tem_a_mesma_categoria_principal(config):
    for tipo_id in range(1, N_TIPOS_HEROI + 1):
        categorias = {categorias_da_variacao(vid, config)[0] for vid in variacoes_do_tipo(tipo_id, config)}
        assert len(categorias) == 1


def test_105_variacoes_dividem_em_35_tipos_disjuntos(config):
    todas_variacoes = set()
    for tipo_id in range(1, N_TIPOS_HEROI + 1):
        variacoes = variacoes_do_tipo(tipo_id, config)
        assert todas_variacoes.isdisjoint(variacoes)
        todas_variacoes.update(variacoes)
    assert todas_variacoes == set(range(1, N_VARIACOES_OFICIAIS + 1))


def test_forca_heroi_dentro_da_faixa_da_raridade(config):
    pool = CardPool(config, seed=10)
    for raridade, (lo, hi) in config["forca_por_raridade"].items():
        for _ in range(50):
            h = pool.novo_heroi(raridade, variacao_id=1)
            assert lo <= h.forca_impressa <= hi
            assert (h.forca_impressa - lo) % config["forca_passo"] == 0


def test_forca_especial_dentro_da_faixa(config):
    pool = CardPool(config, seed=11)
    for raridade, (lo, hi) in config["forca_especiais"].items():
        for _ in range(20):
            h = pool.novo_heroi(raridade, variacao_id=2)
            assert lo <= h.forca_impressa <= hi


def test_poderes_seguem_tabela_por_raridade(config):
    for raridade in config["raridades"]:
        principal, secundario, terciario = poderes_da_raridade(raridade, config)
        esperado = config["poderes_por_raridade"][raridade]
        assert [principal, secundario, terciario] == esperado


def test_poderes_de_especial_seguem_raridade_equivalente(config):
    for especial, base in config["especiais_por_raridade"].items():
        assert poderes_da_raridade(especial, config) == poderes_da_raridade(base, config)
        assert pontos_da_raridade(especial, config) == pontos_da_raridade(base, config)
        assert raridade_equivalente(especial, config) == base


def test_categorias_da_variacao_sao_distintas(config):
    for variacao_id in range(1, 20):
        c1, c2, c3 = categorias_da_variacao(variacao_id, config)
        assert len({c1, c2, c3}) == 3
        for c in (c1, c2, c3):
            assert c in config["categorias"]


def test_item_e_local_apenas_comum_ou_rara(config):
    pool = CardPool(config, seed=12)
    for _ in range(30):
        item = pool.novo_item()
        assert item.raridade in ("comum", "rara")
        local = pool.novo_local()
        assert local.raridade in ("comum", "rara")


def _n_invocacoes(deck):
    return sum(1 for c in deck if isinstance(c, Invocacao))


@pytest.mark.parametrize("arquetipo", ["balanceado", "agro", "controle", "combo"])
def test_perfil_invocacoes_e_um_eixo_independente_e_ordenado(config, arquetipo):
    """Escasso < moderado < abundante em nº de invocações, com o resto do
    deck (heróis/mestres/guardiões/juiz) mantido igual — é o eixo de
    "economia de invocações" da estratégia de deck, testável isoladamente."""
    escasso = montar_deck(config, faixa_forca="medio", arquetipo=arquetipo, perfil_invocacoes="escasso", seed=1)
    moderado = montar_deck(config, faixa_forca="medio", arquetipo=arquetipo, perfil_invocacoes="moderado", seed=1)
    abundante = montar_deck(config, faixa_forca="medio", arquetipo=arquetipo, perfil_invocacoes="abundante", seed=1)

    assert len(escasso) == len(moderado) == len(abundante) == config["tamanho_deck"]
    assert _n_invocacoes(escasso) < _n_invocacoes(moderado) < _n_invocacoes(abundante)

    for deck in (escasso, moderado, abundante):
        assert validar_deck(deck, config) == []


def test_perfil_invocacoes_invalido_leva_erro(config):
    with pytest.raises(ValueError):
        montar_deck(config, perfil_invocacoes="inexistente", seed=1)


def test_arquetipo_hiperinvocacao_e_extremo_mas_valido(config):
    """Arquétipo "insano" propositalmente: poucos heróis, invocação no talo —
    usado para testar os limites da economia de invocações (seção 4)."""
    deck = montar_deck(config, faixa_forca="medio", arquetipo="hiperinvocacao", perfil_invocacoes="abundante", seed=1)
    assert len(deck) == config["tamanho_deck"]
    assert validar_deck(deck, config) == []

    from cards import Heroi

    herois = [c for c in deck if isinstance(c, Heroi)]
    assert len(herois) == 10
    assert any(h.raridade == "comum" for h in herois)  # precisa continuar jogável
