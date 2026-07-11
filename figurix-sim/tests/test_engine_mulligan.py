"""Seção 3, itens 3-5, e seção 3.4 (recusa voluntária de mão): caso 8.

`registrar_decisao_mulligan` é a lógica PURA de consequência de UMA
rejeição de mão (chamada só quando o jogador acabou de recusar) — a
orquestração real (comprar cartas, chamar `ai.aceitar_mao`, repetir até
os dois aceitarem) vive em `match._preparar_maos_iniciais` e é testada
via integração em test_match_mulligan_espiral.py.
"""
from cardpool import CardPool
from engine import (
    mao_aceitavel_por_heuristica_padrao,
    quem_age_primeiro,
    registrar_decisao_mulligan,
    tem_heroi_comum,
)


def test_aceitar_nao_gera_consequencia():
    # aceitar não é modelado por registrar_decisao_mulligan (só é chamada
    # quando alguém REJEITA) — mas confirmamos que rejeitar com o outro
    # ainda indeciso também não gera nada, o caso "de fronteira" mais perto.
    consequencia = registrar_decisao_mulligan(
        nome="P2", outro_nome="P1", outro_ja_aceitou=False,
        titular_atual="P1", desistencias_nome=1, config={},
    )
    assert consequencia.compra_bonus_para is None
    assert consequencia.ponto_para is None
    assert consequencia.titular_prioridade == "P1"


def test_rejeicao_dos_dois_na_mesma_rodada_nao_premia_ninguem():
    # P2 rejeita primeiro (outro=P1 ainda não decidiu) -> nada.
    c1 = registrar_decisao_mulligan(
        nome="P2", outro_nome="P1", outro_ja_aceitou=False,
        titular_atual="P1", desistencias_nome=1, config={},
    )
    # P1 (titular) rejeita também, na MESMA rodada (P2 também não aceitou) -> nada.
    c2 = registrar_decisao_mulligan(
        nome="P1", outro_nome="P2", outro_ja_aceitou=False,
        titular_atual="P1", desistencias_nome=1, config={},
    )
    assert c1.compra_bonus_para is None and c1.ponto_para is None
    assert c2.compra_bonus_para is None and c2.ponto_para is None
    assert c2.titular_prioridade == "P1"  # sem troca — ninguém aceitou ainda


def test_nao_titular_rejeita_com_titular_ja_aceito_premia_titular_sem_troca():
    # Cenário do usuário: "o adversário [não-titular] decidiu trocar a mão
    # inicial e o vencedor [titular] não [rejeitou] -> o vencedor puxa uma carta".
    consequencia = registrar_decisao_mulligan(
        nome="P2", outro_nome="P1", outro_ja_aceitou=True,
        titular_atual="P1", desistencias_nome=1, config={},
    )
    assert consequencia.compra_bonus_para == "P1"
    assert consequencia.ponto_para is None  # só a partir da 2ª desistência
    assert consequencia.titular_prioridade == "P1"  # sem troca de titularidade


def test_nao_titular_segunda_rejeicao_consecutiva_tambem_da_ponto():
    # "Se na próxima mão do adversário ele insiste em trocar, além de o
    # vencedor puxar uma carta, ele também ganha um ponto."
    consequencia = registrar_decisao_mulligan(
        nome="P2", outro_nome="P1", outro_ja_aceitou=True,
        titular_atual="P1", desistencias_nome=2, config={},
    )
    assert consequencia.compra_bonus_para == "P1"
    assert consequencia.ponto_para == "P1"
    assert consequencia.titular_prioridade == "P1"


def test_titular_rejeita_com_nao_titular_ja_aceito_troca_titularidade():
    # "Se o adversário decidiu continuar com a mão e o vencedor do par ou
    # ímpar desistir da dele, o jogo muda de lado: o adversário passa a
    # ser o 'vencedor' e puxa uma carta."
    consequencia = registrar_decisao_mulligan(
        nome="P1", outro_nome="P2", outro_ja_aceitou=True,
        titular_atual="P1", desistencias_nome=1, config={},
    )
    assert consequencia.compra_bonus_para == "P2"
    assert consequencia.titular_prioridade == "P2"


def test_titular_ja_trocado_nao_troca_de_novo_em_rejeicoes_seguintes():
    # depois da troca (titular_atual já é P2), uma nova rejeição de P1
    # (agora não-titular) só premia P2 de novo, sem re-disparar troca.
    consequencia = registrar_decisao_mulligan(
        nome="P1", outro_nome="P2", outro_ja_aceitou=True,
        titular_atual="P2", desistencias_nome=2, config={},
    )
    assert consequencia.compra_bonus_para == "P2"
    assert consequencia.ponto_para == "P2"
    assert consequencia.titular_prioridade == "P2"  # já era P2, permanece


def test_tem_heroi_comum():
    from cards import Heroi

    comum = Heroi(raridade="comum")
    rara = Heroi(raridade="rara")
    assert tem_heroi_comum([rara, comum]) is True
    assert tem_heroi_comum([rara]) is False
    assert tem_heroi_comum([]) is False


def test_mao_aceitavel_por_heuristica_padrao():
    from cards import Heroi, Invocacao

    comum = Heroi(raridade="comum")
    rara = Heroi(raridade="rara")
    invocacao = Invocacao(categoria="Acao")

    assert mao_aceitavel_por_heuristica_padrao([comum]) is False  # nada além do comum
    assert mao_aceitavel_por_heuristica_padrao([comum, invocacao]) is True
    assert mao_aceitavel_por_heuristica_padrao([comum, rara]) is True


def test_comum_de_menor_forca_age_primeiro(config):
    pool = CardPool(config, seed=1)
    fraca = pool.novo_heroi("comum", variacao_id=1, forca=60)
    forte = pool.novo_heroi("comum", variacao_id=2, forca=120)
    assert quem_age_primeiro(("P1", fraca), ("P2", forte), titular_prioridade="P2") == "P1"
    assert quem_age_primeiro(("P1", forte), ("P2", fraca), titular_prioridade="P2") == "P2"


def test_empate_de_forca_vale_a_prioridade(config):
    pool = CardPool(config, seed=2)
    h1 = pool.novo_heroi("comum", variacao_id=1, forca=90)
    h2 = pool.novo_heroi("comum", variacao_id=2, forca=90)
    assert quem_age_primeiro(("P1", h1), ("P2", h2), titular_prioridade="P2") == "P2"
