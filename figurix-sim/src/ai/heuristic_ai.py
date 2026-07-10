"""Nível 2: HeuristicAI — o "jogador certinho" (seção 4 da spec do simulador).

Prioridades, na ordem:
  1. Repor herói derrotado (grátis — sempre que possível).
  2. Acumular invocações em mesa sempre que possível (não custa nada e
     não encerra o turno — sem isso, ataques principal/secundário ficam
     ilegais por falta de pagamento e a IA se vê forçada a usar só o
     terciário fraco, perdendo justamente a vantagem de poder do deck).
  3. Usar o Juiz quando (força restante do adversário - própria) > limiar.
  4. Atacar quando o dano esperado derrota o herói inimigo (preferindo o
     ataque mais barato entre os que já matam: terciário > secundário > principal).
  5. Evoluir quando seguro (sempre que legal — restaura força cheia).
  6. Maximizar múltiplo antes de atacar: mestre do próprio tipo, depois
     local que favoreça a categoria do ataque principal.
  7. Anexar item (poder principal +10, sempre vale a pena).
  8. Guardiões utilitários (o que sobrar, sem ordem forte de preferência).
  9. Sem mais setup útil: ataque não-letal (chip damage) se disponível,
     senão passa.

Barragens: só barra ameaças cuja força impressa está acima de um limiar
(qualquer Juiz é sempre tratado como ameaça alta, por ser a "carta-furacão").

Os limiares abaixo são parâmetros de COMPORTAMENTO DA IA, não regras do
jogo — por isso vivem aqui, não em config/regras_v1.json (que é
exclusivamente para regras numéricas do jogo em si).
"""
from __future__ import annotations

import random

import engine as eng
from cards import Juiz


