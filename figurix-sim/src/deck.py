"""Validação de deck (seção 2 das regras).

Regras verificadas:
  - Tamanho exato do deck (tamanho_deck).
  - Heróis: unicidade por variação, exceto raridades diferentes do MESMO
    participante (até 4, uma por nível de raridade base — especiais
    ocupam o slot da raridade equivalente).
  - Mestres: até `max_mesmo_mestre` do mesmo tipo dominado.
  - Guardiões: até `max_mesmo_guardiao` por "guardião específico"
    (identidade = tipo + categoria + raridade equivalente — a força não
    entra na identidade porque, no jogo real, uma carta impressa já fixa
    nome/categoria/raridade; aqui é a aproximação sintética mais próxima).
  - Juiz: até `max_juiz_deck` no deck inteiro.
  - Locais, Itens, Invocações: livres.
"""
from __future__ import annotations

from collections import defaultdict

from cards import Guardiao, Heroi, Invocacao, ItemHeroi, Juiz, Local, Mestre, raridade_equivalente


class DeckError(ValueError):
    """Levantado por `validar_deck_ou_lanca` quando o deck é inválido."""


def validar_deck(cartas: list, config: dict) -> list[str]:
    """Retorna lista de violações (vazia = deck válido)."""
    violacoes: list[str] = []

    tamanho_esperado = config["tamanho_deck"]
    if len(cartas) != tamanho_esperado:
        violacoes.append(
            f"Deck deve ter exatamente {tamanho_esperado} cartas, tem {len(cartas)}."
        )

    violacoes += _validar_herois(cartas, config)
    violacoes += _validar_mestres(cartas, config)
    violacoes += _validar_guardioes(cartas, config)
    violacoes += _validar_juiz(cartas, config)

    return violacoes


def deck_valido(cartas: list, config: dict) -> bool:
    return len(validar_deck(cartas, config)) == 0


def validar_deck_ou_lanca(cartas: list, config: dict) -> None:
    violacoes = validar_deck(cartas, config)
    if violacoes:
        raise DeckError("; ".join(violacoes))


def _validar_herois(cartas: list, config: dict) -> list[str]:
    violacoes = []
    por_variacao: dict[int, list[Heroi]] = defaultdict(list)
    for c in cartas:
        if isinstance(c, Heroi):
            por_variacao[c.variacao_id].append(c)

    for variacao_id, herois in por_variacao.items():
        participantes = {h.participante_id for h in herois}
        if len(participantes) > 1:
            violacoes.append(
                f"Variação {variacao_id}: cartas de participantes diferentes "
                f"({participantes}) não podem coexistir (unicidade por variação)."
            )
            continue

        if len(herois) > 4:
            violacoes.append(
                f"Variação {variacao_id}: {len(herois)} cópias, máximo absoluto é 4 "
                f"(uma por nível de raridade)."
            )

        slots_raridade: dict[str, list[Heroi]] = defaultdict(list)
        for h in herois:
            base = raridade_equivalente(h.raridade, config)
            slots_raridade[base].append(h)
        for base, grupo in slots_raridade.items():
            if len(grupo) > 1:
                violacoes.append(
                    f"Variação {variacao_id}: mais de 1 carta no slot de raridade "
                    f"'{base}' ({[c.raridade for c in grupo]}) — especial e base "
                    f"do mesmo participante não coexistem."
                )
    return violacoes


def _validar_mestres(cartas: list, config: dict) -> list[str]:
    violacoes = []
    max_mesmo_mestre = config["max_mesmo_mestre"]
    por_tipo: dict[int, int] = defaultdict(int)
    for c in cartas:
        if isinstance(c, Mestre):
            por_tipo[c.tipo_heroi_dominado] += 1
    for tipo, n in por_tipo.items():
        if n > max_mesmo_mestre:
            violacoes.append(
                f"Mestre do tipo {tipo}: {n} cópias, máximo é {max_mesmo_mestre}."
            )
    return violacoes


def _validar_guardioes(cartas: list, config: dict) -> list[str]:
    violacoes = []
    max_mesmo_guardiao = config["max_mesmo_guardiao"]
    por_combo: dict[tuple, int] = defaultdict(int)
    for c in cartas:
        if isinstance(c, Guardiao):
            combo = (c.tipo, c.categoria, raridade_equivalente(c.raridade, config))
            por_combo[combo] += 1
    for combo, n in por_combo.items():
        if n > max_mesmo_guardiao:
            violacoes.append(
                f"Guardião específico {combo}: {n} cópias, máximo é {max_mesmo_guardiao}."
            )
    return violacoes


def _validar_juiz(cartas: list, config: dict) -> list[str]:
    max_juiz_deck = config["max_juiz_deck"]
    n = sum(1 for c in cartas if isinstance(c, Juiz))
    if n > max_juiz_deck:
        return [f"Juiz: {n} cópias no deck, máximo é {max_juiz_deck}."]
    return []


def contar_por_tipo(cartas: list) -> dict[str, int]:
    tipos = {
        Heroi: "herois",
        Mestre: "mestres",
        Guardiao: "guardioes",
        Juiz: "juizes",
        ItemHeroi: "itens",
        Local: "locais",
        Invocacao: "invocacoes",
    }
    contagem: dict[str, int] = defaultdict(int)
    for c in cartas:
        contagem[tipos.get(type(c), "desconhecido")] += 1
    return dict(contagem)
