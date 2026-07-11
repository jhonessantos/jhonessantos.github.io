"""Figurix Studio — servidor web local (Fase 1: deck builder + cartas).

Rodar com: python3 -m uvicorn app:app --reload --port 8765
(a partir da pasta webapp/; ver README na raiz do projeto para detalhes)
"""
from __future__ import annotations

import random
import sys
import uuid
from pathlib import Path
from typing import Any, Optional

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

import cartas_lote  # noqa: E402
import db  # noqa: E402
from ai.personas_catalogo import listar_ias  # noqa: E402
from analise_lote import analisar_lote  # noqa: E402
from card_view import construir_view_carta, desserializar_carta, serializar_carta  # noqa: E402
from cardpool import CardPool, N_VARIACOES_OFICIAIS, montar_deck  # noqa: E402
from config import carregar_config  # noqa: E402
from deck import contar_por_tipo, validar_deck  # noqa: E402
from lote_runner import iniciar_lote_em_background  # noqa: E402
from lotes_combinacoes import gerar_combinacoes, nome_da_combinacao, seed_da_combinacao  # noqa: E402

app = FastAPI(title="Figurix Studio")
CONFIG = carregar_config()
STATIC_DIR = Path(__file__).resolve().parent / "static"

db.inicializar_banco()


# ------------------------------------------------------------------
# Catálogo — tudo que o frontend precisa para montar os formulários
# ------------------------------------------------------------------

@app.get("/api/config")
def obter_config() -> dict:
    """Config bruta (regras_v1.json) — usada pela página de Regras para
    exibir os números oficiais sem duplicá-los/hardcodar no HTML."""
    return CONFIG


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
    categoria_preferida: Optional[str] = None
    seed: Optional[int] = None


@app.post("/api/decks/gerar")
def gerar_deck(params: ParametrosGeracao) -> dict:
    try:
        cartas = montar_deck(
            CONFIG,
            faixa_forca=params.faixa_forca,
            arquetipo=params.arquetipo,
            perfil_invocacoes=params.perfil_invocacoes,
            categoria_preferida=params.categoria_preferida,
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
        carta = cartas_lote.gerar_uma_carta(pool, params)
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"view": construir_view_carta(carta, CONFIG), "serializada": serializar_carta(carta)}


class RegraCartaLote(BaseModel):
    quantidade: int = 1
    tipo_carta: str
    raridade: Optional[str] = None
    categoria: Optional[str] = None
    variacao_id: Optional[int] = None
    participante_id: Optional[int] = None
    tipo_heroi_dominado: Optional[int] = None
    tipo_guardiao: Optional[str] = None
    tipo_heroi: Optional[int] = None
    forca: Optional[int] = None


class LoteCartasEntrada(BaseModel):
    regras: list[RegraCartaLote]
    cartas_existentes: list[dict[str, Any]] = []
    seed: Optional[int] = None


@app.post("/api/cartas/lote")
def gerar_cartas_lote(entrada: LoteCartasEntrada) -> dict:
    """Preenchimento em lote do deck builder: N regras do tipo "X cartas de
    Y tipo com Z filtro", geradas em sequência a partir de UM pool com seed
    compartilhada (reprodutível como o resto do simulador). A resolução de
    "quantas cartas cada regra deve gerar" (incl. a regra de "preencher o
    restante do deck") é decidida no frontend, que é quem sabe o tamanho
    atual do deck em edição — aqui só executamos as quantidades já resolvidas.

    `cartas_existentes`: cartas já no deck em edição (serializadas) — usadas
    só para inicializar o controle de variações de herói já ocupadas, para
    que o lote gerado não duplique um herói que o usuário já colocou manual
    ou parametricamente antes de abrir esta ferramenta.
    """
    try:
        cartas_geradas = cartas_lote.gerar_lote(CONFIG, entrada.regras, entrada.cartas_existentes, entrada.seed)
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "cartas": [
            {"view": construir_view_carta(c, CONFIG), "serializada": serializar_carta(c)} for c in cartas_geradas
        ]
    }


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
    if db.nome_de_deck_em_uso(entrada.nome):
        raise HTTPException(status_code=409, detail=f"Já existe um deck chamado {entrada.nome!r}")
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
    if db.nome_de_deck_em_uso(entrada.nome, excluir_id=deck_id):
        raise HTTPException(status_code=409, detail=f"Já existe um deck chamado {entrada.nome!r}")
    db.atualizar_deck(deck_id, entrada.nome, entrada.cartas)
    return _deck_completo(deck_id)


