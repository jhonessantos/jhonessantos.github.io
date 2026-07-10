"""M6: variantes de config carregam corretamente e não quebram uma partida."""
import pytest

from ai.heuristic_ai import HeuristicAI
from cardpool import montar_deck_medio
from config import carregar_variante
from match import jogar_partida


@pytest.mark.parametrize("nome_variante", ["pontos_ur4", "cura_juiz50", "compra_dupla_off"])
def test_variante_carrega_e_roda_partida_sem_crash(nome_variante):
    config = carregar_variante(nome_variante)
    deck1 = montar_deck_medio(config, seed=1)
    deck2 = montar_deck_medio(config, seed=2)
    resultado = jogar_partida(config, deck1, deck2, HeuristicAI(seed=1), HeuristicAI(seed=2), seed=1)
    assert resultado.turnos > 0


def test_pontos_ur4_nao_afeta_outras_raridades(config):
    variante = carregar_variante("pontos_ur4")
    assert variante["pontos_por_raridade"]["comum"] == config["pontos_por_raridade"]["comum"]
    assert variante["pontos_por_raridade"]["rara"] == config["pontos_por_raridade"]["rara"]
    assert variante["pontos_por_raridade"]["super_rara"] == config["pontos_por_raridade"]["super_rara"]
    assert variante["pontos_por_raridade"]["ultra_rara"] == 4


def test_cura_juiz50_nao_afeta_outros_parametros(config):
    variante = carregar_variante("cura_juiz50")
    assert variante["cura_juiz"] == 50
    assert variante["cura_descanso"] == config["cura_descanso"]


def test_compra_dupla_off_nao_afeta_limiar(config):
    variante = carregar_variante("compra_dupla_off")
    assert variante["compra_dupla_mao_baixa"] is False
    assert variante["limiar_mao_baixa"] == config["limiar_mao_baixa"]
