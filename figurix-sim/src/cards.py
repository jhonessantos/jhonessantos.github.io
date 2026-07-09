"""Modelos de carta do Figurix Card Game.

Cada carta é um template imutável (dataclass frozen). Estado de partida
(força atual, item anexado, rodadas restantes de efeito etc.) NÃO mora
aqui — isso é responsabilidade do engine.py, que envolve estas cartas em
estruturas de estado clonáveis.

Nenhum número de regra é hardcoded: tudo vem do dict de config
carregado por config.py (ver seção 12 das regras / regras_v1.json).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count
from typing import Optional

RARIDADES_BASE = ("comum", "rara", "super_rara", "ultra_rara")

_uid_counter = count(1)


def _next_uid() -> int:
    return next(_uid_counter)


def reset_uid_counter(start: int = 1) -> None:
    """Usado pelos testes para tornar uids determinísticos entre execuções."""
    global _uid_counter
    _uid_counter = count(start)


def raridade_equivalente(raridade: str, config: dict) -> str:
    """Mapeia uma raridade (base ou especial) para a raridade base equivalente.

    Especiais (comemorativa, pos_rara, pos_super, pos_ultra) têm
    EQUIVALÊNCIA TOTAL com a raridade base correspondente (seção 1).
    """
    especiais = config["especiais_por_raridade"]
    if raridade in especiais:
        return especiais[raridade]
    if raridade in config["raridades"]:
        return raridade
    raise ValueError(f"Raridade desconhecida: {raridade!r}")


def eh_especial(raridade: str, config: dict) -> bool:
    return raridade in config["especiais_por_raridade"]


def poderes_da_raridade(raridade: str, config: dict) -> tuple[int, int, int]:
    base = raridade_equivalente(raridade, config)
    principal, secundario, terciario = config["poderes_por_raridade"][base]
    return principal, secundario, terciario


def pontos_da_raridade(raridade: str, config: dict) -> int:
    base = raridade_equivalente(raridade, config)
    return config["pontos_por_raridade"][base]


def duracao_mestre_da_raridade(raridade: str, config: dict) -> int:
    base = raridade_equivalente(raridade, config)
    return config["duracao_mestre"][base]


def duracao_portais_da_raridade(raridade: str, config: dict) -> int:
    base = raridade_equivalente(raridade, config)
    return config["duracao_portais"][base]


def custo_auxiliar_da_raridade(raridade: str, config: dict, mixto: bool = False) -> int:
    base = raridade_equivalente(raridade, config)
    custo = config["custos_auxiliares"][base]
    if mixto:
        custo += config["custo_auxiliar_mixto_extra"]
    return custo


@dataclass(frozen=True)
class Carta:
    uid: int = field(default_factory=_next_uid, compare=False)


@dataclass(frozen=True)
class Heroi(Carta):
    variacao_id: int = 0
    participante_id: int = 0
    raridade: str = "comum"
    categoria_principal: str = ""
    categoria_secundaria: str = ""
    categoria_terciaria: str = ""
    forca_impressa: int = 0
    poder_principal: int = 0
    poder_secundario: int = 0
    poder_terciario: int = 0

    @property
    def tipo(self) -> str:
        """'tipo' do herói = a variação de personagem (identidade de jogo)."""
        return f"variacao_{self.variacao_id}"


@dataclass(frozen=True)
class Mestre(Carta):
    tipo_heroi_dominado: int = 0  # variacao_id do tipo de herói que domina
    categoria: str = ""
    raridade: str = "comum"
    forca_impressa: int = 0


@dataclass(frozen=True)
class Guardiao(Carta):
    tipo: str = ""  # um dos tipos_guardiao
    categoria: str = ""
    raridade: str = "comum"
    forca_impressa: int = 0


@dataclass(frozen=True)
class Juiz(Carta):
    categoria: str = ""
    raridade: str = "comum"
    forca_impressa: int = 0


@dataclass(frozen=True)
class ItemHeroi(Carta):
    tipo_heroi: int = 0  # variacao_id do tipo de herói ao qual está vinculado
    raridade: str = "comum"  # comum ou rara


@dataclass(frozen=True)
class Local(Carta):
    categoria: str = ""
    raridade: str = "comum"  # comum ou rara


@dataclass(frozen=True)
class Invocacao(Carta):
    categoria: str = ""