@app.delete("/api/decks/{deck_id}")
def excluir_deck(deck_id: int) -> dict:
    if db.obter_deck(deck_id) is None:
        raise HTTPException(status_code=404, detail="Deck não encontrado")
    db.excluir_deck(deck_id)
    return {"ok": True}


# ------------------------------------------------------------------
# Lotes de simulação (Fase 3): escolher IA A, IA B, deck A, deck B e
# quantas partidas rodar dessa combinação — roda em segundo plano.
# ------------------------------------------------------------------

class LoteEntrada(BaseModel):
    nome: Optional[str] = None
    ia_a_chave: str
    ia_b_chave: str
    deck_a_id: int
    deck_b_id: int
    n_partidas: int
    seed_base: Optional[int] = None


@app.post("/api/lotes")
def criar_lote(entrada: LoteEntrada) -> dict:
    deck_a = db.obter_deck(entrada.deck_a_id)
    deck_b = db.obter_deck(entrada.deck_b_id)
    if deck_a is None or deck_b is None:
        raise HTTPException(status_code=404, detail="Deck A ou Deck B não encontrado")
    if entrada.n_partidas < 1:
        raise HTTPException(status_code=400, detail="n_partidas precisa ser >= 1")

    ias_validas = {ia["chave"] for ia in listar_ias()}
    if entrada.ia_a_chave not in ias_validas or entrada.ia_b_chave not in ias_validas:
        raise HTTPException(status_code=400, detail="ia_a_chave ou ia_b_chave desconhecida")

    seed_base = entrada.seed_base if entrada.seed_base is not None else random.randrange(2**31)
    nome = entrada.nome or f"{entrada.ia_a_chave} x {entrada.ia_b_chave} — {deck_a['nome']} x {deck_b['nome']}"

    lote_id = _criar_e_iniciar_lote(
        nome=nome,
        ia_a_chave=entrada.ia_a_chave,
        ia_b_chave=entrada.ia_b_chave,
        deck_a=deck_a,
        deck_b=deck_b,
        deck_a_id=entrada.deck_a_id,
        deck_b_id=entrada.deck_b_id,
        n_partidas=entrada.n_partidas,
        seed_base=seed_base,
    )
    return db.obter_lote(lote_id)


class LoteCombinacoesEntrada(BaseModel):
    nome_grupo: Optional[str] = None
    ia_a_chaves: list[str]
    ia_b_chaves: list[str]
    deck_a_ids: list[int]
    deck_b_ids: list[int]
    n_partidas: int
    seed_base: Optional[int] = None


@app.post("/api/lotes/combinacoes")
def criar_lotes_combinacoes(entrada: LoteCombinacoesEntrada) -> dict:
    """"Rodar tudo de uma vez": M IAs do lado A x N do lado B x P decks A x
    Q decks B vira M*N*P*Q lotes independentes, cada um com `n_partidas`
    partidas — a quantidade pedida vale POR combinação, não no total."""
    if not (entrada.ia_a_chaves and entrada.ia_b_chaves and entrada.deck_a_ids and entrada.deck_b_ids):
        raise HTTPException(status_code=400, detail="Selecione ao menos uma IA e um deck para cada lado")
    if entrada.n_partidas < 1:
        raise HTTPException(status_code=400, detail="n_partidas precisa ser >= 1")

    ias_validas = {ia["chave"] for ia in listar_ias()}
    desconhecidas = sorted({*entrada.ia_a_chaves, *entrada.ia_b_chaves} - ias_validas)
    if desconhecidas:
        raise HTTPException(status_code=400, detail=f"IA(s) desconhecida(s): {desconhecidas}")

    decks = {deck_id: db.obter_deck(deck_id) for deck_id in {*entrada.deck_a_ids, *entrada.deck_b_ids}}
    faltando = sorted(deck_id for deck_id, deck in decks.items() if deck is None)
    if faltando:
        raise HTTPException(status_code=404, detail=f"Deck(s) não encontrado(s): {faltando}")

    grupo_id = uuid.uuid4().hex[:12]
    seed_base_grupo = entrada.seed_base if entrada.seed_base is not None else random.randrange(2**31)

    lote_ids = []
    combinacoes = gerar_combinacoes(entrada.ia_a_chaves, entrada.ia_b_chaves, entrada.deck_a_ids, entrada.deck_b_ids)
    for indice, (ia_a, ia_b, deck_a_id, deck_b_id) in enumerate(combinacoes):
        deck_a, deck_b = decks[deck_a_id], decks[deck_b_id]
        nome = nome_da_combinacao(entrada.nome_grupo, ia_a, ia_b, deck_a["nome"], deck_b["nome"])
        lote_id = _criar_e_iniciar_lote(
            nome=nome,
            ia_a_chave=ia_a,
            ia_b_chave=ia_b,
            deck_a=deck_a,
            deck_b=deck_b,
            deck_a_id=deck_a_id,
            deck_b_id=deck_b_id,
            n_partidas=entrada.n_partidas,
            seed_base=seed_da_combinacao(seed_base_grupo, indice),
            grupo_id=grupo_id,
        )
        lote_ids.append(lote_id)

    return {"grupo_id": grupo_id, "lote_ids": lote_ids, "total_combinacoes": len(lote_ids)}


