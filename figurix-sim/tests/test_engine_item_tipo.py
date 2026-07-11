"""Item de Herói se vincula a um TIPO de herói (seção 1), não a uma
variação específica — mesma correção aplicada ao Mestre. Anexar um item
precisa ser elegível para QUALQUER uma das 3 variações do tipo vinculado,
não só a variacao_id exata."""
from cardpool import CardPool, variacoes_do_tipo
from engine import EstadoHeroiCampo, EstadoJogador, EstadoPartida, acoes_legais


def _acoes_de_anexar_item(pool, config, tipo_vinculado, variacao_heroi_ativo):
    heroi_ativo = pool.novo_heroi("comum", variacao_id=variacao_heroi_ativo, forca=100)
    item = pool.novo_item(tipo_heroi=tipo_vinculado, raridade="comum")

    campo = EstadoHeroiCampo.entrar_em_campo(heroi_ativo, rodada_atual=1)
    p1 = EstadoJogador(nome="P1", heroi_ativo=campo, mao=[item])
    heroi_p2 = pool.novo_heroi("comum", variacao_id=variacoes_do_tipo(2, config)[0], forca=100)
    p2 = EstadoJogador(nome="P2", heroi_ativo=EstadoHeroiCampo.entrar_em_campo(heroi_p2, rodada_atual=1))
    estado = EstadoPartida(jogadores={"P1": p1, "P2": p2}, turno_de="P1")

    contadores = {"invocacoes": 0, "locais": 0, "mestres": 0, "juizes": 0, "atacou": False}
    return [a for a in acoes_legais(estado, "P1", contadores, config) if a.tipo == "anexar_item"]


def test_item_elegivel_para_qualquer_variacao_do_mesmo_tipo(config):
    pool = CardPool(config, seed=1)
    tipo_vinculado = 1
    v1, v2, v3 = variacoes_do_tipo(tipo_vinculado, config)

    for variacao in (v1, v2, v3):
        acoes = _acoes_de_anexar_item(pool, config, tipo_vinculado, variacao)
        assert len(acoes) == 1, f"variação {variacao} (tipo {tipo_vinculado}) deveria poder anexar o item"


def test_item_nao_elegivel_para_variacao_de_tipo_diferente(config):
    pool = CardPool(config, seed=2)
    tipo_vinculado = 1
    variacao_outro_tipo = variacoes_do_tipo(2, config)[0]

    acoes = _acoes_de_anexar_item(pool, config, tipo_vinculado, variacao_outro_tipo)
    assert acoes == []
