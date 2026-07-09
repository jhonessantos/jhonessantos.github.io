"""Gerador sintético de cartas (não usamos as cartas reais do jogo).

Produz pools controlados de cartas para os experimentos, seguindo a seção 3
da spec do simulador. Toda faixa numérica (força, poderes, pontos, custos)
vem do config — nada hardcoded aqui.
"""
from __future__ import annotations

import random

from cards import (
    Guardiao,
    Heroi,
    Invocacao,
    ItemHeroi,
    Juiz,
    Local,
    Mestre,
    eh_especial,
    poderes_da_raridade,
)

N_VARIACOES_OFICIAIS = 105


def categorias_da_variacao(variacao_id: int, config: dict) -> tuple[str, str, str]:
    """Categorias fixas (principal/secundária/terciária) de uma variação.

    Determinístico: cada variação/participante tem 3 características fixas,
    distintas entre si (seção 1). Usamos offsets módulo 5 para garantir isso.
    """
    categorias = config["categorias"]
    n = len(categorias)
    i = variacao_id % n
    return categorias[i], categorias[(i + 1) % n], categorias[(i + 2) % n]


def _valores_forca(raridade: str, config: dict) -> list[int]:
    passo = config["forca_passo"]
    if eh_especial(raridade, config):
        lo, hi = config["forca_especiais"][raridade]
    else:
        lo, hi = config["forca_por_raridade"][raridade]
    return list(range(lo, hi + 1, passo))


def forca_aleatoria(raridade: str, config: dict, rng: random.Random) -> int:
    return rng.choice(_valores_forca(raridade, config))


class CardPool:
    """Gera cartas sintéticas com identidades controladas.

    `participante_de` mapeia variacao_id -> participante_id "canônico"
    (por padrão 1:1) para permitir a exceção de deck: várias raridades
    do MESMO participante coexistindo sob a MESMA variação.
    """

    def __init__(self, config: dict, seed: int | None = None):
        self.config = config
        self.rng = random.Random(seed)

    # ---- cartas de personagem ----------------------------------------

    def novo_heroi(
        self,
        raridade: str,
        variacao_id: int | None = None,
        participante_id: int | None = None,
        forca: int | None = None,
    ) -> Heroi:
        if variacao_id is None:
            variacao_id = self.rng.randint(1, N_VARIACOES_OFICIAIS)
        if participante_id is None:
            participante_id = variacao_id
        cat_p, cat_s, cat_t = categorias_da_variacao(variacao_id, self.config)
        if forca is None:
            forca = forca_aleatoria(raridade, self.config, self.rng)
        p_princ, p_sec, p_terc = poderes_da_raridade(raridade, self.config)
        return Heroi(
            variacao_id=variacao_id,
            participante_id=participante_id,
            raridade=raridade,
            categoria_principal=cat_p,
            categoria_secundaria=cat_s,
            categoria_terciaria=cat_t,
            forca_impressa=forca,
            poder_principal=p_princ,
            poder_secundario=p_sec,
            poder_terciario=p_terc,
        )

    def novo_mestre(
        self,
        raridade: str,
        tipo_heroi_dominado: int | None = None,
        categoria: str | None = None,
        forca: int | None = None,
    ) -> Mestre:
        if tipo_heroi_dominado is None:
            tipo_heroi_dominado = self.rng.randint(1, N_VARIACOES_OFICIAIS)
        if categoria is None:
            categoria = self.rng.choice(self.config["categorias"])
        if forca is None:
            forca = forca_aleatoria(raridade, self.config, self.rng)
        return Mestre(
            tipo_heroi_dominado=tipo_heroi_dominado,
            categoria=categoria,
            raridade=raridade,
            forca_impressa=forca,
        )

    def novo_guardiao(
        self,
        tipo: str | None = None,
        categoria: str | None = None,
        raridade: str | None = None,
        forca: int | None = None,
    ) -> Guardiao:
        if tipo is None:
            tipo = self.rng.choice(self.config["tipos_guardiao"])
        if categoria is None:
            categoria = self.rng.choice(self.config["categorias"])
        if raridade is None:
            raridade = self.rng.choice(self.config["raridades"])
        if forca is None:
            forca = forca_aleatoria(raridade, self.config, self.rng)
        return Guardiao(tipo=tipo, categoria=categoria, raridade=raridade, forca_impressa=forca)

    def novo_juiz(
        self,
        categoria: str | None = None,
        raridade: str | None = None,
        forca: int | None = None,
    ) -> Juiz:
        if categoria is None:
            categoria = self.rng.choice(self.config["categorias"])
        if raridade is None:
            raridade = self.rng.choice(self.config["raridades"])
        if forca is None:
            forca = forca_aleatoria(raridade, self.config, self.rng)
        return Juiz(categoria=categoria, raridade=raridade, forca_impressa=forca)

    # ---- cartas de item de jogo ---------------------------------------

    def novo_item(
        self,
        tipo_heroi: int | None = None,
        raridade: str | None = None,
    ) -> ItemHeroi:
        if tipo_heroi is None:
            tipo_heroi = self.rng.randint(1, N_VARIACOES_OFICIAIS)
        if raridade is None:
            raridade = self.rng.choice(["comum", "rara"])
        return ItemHeroi(tipo_heroi=tipo_heroi, raridade=raridade)

    def novo_local(
        self,
        categoria: str | None = None,
        raridade: str | None = None,
    ) -> Local:
        if categoria is None:
            categoria = self.rng.choice(self.config["categorias"])
        if raridade is None:
            raridade = self.rng.choice(["comum", "rara"])
        return Local(categoria=categoria, raridade=raridade)

    def nova_invocacao(self, categoria: str | None = None) -> Invocacao:
        if categoria is None:
            categoria = self.rng.choice(self.config["categorias"])
        return Invocacao(categoria=categoria)


