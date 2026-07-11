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
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # WAL: o motor de simulação escreve de uma thread em segundo plano
    # enquanto a API pode estar lendo ao mesmo tempo (ver lotes/progresso).
    conn.execute("PRAGMA journal_mode = WAL")
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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                criado_em TEXT NOT NULL,
                concluido_em TEXT,
                ia_a_chave TEXT NOT NULL,
                ia_b_chave TEXT NOT NULL,
                deck_a_id INTEGER NOT NULL,
                deck_b_id INTEGER NOT NULL,
                deck_a_nome TEXT NOT NULL,
                deck_b_nome TEXT NOT NULL,
                n_partidas INTEGER NOT NULL,
                seed_base INTEGER NOT NULL,
                grupo_id TEXT,
                status TEXT NOT NULL DEFAULT 'pendente',
                progresso INTEGER NOT NULL DEFAULT 0,
                erro_mensagem TEXT
            )
            """
        )
        _adicionar_coluna_se_faltando(conn, "lotes", "grupo_id", "TEXT")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS partidas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lote_id INTEGER NOT NULL REFERENCES lotes(id) ON DELETE CASCADE,
                indice INTEGER NOT NULL,
                seed INTEGER NOT NULL,
                papel_e_p1 TEXT NOT NULL,
                vencedor_papel TEXT,
                primeiro_papel TEXT NOT NULL,
                turnos INTEGER NOT NULL,
                rodadas INTEGER NOT NULL,
                pontos_a INTEGER NOT NULL,
                pontos_b INTEGER NOT NULL,
                teve_comeback INTEGER NOT NULL,
                juiz_papeis TEXT NOT NULL,
                espiral_papeis TEXT NOT NULL,
                mulligan_desistencia_papeis TEXT NOT NULL,
                eventos_json TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_partidas_lote ON partidas(lote_id)")
        # (lote_id, turnos)/(lote_id, rodadas): o relatório detalhado (seção de
        # estatísticas) busca mediana/quartis via ORDER BY + LIMIT/OFFSET —
        # sem esses índices, isso seria uma ordenação completa da tabela toda
        # vez, inviável em lotes de milhões de partidas (rodando por horas).
        conn.execute("CREATE INDEX IF NOT EXISTS idx_partidas_lote_turnos ON partidas(lote_id, turnos)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_partidas_lote_rodadas ON partidas(lote_id, rodadas)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_lotes_grupo ON lotes(grupo_id)")


def _adicionar_coluna_se_faltando(conn: sqlite3.Connection, tabela: str, coluna: str, definicao_tipo: str) -> None:
    """Migração simples para bancos já existentes de antes desta coluna
    existir — CREATE TABLE IF NOT EXISTS não altera uma tabela já criada."""
    colunas = {linha["name"] for linha in conn.execute(f"PRAGMA table_info({tabela})").fetchall()}
    if coluna not in colunas:
        conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao_tipo}")


def nome_de_deck_em_uso(nome: str, excluir_id: int | None = None) -> bool:
    with _conexao() as conn:
        if excluir_id is None:
            linha = conn.execute("SELECT 1 FROM decks WHERE nome = ?", (nome,)).fetchone()
        else:
            linha = conn.execute(
                "SELECT 1 FROM decks WHERE nome = ? AND id != ?", (nome, excluir_id)
            ).fetchone()
    return linha is not None


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


# ------------------------------------------------------------------
# Lotes de simulação e partidas individuais
# ------------------------------------------------------------------

def criar_lote(
    nome: str,
    ia_a_chave: str,
    ia_b_chave: str,
    deck_a_id: int,
    deck_b_id: int,
    deck_a_nome: str,
    deck_b_nome: str,
    n_partidas: int,
    seed_base: int,
    grupo_id: str | None = None,
) -> int:
    agora = datetime.now(timezone.utc).isoformat()
    with _conexao() as conn:
        cursor = conn.execute(
            """
            INSERT INTO lotes (
                nome, criado_em, ia_a_chave, ia_b_chave, deck_a_id, deck_b_id,
                deck_a_nome, deck_b_nome, n_partidas, seed_base, grupo_id, status, progresso
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pendente', 0)
            """,
            (
                nome, agora, ia_a_chave, ia_b_chave, deck_a_id, deck_b_id,
                deck_a_nome, deck_b_nome, n_partidas, seed_base, grupo_id,
            ),
        )
        return cursor.lastrowid


def atualizar_status_lote(lote_id: int, status: str) -> None:
    with _conexao() as conn:
        conn.execute("UPDATE lotes SET status = ? WHERE id = ?", (status, lote_id))


def atualizar_progresso_lote(lote_id: int, progresso: int) -> None:
    with _conexao() as conn:
        conn.execute("UPDATE lotes SET progresso = ? WHERE id = ?", (progresso, lote_id))


def marcar_lote_concluido(lote_id: int) -> None:
    agora = datetime.now(timezone.utc).isoformat()
    with _conexao() as conn:
        conn.execute(
            "UPDATE lotes SET status = 'concluido', concluido_em = ? WHERE id = ?", (agora, lote_id)
        )


def marcar_lote_erro(lote_id: int, mensagem: str) -> None:
    with _conexao() as conn:
        conn.execute("UPDATE lotes SET status = 'erro', erro_mensagem = ? WHERE id = ?", (mensagem, lote_id))


def inserir_partidas(lote_id: int, partidas: list[dict]) -> None:
    """Inserção em lote (uma transação) — chamado periodicamente pelo
    executor em segundo plano, não uma vez por partida, para não deixar
    a escrita em disco como gargalo em lotes de milhões de partidas."""
    if not partidas:
        return
    with _conexao() as conn:
        conn.executemany(
            """
            INSERT INTO partidas (
                lote_id, indice, seed, papel_e_p1, vencedor_papel, primeiro_papel,
                turnos, rodadas, pontos_a, pontos_b, teve_comeback,
                juiz_papeis, espiral_papeis, mulligan_desistencia_papeis, eventos_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    lote_id,
                    p["indice"],
                    p["seed"],
                    p["papel_e_p1"],
                    p["vencedor_papel"],
                    p["primeiro_papel"],
                    p["turnos"],
                    p["rodadas"],
                    p["pontos_a"],
                    p["pontos_b"],
                    int(p["teve_comeback"]),
                    ",".join(sorted(p["juiz_papeis"])),
                    ",".join(sorted(p["espiral_papeis"])),
                    ",".join(sorted(p["mulligan_desistencia_papeis"])),
                    json.dumps(p["eventos"]),
                )
                for p in partidas
            ],
        )


