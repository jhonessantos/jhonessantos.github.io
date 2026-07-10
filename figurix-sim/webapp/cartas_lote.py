"""Lógica pura de geração de cartas avulsas e em lote (Deck Builder).

Separado de app.py para poder ser testado sem subir o FastAPI/o banco:
levanta ValueError puro (não HTTPException) — quem chama pela API converte
na borda (ver app.py). `params`/`regra` são "duck-typed": tanto o modelo
pydantic da API quanto um objeto simples (ou até um dict-like com atributos)
servem, contanto que tenham os mesmos campos.
"""
from __future__ import annotations

from collections import defaultdict

from cardpool import CardPool, N_VARIACOES_OFICIAIS
from cards import Heroi, raridade_equivalente


def gerar_uma_carta(pool: CardPool, params) -> object:
    if params.tipo_carta == "heroi":
        return pool.novo_heroi(
            params.raridade or "comum",
            variacao_id=params.variacao_id,
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
    """Quando a regra não fixa uma variação, sorteia uma que ainda não esteja
    ocupada NA MESMA raridade (base) — sem isso, pedir "N heróis comuns" ao
    acaso colide cedo (só 105 variações possíveis) e o deck já nasce
    inválido por um motivo trivialmente evitável. Raridades diferentes do
    mesmo participante continuam livres pra formar "famílias" de evolução."""
    raridade = regra.raridade or "comum"
    base = raridade_equivalente(raridade, config)
    usadas = variacoes_usadas[base]

    if regra.variacao_id is not None:
        carta = pool.novo_heroi(
            raridade, variacao_id=regra.variacao_id, participante_id=regra.participante_id, forca=regra.forca
        )
    else:
        livres = [v for v in range(1, N_VARIACOES_OFICIAIS + 1) if v not in usadas]
        if not livres:
            raise ValueError(f"Não há mais variações de herói livres para a raridade '{base}' sem duplicar.")
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


def gerar_lote(config: dict, regras: list, cartas_existentes: list[dict], seed: int | None) -> list:
    """Gera todas as cartas de todas as regras (cada uma já com sua
    `quantidade` resolvida) a partir de UM pool com seed compartilhada."""
    for regra in regras:
        if regra.quantidade < 1:
            raise ValueError("quantidade de cada regra precisa ser >= 1")

    variacoes_usadas = variacoes_usadas_de_cartas_existentes(cartas_existentes, config)
    pool = CardPool(config, seed=seed)
    cartas_geradas = []
    for regra in regras:
        for _ in range(regra.quantidade):
            if regra.tipo_carta == "heroi":
                carta = gerar_heroi_sem_duplicar(pool, regra, variacoes_usadas, config)
            else:
                carta = gerar_uma_carta(pool, regra)
            cartas_geradas.append(carta)
    return cartas_geradas
