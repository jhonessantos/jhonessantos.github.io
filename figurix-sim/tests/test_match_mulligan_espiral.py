"""Seção 3.4: um deck sem heróis comuns é uma escolha de construção válida
— o jogador vai desistindo da mão, o adversário ganha pontos, e a
partida pode terminar (o adversário vence) antes mesmo do primeiro
turno. O motor precisa deixar isso acontecer, não impedir/travar.

Também cobre a recusa VOLUNTÁRIA de mão válida (o outro caso da seção
3.4): uma IA pode recusar uma mão com herói comum por não gostar dela,
não só quando a mão é tecnicamente inválida.
"""
from ai.random_ai import RandomAI
from cardpool import CardPool, montar_deck_medio
from config import carregar_config
from match import configurar_partida, jogar_partida


def _deck_sem_herois_comuns(config, seed):
    """Deck construído à mão: só heróis raros+ (nenhum comum), preenchido
    com invocações — deliberadamente "impossível" de vencer o mulligan."""
    pool = CardPool(config, seed=seed)
    cartas = [pool.novo_heroi("rara", variacao_id=i) for i in range(1, 10)]
    while len(cartas) < config["tamanho_deck"]:
        cartas.append(pool.nova_invocacao())
    return cartas


def _deck_quase_todo_herois_comuns(config, seed):
    """Deck com tantos heróis comuns distintos (49 de 64 cartas) que
    qualquer mão inicial de 8 cartas sorteada ao acaso tem, na prática,
    certeza de incluir pelo menos 1 — usado nos testes de recusa
    VOLUNTÁRIA de mão, pra isolar essa decisão de qualquer chance
    (por menor que seja) de uma recusa FORÇADA por mão inválida atrapalhar
    a contagem esperada."""
    pool = CardPool(config, seed=seed)
    cartas = [pool.novo_heroi("comum", variacao_id=i) for i in range(1, 50)]
    while len(cartas) < config["tamanho_deck"]:
        cartas.append(pool.nova_invocacao())
    return cartas


def test_deck_sem_comuns_perde_por_pontos_via_espiral_de_mulligan():
    config = carregar_config()
    deck_sem_comuns = _deck_sem_herois_comuns(config, seed=1)
    deck_normal = montar_deck_medio(config, seed=2)

    resultados = []
    for seed in range(20):
        resultado = jogar_partida(
            config, deck_sem_comuns, deck_normal, RandomAI(seed=seed), RandomAI(seed=seed + 1), seed=seed
        )
        resultados.append(resultado)

    # o dono do deck sem comuns (P1) nunca deveria vencer, e a partida deve
    # terminar rápido (decidida na espiral de mulligan, antes de qualquer turno)
    assert all(r.vencedor == "P2" for r in resultados)
    assert all(r.turnos == 0 for r in resultados)
    assert all(r.pontos["P2"] >= config["pontos_vitoria"] for r in resultados)


class _AceitaAposNRejeicoes:
    """IA de teste: recusa as N primeiras mãos que vir (mesmo válidas) e
    aceita a partir da (N+1)-ésima — simula uma IA "exigente" de forma
    determinística, pra testar o sequenciamento/bônus do mulligan."""

    def __init__(self, n_rejeicoes: int):
        self.n_rejeicoes = n_rejeicoes
        self.tentativas = 0

    def escolher_acao(self, estado, jogador_nome, acoes_legais, config):
        return acoes_legais[0]

    def aceitar_mao(self, mao, jogador_nome, config):
        self.tentativas += 1
        return self.tentativas > self.n_rejeicoes


