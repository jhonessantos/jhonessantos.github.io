"""Lógica pura de geração de cartas avulsas e em lote (Deck Builder).

Separado de app.py para poder ser testado sem subir o FastAPI/o banco:
levanta ValueError puro (não HTTPException) — quem chama pela API converte
na borda (ver app.py). `params`/`regra` são "duck-typed": tanto o modelo
pydantic da API quanto um objeto simples (ou até um dict-like com atributos)
servem, contanto que tenham os mesmos campos.
"""
from __future__ import annotations

from collections import defaultdict
from types import SimpleNamespace

from cardpool import CardPool, N_VARIACOES_OFICIAIS, categorias_da_variacao
from cards import Heroi, raridade_equivalente

# "Misto balanceado": distribuição usada pra preencher um número arbitrário
# de cartas com a mesma FORMA do arquétipo 'balanceado' + perfil de
# invocações 'moderado' (os padrões já usados no resto do app) — em vez de
# forçar a regra de "preencher o restante" a ser só de 1 tipo/filtro.
_PESOS_MIX_BALANCEADO = {
    "heroi": 28 / 64,
    "mestre": 3 / 64,
    "guardiao": 6 / 64,
    "juiz": 1 / 64,
    "item": 7 / 64,
    "local": 6 / 64,
    "invocacao": 13 / 64,
}
# mistura de raridade estilo faixa "médio" — só usada para as cartas que o
# "misto" gera sozinho (sem o usuário escolher raridade nenhuma).
_RARIDADES_MISTO = ["comum", "rara", "super_rara", "ultra_rara"]
_PESOS_RARIDADE_MISTO = [40, 35, 18, 7]


def _variacoes_candidatas(categoria: str | None, config: dict) -> list[int]:
    """Todas as variações (1..N) cuja categoria PRINCIPAL bate com `categoria`
    — ou todas, se nenhuma categoria for exigida."""
    todas = range(1, N_VARIACOES_OFICIAIS + 1)
    if categoria is None:
        return list(todas)
    return [v for v in todas if categorias_da_variacao(v, config)[0] == categoria]


def gerar_uma_carta(pool: CardPool, params) -> object:
    if params.tipo_carta == "heroi":
        variacao_id = params.variacao_id
        if variacao_id is None and params.categoria is not None:
            candidatas = _variacoes_candidatas(params.categoria, pool.config)
            if not candidatas:
                raise ValueError(f"Nenhuma variação de herói pertence à categoria {params.categoria!r}.")
            variacao_id = pool.rng.choice(candidatas)
        return pool.novo_heroi(
            params.raridade or "comum",
            variacao_id=variacao_id,
            participante_id=params.participante_id,
            forca=params.forca,
        )
    if params.tipo_carta == "mestre":
        return pool.novo_mestre(
            params.raridade or "comum",
            tipo_heroi_dominado=params.tipo_heroi_dominado,
            categoria=params.categoria,
            forca=params.forca,
        )
    if params.tipo_carta == "guardiao":
        return pool.novo_guardiao(
            tipo=params.tipo_guardiao, categoria=params.categoria, raridade=params.raridade, forca=params.forca
        )
    if params.tipo_carta == "juiz":
        return pool.novo_juiz(categoria=params.categoria, raridade=params.raridade, forca=params.forca)
    if params.tipo_carta == "item":
        return pool.novo_item(tipo_heroi=params.tipo_heroi, raridade=params.raridade)
    if params.tipo_carta == "local":
        return pool.novo_local(categoria=params.categoria, raridade=params.raridade)
    if params.tipo_carta == "invocacao":
        return pool.nova_invocacao(categoria=params.categoria)
    raise ValueError(f"tipo_carta desconhecido: {params.tipo_carta!r}")


