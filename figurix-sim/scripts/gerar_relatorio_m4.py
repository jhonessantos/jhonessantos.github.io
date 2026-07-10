#!/usr/bin/env python3
"""Gera o relatório M4: métricas 1, 3, 5, 7 com HeuristicAI e N=2000 partidas
por experimento, seeds fixas (seção 5 da spec do simulador)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ai.heuristic_ai import HeuristicAI  # noqa: E402
from cardpool import montar_deck_fraco, montar_deck_forte, montar_deck_medio  # noqa: E402
from config import carregar_config  # noqa: E402
from report import (  # noqa: E402
    formatar_relatorio_markdown,
    metrica_duracao,
    metrica_uso_mecanicas,
    metrica_vantagem_primeiro_jogador,
    metrica_winrate_por_forca,
    salvar_csv_resumos,
    salvar_relatorio,
)
from tournament import rodar_torneio  # noqa: E402

N_PARTIDAS = 2000
SAIDA = ROOT / "relatorios"
SAIDA.mkdir(exist_ok=True)


def main():
    config = carregar_config()

    print(f"Rodando experimento forte_vs_fraco ({N_PARTIDAS} partidas)...")
    resumos_forca = rodar_torneio(
        config,
        criar_deck_a=lambda seed: montar_deck_forte(config, seed=seed + 1),
        criar_deck_b=lambda seed: montar_deck_fraco(config, seed=seed + 100_000),
        criar_ai_a=lambda seed: HeuristicAI(seed=seed),
        criar_ai_b=lambda seed: HeuristicAI(seed=seed + 1),
        n_partidas=N_PARTIDAS,
        seed_base=0,
    )
    salvar_csv_resumos(resumos_forca, SAIDA / "m4_forte_vs_fraco.csv")

    print(f"Rodando experimento medio_espelho ({N_PARTIDAS} partidas)...")
    resumos_espelho = rodar_torneio(
        config,
        criar_deck_a=lambda seed: montar_deck_medio(config, seed=seed + 1),
        criar_deck_b=lambda seed: montar_deck_medio(config, seed=seed + 100_000),
        criar_ai_a=lambda seed: HeuristicAI(seed=seed),
        criar_ai_b=lambda seed: HeuristicAI(seed=seed + 1),
        n_partidas=N_PARTIDAS,
        seed_base=0,
    )
    salvar_csv_resumos(resumos_espelho, SAIDA / "m4_medio_espelho.csv")

    secoes = {
        "1. Winrate por diferença de poder (deck_forte x deck_fraco, HeuristicAI)": metrica_winrate_por_forca(
            resumos_forca, papel_forte="A"
        ),
        "3. Duração das partidas (deck_medio x deck_medio, HeuristicAI)": metrica_duracao(resumos_espelho),
        "5. Uso de mecânicas (deck_medio x deck_medio, HeuristicAI)": metrica_uso_mecanicas(resumos_espelho),
        "7. Vantagem do primeiro jogador (deck_medio x deck_medio, HeuristicAI)": metrica_vantagem_primeiro_jogador(
            resumos_espelho
        ),
    }
    texto = formatar_relatorio_markdown("Relatório M4 — regras_v1.json", secoes)
    salvar_relatorio(SAIDA / "m4_report.md", texto)
    print(texto)
    print(f"\nSalvo em {SAIDA}/m4_report.md (+ CSVs por experimento)")


if __name__ == "__main__":
    main()
