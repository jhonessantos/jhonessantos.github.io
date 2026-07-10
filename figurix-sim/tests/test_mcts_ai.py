"""M5: MCTSAI — smoke test com orçamento bem enxuto (CI precisa ser rápido;
os experimentos reais do relatório usam mais simulações, ver scripts/)."""
from ai.heuristic_ai import HeuristicAI
from ai.mcts_ai import MCTSAI
from cardpool import montar_deck_medio
from match import jogar_partida


def test_mcts_x_heuristic_sem_crash(config):
    for i in range(5):
        deck1 = montar_deck_medio(config, seed=1000 + i)
        deck2 = montar_deck_medio(config, seed=2000 + i)
        resultado = jogar_partida(
            config, deck1, deck2,
            MCTSAI(n_simulacoes=8, profundidade_rollout=4, seed=i),
            HeuristicAI(seed=i + 1),
            seed=i,
        )
        assert resultado.turnos > 0


def test_mcts_toma_acoes_reais_nao_so_passar(config):
    """Regressão do bug de desempate: MCTS não pode convergir sempre para
    'passar' só porque é o índice 0 de acoes_legais."""
    deck1 = montar_deck_medio(config, seed=1)
    deck2 = montar_deck_medio(config, seed=2)
    resultado = jogar_partida(
        config, deck1, deck2,
        MCTSAI(n_simulacoes=10, profundidade_rollout=4, seed=1),
        HeuristicAI(seed=2),
        seed=1,
    )
    tipos_de_acao = {ev.get("acao") for ev in resultado.log}
    assert "atacar" in tipos_de_acao


def test_mcts_determinizacao_preserva_tamanhos(config):
    from match import configurar_partida

    deck1 = montar_deck_medio(config, seed=5)
    deck2 = montar_deck_medio(config, seed=6)
    estado = configurar_partida(config, deck1, deck2, seed=1)
    mcts = MCTSAI(seed=1)

    jogador_nome = estado.turno_de
    adversario_nome = next(n for n in estado.jogadores if n != jogador_nome)
    adv_original = estado.jogadores[adversario_nome]
    n_mao_antes, n_deck_antes = len(adv_original.mao), len(adv_original.deck)

    clone = mcts._determinizar(estado, jogador_nome)
    adv_clone = clone.jogadores[adversario_nome]
    assert len(adv_clone.mao) == n_mao_antes
    assert len(adv_clone.deck) == n_deck_antes


def test_clonar_estado_nao_afeta_original(config):
    from cardpool import montar_deck_medio as md
    from match import configurar_partida
    import engine as eng

    deck1 = md(config, seed=7)
    deck2 = md(config, seed=8)
    estado = configurar_partida(config, deck1, deck2, seed=1)
    clone = eng.clonar_estado(estado)

    jogador_nome = next(iter(estado.jogadores))
    clone.jogadores[jogador_nome].pontos = 999
    assert estado.jogadores[jogador_nome].pontos != 999

    if estado.jogadores[jogador_nome].heroi_ativo is not None:
        clone.jogadores[jogador_nome].heroi_ativo.forca_atual = -1
        assert estado.jogadores[jogador_nome].heroi_ativo.forca_atual != -1
