"""Análise automática de um lote (webapp/analise_lote.py): explicação em
português de por que um lado venceu mais que o outro, a partir das taxas
de mecânica por papel. Testado com dicts de stats/resumo construídos à
mão (a mesma forma que db.estatisticas_lote/resumo_vitorias_lote produzem)."""
import pytest

from analise_lote import analisar_lote


def _stats(
    media_pontos_a=7.0, media_pontos_b=7.0,
    juiz_a=0.2, juiz_b=0.2,
    espiral_a=0.1, espiral_b=0.1,
    mulligan_a=0.05, mulligan_b=0.05,
    taxa_comeback=0.1,
):
    return {
        "total": 100,
        "pontos": {"media_pontos_a": media_pontos_a, "media_pontos_b": media_pontos_b},
        "taxa_juiz": {"a": juiz_a, "b": juiz_b},
        "taxa_espiral": {"a": espiral_a, "b": espiral_b},
        "taxa_mulligan_desistencia": {"a": mulligan_a, "b": mulligan_b},
        "taxa_comeback": taxa_comeback,
    }


def _resumo(vitorias_a, vitorias_b, indecisas=0):
    return {"vitorias_a": vitorias_a, "vitorias_b": vitorias_b, "indecisas": indecisas, "total": vitorias_a + vitorias_b + indecisas}


def test_lote_vazio_retorna_lista_vazia():
    assert analisar_lote({"total": 0}, {"vitorias_a": 0, "vitorias_b": 0, "indecisas": 0, "total": 0}) == []


def test_equilibrado_nao_declara_dominante():
    paragrafos = analisar_lote(_stats(), _resumo(48, 47, 5))
    assert len(paragrafos) == 1
    assert "equilibrado" in paragrafos[0]
    assert "O lado A teve uma vantagem" not in paragrafos[0]
    assert "O lado B teve uma vantagem" not in paragrafos[0]


@pytest.mark.parametrize("vitorias_a,vitorias_b,esperado_dominante", [(70, 30, "A"), (30, 70, "B")])
def test_vantagem_clara_identifica_o_lado_certo(vitorias_a, vitorias_b, esperado_dominante):
    paragrafos = analisar_lote(_stats(), _resumo(vitorias_a, vitorias_b))
    assert f"lado {esperado_dominante} teve uma vantagem" in paragrafos[0]


def test_vantagem_esmagadora_usa_a_palavra_certa():
    paragrafos = analisar_lote(_stats(), _resumo(90, 10))
    assert "esmagadora" in paragrafos[0]


def test_vantagem_apenas_clara_nao_e_chamada_de_esmagadora():
    paragrafos = analisar_lote(_stats(), _resumo(60, 40))
    assert "clara" in paragrafos[0]
    assert "esmagadora" not in paragrafos[0]


def test_diferenca_de_pontos_e_mencionada_quando_notavel():
    stats = _stats(media_pontos_a=9.0, media_pontos_b=4.0)
    paragrafos = analisar_lote(stats, _resumo(70, 30))
    texto = " ".join(paragrafos)
    assert "pontuação" in texto
    assert "9.0" in texto and "4.0" in texto


def test_juiz_explica_a_vantagem_do_dominante():
    stats = _stats(juiz_a=0.6, juiz_b=0.1)
    paragrafos = analisar_lote(stats, _resumo(70, 30))
    texto = " ".join(paragrafos)
    assert "Juiz" in texto
    assert "lado A invocou o Juiz" in texto


def test_espiral_explica_a_derrota_do_dominado():
    stats = _stats(espiral_a=0.05, espiral_b=0.5)
    paragrafos = analisar_lote(stats, _resumo(70, 30))
    texto = " ".join(paragrafos)
    assert "espiral de busca" in texto
    assert "lado B caiu na espiral" in texto


def test_mulligan_explica_a_derrota_do_dominado():
    stats = _stats(mulligan_a=0.02, mulligan_b=0.4)
    paragrafos = analisar_lote(stats, _resumo(70, 30))
    texto = " ".join(paragrafos)
    assert "desistiu da mão inicial" in texto
    assert "lado B" in texto


def test_sem_mecanica_notavel_usa_fallback():
    paragrafos = analisar_lote(_stats(), _resumo(70, 30))
    texto = " ".join(paragrafos)
    assert "não mede diretamente" in texto


def test_comeback_notavel_e_mencionado():
    stats = _stats(taxa_comeback=0.4)
    paragrafos = analisar_lote(stats, _resumo(70, 30))
    texto = " ".join(paragrafos)
    assert "desvantagem grande" in texto


def test_comeback_baixo_nao_e_mencionado():
    stats = _stats(taxa_comeback=0.05)
    paragrafos = analisar_lote(stats, _resumo(70, 30))
    texto = " ".join(paragrafos)
    assert "desvantagem grande" not in texto
