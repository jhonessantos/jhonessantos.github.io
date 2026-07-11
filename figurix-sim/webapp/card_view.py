"""Camada de apresentação: transforma cartas do motor (src/cards.py) em
"view models" (dicts JSON-serializáveis) que o frontend usa para desenhar
a carta, e serializa/desserializa cartas para persistência em SQLite.

Convenções visuais (definidas junto com o usuário):
  - Toda carta de personagem (Heroi/Mestre/Guardiao/Juiz) tem um emoji de
    categoria + uma letra (H/M/G/J) + o nome embaixo + força visível.
  - Invocação: emoji da categoria grande, fundo na cor da categoria.
  - Item de herói: "I" + emoji da categoria do herói vinculado + nome do herói embaixo.
  - Local: emoji da categoria + "L".
  - Raridade tem uma cor própria; especiais usam a cor da raridade
    equivalente (são a mesma coisa mecanicamente — seção 1 das regras).
"""
from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cardpool import categorias_da_variacao  # noqa: E402
from cards import (  # noqa: E402
    Guardiao,
    Heroi,
    Invocacao,
    ItemHeroi,
    Juiz,
    Local,
    Mestre,
    eh_especial,
    raridade_equivalente,
)
from naming import nome_guardiao, nome_item, nome_mestre, nome_participante  # noqa: E402

CATEGORIA_EMOJI = {
    "Conexao": "🤝",
    "Coracao": "❤️",
    "Acao": "⚡",
    "Mente": "🧠",
    "Criacao": "🎨",
}

CATEGORIA_COR = {
    "Conexao": "#3b82f6",
    "Coracao": "#ef4444",
    "Acao": "#f59e0b",
    "Mente": "#8b5cf6",
    "Criacao": "#10b981",
}

RARIDADE_COR = {
    "comum": "#9ca3af",
    "rara": "#3b82f6",
    "super_rara": "#a855f7",
    "ultra_rara": "#f59e0b",
}

# símbolo de forma (não só cor) pra cada raridade — círculo/losango/estrela/
# fogo, pra distinguir raridade mesmo sem depender de cor (ex.: daltonismo).
# Especiais usam o símbolo da raridade equivalente (são a mesma coisa
# mecanicamente — seção 1 das regras).
RARIDADE_EMOJI = {
    "comum": "⚪",
    "rara": "🔷",
    "super_rara": "⭐",
    "ultra_rara": "🔥",
}

_TIPO_PARA_LETRA = {
    Heroi: "H",
    Mestre: "M",
    Guardiao: "G",
    Juiz: "J",
    ItemHeroi: "I",
    Local: "L",
}

_TIPO_PARA_NOME_CLASSE = {
    Heroi: "heroi",
    Mestre: "mestre",
    Guardiao: "guardiao",
    Juiz: "juiz",
    ItemHeroi: "item",
    Local: "local",
    Invocacao: "invocacao",
}


def _cor_raridade(raridade: str, config: dict) -> str:
    base = raridade_equivalente(raridade, config)
    return RARIDADE_COR[base]


def _emoji_raridade(raridade: str, config: dict) -> str:
    base = raridade_equivalente(raridade, config)
    return RARIDADE_EMOJI[base]