def gerar_heroi_sem_duplicar(pool: CardPool, regra, variacoes_usadas: dict, config: dict) -> Heroi:
    """Quando a regra não fixa uma variação, sorteia uma (dentre as que
    batem com `regra.categoria`, se exigida) que ainda não esteja ocupada
    NA MESMA raridade (base) — sem isso, pedir "N heróis comuns" ao acaso
    colide cedo (só 105 variações possíveis, menos ainda se restrito a 1
    categoria) e o deck já nasce inválido por um motivo trivialmente
    evitável. Raridades diferentes do mesmo participante continuam livres
    pra formar "famílias" de evolução."""
    raridade = regra.raridade or "comum"
    base = raridade_equivalente(raridade, config)
    usadas = variacoes_usadas[base]

    if regra.variacao_id is not None:
        carta = pool.novo_heroi(
            raridade, variacao_id=regra.variacao_id, participante_id=regra.participante_id, forca=regra.forca
        )
    else:
        candidatas = _variacoes_candidatas(regra.categoria, config)
        livres = [v for v in candidatas if v not in usadas]
        if not livres:
            recorte = f"da categoria {regra.categoria!r} " if regra.categoria else ""
            raise ValueError(f"Não há mais variações de herói {recorte}livres para a raridade '{base}' sem duplicar.")
        variacao_escolhida = pool.rng.choice(livres)
        carta = pool.novo_heroi(
            raridade, variacao_id=variacao_escolhida, participante_id=regra.participante_id, forca=regra.forca
        )

    usadas.add(carta.variacao_id)
    return carta


def variacoes_usadas_de_cartas_existentes(cartas_existentes: list[dict], config: dict) -> dict:
    """Reconstrói o controle de "variações já ocupadas por raridade" a partir
    das cartas serializadas já presentes no deck em edição."""
    variacoes_usadas: dict[str, set] = defaultdict(set)
    for dados in cartas_existentes:
        if dados.get("classe") != "Heroi":
            continue
        base = raridade_equivalente(dados["raridade"], config)
        variacoes_usadas[base].add(dados["variacao_id"])
    return variacoes_usadas


def _distribuir_mix_balanceado(quantidade: int) -> dict[str, int]:
    contagens = {tipo: int(peso * quantidade) for tipo, peso in _PESOS_MIX_BALANCEADO.items()}
    falta = quantidade - sum(contagens.values())
    contagens["invocacao"] += falta  # sobra do arredondamento cai na invocação (recurso mais "neutro")
    return contagens


def _expandir_misto(pool: CardPool, quantidade: int, variacoes_usadas: dict, config: dict) -> list:
    """"Misto balanceado": em vez de 1 tipo só, distribui `quantidade`
    cartas pelos 7 tipos na forma do arquétipo padrão do app — pensado
    pra ser o valor natural de uma regra de "preencher o restante"."""
    cartas: list = []
    for tipo, n in _distribuir_mix_balanceado(quantidade).items():
        for _ in range(n):
            if tipo == "heroi":
                regra = SimpleNamespace(
                    tipo_carta="heroi",
                    raridade=pool.rng.choices(_RARIDADES_MISTO, weights=_PESOS_RARIDADE_MISTO, k=1)[0],
                    categoria=None,
                    variacao_id=None,
                    participante_id=None,
                    forca=None,
                )
                cartas.append(gerar_heroi_sem_duplicar(pool, regra, variacoes_usadas, config))
            else:
                raridade = (
                    pool.rng.choices(_RARIDADES_MISTO, weights=_PESOS_RARIDADE_MISTO, k=1)[0]
                    if tipo in ("mestre", "guardiao", "juiz")
                    else None
                )
                regra = SimpleNamespace(
                    tipo_carta=tipo,
                    raridade=raridade,
                    categoria=None,
                    tipo_heroi_dominado=None,
                    tipo_guardiao=None,
                    tipo_heroi=None,
                    forca=None,
                )
                cartas.append(gerar_uma_carta(pool, regra))
    return cartas


def gerar_lote(config: dict, regras: list, cartas_existentes: list[dict], seed: int | None) -> list:
    """Gera todas as cartas de todas as regras (cada uma já com sua
    `quantidade` resolvida) a partir de UM pool com seed compartilhada.
    Uma regra com `tipo_carta == "misto"` gera sua quantidade inteira como
    um mix balanceado (ver `_expandir_misto`), não um único tipo de carta."""
    for regra in regras:
        if regra.quantidade < 1:
            raise ValueError("quantidade de cada regra precisa ser >= 1")

    variacoes_usadas = variacoes_usadas_de_cartas_existentes(cartas_existentes, config)
    pool = CardPool(config, seed=seed)
    cartas_geradas = []
    for regra in regras:
        if regra.tipo_carta == "misto":
            cartas_geradas.extend(_expandir_misto(pool, regra.quantidade, variacoes_usadas, config))
            continue
        for _ in range(regra.quantidade):
            if regra.tipo_carta == "heroi":
                carta = gerar_heroi_sem_duplicar(pool, regra, variacoes_usadas, config)
            else:
                carta = gerar_uma_carta(pool, regra)
            cartas_geradas.append(carta)
    return cartas_geradas
