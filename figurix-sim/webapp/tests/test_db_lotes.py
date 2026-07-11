"""CRUD de lotes/partidas em db.py (Fase 3): criação, progresso,
conclusão/erro, inserção em lote de partidas e agregação de vitórias."""
import sqlite3
import time


def _resumo_fake(indice: int, seed: int, vencedor_papel: str | None) -> dict:
    return {
        "indice": indice,
        "seed": seed,
        "papel_e_p1": "A" if indice % 2 == 0 else "B",
        "vencedor_papel": vencedor_papel,
        "primeiro_papel": "A",
        "turnos": 10,
        "rodadas": 5,
        "pontos_a": 7,
        "pontos_b": 3,
        "teve_comeback": indice == 0,
        "juiz_papeis": frozenset({"A"}) if indice == 0 else frozenset(),
        "espiral_papeis": frozenset(),
        "mulligan_desistencia_papeis": frozenset(),
        "eventos": {"atacar_arriscado": 3},
    }


def test_criar_e_obter_lote(db_temporario):
    lote_id = db_temporario.criar_lote(
        nome="teste x teste",
        ia_a_chave="aleatoria",
        ia_b_chave="certinho_v2",
        deck_a_id=1,
        deck_b_id=2,
        deck_a_nome="Deck A",
        deck_b_nome="Deck B",
        n_partidas=50,
        seed_base=123,
    )
    lote = db_temporario.obter_lote(lote_id)
    assert lote is not None
    assert lote["status"] == "pendente"
    assert lote["progresso"] == 0
    assert lote["n_partidas"] == 50
    assert lote["seed_base"] == 123


def test_obter_lote_inexistente_retorna_none(db_temporario):
    assert db_temporario.obter_lote(999) is None


def test_atualizar_status_e_progresso(db_temporario):
    lote_id = db_temporario.criar_lote(
        nome="lote", ia_a_chave="aleatoria", ia_b_chave="aleatoria",
        deck_a_id=1, deck_b_id=2, deck_a_nome="A", deck_b_nome="B",
        n_partidas=10, seed_base=1,
    )
    db_temporario.atualizar_status_lote(lote_id, "rodando")
    db_temporario.atualizar_progresso_lote(lote_id, 4)

    lote = db_temporario.obter_lote(lote_id)
    assert lote["status"] == "rodando"
    assert lote["progresso"] == 4


def test_marcar_concluido_e_erro(db_temporario):
    id_ok = db_temporario.criar_lote(
        nome="ok", ia_a_chave="aleatoria", ia_b_chave="aleatoria",
        deck_a_id=1, deck_b_id=2, deck_a_nome="A", deck_b_nome="B",
        n_partidas=1, seed_base=1,
    )
    id_erro = db_temporario.criar_lote(
        nome="erro", ia_a_chave="aleatoria", ia_b_chave="aleatoria",
        deck_a_id=1, deck_b_id=2, deck_a_nome="A", deck_b_nome="B",
        n_partidas=1, seed_base=1,
    )

    db_temporario.marcar_lote_concluido(id_ok)
    db_temporario.marcar_lote_erro(id_erro, "traceback qualquer")

    lote_ok = db_temporario.obter_lote(id_ok)
    lote_erro = db_temporario.obter_lote(id_erro)
    assert lote_ok["status"] == "concluido"
    assert lote_ok["concluido_em"] is not None
    assert lote_erro["status"] == "erro"
    assert lote_erro["erro_mensagem"] == "traceback qualquer"


def test_inserir_partidas_e_listar(db_temporario):
    lote_id = db_temporario.criar_lote(
        nome="lote", ia_a_chave="aleatoria", ia_b_chave="aleatoria",
        deck_a_id=1, deck_b_id=2, deck_a_nome="A", deck_b_nome="B",
        n_partidas=3, seed_base=100,
    )
    partidas = [_resumo_fake(i, 100 + i, "A" if i < 2 else "B") for i in range(3)]
    db_temporario.inserir_partidas(lote_id, partidas)

    listadas = db_temporario.listar_partidas_lote(lote_id)
    assert len(listadas) == 3
    assert [p["indice"] for p in listadas] == [0, 1, 2]
    assert listadas[0]["juiz_papeis"] == "A"
    assert listadas[1]["juiz_papeis"] == ""


def test_inserir_partidas_lista_vazia_nao_falha(db_temporario):
    lote_id = db_temporario.criar_lote(
        nome="lote", ia_a_chave="aleatoria", ia_b_chave="aleatoria",
        deck_a_id=1, deck_b_id=2, deck_a_nome="A", deck_b_nome="B",
        n_partidas=0, seed_base=1,
    )
    db_temporario.inserir_partidas(lote_id, [])
    assert db_temporario.listar_partidas_lote(lote_id) == []


def test_resumo_vitorias_lote(db_temporario):
    lote_id = db_temporario.criar_lote(
        nome="lote", ia_a_chave="aleatoria", ia_b_chave="aleatoria",
        deck_a_id=1, deck_b_id=2, deck_a_nome="A", deck_b_nome="B",
        n_partidas=5, seed_base=1,
    )
    resultados = ["A", "A", "B", "A", None]
    partidas = [_resumo_fake(i, i, resultados[i]) for i in range(5)]
    db_temporario.inserir_partidas(lote_id, partidas)

    resumo = db_temporario.resumo_vitorias_lote(lote_id)
    assert resumo["vitorias_a"] == 3
    assert resumo["vitorias_b"] == 1
    assert resumo["indecisas"] == 1
    assert resumo["total"] == 5


