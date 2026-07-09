"""Seção 6, caso 9: espiral de fim de deck (busca de herói)."""
from cardpool import CardPool
from engine import EstadoEspiral, EstadoJogador, EstadoPartida, em_busca_de_heroi, passo_espiral


def _carta_qualquer(pool):
    return pool.nova_invocacao()


def test_em_busca_de_heroi_detecta_sem_heroi_ativo_e_sem_comum_na_mao(config):
    pool = CardPool(config, seed=1)
    rara = pool.novo_heroi("rara", variacao_id=1)
    jogador = EstadoJogador(nome="P1", heroi_ativo=None, mao=[rara])
    assert em_busca_de_heroi(jogador) is True

    comum = pool.novo_heroi("comum", variacao_id=2)
    jogador2 = EstadoJogador(nome="P1", heroi_ativo=None, mao=[comum])
    assert em_busca_de_heroi(jogador2) is False


def test_escalada_de_compras_aumenta_a_cada_rodada_sem_heroi(config):
    pool = CardPool(config, seed=2)
    deck_grande = [_carta_qualquer(pool) for _ in range(20)]
    jogador = EstadoJogador(nome="P1", heroi_ativo=None, mao=[], deck=list(deck_grande))
    adversario = EstadoJogador(nome="P2", heroi_ativo=None, mao=[], deck=[_carta_qualquer(pool) for _ in range(20)])
    partida = EstadoPartida(jogadores={"P1": jogador, "P2": adversario}, turno_de="P1")
    espiral = EstadoEspiral(jogador_em_busca="P1")

    assert espiral.compras_devidas_busca == 1
    passo_espiral(partida, jogador, adversario, espiral, config)
    assert len(jogador.mao) == 1  # comprou 1
    assert espiral.compras_devidas_busca == 2  # continua sem herói -> escalada

    passo_espiral(partida, jogador, adversario, espiral, config)
    assert len(jogador.mao) == 3  # comprou +2
    assert espiral.compras_devidas_busca == 3


def test_escalada_para_quando_acha_heroi_comum(config):
    pool = CardPool(config, seed=3)
    comum = pool.novo_heroi("comum", variacao_id=1)
    deck = [comum] + [_carta_qualquer(pool) for _ in range(10)]  # topo do deck = último elemento
    jogador = EstadoJogador(nome="P1", heroi_ativo=None, mao=[], deck=list(reversed(deck)))
    adversario = EstadoJogador(nome="P2", heroi_ativo=None, mao=[], deck=[_carta_qualquer(pool) for _ in range(10)])
    partida = EstadoPartida(jogadores={"P1": jogador, "P2": adversario}, turno_de="P1")
    espiral = EstadoEspiral(jogador_em_busca="P1")

    passo_espiral(partida, jogador, adversario, espiral, config)
    assert em_busca_de_heroi(jogador) is False
    assert espiral.compras_devidas_busca == 1  # não escala mais, achou herói


def test_deck_esgota_sem_heroi_cede_5_pontos_e_termina(config):
    pool = CardPool(config, seed=4)
    jogador = EstadoJogador(nome="P1", heroi_ativo=None, mao=[], deck=[], pontos=3)
    adversario = EstadoJogador(nome="P2", heroi_ativo=None, mao=[], deck=[_carta_qualquer(pool)], pontos=2)
    partida = EstadoPartida(jogadores={"P1": jogador, "P2": adversario}, turno_de="P1")
    espiral = EstadoEspiral(jogador_em_busca="P1")

    vencedor = passo_espiral(partida, jogador, adversario, espiral, config)

    assert adversario.pontos == 2 + config["penalidade_sem_deck"]
    assert vencedor == "P2"
    assert partida.vencedor == "P2"


def test_adversario_sem_deck_da_ponto_por_carta_comprada(config):
    pool = CardPool(config, seed=5)
    deck_grande = [_carta_qualquer(pool) for _ in range(5)]
    jogador = EstadoJogador(nome="P1", heroi_ativo=None, mao=[], deck=list(deck_grande))
    adversario = EstadoJogador(nome="P2", heroi_ativo=None, mao=[], deck=[], pontos=0)
    partida = EstadoPartida(jogadores={"P1": jogador, "P2": adversario}, turno_de="P1")
    espiral = EstadoEspiral(jogador_em_busca="P1", compras_devidas_busca=2)

    passo_espiral(partida, jogador, adversario, espiral, config)

    assert adversario.pontos == 2  # 1 ponto por carta comprada pelo jogador em busca
    assert len(jogador.mao) == 2  # jogador em busca continua comprando normalmente