class HeuristicAI:
    def __init__(
        self,
        limiar_barragem_forca: int = 200,
        limiar_juiz: int = 100,
        seed: int | None = None,
    ):
        self.limiar_barragem_forca = limiar_barragem_forca
        self.limiar_juiz = limiar_juiz
        self.rng = random.Random(seed)

    def escolher_acao(self, estado, jogador_nome: str, acoes_legais: list, config: dict):
        tipos_presentes = {a.tipo for a in acoes_legais}
        if "passar_barragem" in tipos_presentes:
            return self._decidir_barragem(acoes_legais)
        return self._decidir_turno(estado, jogador_nome, acoes_legais, config)

    # ------------------------------------------------------------------
    # Barragem
    # ------------------------------------------------------------------

    def _decidir_barragem(self, acoes_legais: list):
        opcoes = [a for a in acoes_legais if a.tipo == "barrar"]
        ameacas = [a for a in opcoes if self._e_ameaca_relevante(a.dados["alvo"])]
        if not ameacas:
            return eng.Acao("passar_barragem")
        # entre as opções válidas, usa a carta mais barata, preservando as
        # mais fortes para ameaças futuras
        ameacas.sort(key=lambda a: (len(a.dados["pagamento"]), a.dados["carta"].forca_impressa))
        return ameacas[0]

    def _e_ameaca_relevante(self, alvo) -> bool:
        if isinstance(alvo, Juiz):
            return True
        return alvo.forca_impressa >= self.limiar_barragem_forca

    # ------------------------------------------------------------------
    # Turno normal
    # ------------------------------------------------------------------

    def _decidir_turno(self, estado, jogador_nome: str, acoes_legais: list, config: dict):
        jogador = estado.jogadores[jogador_nome]
        adversario_nome = next(n for n in estado.jogadores if n != jogador_nome)
        adversario = estado.jogadores[adversario_nome]

        por_tipo: dict[str, list] = {}
        for a in acoes_legais:
            por_tipo.setdefault(a.tipo, []).append(a)

        if por_tipo.get("trocar_heroi_derrotado"):
            return max(por_tipo["trocar_heroi_derrotado"], key=lambda a: a.dados["carta"].forca_impressa)

        # acumula invocações sempre que possível: colocar uma em mesa não custa
        # nada e não consome a única ação do turno (a fase de ações continua
        # até passar/atacar), então maximizar a mesa cedo só abre opções —
        # inclusive para os ataques principal/secundário, que sem invocação
        # disponível ficam ilegais e forçam um "chip damage" fraco demais
        # via terciário (perdendo justamente a vantagem de força do deck).
        if por_tipo.get("colocar_invocacao"):
            return por_tipo["colocar_invocacao"][0]

        if (
            por_tipo.get("invocar_juiz")
            and jogador.heroi_ativo is not None
            and adversario.heroi_ativo is not None
            and (adversario.heroi_ativo.forca_atual - jogador.heroi_ativo.forca_atual) > self.limiar_juiz
        ):
            return por_tipo["invocar_juiz"][0]

        ataque_letal = self._ataque_letal(estado, jogador_nome, por_tipo.get("atacar", []), config)
        if ataque_letal is not None:
            return ataque_letal

        if por_tipo.get("evoluir"):
            # prioriza evoluir para a maior força disponível (mais "seguro" ao restaurar força cheia)
            return max(por_tipo["evoluir"], key=lambda a: a.dados["carta"].forca_impressa)

        if por_tipo.get("invocar_mestre"):
            acao = self._mestre_do_proprio_tipo(por_tipo["invocar_mestre"], jogador)
            if acao is not None:
                return acao

        if por_tipo.get("colocar_local"):
            acao = self._local_favoravel(por_tipo["colocar_local"], jogador)
            if acao is not None:
                return acao

        if por_tipo.get("anexar_item"):
            return por_tipo["anexar_item"][0]

        if por_tipo.get("invocar_guardiao"):
            return por_tipo["invocar_guardiao"][0]

        if por_tipo.get("atacar"):
            return self._melhor_ataque_disponivel(estado, jogador_nome, por_tipo["atacar"], config)

        return eng.Acao("passar")

    def _ataque_letal(self, estado, jogador_nome, opcoes_atacar, config):
        if not opcoes_atacar:
            return None
        adversario_nome = next(n for n in estado.jogadores if n != jogador_nome)
        adversario = estado.jogadores[adversario_nome]
        if adversario.heroi_ativo is None:
            return None

        ordem_preferencia = {"terciario": 0, "secundario": 1, "principal": 2}
        candidatos = sorted(opcoes_atacar, key=lambda a: ordem_preferencia[a.dados["tipo_ataque"]])
        for acao in candidatos:
            resultado = eng.prever_resultado_ataque(estado, jogador_nome, acao.dados["tipo_ataque"], config)
            if resultado.dano_final >= adversario.heroi_ativo.forca_atual:
                return acao
        return None

    def _melhor_ataque_disponivel(self, estado, jogador_nome, opcoes_atacar, config):
        # sem chance de derrota: maximiza dano esperado (chip damage), preferindo
        # o mais barato em caso de empate (guarda invocações para reagir)
        ordem_preferencia = {"terciario": 0, "secundario": 1, "principal": 2}
        melhor, melhor_dano = None, -1
        for acao in sorted(opcoes_atacar, key=lambda a: ordem_preferencia[a.dados["tipo_ataque"]]):
            resultado = eng.prever_resultado_ataque(estado, jogador_nome, acao.dados["tipo_ataque"], config)
            if resultado.dano_final > melhor_dano:
                melhor, melhor_dano = acao, resultado.dano_final
        return melhor

    def _mestre_do_proprio_tipo(self, opcoes, jogador):
        if jogador.heroi_ativo is None:
            return None
        tipo_heroi = jogador.heroi_ativo.carta.variacao_id
        candidatos = [a for a in opcoes if a.dados["carta"].tipo_heroi_dominado == tipo_heroi]
        if not candidatos:
            return None
        return max(candidatos, key=lambda a: a.dados["carta"].forca_impressa)

    def _local_favoravel(self, opcoes, jogador):
        if jogador.heroi_ativo is None:
            return None
        categoria_heroi = jogador.heroi_ativo.carta.categoria_principal
        candidatos = [a for a in opcoes if a.dados["carta"].categoria == categoria_heroi]
        if not candidatos:
            return None
        return self.rng.choice(candidatos)
