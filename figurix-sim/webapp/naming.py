"""Nomes de exibição para entidades sintéticas (participantes, guardiões...).

O motor (src/cards.py) só guarda IDs numéricos (variacao_id, participante_id,
tipo) — não há "nomes" de verdade, já que as cartas são geradas
sinteticamente (spec do simulador, seção 3). Este módulo só existe para a
CAMADA VISUAL: dar um nome estável e legível a cada participante/guardião,
sem inventar nenhuma regra de jogo nova.
"""
from __future__ import annotations

_NOMES_PARTICIPANTES = [
    "Joaquim", "Maria Luiza", "Pedro Henrique", "Alice", "Miguel", "Sophia", "Arthur", "Manuela",
    "Heitor", "Laura", "Davi", "Isabella", "Bernardo", "Valentina", "Théo", "Helena",
    "Gabriel", "Lívia", "Samuel", "Cecília", "Lorenzo", "Maitê", "Anthony", "Beatriz",
    "Benjamin", "Luiza", "Isaac", "Antonella", "Ravi", "Elisa", "Enzo", "Julia",
    "Matheus", "Marina", "Rafael", "Clara", "Nicolas", "Alícia", "Vicente", "Melissa",
    "Guilherme", "Yasmin", "Daniel", "Emanuelly", "Lucas", "Ana Clara", "Pietro", "Esther",
    "Bryan", "Lorena", "Emanuel", "Rafaela", "Otávio", "Catarina", "João Miguel", "Mirella",
    "Caio", "Amanda", "Vitor", "Sarah", "Henrique", "Murilo", "Isadora", "Gustavo",
    "Bianca", "Erick", "Agatha", "Thiago", "Rebeca", "Fernando", "Milena", "Leonardo",
    "Aurora", "Bruno", "Vitória", "Felipe", "Diego", "Luna", "Igor", "Nicole",
    "Renato", "Raquel", "Marcelo", "Débora", "Vinícius", "Camila", "André", "Letícia",
    "Rodrigo", "Fernanda", "Eduardo", "Larissa", "Alana", "João Pedro", "Stella", "José",
    "Eloá", "Breno", "Maria Eduarda", "Kevin", "Sofia", "Wesley", "Noah", "Maria Cecília",
    "Enzo Gabriel", "Liz",
]

_NOME_GUARDIAO = {
    "Portais": "Guardião dos Portais",
    "Restauracao": "Guardião da Restauração",
    "Escudos": "Guardião dos Escudos",
    "Oprimidos": "Guardião dos Oprimidos",
    "Descanso": "Guardião do Descanso",
}


def nome_participante(participante_id: int) -> str:
    return _NOMES_PARTICIPANTES[(participante_id - 1) % len(_NOMES_PARTICIPANTES)]


def nome_guardiao(tipo: str) -> str:
    return _NOME_GUARDIAO.get(tipo, tipo)


def nome_mestre(tipo_heroi_dominado: int) -> str:
    return f"Mestre de {nome_participante(tipo_heroi_dominado)}"


def nome_item(tipo_heroi: int) -> str:
    return f"Item de {nome_participante(tipo_heroi)}"
