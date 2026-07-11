"""Toda carta com raridade precisa mostrar um símbolo de FORMA (não só cor)
pra distinguir raridade — comum=circulo, rara=losango, super_rara=estrela,
ultra_rara=fogo (pedido do usuário, ex.: acessibilidade a daltonismo).
Invocação não tem raridade (seção 1 das regras), então não deve ter emoji."""
from card_view import RARIDADE_EMOJI, construir_view_carta
from cardpool import CardPool


def test_raridade_emoji_tem_as_4_formas_esperadas():
    assert RARIDADE_EMOJI == {
        "comum": "⚪",
        "rara": "🔷",
        "super_rara": "⭐",
        "ultra_rara": "🔥",
    }


def test_heroi_tem_raridade_emoji_por_raridade(config):
    pool = CardPool(config, seed=1)
    for raridade, emoji in RARIDADE_EMOJI.items():
        carta = pool.novo_heroi(raridade)
        view = construir_view_carta(carta, config)
        assert view["raridade_emoji"] == emoji


def test_mestre_guardiao_juiz_item_local_tem_raridade_emoji(config):
    pool = CardPool(config, seed=2)
    cartas = [
        pool.novo_mestre("comum"),
        pool.novo_guardiao(raridade="rara"),
        pool.novo_juiz(raridade="super_rara"),
        pool.novo_item(raridade="rara"),
        pool.novo_local(raridade="ultra_rara"),
    ]
    for carta in cartas:
        view = construir_view_carta(carta, config)
        assert view["raridade_emoji"] == RARIDADE_EMOJI[carta.raridade]


def test_raridade_especial_usa_emoji_da_raridade_equivalente(config):
    especiais = list(config["especiais_por_raridade"].keys())
    assert especiais, "esperava ao menos uma raridade especial (comemorativa/pos_*) no config"
    pool = CardPool(config, seed=3)
    for raridade_especial in especiais:
        carta = pool.novo_heroi(raridade_especial)
        view = construir_view_carta(carta, config)
        assert view["raridade_emoji"] in RARIDADE_EMOJI.values()


def test_invocacao_nao_tem_raridade_emoji(config):
    pool = CardPool(config, seed=4)
    carta = pool.nova_invocacao()
    view = construir_view_carta(carta, config)
    assert view["raridade_emoji"] is None
    assert view["raridade"] is None
