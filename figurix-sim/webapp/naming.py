"""Nomes de exibição para entidades sintéticas (heróis, mestres, guardiões...).

O motor (src/cards.py) só guarda IDs numéricos (variacao_id, tipo_heroi_dominado,
tipo de guardião) — mas os 105 heróis (variação 1-105) TÊM nomes de
personagem reais: 5 categorias de 21 heróis cada, e cada 21 dividido em 7
"tipos de herói" (família temática, ex.: "Anjo") de 3 variantes cada
(ex.: "Anjo Vigilante", "Anjo Transcendente", "Anjo de Cristal") — 35
tipos ao todo. Um Mestre domina um TIPO inteiro, não uma variação
específica (seção 9) — "Mestre dos Protetores" domina as 3 variações de
Protetor. Este módulo mapeia os IDs numéricos pra esses nomes — camada de
exibição só, não inventa nenhuma regra de jogo.

A categoria/tipo de uma variação vêm de `cardpool.categorias_da_variacao`/
`tipo_da_variacao` (a mesma lógica usada pelo motor) — importado de src/
em vez de duplicado aqui, pra garantir que o nome exibido nunca desalinhe
do agrupamento real que o motor calcula.
"""
from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cardpool import N_VARIACOES_OFICIAIS, categorias_da_variacao, tipo_da_variacao  # noqa: E402
from config import carregar_config  # noqa: E402

CONFIG = carregar_config()

# 21 nomes por categoria, na ordem dos 7 "tipos de herói" (3 variantes cada, agrupadas)
_HEROIS_POR_CATEGORIA = {
    "Coracao": [
        "Anjo Vigilante", "Anjo Transcendente", "Anjo de Cristal",
        "Curador do Farol", "Curador da Biblioteca Perdida", "Curador das Estrelas",
        "Druida dos Sete Ventos", "Druida da Lua Nova", "Druida do Coração Verde",
        "Fada das Missões Impossíveis", "Fada Encantada", "Fada da Boa Sorte",
        "Monge da Ordem", "Monge Iluminado", "Monge Senhor do Cochilo",
        "Pacificador da Lua Nova", "Pacificador do Selo Antigo", "Pacificador Sereno",
        "Protetor da Lua Vermelha", "Protetor do Olhar Eterno", "Protetor do Vale Silente",
    ],
    "Mente": [
        "Androide Sideral", "Androide Ressonante", "Androide Tempestuoso",
        "Arcanista da Névoa", "Arcanista Sussurrante", "Arcanista do Vórtice",
        "Estrategista dos Dois Lados", "Estrategista Temporal", "Estrategista do Labirinto",
        "Mago da Lua Esquecida", "Mago do Santuário", "Mago do Trono Perdido",
        "Oráculo de Mil Faces", "Oráculo da Teia de Vozes", "Oráculo do Espelho Partido",
        "Sábio da Chave Esquecida", "Sábio do Tempo", "Sábio da Memória Viva",
        "Telepata Invadente", "Telepata de Mil Vozes", "Telepata da Lua Espectral",
    ],
    "Criacao": [
        "Alquimista das Runas", "Alquimista das Águas Trocadas", "Alquimista Primordial",
        "Artífice das Rodas Engendradas", "Artífice do Vapor", "Artífice da Chama Fria",
        "Bardo das Brumas", "Bardo da Cura Noturna", "Bardo do Pergaminho",
        "Ilusionista Fantasma", "Ilusionista das Marionetes", "Ilusionista Hipnótico",
        "Inventor Excêntrico", "Inventor Cibernético", "Inventor de Neon",
        "Modelador dos Ventos Curvosos", "Modelador de Argila", "Modelador de Cristal",
        "Viajante Estelar", "Viajante Nocturno", "Viajante de Mil Mapas",
    ],
    "Acao": [
        "Centurião Fantasma", "Centurião da Fortaleza", "Centurião Sísmico",
        "Espadachim da Penumbra", "Espadachim Glacial", "Espadachim da Tempestade",
        "Gladiador das Chamas", "Gladiador Implacável", "Gladiador do Coliseu",
        "Guerreiro da Aurora", "Guerreiro do Relâmpago", "Guerreiro Filho do Vulcão",
        "Ninja Flamejante", "Ninja do Futuro", "Ninja da Água Corrente",
        "Samurai dos Mil Cortes", "Samurai da Areia Negra", "Samurai da Flor Carmesim",
        "Soldado Dourado", "Soldado Inoxidável", "Soldado do Gelo",
    ],
    "Conexao": [
        "Arquiduque Benevolente", "Arquiduque da Corte Fantasma", "Arquiduque Imperial",
        "Cavaleiro do Sistema Solar", "Cavaleiro do Gelo Azul", "Cavaleiro do Deserto",
        "Conselheiro Voz das Câmaras", "Conselheiro da Tradição", "Conselheiro da Corte",
        "Diplomata Ancestral", "Diplomata do Pano Fino", "Diplomata Astuto",
        "Mensageiro Águia", "Mensageiro do Portal", "Mensageiro da Encruzilhada",
        "Sacerdote da Floresta Antiga", "Sacerdote da Aurora", "Sacerdote Astral",
        "Sentinela da Fortaleza", "Sentinela do Último Farol", "Sentinela Boreal",
    ],
}

