"""Mestre domina um TIPO de herói (seção 9), não uma variação específica —
35 tipos ao todo, cada um agrupando 3 variações (ex.: os 3 "Protetor").
O bônus de múltiplo do Mestre precisa valer para QUALQUER uma das 3
variações do tipo que ele domina, não só uma variacao_id exata."""
from cardpool import CardPool, variacoes_do_tipo
from engine import (
    EstadoHeroiCampo,
    EstadoJogador,
    EstadoMestreCampo,
    EstadoPartida,
    prever_resultado_ataque,
)


def _multiplo_do_ataque(pool, config, tipo_dominado, variacao_atacante, variacao_defensor):
    heroi_atacante = pool.novo_heroi("comum", variacao_id=variacao_atacante, forca=100)
    heroi_defensor = pool.novo_heroi("comum", variacao_id=variacao_defensor, forca=200)
    mestre = EstadoMestreCampo(
        carta=pool.novo_mestre("comum", tipo_heroi_dominado=tipo_dominado), rodadas_restantes=1
    )
    p1 = EstadoJogador(
        nome="P1", heroi_ativo=EstadoHeroiCampo.entrar_em_campo(heroi_atacante, rodada_atual=1), mestre=mestre
    )
    p2 = EstadoJogador(nome="P2", heroi_ativo=EstadoHeroiCampo.entrar_em_campo(heroi_defensor, rodada_atual=1))
    estado = EstadoPartida(jogadores={"P1": p1, "P2": p2}, turno_de="P1")
    return prever_resultado_ataque(estado, "P1", "principal", config).multiplo


def test_mestre_bonus_vale_para_qualquer_variacao_do_mesmo_tipo(config):
    pool = CardPool(config, seed=1)
    tipo_dominado = 1
    v1, _v2, v3 = variacoes_do_tipo(tipo_dominado, config)
    # tipos 1, 2 e 3 pertencem à mesma categoria (os primeiros 7 tipos são
    # sempre da mesma categoria) — usados aqui só pra manter a categoria do
    # defensor/atacante-de-tipo-diferente igual à do atacante, isolando o
    # efeito do Mestre de qualquer bônus de vantagem de categoria.
    v_tipo_diferente = variacoes_do_tipo(2, config)[0]
    v_defensor_fixo = variacoes_do_tipo(3, config)[0]

    multiplo_v1 = _multiplo_do_ataque(pool, config, tipo_dominado, v1, v_defensor_fixo)
    multiplo_v3 = _multiplo_do_ataque(pool, config, tipo_dominado, v3, v_defensor_fixo)
    multiplo_tipo_diferente = _multiplo_do_ataque(pool, config, tipo_dominado, v_tipo_diferente, v_defensor_fixo)

    assert multiplo_v1 == multiplo_v3  # 2 variações DIFERENTES do MESMO tipo -> mesmo bônus
    assert multiplo_v1 == multiplo_tipo_diferente + 1  # variação de outro tipo -> sem o bônus do mestre
