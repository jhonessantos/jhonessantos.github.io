"""Cadeias de barragem (contraturno) — seção 6 das regras.

Modelada como pilha (estilo "stack" de MTG): cada barragem responde ao
elemento que está no topo no momento em que é declarada. Resolução
sempre do topo para a base — o par (barragem, alvo-imediatamente-abaixo)
se cancela (ambos ao descarte); o que sobrar embaixo (se ficar sozinho)
resolve normalmente.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from cards import Guardiao, Juiz, Mestre
from combat import tem_vantagem


def _tipo_carta(carta) -> str:
    if isinstance(carta, Guardiao):
        return "guardiao"
    if isinstance(carta, Mestre):
        return "mestre"
    if isinstance(carta, Juiz):
        return "juiz"
    raise ValueError(f"Carta não barrável: {carta!r}")


def pode_barrar(barrador, alvo, config: dict) -> bool:
    """Verifica só a condição de FORÇA/tipo (seção 6). Custo é tratado à parte."""
    tipo_b = _tipo_carta(barrador)
    tipo_a = _tipo_carta(alvo)
    desconto_vantagem = config["desconto_vantagem_barragem"]

    if tipo_b == "guardiao":
        if tipo_a != "guardiao":
            return False
        if barrador.forca_impressa > alvo.forca_impressa:
            return True
        if tem_vantagem(barrador.categoria, alvo.categoria, config):
            return barrador.forca_impressa >= alvo.forca_impressa - desconto_vantagem
        return False

    if tipo_b == "mestre":
        if tipo_a not in ("guardiao", "mestre"):
            return False
        return barrador.forca_impressa > alvo.forca_impressa

    if tipo_b == "juiz":
        if tipo_a == "juiz":
            if barrador.forca_impressa > alvo.forca_impressa:
                return True
            if tem_vantagem(barrador.categoria, alvo.categoria, config):
                return barrador.forca_impressa >= alvo.forca_impressa - desconto_vantagem
            return False
        if tipo_a in ("guardiao", "mestre"):
            desconto_juiz = config["desconto_juiz_vs_aux"]
            return barrador.forca_impressa >= alvo.forca_impressa - desconto_juiz
        return False

    return False


def custo_barragem(barrador, config: dict) -> tuple[int, str]:
    """Retorna (quantidade, categoria) de invocações exigidas para barrar."""
    return config["custo_barragem"], barrador.categoria


@dataclass
class ElementoCadeia:
    carta: object  # Guardiao | Mestre | Juiz
    jogador: str  # identificador de quem controla a carta


@dataclass
class ResultadoCadeia:
    sobrevivente: Optional[ElementoCadeia]
    descartes: list  # lista de cartas que foram para o descarte, na ordem de resolução


def resolver_cadeia(pilha: list[ElementoCadeia]) -> ResultadoCadeia:
    """Resolve a pilha do topo para a base, aos pares.

    Assume que a legalidade de cada barragem (pode_barrar) já foi
    verificada no momento da declaração (ao empilhar). Aqui só
    aplicamos a mecânica de cancelamento em pares.
    """
    restante = list(pilha)
    descartes = []
    while len(restante) >= 2:
        barragem = restante.pop()
        alvo = restante.pop()
        descartes.append(barragem.carta)
        descartes.append(alvo.carta)
    sobrevivente = restante[0] if restante else None
    return ResultadoCadeia(sobrevivente=sobrevivente, descartes=descartes)
