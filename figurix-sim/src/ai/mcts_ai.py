"""Nível 3: MCTSAI — Monte Carlo Tree Search com rollouts pela HeuristicAI
(seção 4 da spec do simulador).

Abordagem (bandit de 1 nível + rollout, não uma árvore profunda completa
— tratável dado o fator de ramificação e o custo de simular o motor):
  1. Para a decisão atual, cada ação candidata é um braço de um bandit UCT.
  2. Cada simulação: clona o estado, DETERMINIZA a informação oculta (mão
     e deck do adversário são remisturados entre si — sabemos os tamanhos,
     não as cartas exatas), aplica a ação candidata e joga o resto da
     partida com a HeuristicAI (para os dois lados) até o fim ou um teto
     de turnos de rollout.
  3. O valor do resultado (vitória/derrota/heurística de posição, se o
     rollout não terminar a tempo) é retropropagado para a média do braço.
  4. Ao final, escolhe a ação mais visitada (padrão AlphaZero/UCT: robusto
     a variância melhor que "maior valor médio").

Determinização: como o motor não separa "o que EU vejo" de "o estado
completo" (ambas as mãos ficam no mesmo objeto EstadoPartida), a
determinização apenas re-embaralha mão+deck do ADVERSÁRIO entre si,
preservando os tamanhos exatos — a IA nunca lê a mão real do oponente,
só reamostra uma mão hipoteticamente consistente com o que é público
(tamanhos de mão/deck, cartas já descartadas/em campo).

`n_simulacoes` (200–1000) e `profundidade_rollout` são parâmetros de
COMPORTAMENTO DA IA, não regras do jogo — não entram em regras_v1.json.
"""
from __future__ import annotations

import math
import random

import engine as eng
import match
from ai.heuristic_ai import HeuristicAI


class MCTSAI:
    def __init__(
        self,
        n_simulacoes: int = 300,
        profundidade_rollout: int = 40,
        constante_uct: float = 1.4,
        seed: int | None = None,
    ):
        self.n_simulacoes = n_simulacoes
        self.profundidade_rollout = profundidade_rollout
        self.constante_uct = constante_uct
        self.rng = random.Random(seed)
        self.rollout_ai = HeuristicAI(seed=seed)

    def escolher_acao(self, estado, jogador_nome: str, acoes_legais: list, config: dict):
        if len(acoes_legais) == 1:
            return acoes_legais[0]

        # decisões de barragem usam um fluxo próprio (fora de _aplicar_acao,
        # ver match._resolver_entrada_auxiliar) — buscar a árvore aqui exigiria
        # simular a cadeia de contraturno inteira à parte; delegamos para a
        # política de rollout (HeuristicAI), que já sabe decidir isso.
        if any(a.tipo == "passar_barragem" for a in acoes_legais):
            return self.rollout_ai.escolher_acao(estado, jogador_nome, acoes_legais, config)

        candidatos = list(acoes_legais)
        n = len(candidatos)
        visitas = [0] * n
        soma_valor = [0.0] * n
        adversario_nome = next(nm for nm in estado.jogadores if nm != jogador_nome)

        for _ in range(self.n_simulacoes):
            i = self._selecionar_braco(visitas, soma_valor)
            valor = self._simular(estado, jogador_nome, adversario_nome, candidatos[i], config)
            visitas[i] += 1
            soma_valor[i] += valor

        # mais visitado vence; empate é desempatado pelo valor médio — sem
        # isso, com orçamento de simulações baixo perto do nº de candidatos
        # (comum aqui, dado o fator de ramificação), empates são frequentes
        # e "max" por posição sempre favoreceria o candidato de índice 0,
        # que por construção de acoes_legais() é sempre "passar".
        def media(k: int) -> float:
            return soma_valor[k] / visitas[k] if visitas[k] else 0.0

        melhor = max(range(n), key=lambda k: (visitas[k], media(k)))
        return candidatos[melhor]

    def aceitar_mao(self, mao: list, jogador_nome: str, config: dict) -> bool:
        # decisão binária pré-jogo, sem estado de tabuleiro pra simular
        # rollout em cima — busca completa seria overkill aqui, delegamos
        # pra mesma heurística usada na política de rollout.
        return self.rollout_ai.aceitar_mao(mao, jogador_nome, config)

    def _selecionar_braco(self, visitas: list[int], soma_valor: list[float]) -> int:
        total = sum(visitas)
        nao_visitados = [i for i, v in enumerate(visitas) if v == 0]
        if nao_visitados:
            return nao_visitados[0]

        def uct(i: int) -> float:
            media = soma_valor[i] / visitas[i]
            return media + self.constante_uct * math.sqrt(math.log(total) / visitas[i])

        return max(range(len(visitas)), key=uct)

    def _determinizar(self, estado, jogador_nome: str):
        """Reamostra mão+deck do adversário entre si (preservando os
        tamanhos). Cartas "presas" por um efeito em andamento — o herói
        titular do Guardião do Descanso, que precisa continuar
        localizável na mão até seu retorno (engine.resolver_retorno_descanso)
        — ficam de fora do reembaralhamento para não quebrar esse invariante."""
        clone = eng.clonar_estado(estado)
        adversario_nome = next(nm for nm in clone.jogadores if nm != jogador_nome)
        adversario = clone.jogadores[adversario_nome]

        presas = []
        if adversario.descanso is not None:
            presas.append(adversario.descanso.heroi_descansando.carta)
        ids_presas = {id(c) for c in presas}

        mao_livre = [c for c in adversario.mao if id(c) not in ids_presas]
        pool_desconhecido = mao_livre + list(adversario.deck)
        self.rng.shuffle(pool_desconhecido)
        n_mao_livre = len(mao_livre)
        adversario.mao = presas + pool_desconhecido[:n_mao_livre]
        adversario.deck = pool_desconhecido[n_mao_livre:]
        return clone

    def _simular(self, estado_real, jogador_nome: str, adversario_nome: str, acao_raiz, config: dict) -> float:
        clone = self._determinizar(estado_real, jogador_nome)
        ais = {jogador_nome: self.rollout_ai, adversario_nome: self.rollout_ai}
        contadores = {"invocacoes": 0, "locais": 0, "mestres": 0, "juizes": 0, "atacou": False}

        match.simular_acao_e_continuar(
            clone, jogador_nome, adversario_nome, acao_raiz, contadores, config, ais, self.rng,
            max_turnos_rollout=self.profundidade_rollout,
        )
        return self._avaliar_estado(clone, jogador_nome, config)

    def _avaliar_estado(self, estado, jogador_nome: str, config: dict) -> float:
        if estado.vencedor == jogador_nome:
            return 1.0
        if estado.vencedor is not None:
            return 0.0

        adversario_nome = next(nm for nm in estado.jogadores if nm != jogador_nome)
        jogador = estado.jogadores[jogador_nome]
        adversario = estado.jogadores[adversario_nome]

        diff_pontos = jogador.pontos - adversario.pontos
        forca_jogador = jogador.heroi_ativo.forca_atual if jogador.heroi_ativo else 0
        forca_adversario = adversario.heroi_ativo.forca_atual if adversario.heroi_ativo else 0
        diff_forca = forca_jogador - forca_adversario

        pontuacao = 0.5 + 0.04 * diff_pontos + 0.0003 * diff_forca
        return max(0.0, min(1.0, pontuacao))
