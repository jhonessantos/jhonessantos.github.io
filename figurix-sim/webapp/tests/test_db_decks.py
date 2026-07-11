"""CRUD de decks em db.py, incluindo a checagem de nome duplicado usada
pelo app.py antes de criar/renomear um deck (dois decks com o mesmo nome
deixariam a lista de "Meus decks" ambígua para escolher)."""


def test_salvar_e_obter_deck(db_temporario):
    deck_id = db_temporario.salvar_deck("Deck A", [{"classe": "Local"}], {"arquetipo": "agro"})
    deck = db_temporario.obter_deck(deck_id)
    assert deck["nome"] == "Deck A"
    assert deck["cartas"] == [{"classe": "Local"}]
    assert deck["parametros"] == {"arquetipo": "agro"}


def test_obter_deck_inexistente_retorna_none(db_temporario):
    assert db_temporario.obter_deck(999) is None


def test_listar_decks(db_temporario):
    db_temporario.salvar_deck("Deck A", [{"classe": "Local"}])
    db_temporario.salvar_deck("Deck B", [{"classe": "Local"}, {"classe": "Local"}])
    nomes = {d["nome"]: d["n_cartas"] for d in db_temporario.listar_decks()}
    assert nomes == {"Deck A": 1, "Deck B": 2}


def test_atualizar_deck(db_temporario):
    deck_id = db_temporario.salvar_deck("Deck A", [{"classe": "Local"}])
    db_temporario.atualizar_deck(deck_id, "Deck A renomeado", [{"classe": "Local"}, {"classe": "Local"}])
    deck = db_temporario.obter_deck(deck_id)
    assert deck["nome"] == "Deck A renomeado"
    assert len(deck["cartas"]) == 2


def test_excluir_deck(db_temporario):
    deck_id = db_temporario.salvar_deck("Deck A", [{"classe": "Local"}])
    db_temporario.excluir_deck(deck_id)
    assert db_temporario.obter_deck(deck_id) is None
    assert db_temporario.listar_decks() == []


def test_nome_de_deck_em_uso(db_temporario):
    db_temporario.salvar_deck("Deck A", [{"classe": "Local"}])
    assert db_temporario.nome_de_deck_em_uso("Deck A") is True
    assert db_temporario.nome_de_deck_em_uso("Deck B") is False


def test_nome_de_deck_em_uso_ignora_o_proprio_deck_ao_excluir_id(db_temporario):
    """Salvar um deck já existente com o MESMO nome (ex.: só editando as
    cartas) não pode ser barrado como "duplicado" — só nomes usados por
    OUTRO deck contam."""
    deck_id = db_temporario.salvar_deck("Deck A", [{"classe": "Local"}])
    assert db_temporario.nome_de_deck_em_uso("Deck A", excluir_id=deck_id) is False

    outro_id = db_temporario.salvar_deck("Deck B", [{"classe": "Local"}])
    assert db_temporario.nome_de_deck_em_uso("Deck A", excluir_id=outro_id) is True