def listar_lotes() -> list[dict]:
    with _conexao() as conn:
        linhas = conn.execute("SELECT * FROM lotes ORDER BY criado_em DESC").fetchall()
    return [dict(linha) for linha in linhas]


def obter_lote(lote_id: int) -> dict | None:
    with _conexao() as conn:
        linha = conn.execute("SELECT * FROM lotes WHERE id = ?", (lote_id,)).fetchone()
    return dict(linha) if linha else None


def excluir_lote(lote_id: int) -> None:
    with _conexao() as conn:
        conn.execute("DELETE FROM partidas WHERE lote_id = ?", (lote_id,))
        conn.execute("DELETE FROM lotes WHERE id = ?", (lote_id,))


def resumo_vitorias_lote(lote_id: int) -> dict:
    with _conexao() as conn:
        linha = conn.execute(
            """
            SELECT
                SUM(CASE WHEN vencedor_papel = 'A' THEN 1 ELSE 0 END) AS vitorias_a,
                SUM(CASE WHEN vencedor_papel = 'B' THEN 1 ELSE 0 END) AS vitorias_b,
                SUM(CASE WHEN vencedor_papel IS NULL THEN 1 ELSE 0 END) AS indecisas,
                COUNT(*) AS total
            FROM partidas WHERE lote_id = ?
            """,
            (lote_id,),
        ).fetchone()
    return dict(linha)


def _percentil(conn: sqlite3.Connection, lote_id: int, coluna: str, fracao: float, total: int) -> float | None:
    """Percentil via ORDER BY + LIMIT/OFFSET (usa o índice (lote_id, coluna) —
    não precisa carregar/ordenar tudo em Python nem em memória)."""
    if total == 0:
        return None
    offset = min(total - 1, int(total * fracao))
    linha = conn.execute(
        f"SELECT {coluna} AS v FROM partidas WHERE lote_id = ? ORDER BY {coluna} ASC LIMIT 1 OFFSET ?",
        (lote_id, offset),
    ).fetchone()
    return linha["v"]


