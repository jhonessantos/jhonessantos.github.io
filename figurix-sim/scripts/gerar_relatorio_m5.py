#!/usr/bin/env python3
"""Gera o relatório M5 completo: métricas 1-7 (seção 5 da spec do simulador).

Métricas 1, 3, 5, 7 usam HeuristicAI (N=2000, rápido). Métrica 2 (skill
gap) exige MCTSAI por definição — dado o custo computacional de MCTS
neste ambiente (partidas deste jogo são naturalmente longas, ver achado
do M4), rodamos com um N bem menor e parâmetros enxutos de MCTS,
documentado explicitamente no relatório como uma limitação de ambiente,
não de design. Métricas 4 (fator Juiz) e 6 (comebacks) não exigem MCTS
no enunciado — usamos o mesmo dataset HeuristicAI de N=2000.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ai.heuristic_ai import HeuristicAI  # noqa: E402
from ai.mcts_ai import MCTSAI  # noqa: E402
from cardpool import montar_deck_fraco, montar_deck_forte, montar_deck_medio  # noqa: E402
from config import carregar_config  # noqa: E402
from report import (  # noqa: E402
    formatar_relatorio_markdown,
    metrica_comebacks,
    metrica_duracao,
    metrica_fator_juiz,
    metrica_skill_gap,
    metrica_uso_mecanicas,
    metrica_vantagem_primeiro_jogador,
    metrica_winrate_por_forca,
    salvar_csv_resumos,
    salvar_relatorio,
)
from tournament import rodar_torneio  # noqa: E402

N_HEURISTIC = 2000
N_MCTS = 100  # compute-constrained — ver nota no relatório
SAIDA = ROOT / "relatorios"
SAIDA.mkdir(exist_ok=True)


def main():
    config = carregar_config()

    print(f"[1/3] forte_vs_fraco, HeuristicAI ({N_HEURISTIC} partidas)...")
    t0 = time.time()
    resumos_forca = rodar_torneio(
        config,
        criar_deck_a=lambda seed: montar_deck_forte(config, seed=seed + 1),
        criar_deck_b=lambda seed: montar_deck_fraco(config, seed=seed + 100_000),
        criar_ai_a=lambda seed: HeuristicAI(seed=seed),
        criar_ai_b=lambda seed: HeuristicAI(seed=seed + 1),
        n_partidas=N_HEURISTIC,
        seed_base=0,
    )
    salvar_csv_resumos(resumos_forca, SAIDA / "m5_forte_vs_fraco.csv")
    print(f"      ...{round(time.time()-t0,1)}s")

    print(f"[2/3] medio_espelho, HeuristicAI ({N_HEURISTIC} partidas)...")
    t0 = time.time()
    resumos_espelho = rodar_torneio(
        config,
        criar_deck_a=lambda seed: montar_deck_medio(config, seed=seed + 1),
        criar_deck_b=lambda seed: montar_deck_medio(config, seed=seed + 100_000),
        criar_ai_a=lambda seed: HeuristicAI(seed=seed),
        criar_ai_b=lambda seed: HeuristicAI(seed=seed + 1),
        n_partidas=N_HEURISTIC,
        seed_base=0,
    )
    salvar_csv_resumos(resumos_espelho, SAIDA / "m5_medio_espelho.csv")
    print(f"      ...{round(time.time()-t0,1)}s")

    print(f"[3/3] skill_gap MCTS+fraco x Heuristic+forte ({N_MCTS} partidas, "
          f"n_simulacoes=20, profundidade_rollout=6)...")
    t0 = time.time()
    resumos_skill = rodar_torneio(
        config,
        criar_deck_a=lambda seed: montar_deck_fraco(config, seed=seed + 1),
        criar_deck_b=lambda seed: montar_deck_forte(config, seed=seed + 100_000),
        criar_ai_a=lambda seed: MCTSAI(n_simulacoes=20, profundidade_rollout=6, seed=seed),
        criar_ai_b=lambda seed: HeuristicAI(seed=seed + 1),
        n_partidas=N_MCTS,
        seed_base=0,
    )
    salvar_csv_resumos(resumos_skill, SAIDA / "m5_skill_gap.csv")
    print(f"      ...{round(time.time()-t0,1)}s")

    indecisas_skill = sum(1 for r in resumos_skill if r.vencedor_papel is None)

    secoes = {
        "1. Winrate por diferença de poder (deck_forte x deck_fraco, HeuristicAI)": metrica_winrate_por_forca(
            resumos_forca, papel_forte="A"
        ),
        "2. Skill gap — MCTS+deck_fraco x HeuristicAI+deck_forte": {
            **metrica_skill_gap(resumos_skill, papel_ia_esperta="A"),
            "partidas_indecisas_no_limite_de_turnos": indecisas_skill,
            "nota": (
                f"N={N_MCTS} (não 2000) e MCTSAI com apenas 20 simulações/6 turnos de "
                f"rollout — orçamento de tempo deste ambiente não permite N maior; "
                f"partidas deste jogo são naturalmente longas (ver métrica 3), o que "
                f"torna MCTS caro. Resultado é indicativo, não definitivo."
            ),
        },
        "3. Duração das partidas (deck_medio x deck_medio, HeuristicAI)": metrica_duracao(resumos_espelho),
        "4. Fator Juiz (deck_medio x deck_medio, HeuristicAI)": metrica_fator_juiz(resumos_espelho),
        "5. Uso de mecânicas (deck_medio x deck_medio, HeuristicAI)": metrica_uso_mecanicas(resumos_espelho),
        "6. Comebacks — vitórias vindo de >= 4 pontos atrás (deck_medio x deck_medio, HeuristicAI)": metrica_comebacks(
            resumos_espelho
        ),
        "7. Vantagem do primeiro jogador (deck_medio x deck_medio, HeuristicAI)": metrica_vantagem_primeiro_jogador(
            resumos_espelho
        ),
    }
    texto = formatar_relatorio_markdown("Relatório completo M5 — regras_v1.json", secoes)
    salvar_relatorio(SAIDA / "m5_report_completo.md", texto)
    print(texto)
    print(f"\nSalvo em {SAIDA}/m5_report_completo.md (+ CSVs por experimento)")


if __name__ == "__main__":
    main()
