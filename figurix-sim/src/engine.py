"""Motor de regras: estado de partida e funções de resolução (seção 4, 7, 9, 10 das regras).

Este módulo contém os modelos de estado mutáveis de uma partida e as
funções que aplicam as regras que não são puramente de combate (que
fica em combat.py) nem de barragem (chains.py): evolução de herói,
entrada do Juiz, Guardião do Descanso, mulligan e a espiral de fim de
deck.

Todas as regras numéricas vêm do config — nada hardcoded.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import combat
from cardpool import tipo_da_variacao
from cards import (
    Guardiao,
    Heroi,
    Invocacao,
    ItemHeroi,
    Juiz,
    Local,
    Mestre,
    custo_auxiliar_da_raridade,
    pontos_da_raridade,
    raridade_equivalente,
)

PODER_POR_TIPO_ATAQUE = {
    "principal": "poder_principal",
    "secundario": "poder_secundario",
    "terciario": "poder_terciario",
}
CATEGORIA_POR_TIPO_ATAQUE = {
    "principal": "categoria_principal",
    "secundario": "categoria_secundaria",
    "terciario": "categoria_terciaria",
}


# ------------------------------------------------------------------
# Estado
# ------------------------------------------------------------------

@dataclass
class EstadoHeroiCampo:
    carta: Heroi
    forca_atual: int
    item_anexado: Optional[ItemHeroi] = None
    rodada_entrada: int = 0
    evoluiu: bool = False
    dano_acumulado_rodada: int = 0  # usado pelo Guardião dos Oprimidos

    @classmethod
    def entrar_em_campo(cls, carta: Heroi, rodada_atual: int) -> "EstadoHeroiCampo":
        return cls(carta=carta, forca_atual=carta.forca_impressa, rodada_entrada=rodada_atual)


@dataclass
class EstadoMestreCampo:
    carta: object  # Mestre
    rodadas_restantes: int


@dataclass
class EstadoGuardiaoCampo:
    carta: object  # Guardiao
    forca_atual: int
    rodadas_restantes: Optional[int] = None  # None = sem expiração natural (ex.: Oprimidos)


@dataclass
class EstadoDescanso:
    heroi_descansando: EstadoHeroiCampo  # o herói que foi para a "reserva" (mão)
    heroi_isca: EstadoHeroiCampo  # a isca comum que está em campo
    rodada_retorno: int  # rodada em que a isca deve voltar e o titular retornar


@dataclass
class EstadoLocal:
    carta: object  # Local
    portais_rodadas_restantes: int = 0
    portais_raridade: Optional[str] = None


@dataclass
class EstadoJogador:
    nome: str
    mao: list = field(default_factory=list)
    deck: list = field(default_factory=list)  # topo = deck[-1]
    descarte: list = field(default_factory=list)
    pontos: int = 0
    heroi_ativo: Optional[EstadoHeroiCampo] = None
    mestre: Optional[EstadoMestreCampo] = None
    guardioes: list = field(default_factory=list)  # list[EstadoGuardiaoCampo]
    descanso: Optional[EstadoDescanso] = None
    invocacoes_em_mesa: list = field(default_factory=list)


@dataclass
class EstadoPartida:
    jogadores: dict  # nome -> EstadoJogador
    local: Optional[EstadoLocal] = None
    rodada: int = 1
    turno_de: str = ""
    ordem_turno: list = field(default_factory=list)  # [primeiro, segundo] — fixo após o início
    vencedor: Optional[str] = None
    espirais: dict = field(default_factory=dict)  # nome -> EstadoEspiral (busca de herói em andamento)
    log: list = field(default_factory=list)


def registrar_evento(estado: EstadoPartida, **campos) -> None:
    evento = {"rodada": estado.rodada, "turno_de": estado.turno_de, **campos}
    estado.log.append(evento)


def clonar_estado(estado: EstadoPartida) -> EstadoPartida:
    """Clone barato de EstadoPartida (seção 2.5 da spec do simulador — usado
    pelo MCTSAI para simular rollouts). As cartas (Heroi/Mestre/... em
    cards.py) são dataclasses IMUTÁVEIS — reaproveitamos as mesmas
    referências em vez de copiá-las com `copy.deepcopy`, que não sabe
    disso e recursivamente duplicaria tudo (caro, e desnecessário já que
    nada nelas muda). Só as estruturas de estado MUTÁVEIS (EstadoHeroiCampo,
    EstadoMestreCampo etc.) precisam de cópia de fato. O log não é
    copiado — é só histórico para auditoria, não afeta a simulação, e
    cresce demais em partidas longas para valer a pena duplicar a cada
    rollout."""
    return EstadoPartida(
        jogadores={nome: _clonar_jogador(j) for nome, j in estado.jogadores.items()},
        local=_clonar_local(estado.local),
        rodada=estado.rodada,
        turno_de=estado.turno_de,
        ordem_turno=list(estado.ordem_turno),
        vencedor=estado.vencedor,
        espirais={nome: EstadoEspiral(**vars(e)) for nome, e in estado.espirais.items()},
        log=[],
    )


def _clonar_heroi_campo(h: Optional[EstadoHeroiCampo]) -> Optional[EstadoHeroiCampo]:
    return None if h is None else EstadoHeroiCampo(**vars(h))


def _clonar_mestre_campo(m: Optional[EstadoMestreCampo]) -> Optional[EstadoMestreCampo]:
    return None if m is None else EstadoMestreCampo(**vars(m))


def _clonar_guardiao_campo(g: EstadoGuardiaoCampo) -> EstadoGuardiaoCampo:
    return EstadoGuardiaoCampo(**vars(g))


def _clonar_local(loc: Optional[EstadoLocal]) -> Optional[EstadoLocal]:
    return None if loc is None else EstadoLocal(**vars(loc))


def _clonar_jogador(j: EstadoJogador) -> EstadoJogador:
    heroi_ativo_clone = _clonar_heroi_campo(j.heroi_ativo)

    descanso_clone = None
    if j.descanso is not None:
        # heroi_isca é o MESMO objeto que heroi_ativo enquanto a isca está em
        # campo (aplicar_descanso faz jogador.heroi_ativo = estado_isca =
        # descanso.heroi_isca) — preserva essa identidade no clone, senão
        # os checks "is" em _aplicar_dano/_fim_de_rodada (que detectam a
        # isca caindo ou retornando) quebram silenciosamente.
        heroi_isca_clone = (
            heroi_ativo_clone if j.descanso.heroi_isca is j.heroi_ativo else _clonar_heroi_campo(j.descanso.heroi_isca)
        )
        descanso_clone = EstadoDescanso(
            heroi_descansando=_clonar_heroi_campo(j.descanso.heroi_descansando),
            heroi_isca=heroi_isca_clone,
            rodada_retorno=j.descanso.rodada_retorno,
        )

    return EstadoJogador(
        nome=j.nome,
        mao=list(j.mao),
        deck=list(j.deck),
        descarte=list(j.descarte),
        pontos=j.pontos,
        heroi_ativo=heroi_ativo_clone,
        mestre=_clonar_mestre_campo(j.mestre),
        guardioes=[_clonar_guardiao_campo(g) for g in j.guardioes],
        descanso=descanso_clone,
        invocacoes_em_mesa=list(j.invocacoes_em_mesa),
    )


# ------------------------------------------------------------------
# Evolução de herói (seção 7 / seção 6 caso 5)
# ------------------------------------------------------------------

def pode_evoluir(
    heroi_campo: EstadoHeroiCampo,
    carta_destino: Heroi,
    rodada_atual: int,
    item_raro_anexado: bool,
    config: dict,
) -> tuple[bool, str]:
    """Retorna (pode, motivo_se_nao)."""
    if heroi_campo.evoluiu:
        return False, "herói já evoluiu uma vez"
    if carta_destino.participante_id != heroi_campo.carta.participante_id:
        return False, "carta de destino não é do mesmo participante"
    if raridade_equivalente(carta_destino.raridade, config) == raridade_equivalente(
        heroi_campo.carta.raridade, config
    ):
        return False, "destino precisa ser raridade superior à comum de entrada"
    entrou_nesta_rodada = heroi_campo.rodada_entrada == rodada_atual
    if entrou_nesta_rodada and not item_raro_anexado:
        return False, "só pode evoluir a partir da rodada seguinte (sem item raro)"
    return True, ""


def custo_evolucao(item_raro_anexado: bool, config: dict) -> int:
    return 0 if item_raro_anexado else config["custo_evolucao"]


def aplicar_evolucao(
    heroi_campo: EstadoHeroiCampo,
    carta_destino: Heroi,
    rodada_atual: int,
    item_raro_anexado: bool,
    config: dict,
) -> EstadoHeroiCampo:
    pode, motivo = pode_evoluir(heroi_campo, carta_destino, rodada_atual, item_raro_anexado, config)
    if not pode:
        raise ValueError(f"Evolução ilegal: {motivo}")
    return EstadoHeroiCampo(
        carta=carta_destino,
        forca_atual=carta_destino.forca_impressa,  # restaura força cheia
        item_anexado=heroi_campo.item_anexado,
        rodada_entrada=heroi_campo.rodada_entrada,
        evoluiu=True,
    )


# ------------------------------------------------------------------
# Entrada do Juiz (seção 9 / seção 6 caso 6)
# ------------------------------------------------------------------

@dataclass
class ResultadoEntradaJuiz:
    forca_defensor_antes: int
    forca_defensor_depois: int
    forca_proprio_antes: int
    forca_proprio_depois: int
    cartas_removidas_do_adversario: list


def resolver_entrada_juiz(
    jogador_proprio: EstadoJogador,
    jogador_adversario: EstadoJogador,
    estado_partida: EstadoPartida,
    escolhas_remocao: list,
    config: dict,
) -> ResultadoEntradaJuiz:
    """Aplica, nesta ordem: equalização, cura, limpeza seletiva (seção 9).

    `escolhas_remocao`: lista de cartas do ADVERSÁRIO (item anexado,
    guardiões, mestre, local) que o jogador que invocou o Juiz decide
    remover. Invocações nunca são tocadas — não podem aparecer aqui.
    """
    heroi_proprio = jogador_proprio.heroi_ativo
    heroi_adversario = jogador_adversario.heroi_ativo

    forca_defensor_antes = heroi_adversario.forca_atual if heroi_adversario else 0
    forca_proprio_antes = heroi_proprio.forca_atual

    # 1. Golpe de equalização: só se adversário tiver MAIS força restante.
    if heroi_adversario is not None and heroi_adversario.forca_atual > heroi_proprio.forca_atual:
        heroi_adversario.forca_atual = heroi_proprio.forca_atual

    # 2. Cura: +cura_juiz, limitada à força impressa.
    cura = config["cura_juiz"]
    heroi_proprio.forca_atual = min(
        heroi_proprio.carta.forca_impressa, heroi_proprio.forca_atual + cura
    )

    # 3. Limpeza seletiva: só cartas escolhidas pelo jogador, só do adversário.
    for carta in escolhas_remocao:
        if isinstance(carta, Invocacao):
            raise ValueError("Invocações nunca são tocadas pela limpeza do Juiz")

        if (
            jogador_adversario.heroi_ativo is not None
            and jogador_adversario.heroi_ativo.item_anexado is carta
        ):
            jogador_adversario.heroi_ativo.item_anexado = None
            jogador_adversario.descarte.append(carta)
            continue

        guardioes_restantes = [g for g in jogador_adversario.guardioes if g.carta is not carta]
        if len(guardioes_restantes) != len(jogador_adversario.guardioes):
            jogador_adversario.guardioes = guardioes_restantes
            jogador_adversario.descarte.append(carta)
            continue

        if jogador_adversario.mestre is not None and jogador_adversario.mestre.carta is carta:
            jogador_adversario.descarte.append(carta)
            jogador_adversario.mestre = None
            continue

        if estado_partida.local is not None and estado_partida.local.carta is carta:
            jogador_adversario.descarte.append(carta)
            estado_partida.local = None
            continue

    return ResultadoEntradaJuiz(
        forca_defensor_antes=forca_defensor_antes,
        forca_defensor_depois=heroi_adversario.forca_atual if heroi_adversario else 0,
        forca_proprio_antes=forca_proprio_antes,
        forca_proprio_depois=heroi_proprio.forca_atual,
        cartas_removidas_do_adversario=list(escolhas_remocao),
    )


def juiz_vai_para_descarte(juiz_carta: Juiz, jogador: EstadoJogador) -> None:
    """O Juiz nunca persiste em campo — vai ao descarte ao fim do turno em que entrou."""
    jogador.descarte.append(juiz_carta)


# ------------------------------------------------------------------
# Guardião do Descanso (seção 9, item 13.3 / seção 6 caso 7)
# ------------------------------------------------------------------

def aplicar_descanso(
    jogador: EstadoJogador,
    heroi_isca: Heroi,
    rodada_atual: int,
    config: dict,
) -> EstadoDescanso:
    """Devolve o herói ativo à mão e coloca a isca (comum) no lugar por 1 rodada."""
    if heroi_isca.raridade != "comum":
        raise ValueError("Isca do Guardião do Descanso precisa ser uma carta comum")

    heroi_que_descansa = jogador.heroi_ativo
    jogador.mao.append(heroi_que_descansa.carta)

    estado_isca = EstadoHeroiCampo.entrar_em_campo(heroi_isca, rodada_atual)
    jogador.heroi_ativo = estado_isca

    descanso = EstadoDescanso(
        heroi_descansando=heroi_que_descansa,
        heroi_isca=estado_isca,
        rodada_retorno=rodada_atual + 1,
    )
    jogador.descanso = descanso
    return descanso


def resolver_retorno_descanso(
    jogador: EstadoJogador,
    oponente: EstadoJogador,
    isca_foi_derrotada: bool,
    config: dict,
) -> None:
    """Ao fim da rodada de descanso: se a isca caiu, ponto ao adversário;
    senão o titular volta com +cura_descanso (cap na força impressa)."""
    descanso = jogador.descanso
    if descanso is None:
        raise ValueError("Nenhum descanso ativo para resolver")

    if isca_foi_derrotada:
        oponente.pontos += pontos_da_raridade(descanso.heroi_isca.carta.raridade, config)
        jogador.heroi_ativo = None
    else:
        titular = descanso.heroi_descansando
        titular.forca_atual = min(
            titular.carta.forca_impressa, titular.forca_atual + config["cura_descanso"]
        )
        jogador.mao.remove(titular.carta)
        jogador.heroi_ativo = titular

    jogador.descanso = None


# ------------------------------------------------------------------
# Mulligan (seção 3, itens 3-5 e seção 3.4 / seção 6 caso 8)
# ------------------------------------------------------------------

def tem_heroi_comum(mao: list) -> bool:
    return any(isinstance(c, Heroi) and c.raridade == "comum" for c in mao)


def mao_aceitavel_por_heuristica_padrao(mao: list) -> bool:
    """Critério padrão de aceite de mão (seção 3.4 — recusa VOLUNTÁRIA de
    mão tecnicamente válida): recusa uma mão que tem herói comum mas
    nenhum outro recurso à vista (nem invocação pra pagar nada, nem herói
    de raridade maior como alvo de evolução). É comportamento de IA, não
    regra de jogo — por isso não usa nenhum valor de config; usado por
    HeuristicAI, MCTSAI e por qualquer persona que não sobrescreva o
    critério (parâmetro `mao_exigente` de PersonaAI)."""
    tem_invocacao = any(isinstance(c, Invocacao) for c in mao)
    tem_heroi_forte = any(isinstance(c, Heroi) and c.raridade != "comum" for c in mao)
    return tem_invocacao or tem_heroi_forte


@dataclass
class ConsequenciaDecisaoMulligan:
    titular_prioridade: str
    compra_bonus_para: Optional[str] = None
    ponto_para: Optional[str] = None


def registrar_decisao_mulligan(
    nome: str,
    outro_nome: str,
    outro_ja_aceitou: bool,
    titular_atual: str,
    desistencias_nome: int,
    config: dict,
) -> ConsequenciaDecisaoMulligan:
    """Consequências de UMA rejeição de mão — só chamado quando `nome`
    acabou de recusar a mão que acabou de comprar (aceitar não tem
    consequência nenhuma pro outro jogador).

    Regras (seção 3, itens 3-5):
      - Se o outro jogador AINDA não aceitou a dele (também está decidindo
        ou também acabou de recusar nesta mesma rodada), ninguém é
        premiado agora — a compensação existe só para quem MANTÉM a mão
        enquanto o outro desiste, não quando os dois desistem juntos.
      - Senão (o outro já tem mão aceita), o outro ganha +1 compra; a
        partir da 2ª desistência CONSECUTIVA de `nome`, o outro também
        ganha +1 ponto.
      - Se quem recusou é o titular da prioridade (o vencedor do par ou
        ímpar, ou quem herdou a titularidade depois) e o outro já tinha
        aceitado, a titularidade vira para o outro — "a partir daí é como
        se o perdedor fosse quem tivesse ganho no par ou ímpar".
    """
    if not outro_ja_aceitou:
        return ConsequenciaDecisaoMulligan(titular_prioridade=titular_atual)

    novo_titular = outro_nome if nome == titular_atual else titular_atual
    ponto_para = outro_nome if desistencias_nome >= 2 else None
    return ConsequenciaDecisaoMulligan(
        titular_prioridade=novo_titular,
        compra_bonus_para=outro_nome,
        ponto_para=ponto_para,
    )


def quem_age_primeiro(
    carta_inicial_a: tuple[str, Heroi],
    carta_inicial_b: tuple[str, Heroi],
    titular_prioridade: str,
) -> str:
    """A carta comum de MENOR força age primeiro; empate -> vale a prioridade."""
    nome_a, heroi_a = carta_inicial_a
    nome_b, heroi_b = carta_inicial_b
    if heroi_a.forca_impressa < heroi_b.forca_impressa:
        return nome_a
    if heroi_b.forca_impressa < heroi_a.forca_impressa:
        return nome_b
    return titular_prioridade


# ------------------------------------------------------------------
# Espiral de fim de deck (seção 10 / seção 6 caso 9)
# ------------------------------------------------------------------

@dataclass
class EstadoEspiral:
    jogador_em_busca: str
    compras_devidas_busca: int = 1
    compras_devidas_adversario: int = 1


def em_busca_de_heroi(jogador: EstadoJogador) -> bool:
    return jogador.heroi_ativo is None and not tem_heroi_comum(jogador.mao)


def passo_espiral(
    estado_partida: EstadoPartida,
    jogador: EstadoJogador,
    adversario: EstadoJogador,
    espiral: EstadoEspiral,
    config: dict,
) -> Optional[str]:
    """Executa um passo da escalada de compras. Retorna o vencedor se a
    partida terminar neste passo (deck de alguém esgota), senão None.

    Regras: o jogador em busca compra N cartas; o adversário ganha o
    direito de comprar N+1 na rodada seguinte (a escalada cresce). Se o
    adversário não tiver mais cartas para comprar durante a espiral, ele
    passa a ganhar 1 ponto por carta que o jogador em busca comprar. Se o
    deck do jogador em busca esgotar sem achar herói, ele cede
    `penalidade_sem_deck` pontos e a partida termina.
    """
    n = espiral.compras_devidas_busca

    for _ in range(n):
        if not jogador.deck:
            adversario.pontos += config["penalidade_sem_deck"]
            estado_partida.vencedor = _vencedor_por_pontos(estado_partida)
            return estado_partida.vencedor
        carta = jogador.deck.pop()
        jogador.mao.append(carta)
        if not adversario.deck:
            adversario.pontos += 1

    if em_busca_de_heroi(jogador):
        espiral.compras_devidas_busca += 1

    return None


def _vencedor_por_pontos(estado: EstadoPartida) -> str:
    nomes = list(estado.jogadores.keys())
    a, b = nomes[0], nomes[1]
    if estado.jogadores[a].pontos > estado.jogadores[b].pontos:
        return a
    if estado.jogadores[b].pontos > estado.jogadores[a].pontos:
        return b
    return "empate"


# ------------------------------------------------------------------
# Pagamento de custos com invocações (seção 4)
# ------------------------------------------------------------------

def pagar_mesma_categoria(mesa: list, categoria: str, quantidade: int) -> Optional[list]:
    disponiveis = [c for c in mesa if c.categoria == categoria]
    if len(disponiveis) >= quantidade:
        return disponiveis[:quantidade]
    return None


def pagar_ataque(mesa: list, categoria_ataque: str, config: dict) -> Optional[list]:
    custo = config["custo_ataque"]
    pagamento = pagar_mesma_categoria(mesa, categoria_ataque, custo["mesma_categoria"])
    if pagamento is not None:
        return pagamento
    qtd_mista = custo["categorias_diferentes"]
    if len(mesa) >= qtd_mista:
        return mesa[:qtd_mista]
    return None


def pagar_auxiliar(mesa: list, categoria: str, raridade: str, config: dict) -> Optional[list]:
    custo = custo_auxiliar_da_raridade(raridade, config, mixto=False)
    pagamento = pagar_mesma_categoria(mesa, categoria, custo)
    if pagamento is not None:
        return pagamento
    custo_misto = custo_auxiliar_da_raridade(raridade, config, mixto=True)
    if len(mesa) >= custo_misto:
        return mesa[:custo_misto]
    return None


def pagar_barragem(mesa: list, categoria_barrador: str, config: dict) -> Optional[list]:
    return pagar_mesma_categoria(mesa, categoria_barrador, config["custo_barragem"])


def pagar_evolucao(mesa: list, categoria_heroi: str, item_raro_anexado: bool, config: dict) -> Optional[list]:
    custo = custo_evolucao(item_raro_anexado, config)
    if custo == 0:
        return []
    return pagar_mesma_categoria(mesa, categoria_heroi, custo)


# ------------------------------------------------------------------
# Ações legais (seção 2 da spec do simulador)
# ------------------------------------------------------------------

@dataclass(frozen=True)
class Acao:
    tipo: str
    dados: dict = field(default_factory=dict, compare=False)


def acoes_legais(
    estado: EstadoPartida,
    jogador_nome: str,
    contadores_turno: dict,
    config: dict,
) -> list[Acao]:
    """Lista de ações legais da fase de ações do turno (não inclui barragens,
    que são resolvidas em uma janela à parte — ver match.janela_barragem).

    `contadores_turno`: quantas vezes cada tipo de ação já foi usado neste
    turno (chaves: invocacoes, locais, mestres, juizes).
    """
    jogador = estado.jogadores[jogador_nome]
    mesa = jogador.invocacoes_em_mesa
    acoes: list[Acao] = [Acao("passar")]

    if jogador.heroi_ativo is None:
        herois_comuns = [c for c in jogador.mao if isinstance(c, Heroi) and c.raridade == "comum"]
        for carta in herois_comuns:
            acoes.append(Acao("trocar_heroi_derrotado", {"carta": carta}))
        # sem herói ativo: não há mais ações de campo relevantes até repor o herói
        return acoes

    if contadores_turno.get("invocacoes", 0) < config["invocacoes_por_turno"]:
        for carta in jogador.mao:
            if isinstance(carta, Invocacao):
                acoes.append(Acao("colocar_invocacao", {"carta": carta}))

    if contadores_turno.get("locais", 0) < config["locais_por_turno"]:
        for carta in jogador.mao:
            if isinstance(carta, Local):
                if _troca_de_local_permitida(estado, carta, config):
                    acoes.append(Acao("colocar_local", {"carta": carta}))

    tem_outra_comum_para_descanso = any(
        isinstance(c, Heroi) and c.raridade == "comum" for c in jogador.mao
    )
    for carta in jogador.mao:
        if isinstance(carta, Guardiao):
            if carta.tipo == "Descanso" and not tem_outra_comum_para_descanso:
                continue  # precisa de uma isca comum na mão para valer a pena
            pagamento = pagar_auxiliar(mesa, carta.categoria, carta.raridade, config)
            if pagamento is not None:
                acoes.append(Acao("invocar_guardiao", {"carta": carta, "pagamento": pagamento}))

    if contadores_turno.get("mestres", 0) < config["mestres_por_turno"]:
        for carta in jogador.mao:
            if isinstance(carta, Mestre):
                pagamento = pagar_auxiliar(mesa, carta.categoria, carta.raridade, config)
                if pagamento is not None:
                    acoes.append(Acao("invocar_mestre", {"carta": carta, "pagamento": pagamento}))

    if contadores_turno.get("juizes", 0) < config["juizes_por_turno"]:
        for carta in jogador.mao:
            if isinstance(carta, Juiz):
                pagamento = pagar_auxiliar(mesa, carta.categoria, carta.raridade, config)
                if pagamento is not None:
                    acoes.append(Acao("invocar_juiz", {"carta": carta, "pagamento": pagamento}))

    if jogador.heroi_ativo.item_anexado is None:
        for carta in jogador.mao:
            if isinstance(carta, ItemHeroi) and carta.tipo_heroi == jogador.heroi_ativo.carta.variacao_id:
                acoes.append(Acao("anexar_item", {"carta": carta}))

    item_raro_anexado = (
        jogador.heroi_ativo.item_anexado is not None
        and jogador.heroi_ativo.item_anexado.raridade == "rara"
    )
    for carta in jogador.mao:
        if not isinstance(carta, Heroi):
            continue
        pode, _ = pode_evoluir(
            jogador.heroi_ativo, carta, rodada_atual=estado.rodada, item_raro_anexado=item_raro_anexado, config=config
        )
        if not pode:
            continue
        pagamento = pagar_evolucao(mesa, jogador.heroi_ativo.carta.categoria_principal, item_raro_anexado, config)
        if pagamento is not None:
            acoes.append(Acao("evoluir", {"carta": carta, "pagamento": pagamento}))

    adversario_nome = next(n for n in estado.jogadores if n != jogador_nome)
    adversario = estado.jogadores[adversario_nome]
    if not contadores_turno.get("atacou", False) and adversario.heroi_ativo is not None:
        pagamento_principal = pagar_ataque(mesa, jogador.heroi_ativo.carta.categoria_principal, config)
        if pagamento_principal is not None:
            acoes.append(Acao("atacar", {"tipo_ataque": "principal", "pagamento": pagamento_principal}))
        pagamento_secundario = pagar_ataque(mesa, jogador.heroi_ativo.carta.categoria_secundaria, config)
        if pagamento_secundario is not None:
            acoes.append(Acao("atacar", {"tipo_ataque": "secundario", "pagamento": pagamento_secundario}))
        acoes.append(Acao("atacar", {"tipo_ataque": "terciario", "pagamento": []}))  # grátis

    return acoes


def _troca_de_local_permitida(estado: EstadoPartida, novo_local: Local, config: dict) -> bool:
    """Troca normal de local (seção 8). Enquanto a trava do Guardião dos
    Portais estiver ativa, a troca comum (`colocar_local`) fica bloqueada —
    só uma nova invocação de Portais com força suficiente destrava (seção 8,
    "exceção estratégica"), o que é um fluxo de invocar_guardiao à parte,
    não de colocar_local; fora do escopo desta integração (M3)."""
    if estado.local is None:
        return True
    if estado.local.portais_rodadas_restantes > 0:
        return False
    if estado.local.carta.raridade == "rara" and novo_local.raridade == "comum":
        return False
    return True


# ------------------------------------------------------------------
# Efeitos de guardiões (seção 9) além do Descanso (já coberto acima)
# ------------------------------------------------------------------

def aplicar_restauracao(heroi: EstadoHeroiCampo, guardiao: Guardiao, config: dict) -> None:
    """Restaura a força do herói ativo até a força do guardião; -30 se
    categorias diferentes. A carta do guardião é descartada pelo chamador."""
    bonus = guardiao.forca_impressa
    if guardiao.categoria != heroi.carta.categoria_principal:
        bonus -= config["restauracao_desconto_categoria_diferente"]
    heroi.forca_atual = min(heroi.carta.forca_impressa, heroi.forca_atual + max(0, bonus))


def registrar_dano_para_oprimidos(heroi: EstadoHeroiCampo, dano: int) -> None:
    heroi.dano_acumulado_rodada += dano


def resolver_oprimidos(heroi: EstadoHeroiCampo, guardiao_ativo: bool, config: dict) -> int:
    """Ao fim da rodada: se guardião dos Oprimidos ativo e força restante
    <= 60, o dano acumulado vira força de ataque (sem múltiplos/vantagens).
    Retorna o dano convertido (0 se condição não se aplica)."""
    dano_convertido = 0
    if guardiao_ativo and heroi.forca_atual <= 60:
        dano_convertido = heroi.dano_acumulado_rodada
    heroi.dano_acumulado_rodada = 0
    return dano_convertido


# ------------------------------------------------------------------
# Previsão de resultado de ataque (usada tanto por match.py para resolver
# o ataque quanto por IAs para decidir se vale a pena atacar)
# ------------------------------------------------------------------

def prever_resultado_ataque(
    estado: EstadoPartida, jogador_nome: str, tipo_ataque: str, config: dict
) -> combat.ResultadoCombate:
    jogador = estado.jogadores[jogador_nome]
    adversario_nome = next(n for n in estado.jogadores if n != jogador_nome)
    adversario = estado.jogadores[adversario_nome]

    atacante_carta = jogador.heroi_ativo.carta
    defensor_campo = adversario.heroi_ativo
    poder_base = getattr(atacante_carta, PODER_POR_TIPO_ATAQUE[tipo_ataque])
    categoria_ataque_usado = getattr(atacante_carta, CATEGORIA_POR_TIPO_ATAQUE[tipo_ataque])
    local_favorece = estado.local is not None and estado.local.carta.categoria == categoria_ataque_usado
    mestre_presente = (
        jogador.mestre is not None
        and jogador.mestre.carta.tipo_heroi_dominado == tipo_da_variacao(atacante_carta.variacao_id, config)
    )
    item_anexado = jogador.heroi_ativo.item_anexado is not None

    return combat.resolver_ataque(
        poder_base=poder_base,
        tipo_ataque=tipo_ataque,
        item_anexado=item_anexado,
        local_favorece_categoria_ataque=local_favorece,
        mestre_do_tipo_presente=mestre_presente,
        categoria_heroi_atacante=atacante_carta.categoria_principal,
        categoria_heroi_defensor=defensor_campo.carta.categoria_principal,
        categoria_ataque_usado=categoria_ataque_usado,
        config=config,
    )
