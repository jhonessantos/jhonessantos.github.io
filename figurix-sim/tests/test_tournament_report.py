"""M4: tournament.py + report.py — métricas 1, 3, 5, 7."""
from ai.heuristic_ai import HeuristicAI
from ai.random_ai import RandomAI
from cardpool import montar_deck_fraco, montar_deck_forte, montar_deck_medio
from report import (
    metrica_duracao,
    metrica_uso_mecanicas,
    metrica_vantagem_primeiro_jogador,
    metrica_winrate_por_forca,
)
from tournament import rodar_torneio


def test_torneio_produz_resumos_consistentes(config):
    resumos = rodar_torneio(
        config,
        criar_deck_a=lambda seed: montar_deck_medio(config, seed=seed + 1),
        criar_deck_b=lambda seed: montar_deck_medio(config, seed=seed + 1000),
        criar_ai_a=lambda seed: RandomAI(seed=seed),
        criar_ai_b=lambda seed: RandomAI(seed=seed + 1),
        n_partidas=30,
        seed_base=0,
    )
    assert len(resumos) == 30
    for r in resumos:
        assert r.vencedor_papel in ("A", "B", None)
        assert r.primeiro_papel in ("A", "B")
        assert r.turnos > 0


def test_alternar_lados_equilibra_primeiro_jogador_fisico(config):
    # com alternar_lados=True, o papel A não deve SEMPRE cair em P1
    resumos = rodar_torneio(
        config,
        criar_deck_a=lambda seed: montar_deck_medio(config, seed=seed + 1),
        criar_deck_b=lambda seed: montar_deck_medio(config, seed=seed + 1000),
        criar_ai_a=lambda seed: RandomAI(seed=seed),
        criar_ai_b=lambda seed: RandomAI(seed=seed + 1),
        n_partidas=20,
        seed_base=0,
        alternar_lados=True,
    )
    primeiros = [r.primeiro_papel for r in resumos]
    assert "A" in primeiros and "B" in primeiros


def test_metrica_winrate_por_forca(config):
    resumos = rodar_torneio(
        config,
        criar_deck_a=lambda seed: montar_deck_forte(config, seed=seed + 1),
        criar_deck_b=lambda seed: montar_deck_fraco(config, seed=seed + 1000),
        criar_ai_a=lambda seed: HeuristicAI(seed=seed),
        criar_ai_b=lambda seed: HeuristicAI(seed=seed + 1),
        n_partidas=40,
        seed_base=0,
    )
    metricas = metrica_winrate_por_forca(resumos, papel_forte="A")
    assert metricas["n_partidas"] == 40
    assert 0.0 <= metricas["winrate_forte"] <= 1.0
    assert metricas["veredito"] in ("saudável", "força domina (problema)", "fora da faixa saudável (60-70%) — investigar")


def test_metrica_duracao(config):
    resumos = rodar_torneio(
        config,
        criar_deck_a=lambda seed: montar_deck_medio(config, seed=seed + 1),
        criar_deck_b=lambda seed: montar_deck_medio(config, seed=seed + 1000),
        criar_ai_a=lambda seed: RandomAI(seed=seed),
        criar_ai_b=lambda seed: RandomAI(seed=seed + 1),
        n_partidas=30,
        seed_base=0,
    )
    metricas = metrica_duracao(resumos)
    assert metricas["media"] > 0
    assert metricas["mediana"] > 0
    assert 0.0 <= metricas["pct_acima_40_turnos"] <= 1.0


def test_metrica_uso_mecanicas(config):
    resumos = rodar_torneio(
        config,
        criar_deck_a=lambda seed: montar_deck_medio(config, seed=seed + 1),
        criar_deck_b=lambda seed: montar_deck_medio(config, seed=seed + 1000),
        criar_ai_a=lambda seed: HeuristicAI(seed=seed),
        criar_ai_b=lambda seed: HeuristicAI(seed=seed + 1),
        n_partidas=40,
        seed_base=0,
    )
    metricas = metrica_uso_mecanicas(resumos)
    assert "atacar_terciario" in metricas
    assert 0.0 <= metricas["atacar_terciario"]["pct_partidas_com_uso"] <= 1.0
    assert "_profundidade_media_cadeia_barragem" in metricas


def test_metrica_vantagem_primeiro_jogador(config):
    resumos = rodar_torneio(
        config,
        criar_deck_a=lambda seed: montar_deck_medio(config, seed=seed + 1),
        criar_deck_b=lambda seed: montar_deck_medio(config, seed=seed + 1000),
        criar_ai_a=lambda seed: RandomAI(seed=seed),
        criar_ai_b=lambda seed: RandomAI(seed=seed + 1),
        n_partidas=40,
        seed_base=0,
    )
    metricas = metrica_vantagem_primeiro_jogador(resumos)
    assert 0.0 <= metricas["winrate_primeiro_jogador"] <= 1.0


def test_espiral_papeis_detecta_deck_com_poucos_herois(config):
    """Um deck extremo (10 heróis) enfrentando um normal deve cair na
    espiral de busca de herói (seção 10) com bem mais frequência."""
    from cardpool import montar_deck

    resumos = rodar_torneio(
        config,
        criar_deck_a=lambda seed: montar_deck(
            config, seed=seed, faixa_forca="medio", arquetipo="hiperinvocacao", perfil_invocacoes="abundante"
        ),
        criar_deck_b=lambda seed: montar_deck_medio(config, seed=seed + 100_000),
        criar_ai_a=lambda seed: HeuristicAI(seed=seed),
        criar_ai_b=lambda seed: HeuristicAI(seed=seed + 1),
        n_partidas=60,
        seed_base=0,
    )
    pct_espiral_a = sum(1 for r in resumos if "A" in r.espiral_papeis) / len(resumos)
    pct_espiral_b = sum(1 for r in resumos if "B" in r.espiral_papeis) / len(resumos)
    assert pct_espiral_a > pct_espiral_b
