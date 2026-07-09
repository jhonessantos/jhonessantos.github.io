"""Testes de construção de deck — seção 6, caso 10 das regras."""
import pytest

from cardpool import CardPool, montar_deck_medio
from deck import DeckError, contar_por_tipo, validar_deck, validar_deck_ou_lanca


def _deck_minimo_valido(config, pool, n_herois=1, **kwargs):
    """Monta um deck do tamanho exigido preenchendo o resto com invocações."""
    cartas = list(kwargs.get("extra_cartas", []))
    tamanho = config["tamanho_deck"]
    faltam = tamanho - len(cartas)
    for _ in range(faltam):
        cartas.append(pool.nova_invocacao())
    return cartas


def test_rejeita_segunda_copia_mesma_variacao_com_participante_diferente(config):
    pool = CardPool(config, seed=1)
    h1 = pool.novo_heroi("comum", variacao_id=10, participante_id=100)
    h2 = pool.novo_heroi("rara", variacao_id=10, participante_id=200)  # participante diferente!
    cartas = _deck_minimo_valido(config, pool, extra_cartas=[h1, h2])

    violacoes = validar_deck(cartas, config)
    assert any("participantes diferentes" in v for v in violacoes)

    with pytest.raises(DeckError):
        validar_deck_ou_lanca(cartas, config)


def test_aceita_4_raridades_do_mesmo_participante(config):
    pool = CardPool(config, seed=2)
    variacao_id, participante_id = 42, 42
    herois = [
        pool.novo_heroi("comum", variacao_id=variacao_id, participante_id=participante_id),
        pool.novo_heroi("rara", variacao_id=variacao_id, participante_id=participante_id),
        pool.novo_heroi("super_rara", variacao_id=variacao_id, participante_id=participante_id),
        pool.novo_heroi("ultra_rara", variacao_id=variacao_id, participante_id=participante_id),
    ]
    cartas = _deck_minimo_valido(config, pool, extra_cartas=herois)

    violacoes = validar_deck(cartas, config)
    assert violacoes == []


def test_especial_ocupa_slot_da_raridade_equivalente(config):
    """comemorativa (=comum) não pode coexistir com a comum do mesmo participante."""
    pool = CardPool(config, seed=3)
    variacao_id, participante_id = 7, 7
    herois = [
        pool.novo_heroi("comum", variacao_id=variacao_id, participante_id=participante_id),
        pool.novo_heroi("comemorativa", variacao_id=variacao_id, participante_id=participante_id),
    ]
    cartas = _deck_minimo_valido(config, pool, extra_cartas=herois)

    violacoes = validar_deck(cartas, config)
    assert any("slot de raridade 'comum'" in v for v in violacoes)


def test_5a_copia_do_mesmo_participante_excede_maximo_absoluto(config):
    pool = CardPool(config, seed=4)
    variacao_id, participante_id = 5, 5
    # 4 raridades base + 1 especial extra no mesmo slot => 5 cópias no total
    herois = [
        pool.novo_heroi("comum", variacao_id=variacao_id, participante_id=participante_id),
        pool.novo_heroi("rara", variacao_id=variacao_id, participante_id=participante_id),
        pool.novo_heroi("super_rara", variacao_id=variacao_id, participante_id=participante_id),
        pool.novo_heroi("ultra_rara", variacao_id=variacao_id, participante_id=participante_id),
        pool.novo_heroi("pos_ultra", variacao_id=variacao_id, participante_id=participante_id),
    ]
    cartas = _deck_minimo_valido(config, pool, extra_cartas=herois)
    violacoes = validar_deck(cartas, config)
    assert any("máximo absoluto é 4" in v for v in violacoes)


def test_limite_mestre_mesmo_tipo(config):
    pool = CardPool(config, seed=5)
    mestres = [
        pool.novo_mestre("comum", tipo_heroi_dominado=1),
        pool.novo_mestre("rara", tipo_heroi_dominado=1),
        pool.novo_mestre("super_rara", tipo_heroi_dominado=1),  # 3ª do mesmo tipo -> inválido
    ]
    cartas = _deck_minimo_valido(config, pool, extra_cartas=mestres)
    violacoes = validar_deck(cartas, config)
    assert any("Mestre do tipo 1" in v for v in violacoes)

    # 2 do mesmo tipo é permitido
    cartas_ok = _deck_minimo_valido(config, pool, extra_cartas=mestres[:2])
    assert validar_deck(cartas_ok, config) == []


def test_limite_guardiao_especifico(config):
    pool = CardPool(config, seed=6)
    g1 = pool.novo_guardiao(tipo="Portais", categoria="Conexao", raridade="comum")
    g2 = pool.novo_guardiao(tipo="Portais", categoria="Conexao", raridade="comemorativa")  # equivalente a comum
    cartas = _deck_minimo_valido(config, pool, extra_cartas=[g1, g2])
    violacoes = validar_deck(cartas, config)
    assert any("Guardião específico" in v for v in violacoes)

    g3 = pool.novo_guardiao(tipo="Portais", categoria="Conexao", raridade="rara")  # raridade diferente = outro específico
    cartas_ok = _deck_minimo_valido(config, pool, extra_cartas=[g1, g3])
    assert validar_deck(cartas_ok, config) == []


def test_limite_juiz_por_deck(config):
    pool = CardPool(config, seed=7)
    juizes = [pool.novo_juiz(), pool.novo_juiz()]
    cartas = _deck_minimo_valido(config, pool, extra_cartas=juizes)
    violacoes = validar_deck(cartas, config)
    assert any("Juiz: 2 cópias" in v for v in violacoes)

    cartas_ok = _deck_minimo_valido(config, pool, extra_cartas=juizes[:1])
    assert validar_deck(cartas_ok, config) == []


def test_tamanho_deck_deve_ser_exato(config):
    pool = CardPool(config, seed=8)
    cartas = [pool.nova_invocacao() for _ in range(config["tamanho_deck"] - 1)]
    violacoes = validar_deck(cartas, config)
    assert any("exatamente" in v for v in violacoes)


@pytest.mark.parametrize("faixa", ["fraco", "medio", "forte"])
@pytest.mark.parametrize("arquetipo", ["balanceado", "agro", "controle", "combo"])
def test_perfis_de_deck_gerados_sao_validos(config, faixa, arquetipo):
    from cardpool import montar_deck

    cartas = montar_deck(config, faixa_forca=faixa, arquetipo=arquetipo, seed=123)
    assert len(cartas) == config["tamanho_deck"]
    violacoes = validar_deck(cartas, config)
    assert violacoes == [], f"{faixa}/{arquetipo}: {violacoes}"


def test_contar_por_tipo(config):
    cartas = montar_deck_medio(config, seed=99)
    contagem = contar_por_tipo(cartas)
    assert sum(contagem.values()) == config["tamanho_deck"]
    assert "herois" in contagem and contagem["herois"] > 0
