#!/usr/bin/env python3
"""CLI do simulador Figurix. Uso (M3): python run.py --config regras_v1 --n 1000

As IAs heuristic/mcts e o relatório completo chegam em M4/M5 — por
enquanto o CLI roda partidas RandomAI x RandomAI e imprime um resumo
básico de duração e vitórias (smoke test manual da seção 7, M3).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from ai.random_ai import RandomAI  # noqa: E402
from cardpool import montar_deck_fraco, montar_deck_forte, montar_deck_medio  # noqa: E402
from config import carregar_config  # noqa: E402
from match import jogar_partida  # noqa: E402

PERFIS = {"fraco": montar_deck_fraco, "medio": montar_deck_medio, "forte": montar_deck_forte}
AIS_DISPONIVEIS = {"random": RandomAI}


def main():
    parser = argparse.ArgumentParser(description="Simulador Figurix Card Game")
    parser.add_argument("--config", default="regras_v1", help="nome do arquivo em config/ (sem .json)")
    parser.add_argument("--n", type=int, default=100, help="número de partidas")
    parser.add_argument("--ai1", default="random", choices=AIS_DISPONIVEIS.keys())
    parser.add_argument("--ai2", default="random", choices=AIS_DISPONIVEIS.keys())
    parser.add_argument("--deck1", default="medio", choices=PERFIS.keys())
    parser.add_argument("--deck2", default="medio", choices=PERFIS.keys())
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    caminho_config = Path(__file__).resolve().parent / "config" / f"{args.config}.json"
    config = carregar_config(caminho_config)

    montar1 = PERFIS[args.deck1]
    montar2 = PERFIS[args.deck2]
    ai1_cls = AIS_DISPONIVEIS[args.ai1]
    ai2_cls = AIS_DISPONIVEIS[args.ai2]

    turnos, vencedores = [], {"P1": 0, "P2": 0, None: 0}
    for i in range(args.n):
        deck1 = montar1(config, seed=args.seed + 10_000 + i)
        deck2 = montar2(config, seed=args.seed + 20_000 + i)
        ai1 = ai1_cls(seed=args.seed + 30_000 + i)
        ai2 = ai2_cls(seed=args.seed + 40_000 + i)
        resultado = jogar_partida(config, deck1, deck2, ai1, ai2, seed=args.seed + i)
        turnos.append(resultado.turnos)
        vencedores[resultado.vencedor] += 1

    turnos.sort()
    n = len(turnos)
    print(f"Partidas: {n}")
    print(f"Vencedores: {vencedores}")
    print(f"Turnos — média: {sum(turnos) / n:.1f}, mediana: {turnos[n // 2]}, p95: {turnos[int(n * 0.95)]}")


if __name__ == "__main__":
    main()
