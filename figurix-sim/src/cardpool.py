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
N_TIPOS_HEROI = 35  # 5 categorias x 7 "tipos de herói" cada — todo tipo agrupa 3 variações
_VARIACOES_POR_TIPO = 3
_TIPOS_POR_CATEGORIA = N_TIPOS_HEROI // 5  # 7


def categorias_da_variacao(variacao_id: int, config: dict) -> tuple[str, str, str]:
    """Categorias fixas (principal/secundária/terciária) de uma variação.

    Determinístico: cada variação/participante tem 3 características fixas,
    distintas entre si (seção 1). Usamos offsets módulo 5 para garantir isso.
    """
    categorias = config["categorias"]
    n = len(categorias)
    i = variacao_id % n
    return categorias[i], categorias[(i + 1) % n], categorias[(i + 2) % n]


def _primeiro_id_da_categoria(indice_categoria: int, n_categorias: int) -> int:
    # variacao_id vai de 1 a 105 — o índice 0 (ex.: "Conexao") não tem
    # variacao_id=0 (não existe), então o primeiro da categoria é n_categorias.
    return indice_categoria if indice_categoria != 0 else n_categorias


def tipo_da_variacao(variacao_id: int, config: dict) -> int:
    """1-35: a que "tipo de herói" (família de 3 variações — ex.: os 3
    "Protetor") uma variação pertence. Um Mestre domina um TIPO inteiro,
    não uma variação específica (seção 9): qualquer uma das 3 variações
    do tipo conta como "o tipo do Mestre" em campo."""
    n = len(config["categorias"])
    indice_categoria = variacao_id % n
    primeiro_id = _primeiro_id_da_categoria(indice_categoria, n)
    posicao_na_categoria = (variacao_id - primeiro_id) // n
    tipo_dentro_categoria = posicao_na_categoria // _VARIACOES_POR_TIPO
    return indice_categoria * _TIPOS_POR_CATEGORIA + tipo_dentro_categoria + 1


def variacoes_do_tipo(tipo_id: int, config: dict) -> list[int]:
    """As 3 variações (variacao_id) que pertencem a um tipo de herói (1-35)."""
    n = len(config["categorias"])
    indice_categoria, tipo_dentro_categoria = divmod(tipo_id - 1, _TIPOS_POR_CATEGORIA)
    primeiro_id = _primeiro_id_da_categoria(indice_categoria, n)
    primeira_posicao = tipo_dentro_categoria * _VARIACOES_POR_TIPO
    return [primeiro_id + (primeira_posicao + k) * n for k in range(_VARIACOES_POR_TIPO)]


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
            tipo_heroi_dominado = self.rng.randint(1, N_TIPOS_HEROI)
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
            tipo_heroi = self.rng.randint(1, N_TIPOS_HEROI)
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

# contagens de HERÓIS/MESTRES/GUARDIÕES/JUIZ por arquétipo — o que define a
# "identidade" do arquétipo. Itens, locais e invocações são o orçamento
# FLEXÍVEL (ver _PERFIS_INVOCACAO) — não fixamos invocações aqui porque
# quanto investir nesse recurso é, em si, uma escolha estratégica de
# montagem de deck que o simulador precisa poder variar e testar
# isoladamente (uma partida encosta 1 invocação por vez; um deck "abundante"
# aposta em ataques fortes recorrentes, um "escasso" aposta em economizar
# e vencer no desgaste/outras mecânicas — nenhum dos dois é óbvio vencedor
# até rodar a simulação).
_ARQUETIPOS = {
    "balanceado": dict(heroes=28, masters=3, guardians=6, judge=1, items_base=8, locals_base=6),
    "agro": dict(heroes=34, masters=2, guardians=3, judge=0, items_base=5, locals_base=4),
    "controle": dict(heroes=20, masters=4, guardians=12, judge=1, items_base=6, locals_base=6),
    "combo": dict(heroes=24, masters=2, guardians=4, judge=1, items_base=12, locals_base=5),
    # arquétipo EXTREMO (propositalmente "insano", não um perfil recomendado
    # de deck real): aposta o mínimo de heróis possível — só o suficiente
    # pra sustentar mão inicial/reposição por um tempo — pra abrir espaço
    # máximo pra mestres/guardiões/juiz/invocação. Serve pra testar o
    # limite: será que abrir mão de profundidade de heróis (ficar exposto
    # à espiral de busca/fim de deck mais cedo) compensa a vantagem de
    # economia de invocações?
    "hiperinvocacao": dict(heroes=10, masters=4, guardians=14, judge=1, items_base=6, locals_base=6),
}

