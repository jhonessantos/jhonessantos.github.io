"""1 partida: preparação, loop de turnos e log estruturado (seções 3 e 4 das regras).

Orquestra engine.py (estado + regras), combat.py (dano) e chains.py
(barragens) usando duas IAs intercambiáveis (interface em ai/base.py).

Simplificações de escopo assumidas nesta integração (documentadas para
os relatórios de milestone):
  - Recusa voluntária de mão aceitável (seção 3.4) não é simulada: um
    jogador só faz mulligan quando a mão não tem herói comum algum.
  - A carta inicial (herói comum) e a isca do Guardião do Descanso são
    escolhidas aleatoriamente, não estrategicamente — refinável nas IAs
    de nível 2/3.
  - A "limpeza seletiva" do Juiz usa uma escolha aleatória (50% por
    carta elegível) como baseline; heurísticas mais espertas entram no
    M4 (HeuristicAI) via troca dessa função.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

import engine as eng
from cards import Guardiao, Heroi, Juiz, Mestre, duracao_mestre_da_raridade, duracao_portais_da_raridade, pontos_da_raridade
from chains import ElementoCadeia, pode_barrar, resolver_cadeia
from combat import resolver_ataque

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

MAX_TURNOS_SEGURANCA = 1500
MAX_ACOES_POR_TURNO_SEGURANCA = 200
MAX_TENTATIVAS_MULLIGAN = 50


@dataclass
class ResultadoPartida:
    vencedor: str | None  # None = atingiu o limite de segurança sem decisão (deveria ser raríssimo)
    turnos: int
    rodadas: int
    pontos: dict
    log: list


def configurar_partida(config: dict, deck1: list, deck2: list, nome1: str = "P1", nome2: str = "P2", seed=None):
    rng = random.Random(seed)
    j1 = eng.EstadoJogador(nome=nome1, deck=list(deck1))
    j2 = eng.EstadoJogador(nome=nome2, deck=list(deck2))
    estado = eng.EstadoPartida(jogadores={nome1: j1, nome2: j2}, rodada=1)

    vencedor_par_ou_impar = rng.choice([nome1, nome2])
    perdedor = nome2 if vencedor_par_ou_impar == nome1 else nome1
    titular = _preparar_maos_iniciais(estado, [perdedor, vencedor_par_ou_impar], vencedor_par_ou_impar, config, rng)

    cartas_iniciais = {}
    for nome, jogador in estado.jogadores.items():
        comuns = [c for c in jogador.mao if isinstance(c, Heroi) and c.raridade == "comum"]
        escolhida = rng.choice(comuns)
        jogador.mao.remove(escolhida)
        cartas_iniciais[nome] = escolhida

    primeiro = eng.quem_age_primeiro(
        (nome1, cartas_iniciais[nome1]), (nome2, cartas_iniciais[nome2]), titular_prioridade=titular
    )
    segundo = nome2 if primeiro == nome1 else nome1
    for nome, carta in cartas_iniciais.items():
        estado.jogadores[nome].heroi_ativo = eng.EstadoHeroiCampo.entrar_em_campo(carta, rodada_atual=1)

    estado.ordem_turno = [primeiro, segundo]
    estado.turno_de = primeiro
    return estado


def _preparar_maos_iniciais(estado, ordem_decisao, titular_inicial, config, rng):
    perdedor, vencedor = ordem_decisao
    titular = titular_inicial
    desistencias = {perdedor: 0, vencedor: 0}
    aceitas = set()
    tentativas = 0

    while len(aceitas) < 2 and tentativas < MAX_TENTATIVAS_MULLIGAN:
        tentativas += 1
        for nome in (perdedor, vencedor):
            if nome in aceitas:
                continue
            jogador = estado.jogadores[nome]
            rng.shuffle(jogador.deck)
            n = min(config["mao_inicial"], len(jogador.deck))
            jogador.mao = [jogador.deck.pop() for _ in range(n)]

            if any(isinstance(c, Heroi) and c.raridade == "comum" for c in jogador.mao):
                aceitas.add(nome)
                continue

            jogador.deck.extend(jogador.mao)
            jogador.mao = []
            desistencias[nome] += 1
            outro_nome = perdedor if nome == vencedor else vencedor
            outro = estado.jogadores[outro_nome]
            if outro.deck:
                outro.mao.append(outro.deck.pop())
            if desistencias[nome] >= 2:
                outro.pontos += 1
            if nome == titular and outro_nome in aceitas:
                titular = outro_nome

    return titular


def jogar_partida(config: dict, deck1: list, deck2: list, ai1, ai2, nome1="P1", nome2="P2", seed=None) -> ResultadoPartida:
    rng = random.Random(seed)
    estado = configurar_partida(config, deck1, deck2, nome1, nome2, seed=rng.randrange(2**31))
    ais = {nome1: ai1, nome2: ai2}

    turnos = 0
    while estado.vencedor is None and turnos < MAX_TURNOS_SEGURANCA:
        jogar_turno(estado, ais, config, rng)
        turnos += 1

    return ResultadoPartida(
        vencedor=estado.vencedor,
        turnos=turnos,
        rodadas=estado.rodada,
        pontos={nome: j.pontos for nome, j in estado.jogadores.items()},
        log=estado.log,
    )


def jogar_turno(estado: eng.EstadoPartida, ais: dict, config: dict, rng: random.Random) -> str | None:
    jogador_nome = estado.turno_de
    adversario_nome = next(n for n in estado.jogadores if n != jogador_nome)
    jogador = estado.jogadores[jogador_nome]
    adversario = estado.jogadores[adversario_nome]

    # 1. Compra
    n_compra = config["compra_por_turno"]
    if config["compra_dupla_mao_baixa"] and len(jogador.mao) <= config["limiar_mao_baixa"]:
        n_compra = 2
    for _ in range(n_compra):
        if jogador.deck:
            jogador.mao.append(jogador.deck.pop())

    # 2. Espiral de busca de herói (seção 10)
    if jogador.heroi_ativo is None and eng.em_busca_de_heroi(jogador):
        espiral = estado.espirais.setdefault(jogador_nome, eng.EstadoEspiral(jogador_em_busca=jogador_nome))
        vencedor = eng.passo_espiral(estado, jogador, adversario, espiral, config)
        if vencedor:
            return vencedor
        if not eng.em_busca_de_heroi(jogador):
            estado.espirais.pop(jogador_nome, None)
    else:
        estado.espirais.pop(jogador_nome, None)

    # 3. Ações
    contadores = {"invocacoes": 0, "locais": 0, "mestres": 0, "juizes": 0, "atacou": False}
    for _ in range(MAX_ACOES_POR_TURNO_SEGURANCA):
        legais = eng.acoes_legais(estado, jogador_nome, contadores, config)
        acao = ais[jogador_nome].escolher_acao(estado, legais)
        if acao.tipo == "passar":
            break
        _aplicar_acao(estado, jogador_nome, adversario_nome, acao, contadores, config, ais, rng)
        if _verificar_fim_de_jogo(estado, config):
            return estado.vencedor
        if acao.tipo == "atacar":
            break

    # 4. Fim de turno / fim de rodada
    if jogador_nome == estado.ordem_turno[1]:
        estado.rodada += 1
        _fim_de_rodada(estado, config)
        if _verificar_fim_de_jogo(estado, config):
            return estado.vencedor
    estado.turno_de = adversario_nome
    return None


def _verificar_fim_de_jogo(estado: eng.EstadoPartida, config: dict) -> bool:
    for nome, jogador in estado.jogadores.items():
        if jogador.pontos >= config["pontos_vitoria"]:
            estado.vencedor = nome
            return True
    return False


def _aplicar_acao(estado, jogador_nome, adversario_nome, acao, contadores, config, ais, rng):
    jogador = estado.jogadores[jogador_nome]
    adversario = estado.jogadores[adversario_nome]
    tipo, dados = acao.tipo, acao.dados

    if tipo == "trocar_heroi_derrotado":
        carta = dados["carta"]
        jogador.mao.remove(carta)
        jogador.heroi_ativo = eng.EstadoHeroiCampo.entrar_em_campo(carta, estado.rodada)
        return

    if tipo == "colocar_invocacao":
        carta = dados["carta"]
        jogador.mao.remove(carta)
        jogador.invocacoes_em_mesa.append(carta)
        contadores["invocacoes"] += 1
        return

    if tipo == "colocar_local":
        carta = dados["carta"]
        jogador.mao.remove(carta)
        if estado.local is not None:
            jogador.descarte.append(estado.local.carta)
        estado.local = eng.EstadoLocal(carta=carta)
        contadores["locais"] += 1
        return

    if tipo == "anexar_item":
        carta = dados["carta"]
        jogador.mao.remove(carta)
        jogador.heroi_ativo.item_anexado = carta
        return

    if tipo == "evoluir":
        carta_destino, pagamento = dados["carta"], dados["pagamento"]
        item_raro = (
            jogador.heroi_ativo.item_anexado is not None
            and jogador.heroi_ativo.item_anexado.raridade == "rara"
        )
        carta_anterior = jogador.heroi_ativo.carta
        novo_campo = eng.aplicar_evolucao(jogador.heroi_ativo, carta_destino, estado.rodada, item_raro, config)
        jogador.mao.remove(carta_destino)
        jogador.descarte.append(carta_anterior)
        _descartar_pagamento(jogador, pagamento)
        jogador.heroi_ativo = novo_campo
        return

    if tipo in ("invocar_guardiao", "invocar_mestre", "invocar_juiz"):
        carta, pagamento = dados["carta"], dados["pagamento"]
        jogador.mao.remove(carta)
        _descartar_pagamento(jogador, pagamento)
        if tipo == "invocar_mestre":
            contadores["mestres"] += 1
        elif tipo == "invocar_juiz":
            contadores["juizes"] += 1

        sobreviveu = _resolver_entrada_auxiliar(estado, jogador_nome, adversario_nome, ais, carta, config)
        eng.registrar_evento(estado, acao=tipo, sobreviveu=sobreviveu)
        if not sobreviveu:
            return

        if tipo == "invocar_guardiao":
            _aplicar_entrada_guardiao(estado, jogador, carta, config, rng)
        elif tipo == "invocar_mestre":
            if jogador.mestre is not None:
                jogador.descarte.append(jogador.mestre.carta)
            jogador.mestre = eng.EstadoMestreCampo(
                carta=carta, rodadas_restantes=duracao_mestre_da_raridade(carta.raridade, config)
            )
        elif tipo == "invocar_juiz":
            escolhas = _escolher_remocao_juiz(jogador, adversario, estado, rng)
            eng.resolver_entrada_juiz(jogador, adversario, estado, escolhas, config)
            eng.juiz_vai_para_descarte(carta, jogador)
        return

    if tipo == "atacar":
        _resolver_ataque_no_turno(estado, jogador_nome, adversario_nome, dados, config)
        contadores["atacou"] = True
        return

    raise ValueError(f"Ação desconhecida: {tipo!r}")


def _descartar_pagamento(jogador, pagamento):
    for inv in pagamento:
        jogador.invocacoes_em_mesa.remove(inv)
        jogador.descarte.append(inv)


def _resolver_entrada_auxiliar(estado, jogador_nome, adversario_nome, ais, carta_base, config) -> bool:
    """Abre a janela de barragem (pilha estilo MTG stack). Retorna True se a
    carta base sobreviveu à cadeia (isto é, deve ter seu efeito aplicado)."""
    pilha = [ElementoCadeia(carta=carta_base, jogador=jogador_nome)]
    respondente, declarante = adversario_nome, jogador_nome

    while True:
        resp_estado = estado.jogadores[respondente]
        alvo_atual = pilha[-1].carta
        opcoes = []
        for c in resp_estado.mao:
            if isinstance(c, (Guardiao, Mestre, Juiz)) and pode_barrar(c, alvo_atual, config):
                pagamento = eng.pagar_barragem(resp_estado.invocacoes_em_mesa, c.categoria, config)
                if pagamento is not None:
                    opcoes.append(eng.Acao("barrar", {"carta": c, "pagamento": pagamento}))
        opcoes.append(eng.Acao("passar_barragem"))

        escolha = ais[respondente].escolher_acao(estado, opcoes)
        if escolha.tipo != "barrar":
            break

        carta, pagamento = escolha.dados["carta"], escolha.dados["pagamento"]
        resp_estado.mao.remove(carta)
        _descartar_pagamento(resp_estado, pagamento)
        pilha.append(ElementoCadeia(carta=carta, jogador=respondente))
        respondente, declarante = declarante, respondente

    resultado = resolver_cadeia(pilha)
    dono_por_carta = {id(e.carta): e.jogador for e in pilha}
    for carta in resultado.descartes:
        estado.jogadores[dono_por_carta[id(carta)]].descarte.append(carta)

    return resultado.sobrevivente is not None and resultado.sobrevivente.carta is carta_base


def _aplicar_entrada_guardiao(estado, jogador, carta, config, rng):
    if carta.tipo == "Portais":
        if estado.local is not None:
            estado.local.portais_rodadas_restantes = duracao_portais_da_raridade(carta.raridade, config)
            estado.local.portais_raridade = carta.raridade
        jogador.descarte.append(carta)
    elif carta.tipo == "Restauracao":
        eng.aplicar_restauracao(jogador.heroi_ativo, carta, config)
        jogador.descarte.append(carta)
    elif carta.tipo == "Escudos":
        jogador.guardioes.append(eng.EstadoGuardiaoCampo(carta=carta, forca_atual=carta.forca_impressa, rodadas_restantes=1))
    elif carta.tipo == "Oprimidos":
        jogador.guardioes.append(eng.EstadoGuardiaoCampo(carta=carta, forca_atual=carta.forca_impressa, rodadas_restantes=None))
    elif carta.tipo == "Descanso":
        comuns = [c for c in jogador.mao if isinstance(c, Heroi) and c.raridade == "comum"]
        if comuns:
            isca = rng.choice(comuns)
            eng.aplicar_descanso(jogador, isca, estado.rodada, config)
        jogador.descarte.append(carta)


def _escolher_remocao_juiz(jogador, adversario, estado, rng) -> list:
    """Baseline aleatório (50% por carta elegível) — refinável por IAs melhores."""
    candidatos = []
    if adversario.heroi_ativo is not None and adversario.heroi_ativo.item_anexado is not None:
        candidatos.append(adversario.heroi_ativo.item_anexado)
    candidatos.extend(g.carta for g in adversario.guardioes)
    if adversario.mestre is not None:
        candidatos.append(adversario.mestre.carta)
    if estado.local is not None:
        candidatos.append(estado.local.carta)
    return [c for c in candidatos if rng.random() < 0.5]


def _resolver_ataque_no_turno(estado, jogador_nome, adversario_nome, dados, config):
    jogador = estado.jogadores[jogador_nome]
    adversario = estado.jogadores[adversario_nome]
    tipo_ataque, pagamento = dados["tipo_ataque"], dados["pagamento"]
    _descartar_pagamento(jogador, pagamento)

    atacante_carta = jogador.heroi_ativo.carta
    defensor_campo = adversario.heroi_ativo
    poder_base = getattr(atacante_carta, PODER_POR_TIPO_ATAQUE[tipo_ataque])
    categoria_ataque_usado = getattr(atacante_carta, CATEGORIA_POR_TIPO_ATAQUE[tipo_ataque])
    local_favorece = estado.local is not None and estado.local.carta.categoria == categoria_ataque_usado
    mestre_presente = (
        jogador.mestre is not None and jogador.mestre.carta.tipo_heroi_dominado == atacante_carta.variacao_id
    )
    item_anexado = jogador.heroi_ativo.item_anexado is not None

    resultado = resolver_ataque(
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
    eng.registrar_evento(
        estado, acao="atacar", tipo_ataque=tipo_ataque, multiplo=resultado.multiplo, dano=resultado.dano_final
    )
    _aplicar_dano(estado, jogador_nome, adversario_nome, resultado.dano_final, config)


def _aplicar_dano(estado, atacante_nome, defensor_nome, dano, config):
    atacante = estado.jogadores[atacante_nome]
    defensor = estado.jogadores[defensor_nome]
    campo = defensor.heroi_ativo
    if campo is None or dano <= 0:
        return

    escudo = next(
        (g for g in defensor.guardioes if g.carta.tipo == "Escudos" and g.rodadas_restantes and g.rodadas_restantes > 0),
        None,
    )
    dano_ao_heroi = dano
    if escudo is not None:
        absorvido = min(dano, escudo.forca_atual)
        escudo.forca_atual -= absorvido
        dano_ao_heroi = dano - absorvido
        if escudo.forca_atual <= 0:
            defensor.guardioes.remove(escudo)
            defensor.descarte.append(escudo.carta)

    campo.forca_atual = max(0, campo.forca_atual - dano_ao_heroi)
    campo.dano_acumulado_rodada += dano_ao_heroi

    if campo.forca_atual <= 0:
        pontos = pontos_da_raridade(campo.carta.raridade, config)
        atacante.pontos += pontos
        defensor.descarte.append(campo.carta)
        if campo.item_anexado is not None:
            defensor.descarte.append(campo.item_anexado)
        defensor.heroi_ativo = None
        if defensor.descanso is not None and defensor.descanso.heroi_isca is campo:
            defensor.descanso = None


def _fim_de_rodada(estado: eng.EstadoPartida, config: dict):
    for nome, jogador in estado.jogadores.items():
        adversario_nome = next(n for n in estado.jogadores if n != nome)

        if jogador.mestre is not None:
            jogador.mestre.rodadas_restantes -= 1
            if jogador.mestre.rodadas_restantes <= 0:
                jogador.descarte.append(jogador.mestre.carta)
                jogador.mestre = None

        restantes = []
        for g in jogador.guardioes:
            if g.carta.tipo == "Oprimidos" and jogador.heroi_ativo is not None:
                dano_convertido = eng.resolver_oprimidos(jogador.heroi_ativo, guardiao_ativo=True, config=config)
                if dano_convertido > 0:
                    _aplicar_dano(estado, nome, adversario_nome, dano_convertido, config)
            if g.rodadas_restantes is not None:
                g.rodadas_restantes -= 1
                if g.rodadas_restantes <= 0:
                    jogador.descarte.append(g.carta)
                    continue
            restantes.append(g)
        jogador.guardioes = restantes

        if estado.local is not None and estado.local.portais_rodadas_restantes > 0:
            estado.local.portais_rodadas_restantes -= 1

        if jogador.descanso is not None and estado.rodada == jogador.descanso.rodada_retorno:
            adversario = estado.jogadores[adversario_nome]
            if jogador.heroi_ativo is jogador.descanso.heroi_isca:
                eng.resolver_retorno_descanso(jogador, adversario, isca_foi_derrotada=False, config=config)
            else:
                jogador.descanso = None
