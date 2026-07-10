"""Persistência SQLite do webapp (decks por enquanto; partidas/lotes vêm
nas próximas fases). Um único arquivo de banco em webapp/data/figurix.db —
sem servidor externo, só abrir o app já funciona.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "figurix.db"


def _conectar() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def _conexao():
    conn = _conectar()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def inicializar_banco() -> None:
    with _conexao() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS decks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL,
                parametros_json TEXT,
                cartas_json TEXT NOT NULL
            )
            """
        )


def salvar_deck(nome: str, cartas: list[dict], parametros: dict | None = None) -> int:
    agora = datetime.now(timezone.utc).isoformat()
    with _conexao() as conn:
        cursor = conn.execute(
            "INSERT INTO decks (nome, criado_em, atualizado_em, parametros_json, cartas_json) VALUES (?, ?, ?, ?, ?)",
            (nome, agora, agora, json.dumps(parametros) if parametros else None, json.dumps(cartas)),
        )
        return cursor.lastrowid


def atualizar_deck(deck_id: int, nome: str, cartas: list[dict]) -> None:
    agora = datetime.now(timezone.utc).isoformat()
    with _conexao() as conn:
        conn.execute(
            "UPDATE decks SET nome = ?, cartas_json = ?, atualizado_em = ? WHERE id = ?",
            (nome, json.dumps(cartas), agora, deck_id),
        )


def excluir_deck(deck_id: int) -> None:
    with _conexao() as conn:
        conn.execute("DELETE FROM decks WHERE id = ?", (deck_id,))


def listar_decks() -> list[dict]:
    with _conexao() as conn:
        linhas = conn.execute(
            "SELECT id, nome, criado_em, atualizado_em, parametros_json, cartas_json FROM decks ORDER BY atualizado_em DESC"
        ).fetchall()
    resultado = []
    for linha in linhas:
        cartas = json.loads(linha["cartas_json"])
        resultado.append(
            {
                "id": linha["id"],
                "nome": linha["nome"],
                "criado_em": linha["criado_em"],
                "atualizado_em": linha["atualizado_em"],
                "parametros": json.loads(linha["parametros_json"]) if linha["parametros_json"] else None,
                "n_cartas": len(cartas),
            }
        )
    return resultado


def obter_deck(deck_id: int) -> dict | None:
    with _conexao() as conn:
        linha = conn.execute(
            "SELECT id, nome, criado_em, atualizado_em, parametros_json, cartas_json FROM decks WHERE id = ?",
            (deck_id,),
        ).fetchone()
    if linha is None:
        return None
    return {
        "id": linha["id"],
        "nome": linha["nome"],
        "criado_em": linha["criado_em"],
        "atualizado_em": linha["atualizado_em"],
        "parametros": json.loads(linha["parametros_json"]) if linha["parametros_json"] else None,
        "cartas": json.loads(linha["cartas_json"]),
    }