# fração do orçamento FLEXÍVEL (itens + locais + invocações) dedicada a
# invocações — o eixo "economia de invocações" da estratégia de deck
# (seção 4 do custo de ações: quem tem mais invocação paga mais ataques
# principal/secundário e barragens; quem tem menos aposta noutra coisa).
_PERFIS_INVOCACAO = {
    "escasso": 0.20,
    "moderado": 0.50,
    "abundante": 0.80,
}


def _sortear_raridade(orcamento: dict, rng: random.Random) -> str:
    raridades = list(orcamento.keys())
    pesos = list(orcamento.values())
    return rng.choices(raridades, weights=pesos, k=1)[0]


def montar_deck(
    config: dict,
    faixa_forca: str = "medio",
    arquetipo: str = "balanceado",
    perfil_invocacoes: str = "moderado",
    seed: int | None = None,
) -> list:
    """Monta uma lista de cartas (tamanho_deck cartas) respeitando as regras
    de construção de deck (unicidade de herói, limites de mestre/guardião/juiz).

    `faixa_forca`: "fraco" | "medio" | "forte" — orçamento de raridade.
    `arquetipo`: "balanceado" | "agro" | "controle" | "combo" — define
    heróis/mestres/guardiões/juiz.
    `perfil_invocacoes`: "escasso" | "moderado" | "abundante" — quanto do
    orçamento flexível (itens+locais+invocações) vira invocação; o resto
    se divide entre itens e locais na proporção-base do arquétipo. É um
    eixo INDEPENDENTE de faixa_forca/arquetipo — dá pra testar, por
    exemplo, um deck "forte" econômico contra um "fraco" rico em invocação.
    """
    if faixa_forca not in _ORCAMENTO_RARIDADE:
        raise ValueError(f"faixa_forca desconhecida: {faixa_forca!r}")
    if arquetipo not in _ARQUETIPOS:
        raise ValueError(f"arquetipo desconhecido: {arquetipo!r}")
    if perfil_invocacoes not in _PERFIS_INVOCACAO:
        raise ValueError(f"perfil_invocacoes desconhecido: {perfil_invocacoes!r}")

    orcamento = _ORCAMENTO_RARIDADE[faixa_forca]
    base = _ARQUETIPOS[arquetipo]
    tamanho_deck = config["tamanho_deck"]

    fixas_identidade = base["heroes"] + base["masters"] + base["guardians"] + base["judge"]
    orcamento_flexivel = tamanho_deck - fixas_identidade
    if orcamento_flexivel < 0:
        raise ValueError("Contagens do arquétipo excedem tamanho_deck")

    n_invocacoes = round(orcamento_flexivel * _PERFIS_INVOCACAO[perfil_invocacoes])
    resto = orcamento_flexivel - n_invocacoes
    razao_items = base["items_base"] / (base["items_base"] + base["locals_base"])
    n_items = round(resto * razao_items)
    n_locals = resto - n_items

    contagens = {
        "heroes": base["heroes"],
        "masters": base["masters"],
        "guardians": base["guardians"],
        "judge": base["judge"],
        "items": n_items,
        "locals": n_locals,
        "invocations": n_invocacoes,
    }

    pool = CardPool(config, seed=seed)
    cartas: list = []

    # heróis: gerados como "famílias" de participante (mesma variação/pessoa
    # em raridades diferentes — seção 2), do jeito que jogadores de verdade
    # costumam montar: quase sempre 1 carta COMUM (só ela entra em campo —
    # mão inicial e reposição grátis pós-derrota, seção 3/5) e,
    # frequentemente, 1 carta de raridade maior do MESMO participante como
    # alvo de evolução (seção 7). Uma família com 3-4 raridades do mesmo
    # participante é a EXCEÇÃO (redundância estratégica pra aumentar a
    # chance de ter uma cópia em mãos), não a regra — por isso o número de
    # cópias extras por família é sorteado por família (não solto no
    # orçamento geral), com raridades mais altas puxando mais famílias com
    # alvo de evolução e o "modelo raro" de redundância.
    n_heroes = contagens["heroes"]
    p_upgrade = {"fraco": 0.15, "medio": 0.35, "forte": 0.55}[faixa_forca]
    p_redundancia = 0.15  # chance de uma 2ª raridade extra, dado que a família já upou uma vez

    raridades_superiores = ["rara", "super_rara", "ultra_rara"]
    pesos_superiores = [orcamento[r] for r in raridades_superiores]

    variacao_ids = list(range(1, N_VARIACOES_OFICIAIS + 1))
    pool.rng.shuffle(variacao_ids)

    familias: dict[int, set] = {}
    idx_variacao = 0
    cartas_usadas = 0
    while cartas_usadas < n_heroes:
        vid = variacao_ids[idx_variacao]
        idx_variacao += 1
        raridades_familia = {"comum"}
        cartas_usadas += 1

        if cartas_usadas < n_heroes and pool.rng.random() < p_upgrade:
            raridade_upgrade = pool.rng.choices(raridades_superiores, weights=pesos_superiores, k=1)[0]
            raridades_familia.add(raridade_upgrade)
            cartas_usadas += 1

            if cartas_usadas < n_heroes and pool.rng.random() < p_redundancia:
                candidatas = [r for r in raridades_superiores if r not in raridades_familia]
                pesos_candidatas = [orcamento[r] for r in candidatas]
                raridade_extra = pool.rng.choices(candidatas, weights=pesos_candidatas, k=1)[0]
                raridades_familia.add(raridade_extra)
                cartas_usadas += 1

        familias[vid] = raridades_familia

    herois: list = []
    for vid, raridades_presentes in familias.items():
        for raridade in raridades_presentes:
            herois.append(pool.novo_heroi(raridade, variacao_id=vid, participante_id=vid))

    cartas.extend(herois)

    # mestres: no máximo max_mesmo_mestre por tipo dominado
    max_mesmo_mestre = config["max_mesmo_mestre"]
    tipos_mestre_usados: dict[int, int] = {}
    tipos_disponiveis = list(range(1, N_TIPOS_HEROI + 1))
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


def montar_deck_fraco(
    config: dict, arquetipo: str = "balanceado", perfil_invocacoes: str = "moderado", seed: int | None = None
) -> list:
    return montar_deck(config, faixa_forca="fraco", arquetipo=arquetipo, perfil_invocacoes=perfil_invocacoes, seed=seed)


def montar_deck_medio(
    config: dict, arquetipo: str = "balanceado", perfil_invocacoes: str = "moderado", seed: int | None = None
) -> list:
    return montar_deck(config, faixa_forca="medio", arquetipo=arquetipo, perfil_invocacoes=perfil_invocacoes, seed=seed)


def montar_deck_forte(
    config: dict, arquetipo: str = "balanceado", perfil_invocacoes: str = "moderado", seed: int | None = None
) -> list:
    return montar_deck(config, faixa_forca="forte", arquetipo=arquetipo, perfil_invocacoes=perfil_invocacoes, seed=seed)
