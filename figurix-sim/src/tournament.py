"""N partidas, pareamentos e seeds fixas (seção 5 da spec do simulador).

`rodar_torneio` roda partidas entre dois "papéis" lógicos, A e B (cada
um definido por uma fábrica de deck + fábrica de IA), com seeds
determinísticas. Por padrão alterna qual papel joga como P1/P2 a cada
partida, para que a métrica de vantagem do primeiro jogador (seção 5.7)
não seja contaminada por qual papel tende a jogar em qual posição.

Não retemos o log completo de cada partida (inviável em memória para
milhares de partidas) — extraímos um resumo de uso de mecânicas por
partida logo após jogá-la.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from match import jogar_partida


@dataclass
class ResumoPartida:
    vencedor_papel: str | None  # "A" | "B" | None (empate/limite de segurança)
    primeiro_papel: str  # "A" | "B" — quem agiu primeiro
    turnos: int
    rodadas: int
    pontos_a: int
    pontos_b: int
    teve_comeback: bool = False  # vencedor esteve >= limiar de pontos atrás em algum momento
    juiz_papeis: frozenset = frozenset()  # papéis ("A"/"B") que invocaram o Juiz com sucesso
    eventos: dict = field(default_factory=dict)


def _resumir_eventos(log: list) -> dict:
    contagem: dict[str, int] = {}
    for evento in log:
        acao = evento.get("acao")
        if acao is None or acao == "pontos":
            continue
        if acao == "atacar":
            chave = f"atacar_{evento['tipo_ataque']}"
        elif acao == "guardiao_efeito":
            chave = f"guardiao_{evento['tipo']}"
        elif acao == "barragem_cadeia":
            contagem["barragem_profundidade_soma"] = (
                contagem.get("barragem_profundidade_soma", 0) + evento["profundidade"]
            )
            chave = "barragem_cadeia"
        else:
            chave = acao
        contagem[chave] = contagem.get(chave, 0) + 1
    return contagem


def _juiz_jogado_por(log: list, papel_de) -> frozenset:
    papeis = set()
    for evento in log:
        if evento.get("acao") == "invocar_juiz" and evento.get("sobreviveu"):
            papeis.add(papel_de(evento["turno_de"]))
    return frozenset(papeis)


def _teve_comeback(log: list, papel_de, vencedor_papel: str | None, limiar: int = 4) -> bool:
    """Métrica 6: o vencedor chegou a estar >= `limiar` pontos atrás?"""
    if vencedor_papel is None:
        return False
    maior_deficit = 0
    for evento in log:
        if evento.get("acao") != "pontos":
            continue
        pontos_por_papel = {
            papel_de(fisico): pontos for fisico, pontos in evento.items() if fisico in ("P1", "P2")
        }
        pontos_vencedor = pontos_por_papel.get(vencedor_papel, 0)
        pontos_adversario = sum(v for k, v in pontos_por_papel.items() if k != vencedor_papel)
        maior_deficit = max(maior_deficit, pontos_adversario - pontos_vencedor)
    return maior_deficit >= limiar


def rodar_torneio(
    config: dict,
    criar_deck_a,
    criar_deck_b,
    criar_ai_a,
    criar_ai_b,
    n_partidas: int,
    seed_base: int = 0,
    alternar_lados: bool = True,
) -> list[ResumoPartida]:
    """Roda `n_partidas` partidas entre os papéis A e B.

    `criar_deck_a`/`criar_deck_b`/`criar_ai_a`/`criar_ai_b`: callables que
    recebem um `seed: int` e devolvem um deck (list[Carta]) ou uma IA nova
    — chamados uma vez por partida, garantindo reprodutibilidade total a
    partir de `seed_base`.
    """
    resumos = []
    for i in range(n_partidas):
        seed = seed_base + i
        deck_a, deck_b = criar_deck_a(seed), criar_deck_b(seed)
        ai_a, ai_b = criar_ai_a(seed), criar_ai_b(seed)

        papel_e_p1 = "A" if not alternar_lados or i % 2 == 0 else "B"
        if papel_e_p1 == "A":
            deck1, deck2, ai1, ai2 = deck_a, deck_b, ai_a, ai_b
        else:
            deck1, deck2, ai1, ai2 = deck_b, deck_a, ai_b, ai_a

        resultado = jogar_partida(config, deck1, deck2, ai1, ai2, seed=seed)

        def papel_de(fisico: str | None) -> str | None:
            if fisico is None:
                return None
            eh_p1 = fisico == "P1"
            return papel_e_p1 if eh_p1 else ("B" if papel_e_p1 == "A" else "A")

        pontos_p1, pontos_p2 = resultado.pontos["P1"], resultado.pontos["P2"]
        pontos_a, pontos_b = (pontos_p1, pontos_p2) if papel_e_p1 == "A" else (pontos_p2, pontos_p1)
        vencedor_papel = papel_de(resultado.vencedor)

        resumos.append(
            ResumoPartida(
                vencedor_papel=vencedor_papel,
                primeiro_papel=papel_de(resultado.primeiro_jogador),
                turnos=resultado.turnos,
                rodadas=resultado.rodadas,
                pontos_a=pontos_a,
                pontos_b=pontos_b,
                teve_comeback=_teve_comeback(resultado.log, papel_de, vencedor_papel),
                juiz_papeis=_juiz_jogado_por(resultado.log, papel_de),
                eventos=_resumir_eventos(resultado.log),
            )
        )
    return resumos
