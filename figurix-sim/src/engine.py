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

from cards import Heroi, Invocacao, ItemHeroi, Juiz, pontos_da_raridade, raridade_equivalente


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
    vencedor: Optional[str] = None
    log: list = field(default_factory=list)


def registrar_evento(estado: EstadoPartida, **campos) -> None:
    evento = {"rodada": estado.rodada, "turno_de": estado.turno_de, **campos}
    estado.log.append(evento)


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
# Mulligan (seção 3 / seção 6 caso 8)
# ------------------------------------------------------------------

@dataclass
class ResultadoMulligan:
    maos_finais: dict  # nome -> list[Carta]
    titular_prioridade: str
    pontos: dict  # nome -> pontos ganhos por desistências alheias
    compras_extra: dict  # nome -> compras extras ganhas


def _tem_heroi_comum(mao: list) -> bool:
    return any(isinstance(c, Heroi) and c.raridade == "comum" for c in mao)


def resolver_mulligan(
    jogadores_e_maos: list[tuple[str, list]],
    ordem_decisao: list[str],
    titular_inicial: str,
    decisoes: dict,
    config: dict,
) -> ResultadoMulligan:
    """Resolve a sequência de aceite/desistência de mão (seção 3, itens 3-5).

    `ordem_decisao`: [perdedor_par_ou_impar, vencedor] — o vencedor do par
    ou ímpar pergunta primeiro ao ADVERSÁRIO (perdedor) se mantém a mão,
    então decide a sua própria (seção 3, item 5).
    `titular_inicial`: quem detém a prioridade no início (o vencedor).
    `decisoes`: nome -> lista de bools na ordem das tentativas desse jogador
    (True = mantém a mão atual; False = desiste e pede nova mão). A função
    para no primeiro True de cada jogador (mão aceita é definitiva).

    Regras aplicadas:
      - Sem herói comum ou desistência voluntária -> nova mão + adversário
        ganha +1 compra; da 2ª desistência em diante, +1 ponto também.
      - Se o perdedor mantém e o vencedor (titular) desiste depois,
        a titularidade da prioridade vira para o perdedor.
    """
    maos = {nome: list(mao) for nome, mao in jogadores_e_maos}
    pontos = {nome: 0 for nome, _ in jogadores_e_maos}
    compras_extra = {nome: 0 for nome, _ in jogadores_e_maos}
    desistencias = {nome: 0 for nome, _ in jogadores_e_maos}
    titular_prioridade = titular_inicial

    aceitou = {nome: False for nome, _ in jogadores_e_maos}
    ordem_atual = list(ordem_decisao)

    while not all(aceitou.values()):
        for nome in ordem_atual:
            if aceitou[nome]:
                continue
            historico = decisoes.get(nome, [])
            idx = desistencias[nome]
            mantem = historico[idx] if idx < len(historico) else True
            if mantem:
                aceitou[nome] = True
            else:
                desistencias[nome] += 1
                outro = next(n for n in maos if n != nome)
                compras_extra[outro] += 1
                if desistencias[nome] >= 2:
                    pontos[outro] += 1
                # se quem desistiu era o titular da prioridade e o outro já
                # havia aceitado antes, a titularidade vira.
                if nome == titular_prioridade and aceitou[outro]:
                    titular_prioridade = outro

    return ResultadoMulligan(
        maos_finais=maos,
        titular_prioridade=titular_prioridade,
        pontos=pontos,
        compras_extra=compras_extra,
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
    return jogador.heroi_ativo is None and not _tem_heroi_comum(jogador.mao)


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
