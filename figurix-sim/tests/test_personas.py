"""Fase 2 do webapp: catálogo de personas de IA — cobertura + comportamento distinto."""
import pytest

import engine as eng
from ai.persona_ai import PersonaAI
from ai.personas_catalogo import MCTS_VARIANTES, PERSONAS, criar_ia, listar_ias
from cardpool import CardPool, montar_deck_medio
from match import jogar_partida

NAO_MCTS = ["aleatoria", "certinho_v2"] + list(PERSONAS.keys())


def test_catalogo_tem_pelo_menos_15_personas():
    assert len(PERSONAS) >= 15


def test_listar_ias_sem_chaves_duplicadas():
    ias = listar_ias()
    chaves = [ia["chave"] for ia in ias]
    assert len(chaves) == len(set(chaves))
    assert len(chaves) >= 18  # 15+ personas + aleatoria + certinho_v2 + variantes MCTS


def test_criar_ia_funciona_para_todo_o_catalogo():
    for ia_info in listar_ias():
        instancia = criar_ia(ia_info["chave"], seed=1)
        assert hasattr(instancia, "escolher_acao")


def test_criar_ia_chave_desconhecida_da_erro():
    with pytest.raises(ValueError):
        criar_ia("nao-existe", seed=1)


@pytest.mark.parametrize("chave", NAO_MCTS)
def test_persona_joga_partidas_sem_crash(config, chave):
    for seed in range(3):
        deck1 = montar_deck_medio(config, seed=seed + 1)
        deck2 = montar_deck_medio(config, seed=seed + 1000)
        ai1 = criar_ia(chave, seed=seed)
        ai2 = criar_ia("certinho", seed=seed + 1)
        resultado = jogar_partida(config, deck1, deck2, ai1, ai2, seed=seed)
        assert resultado.turnos > 0


@pytest.mark.parametrize("chave", list(MCTS_VARIANTES.keys()))
def test_variante_mcts_decide_sem_crash(config, chave):
    """MCTS é caro (mais ainda a variante 'profunda') — testamos só UMA decisão
    real, não uma partida inteira, pra não deixar a suíte lenta demais."""
    from match import configurar_partida

    deck1 = montar_deck_medio(config, seed=1)
    deck2 = montar_deck_medio(config, seed=2)
    estado = configurar_partida(config, deck1, deck2, seed=1)
    ai = criar_ia(chave, seed=1)

    contadores = {"invocacoes": 0, "locais": 0, "mestres": 0, "juizes": 0, "atacou": False}
    legais = eng.acoes_legais(estado, estado.turno_de, contadores, config)
    acao = ai.escolher_acao(estado, estado.turno_de, legais, config)
    assert acao in legais


# ------------------------------------------------------------------
# Comportamento distinto entre personas (não só "roda sem crash")
# ------------------------------------------------------------------

def _jogador_com_heroi(pool, nome, forca=200):
    from engine import EstadoHeroiCampo, EstadoJogador

    heroi = pool.novo_heroi("rara", variacao_id=1, forca=forca)
    campo = EstadoHeroiCampo.entrar_em_campo(heroi, rodada_atual=1)
    return EstadoJogador(nome=nome, heroi_ativo=campo)


def test_acumuladora_guarda_mais_invocacao_que_gastadora(config):
    pool = CardPool(config, seed=1)
    j1 = _jogador_com_heroi(pool, "P1")
    j1.mao = [pool.nova_invocacao() for _ in range(5)]
    estado = eng.EstadoPartida(jogadores={"P1": j1, "P2": _jogador_com_heroi(pool, "P2")}, turno_de="P1")

    acoes = [eng.Acao("colocar_invocacao", {"carta": c}) for c in j1.mao] + [eng.Acao("passar")]

    acumuladora = criar_ia("acumuladora", seed=1)
    gastadora = criar_ia("gastadora", seed=1)

    # acumuladora (reserva alvo alta) deve preferir colocar invocação
    acao_acumuladora = acumuladora.escolher_acao(estado, "P1", acoes, config)
    assert acao_acumuladora.tipo == "colocar_invocacao"

    # gastadora (reserva alvo 0) nunca acumula por propósito -> deve passar
    # já que não há mais nenhuma ação legal além de invocação/passar aqui
    acao_gastadora = gastadora.escolher_acao(estado, "P1", acoes, config)
    assert acao_gastadora.tipo == "passar"


def test_focada_em_juiz_usa_juiz_com_vantagem_menor_que_certinho(config):
    pool = CardPool(config, seed=2)
    j1 = _jogador_com_heroi(pool, "P1", forca=150)
    j2 = _jogador_com_heroi(pool, "P2", forca=190)  # diferença de 40
    estado = eng.EstadoPartida(jogadores={"P1": j1, "P2": j2}, turno_de="P1")

    juiz = pool.novo_juiz()
    acao_juiz = eng.Acao("invocar_juiz", {"carta": juiz, "pagamento": []})
    acoes = [acao_juiz, eng.Acao("passar")]

    focada = criar_ia("focada_em_juiz", seed=1)  # limiar_juiz=10 -> 40 > 10, deve usar
    certinho = criar_ia("certinho", seed=1)  # limiar_juiz=100 -> 40 < 100, não deve usar

    assert focada.escolher_acao(estado, "P1", acoes, config).tipo == "invocar_juiz"
    assert certinho.escolher_acao(estado, "P1", acoes, config).tipo == "passar"


def test_anti_juiz_barra_mestre_fraco_que_certinho_deixaria_passar(config):
    pool = CardPool(config, seed=3)
    mestre_fraco = pool.novo_mestre("comum", forca=60)  # bem abaixo do limiar padrão (200)
    guardiao_barrador = pool.novo_guardiao(categoria="Acao", raridade="comum")

    opcoes = [
        eng.Acao("barrar", {"carta": guardiao_barrador, "pagamento": [], "alvo": mestre_fraco}),
        eng.Acao("passar_barragem"),
    ]

    anti_juiz = criar_ia("anti_juiz", seed=1)
    certinho = criar_ia("certinho", seed=1)

    # mestre.forca_impressa (60) está bem abaixo dos dois limiares (260 e 200);
    # mas anti_juiz sempre barra Mestre/Juiz independente da força
    assert anti_juiz.escolher_acao(None, "P1", opcoes, config).tipo == "barrar"
    assert certinho.escolher_acao(None, "P1", opcoes, config).tipo == "passar_barragem"


def test_persona_ai_permite_parametros_customizados_sem_registro():
    """O usuário pode criar a 16ª persona só passando um dict novo, sem editar o catálogo."""
    persona_customizada = PersonaAI({"limiar_juiz": 5, "reserva_alvo_invocacoes": 0})
    assert persona_customizada.p["limiar_juiz"] == 5
    assert persona_customizada.p["reserva_alvo_invocacoes"] == 0
    # parâmetros não especificados continuam com o padrão
    assert persona_customizada.p["limiar_barragem_forca"] == 200
