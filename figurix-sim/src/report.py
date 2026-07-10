"""Métricas e relatório (seção 5 da spec do simulador).

M4 implementa as métricas 1, 3, 5 e 7 (as que não dependem de MCTS):
  1. Winrate por diferença de poder (deck_forte x deck_fraco, mesma IA).
  3. Duração das partidas (média/mediana/p95, % acima de 40 turnos).
  5. Uso de mecânicas (barragens, evoluções, trocas de local, guardiões,
     ataques secundário/terciário — mecânica com uso <2% é peso morto).
  7. Vantagem do primeiro jogador (deve ficar perto de 50%).

As métricas 2 (skill gap), 4 (fator Juiz) e 6 (comebacks) exigem a
MCTSAI e entram no M5.
"""
from __future__ import annotations

import csv
import statistics
from pathlib import Path

from tournament import ResumoPartida


def metrica_winrate_por_forca(resumos: list[ResumoPartida], papel_forte: str = "A") -> dict:
    """Métrica 1: winrate do papel mais forte. Alvo saudável: 60-70%; >85% = força domina."""
    decididas = [r for r in resumos if r.vencedor_papel is not None]
    n = len(decididas)
    vitorias_forte = sum(1 for r in decididas if r.vencedor_papel == papel_forte)
    winrate = vitorias_forte / n if n else 0.0
    if winrate > 0.85:
        veredito = "força domina (problema)"
    elif 0.60 <= winrate <= 0.70:
        veredito = "saudável"
    else:
        veredito = "fora da faixa saudável (60-70%) — investigar"
    return {"n_partidas": n, "winrate_forte": winrate, "veredito": veredito}


def metrica_duracao(resumos: list[ResumoPartida]) -> dict:
    """Métrica 3: duração das partidas em turnos."""
    turnos = sorted(r.turnos for r in resumos)
    n = len(turnos)
    if n == 0:
        return {}
    return {
        "n_partidas": n,
        "media": statistics.mean(turnos),
        "mediana": statistics.median(turnos),
        "p95": turnos[int(n * 0.95)] if n > 1 else turnos[0],
        "pct_acima_40_turnos": sum(1 for t in turnos if t > 40) / n,
    }


def metrica_uso_mecanicas(resumos: list[ResumoPartida]) -> dict:
    """Métrica 5: frequência de uso de cada mecânica. Uso <2% das partidas
    sinaliza mecânica como peso morto ou custo mal calibrado."""
    n = len(resumos)
    if n == 0:
        return {}
    chaves = set()
    for r in resumos:
        chaves.update(r.eventos.keys())
    chaves.discard("barragem_profundidade_soma")

    resultado = {}
    for chave in sorted(chaves):
        partidas_com_uso = sum(1 for r in resumos if r.eventos.get(chave, 0) > 0)
        total_ocorrencias = sum(r.eventos.get(chave, 0) for r in resumos)
        resultado[chave] = {
            "pct_partidas_com_uso": partidas_com_uso / n,
            "media_por_partida": total_ocorrencias / n,
        }

    total_cadeias = sum(r.eventos.get("barragem_cadeia", 0) for r in resumos)
    soma_profundidade = sum(r.eventos.get("barragem_profundidade_soma", 0) for r in resumos)
    resultado["_profundidade_media_cadeia_barragem"] = (
        soma_profundidade / total_cadeias if total_cadeias else 0.0
    )
    return resultado


def metrica_vantagem_primeiro_jogador(resumos: list[ResumoPartida]) -> dict:
    """Métrica 7: winrate de quem agiu primeiro. Deve ficar perto de 50%."""
    decididas = [r for r in resumos if r.vencedor_papel is not None]
    n = len(decididas)
    vitorias_primeiro = sum(1 for r in decididas if r.vencedor_papel == r.primeiro_papel)
    winrate = vitorias_primeiro / n if n else 0.0
    return {"n_partidas": n, "winrate_primeiro_jogador": winrate}


def formatar_relatorio_markdown(titulo: str, secoes: dict[str, dict]) -> str:
    linhas = [f"# {titulo}", ""]
    for nome_secao, metricas in secoes.items():
        linhas.append(f"## {nome_secao}")
        linhas.append("")
        for chave, valor in metricas.items():
            if isinstance(valor, dict):
                linhas.append(f"- **{chave}**:")
                for subchave, subvalor in valor.items():
                    linhas.append(f"  - {subchave}: {_fmt(subvalor)}")
            else:
                linhas.append(f"- **{chave}**: {_fmt(valor)}")
        linhas.append("")
    return "\n".join(linhas)


def _fmt(valor):
    if isinstance(valor, float):
        return f"{valor:.3f}"
    return str(valor)


def salvar_relatorio(caminho: str | Path, texto: str) -> None:
    Path(caminho).write_text(texto, encoding="utf-8")


def salvar_csv_resumos(resumos: list[ResumoPartida], caminho: str | Path) -> None:
    """Dump bruto por partida — insumo para auditoria manual e comparação entre variantes."""
    chaves_eventos = sorted({k for r in resumos for k in r.eventos if not k.startswith("_")})
    campos = [
        "vencedor_papel", "primeiro_papel", "turnos", "rodadas", "pontos_a", "pontos_b"
    ] + chaves_eventos

    with open(caminho, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for r in resumos:
            linha = {
                "vencedor_papel": r.vencedor_papel,
                "primeiro_papel": r.primeiro_papel,
                "turnos": r.turnos,
                "rodadas": r.rodadas,
                "pontos_a": r.pontos_a,
                "pontos_b": r.pontos_b,
            }
            for chave in chaves_eventos:
                linha[chave] = r.eventos.get(chave, 0)
            writer.writerow(linha)
