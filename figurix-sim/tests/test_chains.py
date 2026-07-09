"""Seção 6, caso 4: barragens e cadeias de contraturno."""
from cardpool import CardPool
from chains import ElementoCadeia, custo_barragem, pode_barrar, resolver_cadeia


def test_guardiao_barra_guardiao_com_desconto_e_vantagem(config):
    pool = CardPool(config, seed=1)
    # Conexao tem vantagem sobre Coracao
    alvo = pool.novo_guardiao(tipo="Portais", categoria="Coracao", raridade="rara", forca=200)
    barrador = pool.novo_guardiao(tipo="Portais", categoria="Conexao", raridade="rara", forca=170)  # -30 exato
    assert pode_barrar(barrador, alvo, config) is True

    # sem vantagem de categoria, força menor não basta
    barrador_sem_vantagem = pool.novo_guardiao(tipo="Portais", categoria="Coracao", raridade="rara", forca=170)
    assert pode_barrar(barrador_sem_vantagem, alvo, config) is False

    # força superior sempre basta, mesmo sem vantagem
    barrador_forte = pool.novo_guardiao(tipo="Portais", categoria="Coracao", raridade="rara", forca=210)
    assert pode_barrar(barrador_forte, alvo, config) is True


def test_juiz_barra_mestre_com_desconto_80(config):
    pool = CardPool(config, seed=2)
    mestre = pool.novo_mestre("super_rara", forca=300)
    juiz_forte_o_bastante = pool.novo_juiz(raridade="rara", forca=220)  # 300-80=220
    assert pode_barrar(juiz_forte_o_bastante, mestre, config) is True

    juiz_fraco_demais = pool.novo_juiz(raridade="rara", forca=210)
    assert pode_barrar(juiz_fraco_demais, mestre, config) is False


def test_mestre_barra_guardiao_so_com_forca_superior(config):
    pool = CardPool(config, seed=3)
    guardiao = pool.novo_guardiao(categoria="Coracao", raridade="rara", forca=200)
    mestre_forte = pool.novo_mestre("rara", categoria="Conexao", forca=210)
    mestre_fraco = pool.novo_mestre("rara", categoria="Conexao", forca=200)  # empate não basta
    assert pode_barrar(mestre_forte, guardiao, config) is True
    assert pode_barrar(mestre_fraco, guardiao, config) is False


def test_mestre_nao_barra_juiz(config):
    pool = CardPool(config, seed=4)
    juiz = pool.novo_juiz(raridade="comum", forca=60)
    mestre = pool.novo_mestre("ultra_rara", forca=400)
    assert pode_barrar(mestre, juiz, config) is False


def test_custo_barragem_usa_categoria_do_barrador(config):
    pool = CardPool(config, seed=5)
    barrador = pool.novo_guardiao(categoria="Mente", raridade="comum")
    qtd, categoria = custo_barragem(barrador, config)
    assert qtd == config["custo_barragem"]
    assert categoria == "Mente"


def test_cadeia_de_3_niveis_resolve_na_ordem_certa(config):
    """A -> B barra A -> C barra B. C e B se cancelam; A sobrevive."""
    pool = CardPool(config, seed=6)
    a = pool.novo_guardiao(tipo="Escudos", categoria="Conexao", raridade="comum", forca=100)
    b = pool.novo_guardiao(tipo="Escudos", categoria="Conexao", raridade="rara", forca=250)
    c = pool.novo_guardiao(tipo="Escudos", categoria="Conexao", raridade="super_rara", forca=320)

    assert pode_barrar(b, a, config) is True
    assert pode_barrar(c, b, config) is True

    pilha = [
        ElementoCadeia(carta=a, jogador="P1"),
        ElementoCadeia(carta=b, jogador="P2"),
        ElementoCadeia(carta=c, jogador="P1"),
    ]
    resultado = resolver_cadeia(pilha)

    assert resultado.sobrevivente.carta is a
    assert resultado.sobrevivente.jogador == "P1"
    assert set(resultado.descartes) == {b, c}


def test_cadeia_de_4_niveis_original_nao_sobrevive(config):
    pool = CardPool(config, seed=7)
    a = pool.novo_guardiao(tipo="Escudos", categoria="Conexao", raridade="comum", forca=60)
    b = pool.novo_guardiao(tipo="Escudos", categoria="Conexao", raridade="rara", forca=200)
    c = pool.novo_guardiao(tipo="Escudos", categoria="Conexao", raridade="super_rara", forca=310)
    d = pool.novo_guardiao(tipo="Escudos", categoria="Conexao", raridade="ultra_rara", forca=370)

    pilha = [
        ElementoCadeia(carta=a, jogador="P1"),
        ElementoCadeia(carta=b, jogador="P2"),
        ElementoCadeia(carta=c, jogador="P1"),
        ElementoCadeia(carta=d, jogador="P2"),
    ]
    resultado = resolver_cadeia(pilha)

    assert resultado.sobrevivente is None
    assert set(resultado.descartes) == {a, b, c, d}