# ---- perfis de deck para experimentos ---------------------------------

# raridades disponíveis por faixa de orçamento (probabilidades cumulativas
# simples: cada perfil desloca a distribuição para raridades mais altas).
_ORCAMENTO_RARIDADE = {
    "fraco": {"comum": 0.75, "rara": 0.20, "super_rara": 0.04, "ultra_rara": 0.01},
    "medio": {"comum": 0.40, "rara": 0.35, "super_rara": 0.18, "ultra_rara": 0.07},
    "forte": {"comum": 0.10, "rara": 0.25, "super_rara": 0.30, "ultra_rara": 0.35},
}

# contagens de carta por tipo (invocações preenchem o restante até tamanho_deck)
_ARQUETIPOS = {
    "balanceado": dict(heroes=28, masters=3, guardians=6, judge=1, items=8, locals=6),
    "agro": dict(heroes=34, masters=2, guardians=3, judge=0, items=5, locals=4),
    "controle": dict(heroes=20, masters=4, guardians=12, judge=1, items=6, locals=6),
    "combo": dict(heroes=24, masters=2, guardians=4, judge=1, items=12, locals=5),
}


def _sortear_raridade(orcamento: dict, rng: random.Random) -> str:
    raridades = list(orcamento.keys())
    pesos = list(orcamento.values())
    return rng.choices(raridades, weights=pesos, k=1)[0]