def construir_view_carta(carta, config: dict) -> dict:
    """Constrói o view model de UMA carta para o frontend renderizar."""
    view = {
        "uid": carta.uid,
        "tipo_carta": _TIPO_PARA_NOME_CLASSE[type(carta)],
        "letra": _TIPO_PARA_LETRA.get(type(carta)),
        "emoji": None,
        "cor_categoria": None,
        "nome": None,
        "raridade": None,
        "cor_raridade": None,
        "raridade_emoji": None,
        "especial": False,
        "forca": None,
        "extra": {},
    }

    if isinstance(carta, Heroi):
        view.update(
            emoji=CATEGORIA_EMOJI[carta.categoria_principal],
            cor_categoria=CATEGORIA_COR[carta.categoria_principal],
            nome=nome_participante(carta.participante_id),
            raridade=carta.raridade,
            cor_raridade=_cor_raridade(carta.raridade, config),
            raridade_emoji=_emoji_raridade(carta.raridade, config),
            especial=eh_especial(carta.raridade, config),
            forca=carta.forca_impressa,
            extra={
                "participante_id": carta.participante_id,
                "variacao_id": carta.variacao_id,
                "categoria_secundaria": carta.categoria_secundaria,
                "categoria_terciaria": carta.categoria_terciaria,
                "poder_principal": carta.poder_principal,
                "poder_secundario": carta.poder_secundario,
                "poder_terciario": carta.poder_terciario,
            },
        )
    elif isinstance(carta, Mestre):
        view.update(
            emoji=CATEGORIA_EMOJI[carta.categoria],
            cor_categoria=CATEGORIA_COR[carta.categoria],
            nome=nome_mestre(carta.tipo_heroi_dominado),
            raridade=carta.raridade,
            cor_raridade=_cor_raridade(carta.raridade, config),
            raridade_emoji=_emoji_raridade(carta.raridade, config),
            especial=eh_especial(carta.raridade, config),
            forca=carta.forca_impressa,
            extra={"tipo_heroi_dominado": carta.tipo_heroi_dominado, "categoria": carta.categoria},
        )
    elif isinstance(carta, Guardiao):
        view.update(
            emoji=CATEGORIA_EMOJI[carta.categoria],
            cor_categoria=CATEGORIA_COR[carta.categoria],
            nome=nome_guardiao(carta.tipo),
            raridade=carta.raridade,
            cor_raridade=_cor_raridade(carta.raridade, config),
            raridade_emoji=_emoji_raridade(carta.raridade, config),
            especial=eh_especial(carta.raridade, config),
            forca=carta.forca_impressa,
            extra={"tipo_guardiao": carta.tipo, "categoria": carta.categoria},
        )
    elif isinstance(carta, Juiz):
        view.update(
            emoji=CATEGORIA_EMOJI[carta.categoria],
            cor_categoria=CATEGORIA_COR[carta.categoria],
            nome="Juiz",
            raridade=carta.raridade,
            cor_raridade=_cor_raridade(carta.raridade, config),
            raridade_emoji=_emoji_raridade(carta.raridade, config),
            especial=eh_especial(carta.raridade, config),
            forca=carta.forca_impressa,
            extra={"categoria": carta.categoria},
        )
    elif isinstance(carta, ItemHeroi):
        categoria_heroi = categorias_da_variacao(carta.tipo_heroi, config)[0]
        view.update(
            emoji=CATEGORIA_EMOJI[categoria_heroi],
            cor_categoria=CATEGORIA_COR[categoria_heroi],
            nome=nome_item(carta.tipo_heroi),
            raridade=carta.raridade,
            cor_raridade=_cor_raridade(carta.raridade, config),
            raridade_emoji=_emoji_raridade(carta.raridade, config),
            extra={"tipo_heroi": carta.tipo_heroi},
        )
    elif isinstance(carta, Local):
        view.update(
            emoji=CATEGORIA_EMOJI[carta.categoria],
            cor_categoria=CATEGORIA_COR[carta.categoria],
            raridade=carta.raridade,
            cor_raridade=_cor_raridade(carta.raridade, config),
            raridade_emoji=_emoji_raridade(carta.raridade, config),
            extra={"categoria": carta.categoria},
        )
    elif isinstance(carta, Invocacao):
        view.update(
            emoji=CATEGORIA_EMOJI[carta.categoria],
            cor_categoria=CATEGORIA_COR[carta.categoria],
            extra={"categoria": carta.categoria},
        )

    return view


_CLASSE_POR_NOME = {
    "Heroi": Heroi,
    "Mestre": Mestre,
    "Guardiao": Guardiao,
    "Juiz": Juiz,
    "ItemHeroi": ItemHeroi,
    "Local": Local,
    "Invocacao": Invocacao,
}

_CAMPOS_POR_CLASSE = {
    Heroi: (
        "variacao_id", "participante_id", "raridade", "categoria_principal", "categoria_secundaria",
        "categoria_terciaria", "forca_impressa", "poder_principal", "poder_secundario", "poder_terciario",
    ),
    Mestre: ("tipo_heroi_dominado", "categoria", "raridade", "forca_impressa"),
    Guardiao: ("tipo", "categoria", "raridade", "forca_impressa"),
    Juiz: ("categoria", "raridade", "forca_impressa"),
    ItemHeroi: ("tipo_heroi", "raridade"),
    Local: ("categoria", "raridade"),
    Invocacao: ("categoria",),
}


def serializar_carta(carta) -> dict:
    """Carta (objeto do motor) -> dict JSON-serializável, para salvar no banco.

    A chave do envelope é "classe" (não "tipo"!) porque Guardiao já tem um
    campo PRÓPRIO chamado `tipo` (Portais/Escudos/...) — usar "tipo" pro
    nome da classe colidia com esse campo e um sobrescrevia o outro.
    """
    nome_classe = type(carta).__name__
    campos = _CAMPOS_POR_CLASSE[type(carta)]
    dados = {"classe": nome_classe}
    for campo in campos:
        dados[campo] = getattr(carta, campo)
    return dados


def desserializar_carta(dados: dict):
    """dict salvo no banco -> carta (objeto do motor). uid é gerado de novo
    (não é uma regra de jogo, só um identificador de instância)."""
    cls = _CLASSE_POR_NOME[dados["classe"]]
    campos = _CAMPOS_POR_CLASSE[cls]
    kwargs = {campo: dados[campo] for campo in campos}
    return cls(**kwargs)