def estatisticas_lote(lote_id: int) -> dict:
    """Relatório detalhado de UM lote: além de vitórias/derrotas, distribuição
    de duração (turnos/rodadas — incluindo a média separada das partidas mais
    curtas vs. mais longas, cortando na mediana), pontuação, taxas de uso das
    mecânicas (comeback, Juiz, espiral de busca, desistência de mão) por
    papel, vantagem de jogar primeiro e a média de eventos por partida."""
    with _conexao() as conn:
        total = conn.execute("SELECT COUNT(*) AS n FROM partidas WHERE lote_id = ?", (lote_id,)).fetchone()["n"]
        if total == 0:
            return {"total": 0}

        agregados = dict(
            conn.execute(
                """
                SELECT
                    AVG(turnos) AS media_turnos, MIN(turnos) AS min_turnos, MAX(turnos) AS max_turnos,
                    AVG(rodadas) AS media_rodadas, MIN(rodadas) AS min_rodadas, MAX(rodadas) AS max_rodadas,
                    AVG(pontos_a) AS media_pontos_a, AVG(pontos_b) AS media_pontos_b,
                    AVG(ABS(pontos_a - pontos_b)) AS media_diferenca_pontos,
                    MAX(ABS(pontos_a - pontos_b)) AS maior_margem_pontos,
                    SUM(teve_comeback) AS n_comebacks,
                    SUM(CASE WHEN vencedor_papel IS NOT NULL AND vencedor_papel = primeiro_papel THEN 1 ELSE 0 END)
                        AS vitorias_jogando_primeiro,
                    SUM(CASE WHEN vencedor_papel IS NOT NULL THEN 1 ELSE 0 END) AS partidas_decididas,
                    SUM(CASE WHEN juiz_papeis LIKE '%A%' THEN 1 ELSE 0 END) AS juiz_a,
                    SUM(CASE WHEN juiz_papeis LIKE '%B%' THEN 1 ELSE 0 END) AS juiz_b,
                    SUM(CASE WHEN espiral_papeis LIKE '%A%' THEN 1 ELSE 0 END) AS espiral_a,
                    SUM(CASE WHEN espiral_papeis LIKE '%B%' THEN 1 ELSE 0 END) AS espiral_b,
                    SUM(CASE WHEN mulligan_desistencia_papeis LIKE '%A%' THEN 1 ELSE 0 END) AS mulligan_a,
                    SUM(CASE WHEN mulligan_desistencia_papeis LIKE '%B%' THEN 1 ELSE 0 END) AS mulligan_b
                FROM partidas WHERE lote_id = ?
                """,
                (lote_id,),
            ).fetchone()
        )

        mediana_turnos = _percentil(conn, lote_id, "turnos", 0.5, total)
        mediana_rodadas = _percentil(conn, lote_id, "rodadas", 0.5, total)

        def _media_com_filtro(coluna: str, operador: str, valor) -> float | None:
            linha = conn.execute(
                f"SELECT AVG({coluna}) AS m FROM partidas WHERE lote_id = ? AND {coluna} {operador} ?",
                (lote_id, valor),
            ).fetchone()
            return linha["m"]

        media_turnos_curtas = _media_com_filtro("turnos", "<=", mediana_turnos)
        media_turnos_longas = _media_com_filtro("turnos", ">", mediana_turnos)
        # se todas as partidas tiverem a mesma duração, a metade "longa" fica
        # vazia (nada acima da mediana) — cai pro mesmo valor da mediana.
        if media_turnos_longas is None:
            media_turnos_longas = media_turnos_curtas

        eventos_media: dict[str, float] = {}
        for linha in conn.execute(
            """
            SELECT je.key AS chave, SUM(je.value) AS soma
            FROM partidas p, json_each(p.eventos_json) je
            WHERE p.lote_id = ?
            GROUP BY je.key
            """,
            (lote_id,),
        ).fetchall():
            eventos_media[linha["chave"]] = linha["soma"] / total

    partidas_decididas = agregados["partidas_decididas"] or 0

    return {
        "total": total,
        "turnos": {
            "media": agregados["media_turnos"],
            "mediana": mediana_turnos,
            "min": agregados["min_turnos"],
            "max": agregados["max_turnos"],
            "media_metade_mais_curta": media_turnos_curtas,
            "media_metade_mais_longa": media_turnos_longas,
        },
        "rodadas": {
            "media": agregados["media_rodadas"],
            "mediana": mediana_rodadas,
            "min": agregados["min_rodadas"],
            "max": agregados["max_rodadas"],
        },
        "pontos": {
            "media_pontos_a": agregados["media_pontos_a"],
            "media_pontos_b": agregados["media_pontos_b"],
            "media_diferenca": agregados["media_diferenca_pontos"],
            "maior_margem": agregados["maior_margem_pontos"],
        },
        "taxa_comeback": (agregados["n_comebacks"] or 0) / total,
        "vantagem_primeiro_jogador": {
            "partidas_decididas": partidas_decididas,
            "taxa_vitoria_jogando_primeiro": (
                (agregados["vitorias_jogando_primeiro"] or 0) / partidas_decididas if partidas_decididas else None
            ),
        },
        "taxa_juiz": {"a": (agregados["juiz_a"] or 0) / total, "b": (agregados["juiz_b"] or 0) / total},
        "taxa_espiral": {"a": (agregados["espiral_a"] or 0) / total, "b": (agregados["espiral_b"] or 0) / total},
        "taxa_mulligan_desistencia": {
            "a": (agregados["mulligan_a"] or 0) / total, "b": (agregados["mulligan_b"] or 0) / total,
        },
        "eventos_media_por_partida": eventos_media,
    }


def listar_partidas_lote(lote_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
    with _conexao() as conn:
        linhas = conn.execute(
            "SELECT * FROM partidas WHERE lote_id = ? ORDER BY indice ASC LIMIT ? OFFSET ?",
            (lote_id, limit, offset),
        ).fetchall()
    return [dict(linha) for linha in linhas]


def obter_partida(partida_id: int) -> dict | None:
    with _conexao() as conn:
        linha = conn.execute("SELECT * FROM partidas WHERE id = ?", (partida_id,)).fetchone()
    return dict(linha) if linha else None
