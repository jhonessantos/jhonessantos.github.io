#!/usr/bin/env python3
"""M6: roda as variantes prioritárias (pontos_ur=4, cura_juiz=50,
compra_dupla=OFF) e compara com o baseline regras_v1.json.

Usa HeuristicAI (rápido o bastante para N=1000 por experimento) — o
objetivo aqui é comparar o EFEITO RELATIVO de cada variante, não gerar
o relatório mais preciso possível (esse já existe em m5_report_completo.md).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ai.heuristic_ai import HeuristicAI  # noqa: E402
from cardpool import montar_deck_fraco, montar_deck_forte, montar_deck_medio  # noqa: E402
from config import carregar_config, carregar_variante  # noqa: E402
from report import (  # noqa: E402
    metrica_comebacks,
    metrica_duracao,
    metrica_fator_juiz,
    metrica_vantagem_primeiro_jogador,
    metrica_winrate_por_forca,
)
from tournament import rodar_torneio  # noqa: E402

N = 1000
SAIDA = ROOT / "relatorios"
SAIDA.mkdir(exist_ok=True)

VARIANTES = {
    "baseline (regras_v1)": None,
    "pontos_ur=4": "pontos_ur4",
    "cura_juiz=50": "cura_juiz50",
    "compra_dupla=OFF": "compra_dupla_off",
}


def rodar_experimentos(config: dict) -> dict:
    resumos_forca = rodar_torneio(
        config,
        criar_deck_a=lambda seed: montar_deck_forte(config, seed=seed + 1),
        criar_deck_b=lambda seed: montar_deck_fraco(config, seed=seed + 100_000),
        criar_ai_a=lambda seed: HeuristicAI(seed=seed),
        criar_ai_b=lambda seed: HeuristicAI(seed=seed + 1),
        n_partidas=N,
        seed_base=0,
    )
    resumos_espelho = rodar_torneio(
        config,
        criar_deck_a=lambda seed: montar_deck_medio(config, seed=seed + 1),
        criar_deck_b=lambda seed: montar_deck_medio(config, seed=seed + 100_000),
        criar_ai_a=lambda seed: HeuristicAI(seed=seed),
        criar_ai_b=lambda seed: HeuristicAI(seed=seed + 1),
        n_partidas=N,
        seed_base=0,
    )
    return {
        "winrate_forte": metrica_winrate_por_forca(resumos_forca, papel_forte="A")["winrate_forte"],
        "duracao_mediana": metrica_duracao(resumos_espelho)["mediana"],
        "duracao_pct_acima_40": metrica_duracao(resumos_espelho)["pct_acima_40_turnos"],
        "juiz_pct_em_campo": metrica_fator_juiz(resumos_espelho)["pct_partidas_com_juiz_em_campo"],
        "juiz_winrate_de_quem_joga": metrica_fator_juiz(resumos_espelho)["winrate_de_quem_joga_o_juiz"],
        "pct_comebacks": metrica_comebacks(resumos_espelho)["pct_comebacks"],
        "winrate_primeiro_jogador": metrica_vantagem_primeiro_jogador(resumos_espelho)["winrate_primeiro_jogador"],
    }


def main():
    linhas = {}
    for nome, variante in VARIANTES.items():
        print(f"Rodando {nome} ({2 * N} partidas)...")
        config = carregar_config() if variante is None else carregar_variante(variante)
        linhas[nome] = rodar_experimentos(config)

    campos = list(next(iter(linhas.values())).keys())

    texto = ["# Comparativo de variantes — M6\n"]
    cabecalho = "| métrica | " + " | ".join(linhas.keys()) + " |"
    separador = "|---" * (len(linhas) + 1) + "|"
    texto.append(cabecalho)
    texto.append(separador)
    for campo in campos:
        valores = [f"{linhas[nome][campo]:.3f}" for nome in linhas]
        texto.append(f"| {campo} | " + " | ".join(valores) + " |")

    saida_texto = "\n".join(texto)
    print("\n" + saida_texto)
    (SAIDA / "m6_comparativo_variantes.md").write_text(saida_texto, encoding="utf-8")
    print(f"\nSalvo em {SAIDA}/m6_comparativo_variantes.md")


if __name__ == "__main__":
    main()
