"""Funções puras usadas por POST /api/lotes/combinacoes ("rodar todas as
combinações" de IAs x decks de cada lado) — sem precisar subir o FastAPI."""
from lotes_combinacoes import gerar_combinacoes, nome_da_combinacao, seed_da_combinacao


def test_gerar_combinacoes_e_o_produto_cartesiano():
    combinacoes = gerar_combinacoes(["a1", "a2"], ["b1"], [10, 20], [30])
    assert len(combinacoes) == 2 * 1 * 2 * 1
    assert set(combinacoes) == {
        ("a1", "b1", 10, 30),
        ("a1", "b1", 20, 30),
        ("a2", "b1", 10, 30),
        ("a2", "b1", 20, 30),
    }


def test_gerar_combinacoes_uma_de_cada_e_so_1_combinacao():
    assert gerar_combinacoes(["a"], ["b"], [1], [2]) == [("a", "b", 1, 2)]


def test_nome_da_combinacao_sem_grupo():
    assert nome_da_combinacao(None, "aleatoria", "certinho_v2", "Deck A", "Deck B") == (
        "aleatoria x certinho_v2 — Deck A x Deck B"
    )


def test_nome_da_combinacao_com_grupo():
    nome = nome_da_combinacao("Torneio de verão", "aleatoria", "certinho_v2", "Deck A", "Deck B")
    assert nome == "Torneio de verão — aleatoria x certinho_v2 — Deck A x Deck B"


def test_seed_da_combinacao_e_bem_separada_entre_indices():
    seeds = [seed_da_combinacao(1000, i) for i in range(5)]
    assert seeds == [1000, 1000 + 10_000_000, 1000 + 2 * 10_000_000, 1000 + 3 * 10_000_000, 1000 + 4 * 10_000_000]
    assert len(set(seeds)) == 5


def test_combinacoes_de_uma_simulacao_grande_nao_tem_seeds_sobrepostas():
    """Cada combinação roda até `n_partidas` seeds consecutivas a partir da
    sua seed_base (seed_base + i pra cada partida, ver lote_runner.py) — o
    passo entre combinações precisa ser maior que qualquer n_partidas
    realista pra elas nunca se sobreporem."""
    n_partidas = 500_000  # "vou deixar rodando por horas" — lotes grandes
    combinacoes = gerar_combinacoes(["a1", "a2"], ["b1", "b2"], [1], [2])
    seeds_base = [seed_da_combinacao(0, i) for i in range(len(combinacoes))]
    faixas = [range(s, s + n_partidas) for s in seeds_base]
    for i, faixa_i in enumerate(faixas):
        for j, faixa_j in enumerate(faixas):
            if i != j:
                assert faixa_i.stop <= faixa_j.start or faixa_j.stop <= faixa_i.start
