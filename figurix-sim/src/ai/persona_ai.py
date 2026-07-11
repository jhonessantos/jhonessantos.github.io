"""PersonaAI — IA de regras parametrizável, base do catálogo de personas
(seção 4 da spec do simulador, ampliada a pedido do usuário: "no mínimo
15 personalidades diferentes de IA").

Em vez de escrever 15 classes quase idênticas, existe UMA classe cujo
comportamento é definido por um dict de parâmetros: a ORDEM de prioridade
das jogadas (uma lista de nomes de "passos"), limiares de barragem/Juiz,
quanto acumular de invocação antes de agir, viés de comeback, quais
guardiões preferir, etc. `ai/personas_catalogo.py` define os presets
nomeados (Agressiva, Defensiva, Focada em Juiz...) como combinações
desses parâmetros — e o usuário pode criar a 16ª, 17ª... só ajustando
os números, sem programar nada.

Cada "passo" é um método que tenta produzir uma Acao a partir do
contexto do turno, ou devolve None se não se aplica — igual à
HeuristicAI (nível 2), que continua existindo separadamente como a
persona "de referência" já testada nos milestones M4/M5.
"""
from __future__ import annotations

import random

import engine as eng
from cards import Guardiao, Juiz, Mestre

PARAMETROS_PADRAO = {
    "ordem_prioridades": [
        "repor_heroi",
        "acumular_invocacao",
        "juiz_vantagem",
        "ataque_letal",
        "evoluir",
        "mestre_proprio_tipo",
        "local_favoravel",
        "anexar_item",
        "guardiao_util",
        "ataque_nao_letal",
    ],
    "limiar_barragem_forca": 200,
    "limiar_juiz": 100,
    "reserva_alvo_invocacoes": 999,  # "sempre acumula o quanto puder" por padrão
    "nunca_barra": False,
    "barra_tudo_que_pode": False,
    "sempre_barra_tipos": ["Juiz"],  # tipos de carta sempre tratados como ameaça alta
    "guardioes_priorizados": [],  # lista de tipos preferidos (vazia = sem preferência)
    "vies_comeback": False,  # baixa os limiares (mais agressivo) quando está perdendo
    "limiar_comeback_pontos": 2,  # diferença de pontos a partir da qual o viés liga
    "aleatoriedade": 0.0,  # chance de ignorar a estratégia e jogar uma ação aleatória
    "mao_exigente": True,  # seção 3.4: recusa mão válida mas fraca (sem invocação nem herói forte)?
}

_TIPO_PARA_NOME_CLASSE = {Guardiao: "Guardiao", Mestre: "Mestre", Juiz: "Juiz"}


