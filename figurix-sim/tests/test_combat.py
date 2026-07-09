"""Seção 6, casos 1-3: múltiplo, defesa -20, item +10."""
from combat import resolver_ataque


def test_multiplo_4x_no_principal_com_todas_condicoes(config):
    # herói ação (Acao) vs defensor Mente (Acao tem vantagem sobre Mente na roda)
    r = resolver_ataque(
        poder_base=30,
        tipo_ataque="principal",
        item_anexado=False,
        local_favorece_categoria_ataque=True,
        mestre_do_tipo_presente=True,
        categoria_heroi_atacante="Acao",
        categoria_heroi_defensor="Mente",
        categoria_ataque_usado="Acao",
        config=config,
    )
    assert r.multiplo == 4


def test_secundario_so_recebe_local(config):
    r = resolver_ataque(
        poder_base=20,
        tipo_ataque="secundario",
        item_anexado=False,
        local_favorece_categoria_ataque=True,
        mestre_do_tipo_presente=True,  # não deve contar (só principal)
        categoria_heroi_atacante="Acao",
        categoria_heroi_defensor="Mente",  # vantagem existe mas não deve contar p/ secundário
        categoria_ataque_usado="Acao",
        config=config,
    )
    assert r.multiplo == 2  # base 1 + local 1


def test_defesa_20_aplicada_pos_multiplo(config):
    # defensor Mente tem vantagem sobre a categoria do ataque usado (Criacao);
    # atacante é Coracao, que não tem vantagem sobre Mente (não soma no múltiplo)
    r = resolver_ataque(
        poder_base=30,
        tipo_ataque="principal",
        item_anexado=False,
        local_favorece_categoria_ataque=False,
        mestre_do_tipo_presente=False,
        categoria_heroi_atacante="Coracao",
        categoria_heroi_defensor="Mente",
        categoria_ataque_usado="Criacao",
        config=config,
    )
    assert r.defesa_aplicada is True
    # multiplo = 1 (nenhuma condição de incremento) -> dano bruto 30, -20 defesa = 10
    assert r.multiplo == 1
    assert r.dano_final == 10


def test_defesa_nunca_deixa_dano_negativo(config):
    r = resolver_ataque(
        poder_base=10,
        tipo_ataque="principal",
        item_anexado=False,
        local_favorece_categoria_ataque=False,
        mestre_do_tipo_presente=False,
        categoria_heroi_atacante="Acao",
        categoria_heroi_defensor="Mente",
        categoria_ataque_usado="Criacao",
        config=config,
    )
    assert r.dano_final == 0


def test_item_mais_10_antes_do_multiplo(config):
    # (30 + 10) * 3 = 120 (seção 6, caso 3): local + mestre contam, sem vantagem (categorias iguais)
    r = resolver_ataque(
        poder_base=30,
        tipo_ataque="principal",
        item_anexado=True,
        local_favorece_categoria_ataque=True,
        mestre_do_tipo_presente=True,
        categoria_heroi_atacante="Conexao",
        categoria_heroi_defensor="Conexao",  # sem vantagem entre iguais
        categoria_ataque_usado="Conexao",
        config=config,
    )
    assert r.multiplo == 3  # base 1 + local + mestre
    assert r.poder_com_item == 40
    assert r.dano_final == 120


def test_item_com_multiplo_4_maximo(config):
    r = resolver_ataque(
        poder_base=30,
        tipo_ataque="principal",
        item_anexado=True,
        local_favorece_categoria_ataque=True,
        mestre_do_tipo_presente=True,
        categoria_heroi_atacante="Acao",
        categoria_heroi_defensor="Mente",  # Acao tem vantagem sobre Mente
        categoria_ataque_usado="Acao",
        config=config,
    )
    assert r.multiplo == 4
    assert r.dano_final == 160


def test_item_so_conta_no_principal(config):
    r = resolver_ataque(
        poder_base=20,
        tipo_ataque="secundario",
        item_anexado=True,
        local_favorece_categoria_ataque=False,
        mestre_do_tipo_presente=False,
        categoria_heroi_atacante="Acao",
        categoria_heroi_defensor="Mente",
        categoria_ataque_usado="Coracao",
        config=config,
    )
    assert r.poder_com_item == 20  # bônus de item não se aplica fora do principal