# sufixo (com artigo/gênero corretos) do nome do Mestre de cada tipo de
# herói — mesma ordem dos grupos de 3 acima. Pluralização/gênero em
# português não são regulares o bastante pra derivar automaticamente
# (ex.: "Centurião" -> "Centuriões"), por isso é uma lista curada.
_SUFIXO_MESTRE_POR_CATEGORIA = {
    "Coracao": [
        "dos Anjos", "dos Curadores", "dos Druidas", "das Fadas",
        "dos Monges", "dos Pacificadores", "dos Protetores",
    ],
    "Mente": [
        "dos Androides", "dos Arcanistas", "dos Estrategistas", "dos Magos",
        "dos Oráculos", "dos Sábios", "dos Telepatas",
    ],
    "Criacao": [
        "dos Alquimistas", "dos Artífices", "dos Bardos", "dos Ilusionistas",
        "dos Inventores", "dos Modeladores", "dos Viajantes",
    ],
    "Acao": [
        "dos Centuriões", "dos Espadachins", "dos Gladiadores", "dos Guerreiros",
        "dos Ninjas", "dos Samurais", "dos Soldados",
    ],
    "Conexao": [
        "dos Arquiduques", "dos Cavaleiros", "dos Conselheiros", "dos Diplomatas",
        "dos Mensageiros", "dos Sacerdotes", "das Sentinelas",
    ],
}


def _construir_mapas() -> tuple[dict[int, str], dict[int, str]]:
    nomes_herois: dict[int, str] = {}
    sufixos_mestre: dict[int, str] = {}
    for categoria, nomes in _HEROIS_POR_CATEGORIA.items():
        ids_da_categoria = sorted(
            vid for vid in range(1, N_VARIACOES_OFICIAIS + 1) if categorias_da_variacao(vid, CONFIG)[0] == categoria
        )
        nomes_herois.update(zip(ids_da_categoria, nomes))
        for i, sufixo in enumerate(_SUFIXO_MESTRE_POR_CATEGORIA[categoria]):
            primeira_variacao_do_grupo = ids_da_categoria[i * 3]
            tipo_id = tipo_da_variacao(primeira_variacao_do_grupo, CONFIG)
            sufixos_mestre[tipo_id] = sufixo
    return nomes_herois, sufixos_mestre


_NOMES_HEROIS, _SUFIXOS_MESTRE = _construir_mapas()

_NOME_GUARDIAO = {
    "Portais": "Guardião dos Portais",
    "Restauracao": "Guardião da Restauração",
    "Escudos": "Guardião dos Escudos",
    "Oprimidos": "Guardião dos Oprimidos",
    "Descanso": "Guardião do Descanso",
}


def nome_participante(participante_id: int) -> str:
    return _NOMES_HEROIS.get(participante_id, f"Herói #{participante_id}")


def nome_guardiao(tipo: str) -> str:
    return _NOME_GUARDIAO.get(tipo, tipo)


def nome_mestre(tipo_heroi_dominado: int) -> str:
    sufixo = _SUFIXOS_MESTRE.get(tipo_heroi_dominado, f"do Tipo #{tipo_heroi_dominado}")
    return f"Mestre {sufixo}"


def nome_item(tipo_heroi: int) -> str:
    return f"Item de {nome_participante(tipo_heroi)}"