def montar_deck(
    config: dict,
    faixa_forca: str = "medio",
    arquetipo: str = "balanceado",
    seed: int | None = None,
) -> list:
    """Monta uma lista de cartas (tamanho_deck cartas) respeitando as regras
    de construção de deck (unicidade de herói, limites de mestre/guardião/juiz).

    `faixa_forca`: "fraco" | "medio" | "forte" — orçamento de raridade.
    `arquetipo`: "balanceado" | "agro" | "controle" | "combo".
    """
    if faixa_forca not in _ORCAMENTO_RARIDADE:
        raise ValueError(f"faixa_forca desconhecida: {faixa_forca!r}")
    if arquetipo not in _ARQUETIPOS:
        raise ValueError(f"arquetipo desconhecido: {arquetipo!r}")

    orcamento = _ORCAMENTO_RARIDADE[faixa_forca]
    contagens = dict(_ARQUETIPOS[arquetipo])
    tamanho_deck = config["tamanho_deck"]
    fixas = sum(contagens.values())
    if fixas > tamanho_deck:
        raise ValueError("Contagens do arquétipo excedem tamanho_deck")
    contagens["invocations"] = tamanho_deck - fixas

    pool = CardPool(config, seed=seed)
    cartas: list = []

    # heróis: 1 variação distinta por herói (evita colisão de unicidade)
    variacao_ids = list(range(1, N_VARIACOES_OFICIAIS + 1))
    pool.rng.shuffle(variacao_ids)
    for i in range(contagens["heroes"]):
        variacao_id = variacao_ids[i % len(variacao_ids)]
        raridade = _sortear_raridade(orcamento, pool.rng)
        cartas.append(pool.novo_heroi(raridade, variacao_id=variacao_id))

    # mestres: no máximo max_mesmo_mestre por tipo dominado
    max_mesmo_mestre = config["max_mesmo_mestre"]
    tipos_mestre_usados: dict[int, int] = {}
    tipos_disponiveis = list(range(1, N_VARIACOES_OFICIAIS + 1))
    pool.rng.shuffle(tipos_disponiveis)
    idx_tipo = 0
    for _ in range(contagens["masters"]):
        while idx_tipo < len(tipos_disponiveis) and tipos_mestre_usados.get(
            tipos_disponiveis[idx_tipo], 0
        ) >= max_mesmo_mestre:
            idx_tipo += 1
        tipo = tipos_disponiveis[idx_tipo]
        tipos_mestre_usados[tipo] = tipos_mestre_usados.get(tipo, 0) + 1
        raridade = _sortear_raridade(orcamento, pool.rng)
        cartas.append(pool.novo_mestre(raridade, tipo_heroi_dominado=tipo))

    # guardiões: no máximo max_mesmo_guardiao (1) por combinação específica
    combos_guardiao_usados: set[tuple] = set()
    tentativas = 0
    n_guardioes = 0
    while n_guardioes < contagens["guardians"] and tentativas < contagens["guardians"] * 50:
        tentativas += 1
        tipo = pool.rng.choice(config["tipos_guardiao"])
        categoria = pool.rng.choice(config["categorias"])
        raridade = _sortear_raridade(orcamento, pool.rng)
        combo = (tipo, categoria, raridade)
        if combo in combos_guardiao_usados:
            continue
        combos_guardiao_usados.add(combo)
        cartas.append(pool.novo_guardiao(tipo=tipo, categoria=categoria, raridade=raridade))
        n_guardioes += 1

    # juiz: no máximo max_juiz_deck (1)
    for _ in range(min(contagens["judge"], config["max_juiz_deck"])):
        raridade = _sortear_raridade(orcamento, pool.rng)
        cartas.append(pool.novo_juiz(raridade=raridade))

    # itens: livres
    for _ in range(contagens["items"]):
        cartas.append(pool.novo_item())

    # locais: livres
    for _ in range(contagens["locals"]):
        cartas.append(pool.novo_local())

    # invocações: livres (preenche o restante)
    for _ in range(contagens["invocations"]):
        cartas.append(pool.nova_invocacao())

    return cartas


def montar_deck_fraco(config: dict, arquetipo: str = "balanceado", seed: int | None = None) -> list:
    return montar_deck(config, faixa_forca="fraco", arquetipo=arquetipo, seed=seed)


def montar_deck_medio(config: dict, arquetipo: str = "balanceado", seed: int | None = None) -> list:
    return montar_deck(config, faixa_forca="medio", arquetipo=arquetipo, seed=seed)


def montar_deck_forte(config: dict, arquetipo: str = "balanceado", seed: int | None = None) -> list:
    return montar_deck(config, faixa_forca="forte", arquetipo=arquetipo, seed=seed)