def test_quem_mantem_a_mao_ganha_compra_bonus_e_ponto_a_partir_da_2a_recusa_do_outro():
    """Seção 3.4, caso "o vencedor não [recusa] -> puxa uma carta" +
    "insiste de novo -> +1 ponto também" — testado de ponta a ponta via
    match.configurar_partida, não só na função pura de engine.py.

    Usa decks com mão inicial garantidamente válida (ver
    `_deck_quase_todo_herois_comuns`) pra isolar a recusa VOLUNTÁRIA de
    qualquer chance de uma recusa forçada por mão inválida entrar na
    contagem esperada.
    """
    config = carregar_config()
    deck1 = _deck_quase_todo_herois_comuns(config, seed=1)
    deck2 = _deck_quase_todo_herois_comuns(config, seed=2)

    aceita_logo = _AceitaAposNRejeicoes(0)
    recusa_3x = _AceitaAposNRejeicoes(3)

    estado = configurar_partida(config, deck1, deck2, ai1=aceita_logo, ai2=recusa_3x, seed=1)

    eventos_desistencia = [e for e in estado.log if e.get("acao") == "mulligan_desistencia"]
    assert len(eventos_desistencia) == 3
    assert all(e["jogador"] == "P2" for e in eventos_desistencia)
    assert aceita_logo.tentativas == 1  # aceitou na primeira (e única) consulta

    # P1 manteve a mão o tempo todo. Pontos: sempre exatamente 2, não importa
    # quem venceu o par ou ímpar — na hora em que P2 acumula sua 2ª e 3ª
    # recusa CONSECUTIVA, P1 já aceitou de qualquer forma (aceitou na
    # rodada 1, e o ponto só entra a partir da 2ª recusa). Compra-bônus já
    # varia com quem é titular: se P1 é o não-titular (perguntado primeiro),
    # ganha bônus nas 3 recusas de P2; se P1 é o titular (decide por
    # último), a 1ª recusa de P2 na rodada 1 acontece antes de P1 decidir
    # e não gera bônus — só 2 das 3.
    assert estado.jogadores["P1"].pontos == 2
    tamanho_esperado_min = config["mao_inicial"] - 1 + 2  # -1 do herói que entra em campo
    tamanho_esperado_max = config["mao_inicial"] - 1 + 3
    assert tamanho_esperado_min <= len(estado.jogadores["P1"].mao) <= tamanho_esperado_max


def test_mao_aceita_nunca_e_reavaliada():
    """"Não se pode mudar a mão, uma vez que já foi aceita" — uma vez que
    um jogador aceitou, `aceitar_mao` não é chamada de novo pra ele."""
    config = carregar_config()
    deck1 = _deck_quase_todo_herois_comuns(config, seed=3)
    deck2 = _deck_quase_todo_herois_comuns(config, seed=4)

    aceita_logo = _AceitaAposNRejeicoes(0)
    recusa_algumas = _AceitaAposNRejeicoes(2)

    configurar_partida(config, deck1, deck2, ai1=aceita_logo, ai2=recusa_algumas, seed=5)

    # aceita_logo só deveria ter sido consultada 1 vez (aceitou de cara);
    # recusa_algumas deveria ter sido consultada até aceitar (3 tentativas)
    assert aceita_logo.tentativas == 1
    assert recusa_algumas.tentativas == 3


def test_recusa_voluntaria_de_mao_valida_funciona_com_deck_normal():
    """Uma IA "exigente" pode recusar mesmo uma mão TECNICAMENTE válida
    (com herói comum) de um deck normal — não é só o caso de deck sem
    comuns que aciona o mulligan."""
    config = carregar_config()
    deck1 = _deck_quase_todo_herois_comuns(config, seed=6)
    deck2 = _deck_quase_todo_herois_comuns(config, seed=7)

    sempre_exigente = _AceitaAposNRejeicoes(5)
    aceita_logo = _AceitaAposNRejeicoes(0)

    estado = configurar_partida(config, deck1, deck2, ai1=sempre_exigente, ai2=aceita_logo, seed=8)

    eventos_desistencia = [e for e in estado.log if e.get("acao") == "mulligan_desistencia"]
    assert len(eventos_desistencia) == 5
    assert all(e["jogador"] == "P1" for e in eventos_desistencia)
