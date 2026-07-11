"""Relatório detalhado de um lote (db.estatisticas_lote): valores conhecidos
à mão pra conferir cada seção — duração (turnos/rodadas, incl. a média
separada das partidas mais curtas vs. mais longas), pontos, taxas de
mecânica por papel e média de eventos por partida."""


def _partida(indice, turnos, rodadas, pontos_a, pontos_b, teve_comeback, vencedor_papel, primeiro_papel,
             juiz_papeis=frozenset(), espiral_papeis=frozenset(), mulligan_papeis=frozenset(), eventos=None):
    return {
        "indice": indice,
        "seed": 100 + indice,
        "papel_e_p1": "A" if indice % 2 == 0 else "B",
        "vencedor_papel": vencedor_papel,
        "primeiro_papel": primeiro_papel,
        "turnos": turnos,
        "rodadas": rodadas,
        "pontos_a": pontos_a,
        "pontos_b": pontos_b,
        "teve_comeback": teve_comeback,
        "juiz_papeis": juiz_papeis,
        "espiral_papeis": espiral_papeis,
        "mulligan_desistencia_papeis": mulligan_papeis,
        "eventos": eventos or {},
    }


def _lote_com_4_partidas_conhecidas(db_temporario):
    lote_id = db_temporario.criar_lote(
        nome="lote estatisticas", ia_a_chave="aleatoria", ia_b_chave="aleatoria",
        deck_a_id=1, deck_b_id=2, deck_a_nome="A", deck_b_nome="B",
        n_partidas=4, seed_base=1,
    )
    partidas = [
        _partida(0, turnos=10, rodadas=5, pontos_a=7, pontos_b=3, teve_comeback=True,
                  vencedor_papel="A", primeiro_papel="A", juiz_papeis=frozenset({"A"}),
                  eventos={"atacar_principal": 2}),
        _partida(1, turnos=20, rodadas=10, pontos_a=7, pontos_b=3, teve_comeback=False,
                  vencedor_papel="B", primeiro_papel="A",
                  eventos={"atacar_principal": 4, "barragem_cadeia": 1}),
        _partida(2, turnos=30, rodadas=15, pontos_a=7, pontos_b=3, teve_comeback=False,
                  vencedor_papel="A", primeiro_papel="B", juiz_papeis=frozenset({"A", "B"}),
                  eventos={}),
        _partida(3, turnos=40, rodadas=20, pontos_a=7, pontos_b=3, teve_comeback=True,
                  vencedor_papel="B", primeiro_papel="B", juiz_papeis=frozenset({"B"}),
                  eventos={"atacar_principal": 2}),
    ]
    db_temporario.inserir_partidas(lote_id, partidas)
    return lote_id


def test_estatisticas_lote_vazio(db_temporario):
    lote_id = db_temporario.criar_lote(
        nome="vazio", ia_a_chave="aleatoria", ia_b_chave="aleatoria",
        deck_a_id=1, deck_b_id=2, deck_a_nome="A", deck_b_nome="B",
        n_partidas=10, seed_base=1,
    )
    assert db_temporario.estatisticas_lote(lote_id) == {"total": 0}


def test_turnos_media_mediana_min_max_e_metades(db_temporario):
    lote_id = _lote_com_4_partidas_conhecidas(db_temporario)
    stats = db_temporario.estatisticas_lote(lote_id)

    assert stats["total"] == 4
    turnos = stats["turnos"]
    assert turnos["media"] == 25
    assert turnos["mediana"] == 30  # ordenados [10,20,30,40], offset int(4*0.5)=2 -> 30
    assert turnos["min"] == 10
    assert turnos["max"] == 40
    assert turnos["media_metade_mais_curta"] == 20  # media(10,20,30)
    assert turnos["media_metade_mais_longa"] == 40  # media(40)


def test_rodadas_media_mediana_min_max(db_temporario):
    lote_id = _lote_com_4_partidas_conhecidas(db_temporario)
    rodadas = db_temporario.estatisticas_lote(lote_id)["rodadas"]
    assert rodadas["media"] == 12.5
    assert rodadas["min"] == 5
    assert rodadas["max"] == 20