def test_listar_partidas_lote_paginacao(db_temporario):
    lote_id = db_temporario.criar_lote(
        nome="lote", ia_a_chave="aleatoria", ia_b_chave="aleatoria",
        deck_a_id=1, deck_b_id=2, deck_a_nome="A", deck_b_nome="B",
        n_partidas=10, seed_base=1,
    )
    partidas = [_resumo_fake(i, i, "A") for i in range(10)]
    db_temporario.inserir_partidas(lote_id, partidas)

    pagina1 = db_temporario.listar_partidas_lote(lote_id, limit=4, offset=0)
    pagina2 = db_temporario.listar_partidas_lote(lote_id, limit=4, offset=4)
    assert [p["indice"] for p in pagina1] == [0, 1, 2, 3]
    assert [p["indice"] for p in pagina2] == [4, 5, 6, 7]


def test_excluir_lote_remove_partidas_em_cascata(db_temporario):
    lote_id = db_temporario.criar_lote(
        nome="lote", ia_a_chave="aleatoria", ia_b_chave="aleatoria",
        deck_a_id=1, deck_b_id=2, deck_a_nome="A", deck_b_nome="B",
        n_partidas=2, seed_base=1,
    )
    db_temporario.inserir_partidas(lote_id, [_resumo_fake(i, i, "A") for i in range(2)])

    db_temporario.excluir_lote(lote_id)

    assert db_temporario.obter_lote(lote_id) is None
    assert db_temporario.listar_partidas_lote(lote_id) == []


def test_listar_lotes_ordena_por_criacao_desc(db_temporario):
    id1 = db_temporario.criar_lote(
        nome="primeiro", ia_a_chave="aleatoria", ia_b_chave="aleatoria",
        deck_a_id=1, deck_b_id=2, deck_a_nome="A", deck_b_nome="B",
        n_partidas=1, seed_base=1,
    )
    time.sleep(0.01)
    id2 = db_temporario.criar_lote(
        nome="segundo", ia_a_chave="aleatoria", ia_b_chave="aleatoria",
        deck_a_id=1, deck_b_id=2, deck_a_nome="A", deck_b_nome="B",
        n_partidas=1, seed_base=1,
    )
    lotes = db_temporario.listar_lotes()
    ids = [linha["id"] for linha in lotes]
    assert ids.index(id2) < ids.index(id1)


# ------------------------------------------------------------------
# grupo_id: agrupa os lotes gerados por "rodar todas as combinações"
# (múltiplas IAs/decks de cada lado) — cada combinação vira um lote
# independente, mas todos carregam o mesmo grupo_id pra UI conseguir
# mostrá-los juntos.
# ------------------------------------------------------------------

def test_criar_lote_sem_grupo_id_fica_none(db_temporario):
    lote_id = db_temporario.criar_lote(
        nome="solo", ia_a_chave="aleatoria", ia_b_chave="aleatoria",
        deck_a_id=1, deck_b_id=2, deck_a_nome="A", deck_b_nome="B",
        n_partidas=1, seed_base=1,
    )
    assert db_temporario.obter_lote(lote_id)["grupo_id"] is None


def test_criar_lote_com_grupo_id(db_temporario):
    id1 = db_temporario.criar_lote(
        nome="combo 1", ia_a_chave="aleatoria", ia_b_chave="aleatoria",
        deck_a_id=1, deck_b_id=2, deck_a_nome="A", deck_b_nome="B",
        n_partidas=1, seed_base=1, grupo_id="grupo-xyz",
    )
    id2 = db_temporario.criar_lote(
        nome="combo 2", ia_a_chave="aleatoria", ia_b_chave="aleatoria",
        deck_a_id=1, deck_b_id=3, deck_a_nome="A", deck_b_nome="C",
        n_partidas=1, seed_base=2, grupo_id="grupo-xyz",
    )
    lotes = {l["id"]: l for l in db_temporario.listar_lotes()}
    assert lotes[id1]["grupo_id"] == "grupo-xyz"
    assert lotes[id2]["grupo_id"] == "grupo-xyz"


def test_migracao_adiciona_grupo_id_em_banco_antigo(tmp_path, monkeypatch):
    """Simula um banco criado ANTES da coluna grupo_id existir (schema
    antigo da tabela lotes) — inicializar_banco precisa migrar sem quebrar
    os dados já salvos."""
    import db

    caminho = tmp_path / "banco_antigo.db"
    conn = sqlite3.connect(caminho)
    conn.execute(
        """
        CREATE TABLE lotes (
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
            status TEXT NOT NULL DEFAULT 'pendente',
            progresso INTEGER NOT NULL DEFAULT 0,
            erro_mensagem TEXT
        )
        """
    )
    conn.execute(
        """
        INSERT INTO lotes (nome, criado_em, ia_a_chave, ia_b_chave, deck_a_id, deck_b_id,
                            deck_a_nome, deck_b_nome, n_partidas, seed_base)
        VALUES ('velho', '2020-01-01', 'aleatoria', 'aleatoria', 1, 2, 'A', 'B', 5, 1)
        """
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(db, "DB_PATH", caminho)
    db.inicializar_banco()  # não pode lançar (coluna já existe em CREATE TABLE IF NOT EXISTS)

    lotes = db.listar_lotes()
    assert len(lotes) == 1
    assert lotes[0]["nome"] == "velho"
    assert lotes[0]["grupo_id"] is None

    novo_id = db.criar_lote(
        nome="novo", ia_a_chave="aleatoria", ia_b_chave="aleatoria",
        deck_a_id=1, deck_b_id=2, deck_a_nome="A", deck_b_nome="B",
        n_partidas=1, seed_base=1, grupo_id="grupo-pos-migracao",
    )
    assert db.obter_lote(novo_id)["grupo_id"] == "grupo-pos-migracao"
