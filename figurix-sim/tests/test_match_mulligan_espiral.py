"""Seção 3.4: um deck sem heróis comuns é uma escolha de construção válida
— o jogador vai desistindo da mão, o adversário ganha pontos, e a
partida pode terminar (o adversário vence) antes mesmo do primeiro
turno. O motor precisa deixar isso acontecer, não impedir/travar."""
from ai.random_ai import RandomAI
from cardpool import CardPool, montar_deck_medio
from config import carregar_config
from match import jogar_partida


def _deck_sem_herois_comuns(config, seed):
    """Deck construído à mão: só heróis raros+ (nenhum comum), preenchido
    com invocações — deliberadamente "impossível" de vencer o mulligan."""
    pool = CardPool(config, seed=seed)
    cartas = [pool.novo_heroi("rara", variacao_id=i) for i in range(1, 10)]
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
