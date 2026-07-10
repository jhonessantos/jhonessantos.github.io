"""Figurix Studio — servidor web local (Fase 1: deck builder + cartas).

Rodar com: python3 -m uvicorn app:app --reload --port 8765
(a partir da pasta webapp/; ver README na raiz do projeto para detalhes)
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

import db  # noqa: E402
from ai.personas_catalogo import listar_ias  # noqa: E402
from card_view import construir_view_carta, desserializar_carta, serializar_carta  # noqa: E402
from cardpool import CardPool, N_VARIACOES_OFICIAIS, montar_deck  # noqa: E402
from config import carregar_config  # noqa: E402
from deck import contar_por_tipo, validar_deck  # noqa: E402

app = FastAPI(title="Figurix Studio")
CONFIG = carregar_config()
STATIC_DIR = Path(__file__).resolve().parent / "static"

db.inicializar_banco()


# ------------------------------------------------------------------
# Catálogo — tudo que o frontend precisa para montar os formulários
# ------------------------------------------------------------------

@app.get("/api/catalogo")
def catalogo() -> dict:
    return {
        "categorias": CONFIG["categorias"],
        "roda_vantagens": CONFIG["roda_vantagens"],
        "raridades": CONFIG["raridades"],
        "especiais_por_raridade": CONFIG["especiais_por_raridade"],
        "tipos_guardiao": CONFIG["tipos_guardiao"],
        "tamanho_deck": CONFIG["tamanho_deck"],
        "pontos_vitoria": CONFIG["pontos_vitoria"],
        "n_variacoes_oficiais": N_VARIACOES_OFICIAIS,
        "arquetipos": ["balanceado", "agro", "controle", "combo", "hiperinvocacao"],
        "perfis_invocacao": ["escasso", "moderado", "abundante"],
        "faixas_forca": ["fraco", "medio", "forte"],
    }


@app.get("/api/ias")
def ias() -> list[dict]:
    return listar_ias()


# ------------------------------------------------------------------
# Geração paramétrica e cartas avulsas
# ------------------------------------------------------------------

class ParametrosGeracao(BaseModel):
    faixa_forca: str = "medio"
    arquetipo: str = "balanceado"
    perfil_invocacoes: str = "moderado"
    seed: Optional[int] = None


@app.post("/api/decks/gerar")
def gerar_deck(params: ParametrosGeracao) -> dict:
    try:
        cartas = montar_deck(
            CONFIG,
            faixa_forca=params.faixa_forca,
            arquetipo=params.arquetipo,
            perfil_invocacoes=params.perfil_invocacoes,
            seed=params.seed,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _resposta_cartas(cartas, params.model_dump())


class ParametrosCartaAvulsa(BaseModel):
    tipo_carta: str  # "heroi" | "mestre" | "guardiao" | "juiz" | "item" | "local" | "invocacao"
    raridade: Optional[str] = None
    categoria: Optional[str] = None
    variacao_id: Optional[int] = None
    participante_id: Optional[int] = None
    tipo_heroi_dominado: Optional[int] = None
    tipo_guardiao: Optional[str] = None
    tipo_heroi: Optional[int] = None
    forca: Optional[int] = None
    seed: Optional[int] = None


@app.post("/api/cartas/nova")
def nova_carta(params: ParametrosCartaAvulsa) -> dict:
    pool = CardPool(CONFIG, seed=params.seed)
    try:
        if params.tipo_carta == "heroi":
            carta = pool.novo_heroi(
                params.raridade or "comum",
                variacao_id=params.variacao_id,
                participante_id=params.participante_id,
                forca=params.forca,
            )
        elif params.tipo_carta == "mestre":
            carta = pool.novo_mestre(
                params.raridade or "comum",
                tipo_heroi_dominado=params.tipo_heroi_dominado,
                categoria=params.categoria,
                forca=params.forca,
            )
        elif params.tipo_carta == "guardiao":
            carta = pool.novo_guardiao(
                tipo=params.tipo_guardiao, categoria=params.categoria, raridade=params.raridade, forca=params.forca
            )
        elif params.tipo_carta == "juiz":
            carta = pool.novo_juiz(categoria=params.categoria, raridade=params.raridade, forca=params.forca)
        elif params.tipo_carta == "item":
            carta = pool.novo_item(tipo_heroi=params.tipo_heroi, raridade=params.raridade)
        elif params.tipo_carta == "local":
            carta = pool.novo_local(categoria=params.categoria, raridade=params.raridade)
        elif params.tipo_carta == "invocacao":
            carta = pool.nova_invocacao(categoria=params.categoria)
        else:
            raise HTTPException(status_code=400, detail=f"tipo_carta desconhecido: {params.tipo_carta!r}")
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"view": construir_view_carta(carta, CONFIG), "serializada": serializar_carta(carta)}


# ------------------------------------------------------------------
# Decks salvos (CRUD)
# ------------------------------------------------------------------

class DeckEntrada(BaseModel):
    nome: str
    cartas: list[dict[str, Any]]
    parametros: Optional[dict[str, Any]] = None


class CartasParaValidar(BaseModel):
    cartas: list[dict[str, Any]]


@app.post("/api/decks/validar")
def validar_cartas(entrada: CartasParaValidar) -> dict:
    cartas = [desserializar_carta(d) for d in entrada.cartas]
    return {"violacoes": validar_deck(cartas, CONFIG), "contagens": contar_por_tipo(cartas)}


@app.get("/api/decks")
def listar_decks() -> list[dict]:
    return db.listar_decks()


@app.post("/api/decks")
def criar_deck(entrada: DeckEntrada) -> dict:
    deck_id = db.salvar_deck(entrada.nome, entrada.cartas, entrada.parametros)
    return _deck_completo(deck_id)


@app.get("/api/decks/{deck_id}")
def obter_deck(deck_id: int) -> dict:
    resultado = _deck_completo(deck_id)
    if resultado is None:
        raise HTTPException(status_code=404, detail="Deck não encontrado")
    return resultado


@app.put("/api/decks/{deck_id}")
def atualizar_deck(deck_id: int, entrada: DeckEntrada) -> dict:
    if db.obter_deck(deck_id) is None:
        raise HTTPException(status_code=404, detail="Deck não encontrado")
    db.atualizar_deck(deck_id, entrada.nome, entrada.cartas)
    return _deck_completo(deck_id)


@app.delete("/api/decks/{deck_id}")
def excluir_deck(deck_id: int) -> dict:
    if db.obter_deck(deck_id) is None:
        raise HTTPException(status_code=404, detail="Deck não encontrado")
    db.excluir_deck(deck_id)
    return {"ok": True}


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _resposta_cartas(cartas: list, parametros: dict | None) -> dict:
    violacoes = validar_deck(cartas, CONFIG)
    return {
        "parametros": parametros,
        "violacoes": violacoes,
        "contagens": contar_por_tipo(cartas),
        "cartas": [
            {"view": construir_view_carta(c, CONFIG), "serializada": serializar_carta(c)} for c in cartas
        ],
    }


def _deck_completo(deck_id: int) -> dict | None:
    registro = db.obter_deck(deck_id)
    if registro is None:
        return None
    cartas = [desserializar_carta(d) for d in registro["cartas"]]
    violacoes = validar_deck(cartas, CONFIG)
    return {
        "id": registro["id"],
        "nome": registro["nome"],
        "criado_em": registro["criado_em"],
        "atualizado_em": registro["atualizado_em"],
        "parametros": registro["parametros"],
        "violacoes": violacoes,
        "contagens": contar_por_tipo(cartas),
        "cartas": [
            {"view": construir_view_carta(c, CONFIG), "serializada": s}
            for c, s in zip(cartas, registro["cartas"])
        ],
    }


# ------------------------------------------------------------------
# Frontend estático
# ------------------------------------------------------------------

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "deck_builder.html"))


@app.get("/ias")
def pagina_ias():
    return FileResponse(str(STATIC_DIR / "ias.html"))
