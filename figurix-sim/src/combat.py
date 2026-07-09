"""Combate: múltiplo, defesa de vantagem, item e derrota (seção 5 das regras).

Funções puras — recebem categorias/flags já resolvidos pelo chamador
(engine.py decide QUAIS condições são verdadeiras; aqui só calculamos
o número). Nenhum valor numérico é hardcoded: tudo vem do config.
"""
from __future__ import annotations

from dataclasses import dataclass

TIPOS_ATAQUE = ("principal", "secundario", "terciario")


def tem_vantagem(categoria_a: str, categoria_b: str, config: dict) -> bool:
    """True se `categoria_a` tem vantagem sobre `categoria_b` na roda cíclica."""
    roda = config["roda_vantagens"]
    n = len(roda)
    idx = roda.index(categoria_a)
    return roda[(idx + 1) % n] == categoria_b


def _bonus_aplica(tipo_ataque: str, restrito_a_principal: bool) -> bool:
    if tipo_ataque == "principal":
        return True
    return not restrito_a_principal


def calcular_multiplo(
    tipo_ataque: str,
    local_favorece_categoria_ataque: bool,
    mestre_do_tipo_presente: bool,
    categoria_heroi_atacante: str,
    categoria_heroi_defensor: str,
    config: dict,
) -> int:
    """Múltiplo = 1 + condições verdadeiras (seção 5)."""
    if tipo_ataque not in TIPOS_ATAQUE:
        raise ValueError(f"tipo_ataque inválido: {tipo_ataque!r}")

    multiplo = 1
    if local_favorece_categoria_ataque:
        multiplo += 1
    if mestre_do_tipo_presente and _bonus_aplica(tipo_ataque, config["mestre_so_principal"]):
        multiplo += 1
    if tem_vantagem(
        categoria_heroi_atacante, categoria_heroi_defensor, config
    ) and _bonus_aplica(tipo_ataque, config["vantagem_so_principal"]):
        multiplo += 1
    return multiplo


def defesa_vantagem_aplica(categoria_heroi_defensor: str, categoria_ataque_usado: str, config: dict) -> bool:
    """Defesa de -20: categoria do DEFENSOR com vantagem sobre a categoria do ATAQUE usado."""
    return tem_vantagem(categoria_heroi_defensor, categoria_ataque_usado, config)


@dataclass(frozen=True)
class ResultadoCombate:
    multiplo: int
    poder_com_item: int
    dano_bruto: int
    defesa_aplicada: bool
    dano_final: int


def resolver_ataque(
    poder_base: int,
    tipo_ataque: str,
    item_anexado: bool,
    local_favorece_categoria_ataque: bool,
    mestre_do_tipo_presente: bool,
    categoria_heroi_atacante: str,
    categoria_heroi_defensor: str,
    categoria_ataque_usado: str,
    config: dict,
) -> ResultadoCombate:
    """Resolve um ataque completo: múltiplo -> dano -> defesa de vantagem.

    `categoria_ataque_usado` é a categoria do poder efetivamente usado
    (principal/secundário/terciário do atacante), usada só para a defesa
    de vantagem (seção 13, premissa 1: compara-se defensor x categoria do
    ATAQUE, não a categoria "identidade" do herói atacante).
    `categoria_heroi_atacante`/`categoria_heroi_defensor` são as
    categorias-identidade (principal) de cada herói, usadas na condição
    de vantagem do múltiplo.
    """
    multiplo = calcular_multiplo(
        tipo_ataque=tipo_ataque,
        local_favorece_categoria_ataque=local_favorece_categoria_ataque,
        mestre_do_tipo_presente=mestre_do_tipo_presente,
        categoria_heroi_atacante=categoria_heroi_atacante,
        categoria_heroi_defensor=categoria_heroi_defensor,
        config=config,
    )

    bonus_item = config["bonus_item"] if (item_anexado and tipo_ataque == "principal") else 0
    poder_com_item = poder_base + bonus_item
    dano_bruto = poder_com_item * multiplo

    defesa_aplicada = defesa_vantagem_aplica(categoria_heroi_defensor, categoria_ataque_usado, config)
    dano_final = dano_bruto - (config["defesa_vantagem"] if defesa_aplicada else 0)
    dano_final = max(0, dano_final)

    return ResultadoCombate(
        multiplo=multiplo,
        poder_com_item=poder_com_item,
        dano_bruto=dano_bruto,
        defesa_aplicada=defesa_aplicada,
        dano_final=dano_final,
    )


def pontos_por_derrota(raridade: str, config: dict) -> int:
    from cards import pontos_da_raridade

    return pontos_da_raridade(raridade, config)