class PersonaAI:
    def __init__(self, parametros: dict | None = None, seed: int | None = None):
        self.p = {**PARAMETROS_PADRAO, **(parametros or {})}
        self.rng = random.Random(seed)
        self._passos = {
            "repor_heroi": self._passo_repor_heroi,
            "acumular_invocacao": self._passo_acumular_invocacao,
            "juiz_vantagem": self._passo_juiz_vantagem,
            "ataque_letal": self._passo_ataque_letal,
            "evoluir": self._passo_evoluir,
            "mestre_proprio_tipo": self._passo_mestre_proprio_tipo,
            "local_favoravel": self._passo_local_favoravel,
            "anexar_item": self._passo_anexar_item,
            "guardiao_util": self._passo_guardiao_util,
            "ataque_nao_letal": self._passo_ataque_nao_letal,
        }

    def escolher_acao(self, estado, jogador_nome: str, acoes_legais: list, config: dict):
        if any(a.tipo == "passar_barragem" for a in acoes_legais):
            return self._decidir_barragem(acoes_legais)
        if self.p["aleatoriedade"] > 0 and self.rng.random() < self.p["aleatoriedade"]:
            return self.rng.choice(acoes_legais)
        return self._decidir_turno(estado, jogador_nome, acoes_legais, config)

    def aceitar_mao(self, mao: list, jogador_nome: str, config: dict) -> bool:
        if not self.p["mao_exigente"]:
            return True
        return eng.mao_aceitavel_por_heuristica_padrao(mao)

    # ------------------------------------------------------------------
    # Barragem
    # ------------------------------------------------------------------

    def _decidir_barragem(self, acoes_legais: list):
        if self.p["nunca_barra"]:
            return eng.Acao("passar_barragem")
        opcoes = [a for a in acoes_legais if a.tipo == "barrar"]
        if self.p["barra_tudo_que_pode"]:
            candidatas = opcoes
        else:
            candidatas = [a for a in opcoes if self._ameaca_relevante(a.dados["alvo"])]
        if not candidatas:
            return eng.Acao("passar_barragem")
        candidatas.sort(key=lambda a: (len(a.dados["pagamento"]), a.dados["carta"].forca_impressa))
        return candidatas[0]

    def _ameaca_relevante(self, alvo) -> bool:
        nome_classe = _TIPO_PARA_NOME_CLASSE.get(type(alvo))
        if nome_classe in self.p["sempre_barra_tipos"]:
            return True
        return alvo.forca_impressa >= self.p["limiar_barragem_forca"]

    # ------------------------------------------------------------------
    # Turno normal — percorre `ordem_prioridades`, primeiro passo que
    # devolver uma ação vence.
    # ------------------------------------------------------------------

    def _decidir_turno(self, estado, jogador_nome: str, acoes_legais: list, config: dict):
        jogador = estado.jogadores[jogador_nome]
        adversario_nome = next(n for n in estado.jogadores if n != jogador_nome)
        adversario = estado.jogadores[adversario_nome]

        por_tipo: dict[str, list] = {}
        for a in acoes_legais:
            por_tipo.setdefault(a.tipo, []).append(a)

        ctx = _Contexto(estado, jogador_nome, jogador, adversario_nome, adversario, por_tipo, config)

        for passo in self.p["ordem_prioridades"]:
            acao = self._passos[passo](ctx)
            if acao is not None:
                return acao
        return eng.Acao("passar")

    def _limiar_juiz_efetivo(self, ctx) -> float:
        limiar = self.p["limiar_juiz"]
        if self.p["vies_comeback"] and self._esta_perdendo(ctx):
            limiar = min(limiar, 20)
        return limiar

    def _esta_perdendo(self, ctx) -> bool:
        return (ctx.adversario.pontos - ctx.jogador.pontos) >= self.p["limiar_comeback_pontos"]

    # ---- passos ----

    def _passo_repor_heroi(self, ctx):
        opcoes = ctx.por_tipo.get("trocar_heroi_derrotado")
        if not opcoes:
            return None
        return max(opcoes, key=lambda a: a.dados["carta"].forca_impressa)

    def _passo_acumular_invocacao(self, ctx):
        opcoes = ctx.por_tipo.get("colocar_invocacao")
        if not opcoes:
            return None
        if len(ctx.jogador.invocacoes_em_mesa) >= self.p["reserva_alvo_invocacoes"]:
            return None
        return opcoes[0]

    def _passo_juiz_vantagem(self, ctx):
        opcoes = ctx.por_tipo.get("invocar_juiz")
        if not opcoes or ctx.jogador.heroi_ativo is None or ctx.adversario.heroi_ativo is None:
            return None
        diferenca = ctx.adversario.heroi_ativo.forca_atual - ctx.jogador.heroi_ativo.forca_atual
        if diferenca > self._limiar_juiz_efetivo(ctx):
            return opcoes[0]
        return None

    def _passo_ataque_letal(self, ctx):
        opcoes = ctx.por_tipo.get("atacar")
        if not opcoes or ctx.adversario.heroi_ativo is None:
            return None
        ordem_preferencia = {"terciario": 0, "secundario": 1, "principal": 2}
        candidatos = sorted(opcoes, key=lambda a: ordem_preferencia[a.dados["tipo_ataque"]])
        for acao in candidatos:
            resultado = eng.prever_resultado_ataque(ctx.estado, ctx.jogador_nome, acao.dados["tipo_ataque"], ctx.config)
            if resultado.dano_final >= ctx.adversario.heroi_ativo.forca_atual:
                return acao
        return None

    def _passo_evoluir(self, ctx):
        opcoes = ctx.por_tipo.get("evoluir")
        if not opcoes:
            return None
        return max(opcoes, key=lambda a: a.dados["carta"].forca_impressa)

    def _passo_mestre_proprio_tipo(self, ctx):
        opcoes = ctx.por_tipo.get("invocar_mestre")
        if not opcoes or ctx.jogador.heroi_ativo is None:
            return None
        tipo_heroi = ctx.jogador.heroi_ativo.carta.variacao_id
        candidatos = [a for a in opcoes if a.dados["carta"].tipo_heroi_dominado == tipo_heroi]
        if not candidatos:
            return None
        return max(candidatos, key=lambda a: a.dados["carta"].forca_impressa)

    def _passo_local_favoravel(self, ctx):
        opcoes = ctx.por_tipo.get("colocar_local")
        if not opcoes or ctx.jogador.heroi_ativo is None:
            return None
        categoria_heroi = ctx.jogador.heroi_ativo.carta.categoria_principal
        candidatos = [a for a in opcoes if a.dados["carta"].categoria == categoria_heroi]
        if not candidatos:
            return None
        return self.rng.choice(candidatos)

    def _passo_anexar_item(self, ctx):
        opcoes = ctx.por_tipo.get("anexar_item")
        if not opcoes:
            return None
        return opcoes[0]

    def _passo_guardiao_util(self, ctx):
        opcoes = ctx.por_tipo.get("invocar_guardiao")
        if not opcoes:
            return None
        preferidos = self.p["guardioes_priorizados"]
        if preferidos:
            candidatos = [a for a in opcoes if a.dados["carta"].tipo in preferidos]
            if candidatos:
                return candidatos[0]
        return opcoes[0]

    def _passo_ataque_nao_letal(self, ctx):
        opcoes = ctx.por_tipo.get("atacar")
        if not opcoes:
            return None
        ordem_preferencia = {"terciario": 0, "secundario": 1, "principal": 2}
        melhor, melhor_dano = None, -1
        for acao in sorted(opcoes, key=lambda a: ordem_preferencia[a.dados["tipo_ataque"]]):
            resultado = eng.prever_resultado_ataque(ctx.estado, ctx.jogador_nome, acao.dados["tipo_ataque"], ctx.config)
            if resultado.dano_final > melhor_dano:
                melhor, melhor_dano = acao, resultado.dano_final
        return melhor


class _Contexto:
    __slots__ = ("estado", "jogador_nome", "jogador", "adversario_nome", "adversario", "por_tipo", "config")

    def __init__(self, estado, jogador_nome, jogador, adversario_nome, adversario, por_tipo, config):
        self.estado = estado
        self.jogador_nome = jogador_nome
        self.jogador = jogador
        self.adversario_nome = adversario_nome
        self.adversario = adversario
        self.por_tipo = por_tipo
        self.config = config