def test_pontos(db_temporario):
    lote_id = _lote_com_4_partidas_conhecidas(db_temporario)
    pontos = db_temporario.estatisticas_lote(lote_id)["pontos"]
    assert pontos["media_pontos_a"] == 7
    assert pontos["media_pontos_b"] == 3
    assert pontos["media_diferenca"] == 4
    assert pontos["maior_margem"] == 4


def test_taxa_comeback(db_temporario):
    lote_id = _lote_com_4_partidas_conhecidas(db_temporario)
    assert db_temporario.estatisticas_lote(lote_id)["taxa_comeback"] == 0.5


def test_vantagem_primeiro_jogador(db_temporario):
    lote_id = _lote_com_4_partidas_conhecidas(db_temporario)
    vantagem = db_temporario.estatisticas_lote(lote_id)["vantagem_primeiro_jogador"]
    assert vantagem["partidas_decididas"] == 4
    # partida 0 (vencedor A, primeiro A) e partida 3 (vencedor B, primeiro B) batem -> 2/4
    assert vantagem["taxa_vitoria_jogando_primeiro"] == 0.5


def test_taxa_juiz_por_papel(db_temporario):
    lote_id = _lote_com_4_partidas_conhecidas(db_temporario)
    taxa_juiz = db_temporario.estatisticas_lote(lote_id)["taxa_juiz"]
    # A aparece nas partidas 0 e 2 -> 2/4; B aparece nas partidas 2 e 3 -> 2/4
    assert taxa_juiz["a"] == 0.5
    assert taxa_juiz["b"] == 0.5


def test_taxa_espiral_e_mulligan_zeradas_quando_nao_ocorrem(db_temporario):
    lote_id = _lote_com_4_partidas_conhecidas(db_temporario)
    stats = db_temporario.estatisticas_lote(lote_id)
    assert stats["taxa_espiral"] == {"a": 0.0, "b": 0.0}
    assert stats["taxa_mulligan_desistencia"] == {"a": 0.0, "b": 0.0}


def test_eventos_media_por_partida(db_temporario):
    lote_id = _lote_com_4_partidas_conhecidas(db_temporario)
    eventos = db_temporario.estatisticas_lote(lote_id)["eventos_media_por_partida"]
    assert eventos["atacar_principal"] == 2.0  # (2+4+0+2)/4
    assert eventos["barragem_cadeia"] == 0.25  # (0+1+0+0)/4


def test_metade_longa_cai_pra_media_geral_quando_todas_partidas_tem_mesma_duracao(db_temporario):
    lote_id = db_temporario.criar_lote(
        nome="duracao uniforme", ia_a_chave="aleatoria", ia_b_chave="aleatoria",
        deck_a_id=1, deck_b_id=2, deck_a_nome="A", deck_b_nome="B",
        n_partidas=3, seed_base=1,
    )
    partidas = [
        _partida(i, turnos=15, rodadas=7, pontos_a=7, pontos_b=3, teve_comeback=False,
                  vencedor_papel="A", primeiro_papel="A")
        for i in range(3)
    ]
    db_temporario.inserir_partidas(lote_id, partidas)
    turnos = db_temporario.estatisticas_lote(lote_id)["turnos"]
    assert turnos["media_metade_mais_curta"] == 15
    assert turnos["media_metade_mais_longa"] == 15


def test_estatisticas_lote_encaixa_no_formato_esperado_por_analisar_lote(db_temporario):
    """Integração: o dict que db.estatisticas_lote produz precisa ter
    exatamente as chaves que analise_lote.analisar_lote espera (é isso que
    o endpoint /api/lotes/{id}/estatisticas monta na prática)."""
    from analise_lote import analisar_lote

    lote_id = _lote_com_4_partidas_conhecidas(db_temporario)
    stats = db_temporario.estatisticas_lote(lote_id)
    resumo = db_temporario.resumo_vitorias_lote(lote_id)

    paragrafos = analisar_lote(stats, resumo)
    assert len(paragrafos) >= 1
    assert all(isinstance(p, str) and p for p in paragrafos)
