#!/usr/bin/env python3
"""Testa o quanto a ESTRATÉGIA DE MONTAGEM DE DECK (pré-partida) importa,
independente da força bruta das cartas — mesma faixa de força, mesma IA
nos dois lados, variando só a escolha estrutural de deck.

Experimento A — economia de invocações (escasso/moderado/abundante):
testa a hipótese de que "quem investe mais em invocação deveria destroçar
quem economiza" — ou se é só uma troca (economiza invocação, demora mais
pra derrubar o herói adversário) sem um vencedor óbvio.

Experimento B — arquétipos (balanceado/agro/controle/combo), o "E5" da
spec original: nenhum teste anterior comparou os arquétipos entre si.
"""
from __future__ import annotations

import sys
import time
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ai.heuristic_ai import HeuristicAI  # noqa: E402
from cardpool import montar_deck  # noqa: E402
from config import carregar_config  # noqa: E402
from report import metrica_duracao, metrica_winrate_por_forca  # noqa: E402
from tournament import rodar_torneio  # noqa: E402

N = 1000
SAIDA = ROOT / "relatorios"
SAIDA.mkdir(exist_ok=True)

PERFIS_INVOCACAO = ["escasso", "moderado", "abundante"]
ARQUETIPOS = ["balanceado", "agro", "controle", "combo"]


def comparar(config, rotulo_a, deck_a_kwargs, rotulo_b, deck_b_kwargs):
    resumos = rodar_torneio(
        config,
        criar_deck_a=lambda seed: montar_deck(config, seed=seed, **deck_a_kwargs),
        criar_deck_b=lambda seed: montar_deck(config, seed=seed + 100_000, **deck_b_kwargs),
        criar_ai_a=lambda seed: HeuristicAI(seed=seed),
        criar_ai_b=lambda seed: HeuristicAI(seed=seed + 1),
        n_partidas=N,
        seed_base=0,
    )
    winrate_a = metrica_winrate_por_forca(resumos, papel_forte="A")["winrate_forte"]
    duracao = metrica_duracao(resumos)
    n_indecisas = sum(1 for r in resumos if r.vencedor_papel is None)
    return winrate_a, duracao["mediana"], n_indecisas


def main():
    config = carregar_config()
    linhas = ["# Estratégia de montagem de deck — economia de invocações e arquétipos\n"]

    linhas.append("## Experimento A — economia de invocações (força média, arquétipo balanceado)\n")
    linhas.append("| A | B | winrate de A | duração mediana | indecisas |")
    linhas.append("|---|---|---|---|---|")
    for perfil_a, perfil_b in combinations(PERFIS_INVOCACAO, 2):
        print(f"[A] {perfil_a} x {perfil_b} ({N} partidas)...")
        t0 = time.time()
        wr, dur, indecisas = comparar(
            config,
            perfil_a, dict(faixa_forca="medio", arquetipo="balanceado", perfil_invocacoes=perfil_a),
            perfil_b, dict(faixa_forca="medio", arquetipo="balanceado", perfil_invocacoes=perfil_b),
        )
        print(f"      ...{round(time.time()-t0,1)}s")
        linhas.append(f"| {perfil_a} | {perfil_b} | {wr:.3f} | {dur:.0f} | {indecisas} |")

    linhas.append("\n## Experimento B — arquétipos (força média, invocação moderada)\n")
    linhas.append("| A | B | winrate de A | duração mediana | indecisas |")
    linhas.append("|---|---|---|---|---|")
    for arq_a, arq_b in combinations(ARQUETIPOS, 2):
        print(f"[B] {arq_a} x {arq_b} ({N} partidas)...")
        t0 = time.time()
        wr, dur, indecisas = comparar(
            config,
            arq_a, dict(faixa_forca="medio", arquetipo=arq_a, perfil_invocacoes="moderado"),
            arq_b, dict(faixa_forca="medio", arquetipo=arq_b, perfil_invocacoes="moderado"),
        )
        print(f"      ...{round(time.time()-t0,1)}s")
        linhas.append(f"| {arq_a} | {arq_b} | {wr:.3f} | {dur:.0f} | {indecisas} |")

    texto = "\n".join(linhas)
    print("\n" + texto)
    (SAIDA / "estrategia_deck.md").write_text(texto, encoding="utf-8")
    print(f"\nSalvo em {SAIDA}/estrategia_deck.md")


if __name__ == "__main__":
    main()