@app.get("/api/lotes")
def listar_lotes() -> list[dict]:
    return db.listar_lotes()


@app.get("/api/lotes/{lote_id}")
def obter_lote(lote_id: int) -> dict:
    lote = db.obter_lote(lote_id)
    if lote is None:
        raise HTTPException(status_code=404, detail="Lote não encontrado")
    lote["resumo_vitorias"] = db.resumo_vitorias_lote(lote_id)
    return lote


@app.get("/api/lotes/{lote_id}/estatisticas")
def estatisticas_do_lote(lote_id: int) -> dict:
    if db.obter_lote(lote_id) is None:
        raise HTTPException(status_code=404, detail="Lote não encontrado")
    stats = db.estatisticas_lote(lote_id)
    stats["analise"] = analisar_lote(stats, db.resumo_vitorias_lote(lote_id))
    return stats


@app.get("/api/lotes/{lote_id}/partidas")
def listar_partidas_do_lote(lote_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
    if db.obter_lote(lote_id) is None:
        raise HTTPException(status_code=404, detail="Lote não encontrado")
    return db.listar_partidas_lote(lote_id, limit=limit, offset=offset)


@app.delete("/api/lotes/{lote_id}")
def excluir_lote(lote_id: int) -> dict:
    if db.obter_lote(lote_id) is None:
        raise HTTPException(status_code=404, detail="Lote não encontrado")
    db.excluir_lote(lote_id)
    return {"ok": True}


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _criar_e_iniciar_lote(
    nome: str,
    ia_a_chave: str,
    ia_b_chave: str,
    deck_a: dict,
    deck_b: dict,
    deck_a_id: int,
    deck_b_id: int,
    n_partidas: int,
    seed_base: int,
    grupo_id: str | None = None,
) -> int:
    """Compartilhado por /api/lotes (1 combinação) e /api/lotes/combinacoes
    (produto cartesiano de várias) — cria a linha do lote e enfileira a
    execução, sem duplicar essa lógica nos dois endpoints."""
    lote_id = db.criar_lote(
        nome=nome,
        ia_a_chave=ia_a_chave,
        ia_b_chave=ia_b_chave,
        deck_a_id=deck_a_id,
        deck_b_id=deck_b_id,
        deck_a_nome=deck_a["nome"],
        deck_b_nome=deck_b["nome"],
        n_partidas=n_partidas,
        seed_base=seed_base,
        grupo_id=grupo_id,
    )
    iniciar_lote_em_background(
        lote_id=lote_id,
        config=CONFIG,
        deck_a_cartas=deck_a["cartas"],
        deck_b_cartas=deck_b["cartas"],
        ia_a_chave=ia_a_chave,
        ia_b_chave=ia_b_chave,
        n_partidas=n_partidas,
        seed_base=seed_base,
    )
    return lote_id


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


@app.get("/simulacoes")
def pagina_simulacoes():
    return FileResponse(str(STATIC_DIR / "simulacoes.html"))


@app.get("/regras")
def pagina_regras():
    return FileResponse(str(STATIC_DIR / "regras.html"))
