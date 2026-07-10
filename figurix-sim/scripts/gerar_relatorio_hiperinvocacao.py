#!/usr/bin/env python3
"""Testa o arquétipo extremo "hiperinvocacao" (só 10 heróis, o resto do
orçamento em mestres/guardiões/juiz/invocação abundante): será que ele
perde por ceder pontos demais na espiral de busca de herói (seção 10),
apesar da vantagem de economia de invocações (ver estrategia_deck.md)?

Cada confronto reporta: winrate, duração mediana, e em que fração das
partidas cada lado chegou a cair na espiral de busca de herói (ficou sem
herói em campo E sem comum na mão) ou a desistir de ao menos 1 mulligan.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ai.heuristic_ai import HeuristicAI  # noqa: E402
from cardpool import montar_deck  # noqa: E402
from config import carregar_config  # noqa: E402
from report import metrica_duracao, metrica_winrate_por_forca  # noqa: E402
from tournament import rodar_torneio  # noqa: E402

N = 1500
SAIDA = ROOT / "relatorios"
SAIDA.mkdir(exist_ok=True)

CONFRONTOS = [
    ("hiperinvocação (médio, abundante)", dict(faixa_forca="medio", arquetipo="hiperinvocacao", perfil_invocacoes="abundante"),
     "balanceado (médio, moderado)", dict(faixa_forca="medio", arquetipo="balanceado", perfil_invocacoes="moderado")),
    ("hiperinvocação (médio, abundante)", dict(faixa_forca="medio", arquetipo="hiperinvocacao", perfil_invocacoes="abundante"),
     "balanceado (médio, escasso)", dict(faixa_forca="medio", arquetipo="balanceado", perfil_invocacoes="escasso")),
    ("hiperinvocação (médio, abundante)", dict(faixa_forca="medio", arquetipo="hiperinvocacao", perfil_invocacoes="abundante"),
     "balanceado (médio, abundante)", dict(faixa_forca="medio", arquetipo="balanceado", perfil_invocacoes="abundante")),
    ("hiperinvocação (médio, abundante)", dict(faixa_forca="medio", arquetipo="hiperinvocacao", perfil_invocacoes="abundante"),
     "agro (médio, moderado)", dict(faixa_forca="medio", arquetipo="agro", perfil_invocacoes="moderado")),
    ("hiperinvocação (FRACO, abundante)", dict(faixa_forca="fraco", arquetipo="hiperinvocacao", perfil_invocacoes="abundante"),
     "balanceado (FORTE, moderado)", dict(faixa_forca="forte", arquetipo="balanceado", perfil_invocacoes="moderado")),
]


def main():
    config = carregar_config()
    linhas = ["# Arquétipo extremo: hiperinvocação (10 heróis) x adversários\n"]
    linhas.append("| A | B | winrate A | duração mediana | A caiu na espiral | B caiu na espiral | A desistiu mulligan | B desistiu mulligan |")
    linhas.append("|---|---|---|---|---|---|---|---|")

    for rotulo_a, kwargs_a, rotulo_b, kwargs_b in CONFRONTOS:
        print(f"{rotulo_a}  x  {rotulo_b}  ({N} partidas)...")
        resumos = rodar_torneio(
            config,
            criar_deck_a=lambda seed, k=kwargs_a: montar_deck(config, seed=seed, **k),
            criar_deck_b=lambda seed, k=kwargs_b: montar_deck(config, seed=seed + 100_000, **k),
            criar_ai_a=lambda seed: HeuristicAI(seed=seed),
            criar_ai_b=lambda seed: HeuristicAI(seed=seed + 1),
            n_partidas=N,
            seed_base=0,
        )
        wr = metrica_winrate_por_forca(resumos, papel_forte="A")["winrate_forte"]
        dur = metrica_duracao(resumos)["mediana"]
        pct_espiral_a = sum(1 for r in resumos if "A" in r.espiral_papeis) / N
        pct_espiral_b = sum(1 for r in resumos if "B" in r.espiral_papeis) / N
        pct_mulligan_a = sum(1 for r in resumos if "A" in r.mulligan_desistencia_papeis) / N
        pct_mulligan_b = sum(1 for r in resumos if "B" in r.mulligan_desistencia_papeis) / N
        linhas.append(
            f"| {rotulo_a} | {rotulo_b} | {wr:.3f} | {dur:.0f} | "
            f"{pct_espiral_a:.3f} | {pct_espiral_b:.3f} | {pct_mulligan_a:.3f} | {pct_mulligan_b:.3f} |"
        )

    texto = "\n".join(linhas)
    print("\n" + texto)
    (SAIDA / "hiperinvocacao.md").write_text(texto, encoding="utf-8")
    print(f"\nSalvo em {SAIDA}/hiperinvocacao.md")


if __name__ == "__main__":
    main()
