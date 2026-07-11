"""Análise automática de um lote: tenta explicar em português, em texto
corrido, POR QUE um lado tende a vencer mais que o outro — a partir das
taxas de uso das mecânicas por papel (A/B) já calculadas em
`db.estatisticas_lote`. É uma heurística baseada em regras (comparação de
proporções), não um modelo de IA treinado, mas escrita pra "ler" como uma
análise, seguindo o que cada mecânica realmente significa nas regras:

  - Juiz (seção 9): cura o herói ativo, equaliza a força do herói
    adversário a favor de quem invoca, e remove itens/guardiões/mestres
    do oponente — invocar bem-sucedido é quase sempre uma vantagem forte.
  - Espiral de busca (seção 10): punitiva — cair nela significa ficar sem
    herói comum pra repor um derrotado, e pode custar pontos de graça ao
    adversário se o deck esgotar. Cair mais nela é sempre ruim.
  - Desistência de mão / mulligan (seção 3): quem desiste dá 1 compra
    extra ao adversário e, da 2ª vez em diante, 1 ponto de graça — desistir
    mais é sempre uma perda de vantagem para quem desiste.
"""
from __future__ import annotations

LIMIAR_VANTAGEM_CLARA = 0.15  # 15 pontos percentuais de diferença na taxa de vitórias
LIMIAR_VANTAGEM_ESMAGADORA = 0.35
LIMIAR_DIFERENCA_MECANICA = 0.10  # 10 p.p. de diferença numa taxa por papel já é notável
LIMIAR_COMEBACK_NOTAVEL = 0.25


def analisar_lote(stats: dict, resumo_vitorias: dict) -> list[str]:
    """Parágrafos (strings) explicando o resultado do lote — lista vazia
    se não houver partidas registradas ainda."""
    total = resumo_vitorias.get("total") or 0
    if not total or stats.get("total", 0) == 0:
        return []

    vit_a = resumo_vitorias["vitorias_a"]
    vit_b = resumo_vitorias["vitorias_b"]
    indecisas = resumo_vitorias["indecisas"]
    pct_a, pct_b = vit_a / total, vit_b / total
    diferenca = pct_a - pct_b  # positivo = A domina

    if abs(diferenca) < LIMIAR_VANTAGEM_CLARA:
        return [
            f"O confronto ficou equilibrado: A venceu {vit_a} partida(s) ({pct_a:.0%}) e B venceu "
            f"{vit_b} ({pct_b:.0%})" + (f", com {indecisas} indecisa(s)" if indecisas else "") +
            ". Nenhum dos lados teve uma vantagem clara nesse lote."
        ]

    dominante, dominado = ("A", "B") if diferenca > 0 else ("B", "A")
    pct_dominante, pct_dominado = (pct_a, pct_b) if diferenca > 0 else (pct_b, pct_a)
    intensidade = "esmagadora" if abs(diferenca) >= LIMIAR_VANTAGEM_ESMAGADORA else "clara"

    paragrafos = [
        f"O lado {dominante} teve uma vantagem {intensidade}: venceu {pct_dominante:.0%} das partidas contra "
        f"{pct_dominado:.0%} do lado {dominado}" + (f" ({indecisas} indecisa(s))" if indecisas else "") + "."
    ]

    explicou_com_mecanica = False

    pontos_dominante = stats["pontos"][f"media_pontos_{dominante.lower()}"]
    pontos_dominado = stats["pontos"][f"media_pontos_{dominado.lower()}"]
    if pontos_dominante is not None and pontos_dominado is not None:
        diff_pontos = pontos_dominante - pontos_dominado
        if diff_pontos >= 1:
            paragrafos.append(
                f"Isso também aparece na pontuação: em média o lado {dominante} terminou com {pontos_dominante:.1f} "
                f"pontos contra {pontos_dominado:.1f} do lado {dominado} — uma diferença média de "
                f"{diff_pontos:.1f} pontos por partida."
            )

    juiz_dominante = stats["taxa_juiz"][dominante.lower()]
    juiz_dominado = stats["taxa_juiz"][dominado.lower()]
    if juiz_dominante - juiz_dominado >= LIMIAR_DIFERENCA_MECANICA:
        explicou_com_mecanica = True
        paragrafos.append(
            f"O lado {dominante} invocou o Juiz com bem mais frequência ({juiz_dominante:.0%} das partidas, contra "
            f"{juiz_dominado:.0%} do lado {dominado}) — o Juiz cura o herói ativo, equaliza a força do herói "
            f"adversário a seu favor e ainda remove itens, guardiões e mestre do oponente, então essa diferença "
            f"sozinha já explica boa parte da vantagem."
        )

    espiral_dominante = stats["taxa_espiral"][dominante.lower()]
    espiral_dominado = stats["taxa_espiral"][dominado.lower()]
    if espiral_dominado - espiral_dominante >= LIMIAR_DIFERENCA_MECANICA:
        explicou_com_mecanica = True
        paragrafos.append(
            f"O lado {dominado} caiu na espiral de busca de herói com bem mais frequência "
            f"({espiral_dominado:.0%} das partidas, contra {espiral_dominante:.0%} do lado {dominante}) — ficar "
            f"sem herói comum na mão pra repor um herói derrotado é uma das piores posições do jogo (pode até "
            f"custar pontos de graça se o deck esgotar), então essa fragilidade ajuda a explicar a derrota."
        )

    mull_dominante = stats["taxa_mulligan_desistencia"][dominante.lower()]
    mull_dominado = stats["taxa_mulligan_desistencia"][dominado.lower()]
    if mull_dominado - mull_dominante >= LIMIAR_DIFERENCA_MECANICA:
        explicou_com_mecanica = True
        paragrafos.append(
            f"O lado {dominado} também desistiu da mão inicial com mais frequência ({mull_dominado:.0%} das "
            f"partidas, contra {mull_dominante:.0%} do lado {dominante}) — cada desistência dá uma compra extra "
            f"ao adversário e, a partir da segunda, 1 ponto de graça, então essas desistências provavelmente "
            f"somaram vantagem extra para o lado {dominante}."
        )

    if not explicou_com_mecanica:
        paragrafos.append(
            "As taxas de uso do Juiz, espiral de busca e desistência de mão ficaram parecidas entre os dois "
            "lados — a vantagem provavelmente vem de fatores que este relatório não mede diretamente (a força "
            "específica das cartas do deck, decisões jogada a jogada da IA, etc.)."
        )

    taxa_comeback = stats.get("taxa_comeback")
    if taxa_comeback is not None and taxa_comeback >= LIMIAR_COMEBACK_NOTAVEL:
        paragrafos.append(
            f"Vale notar que em {taxa_comeback:.0%} das partidas o vencedor esteve em desvantagem grande em "
            f"algum momento antes de virar o placar — parte da vantagem do lado {dominante} pode vir de "
            f"conseguir reverter jogos difíceis, não só de dominar do início ao fim."
        )

    return paragrafos
