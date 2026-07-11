"""M4: HeuristicAI — smoke test e sanidade (deve jogar bem melhor que RandomAI)."""
from ai.heuristic_ai import HeuristicAI
from ai.random_ai import RandomAI
from cardpool import montar_deck_medio
from cards import Heroi, Invocacao
from match import MAX_TURNOS_SEGURANCA, jogar_partida


def test_heuristic_recusa_mao_fraca_mas_aceita_com_invocacao_ou_heroi_forte():
    ia = HeuristicAI(seed=1)
    so_comum = [Heroi(raridade="comum")]
    comum_com_invocacao = [Heroi(raridade="comum"), Invocacao(categoria="Acao")]
    comum_com_heroi_forte = [Heroi(raridade="comum"), Heroi(raridade="rara")]

    assert ia.aceitar_mao(so_comum, "P1", {}) is False
    assert ia.aceitar_mao(comum_com_invocacao, "P1", {}) is True
    assert ia.aceitar_mao(comum_com_heroi_forte, "P1", {}) is True


def test_random_ai_sempre_aceita_mao_valida():
    ia = RandomAI(seed=1)
    assert ia.aceitar_mao([Heroi(raridade="comum")], "P1", {}) is True


def test_heuristic_x_random_sem_crash_nem_loop_infinito(config):
    for i in range(60):
        deck1 = montar_deck_medio(config, seed=1000 + i)
        deck2 = montar_deck_medio(config, seed=2000 + i)
        resultado = jogar_partida(
            config, deck1, deck2, HeuristicAI(seed=i), RandomAI(seed=i + 50), seed=i
        )
        assert resultado.turnos < MAX_TURNOS_SEGURANCA
        assert resultado.vencedor in ("P1", "P2")


def test_heuristic_x_heuristic_sem_crash(config):
    for i in range(30):
        deck1 = montar_deck_medio(config, seed=3000 + i)
        deck2 = montar_deck_medio(config, seed=4000 + i)
        resultado = jogar_partida(
            config, deck1, deck2, HeuristicAI(seed=i), HeuristicAI(seed=i + 1), seed=i
        )
        assert resultado.turnos < MAX_TURNOS_SEGURANCA


def test_heuristic_bate_random_com_deck_igual(config):
    """Sanidade: com o mesmo deck, a IA nível 2 deve vencer a IA nível 1
    esmagadoramente — se isso não acontecer, a heurística está quebrada."""
    vitorias_heuristic = 0
    n = 60
    for i in range(n):
        deck1 = montar_deck_medio(config, seed=5000 + i)
        deck2 = montar_deck_medio(config, seed=6000 + i)
        resultado = jogar_partida(
            config, deck1, deck2, HeuristicAI(seed=i), RandomAI(seed=i + 90), seed=i
        )
        if resultado.vencedor == "P1":
            vitorias_heuristic += 1
    assert vitorias_heuristic / n >= 0.7
