"""Sanidade do gerador de cartas: tudo deve respeitar as faixas do config."""
from cardpool import CardPool, categorias_da_variacao
from cards import poderes_da_raridade, pontos_da_raridade, raridade_equivalente


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
