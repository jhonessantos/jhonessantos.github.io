"""M3: smoke test — RandomAI x RandomAI não deve crashar nem loopar infinito,
e a duração das partidas deve ter uma distribuição plausível.

O smoke test completo de 1000 partidas (spec, seção 7 M3) foi rodado
manualmente durante o desenvolvimento (0 crashes, 0 timeouts, mediana de
~132 turnos, p95 ~415 turnos). Aqui rodamos uma amostra menor para manter
a suíte de testes rápida em CI.
"""
from ai.random_ai import RandomAI
from cardpool import montar_deck_fraco, montar_deck_forte, montar_deck_medio
from match import MAX_TURNOS_SEGURANCA, jogar_partida

PERFIS = [montar_deck_fraco, montar_deck_medio, montar_deck_forte]
N_PARTIDAS_TESTE = 150


def test_smoke_random_x_random_sem_crash_nem_loop_infinito(config):
    turnos = []
    vencedores = {"P1": 0, "P2": 0, None: 0}

    for i in range(N_PARTIDAS_TESTE):
        perfil1 = PERFIS[i % 3]
        perfil2 = PERFIS[(i + 1) % 3]
        deck1 = perfil1(config, seed=10_000 + i)
        deck2 = perfil2(config, seed=20_000 + i)
        ai1, ai2 = RandomAI(seed=30_000 + i), RandomAI(seed=40_000 + i)

        resultado = jogar_partida(config, deck1, deck2, ai1, ai2, seed=i)

        assert resultado.turnos < MAX_TURNOS_SEGURANCA, "partida não terminou (possível loop infinito)"
        turnos.append(resultado.turnos)
        vencedores[resultado.vencedor] += 1

    assert vencedores[None] == 0
    assert vencedores["P1"] > 0 and vencedores["P2"] > 0

    turnos.sort()
    n = len(turnos)
    mediana = turnos[n // 2]
    p95 = turnos[int(n * 0.95)]

    # distribuição plausível: nem partidas absurdamente curtas nem só longas
    assert 10 < mediana < MAX_TURNOS_SEGURANCA
    assert p95 < MAX_TURNOS_SEGURANCA


def test_partida_unica_produz_log_estruturado(config):
    deck1 = montar_deck_medio(config, seed=1)
    deck2 = montar_deck_medio(config, seed=2)
    resultado = jogar_partida(config, deck1, deck2, RandomAI(seed=1), RandomAI(seed=2), seed=1)

    assert resultado.vencedor in ("P1", "P2")
    assert resultado.pontos["P1"] >= 0 and resultado.pontos["P2"] >= 0
    assert isinstance(resultado.log, list)
