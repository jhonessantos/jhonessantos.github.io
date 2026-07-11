"""Nomes de exibição para entidades sintéticas (heróis, guardiões...).

O motor (src/cards.py) só guarda IDs numéricos (variacao_id, participante_id,
tipo) — mas os 105 heróis (variação 1-105) TÊM nomes de personagem reais:
5 categorias de 21 heróis cada, e cada 21 dividido em 7 "tipos" (família
temática, ex.: "Anjo") de 3 variantes cada (ex.: "Anjo Vigilante", "Anjo
Transcendente", "Anjo de Cristal"). Este módulo mapeia variacao_id para
esses nomes — camada de exibição só, não inventa nenhuma regra de jogo.

A categoria de uma variação é `variacao_id % 5` (mesma lógica de
`cardpool.categorias_da_variacao`, replicada aqui pra este módulo não
precisar importar de src/ — a ordem das categorias é fixa desde a v1 das
regras: ["Conexao", "Coracao", "Acao", "Mente", "Criacao"], igual
`config["categorias"]`).
"""
from __future__ import annotations

_ORDEM_CATEGORIAS = ["Conexao", "Coracao", "Acao", "Mente", "Criacao"]

# 21 nomes por categoria, na ordem dos 7 "tipos" (3 variantes cada, agrupadas)
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


def _construir_mapa_nomes() -> dict[int, str]:
    mapa: dict[int, str] = {}
    for categoria, nomes in _HEROIS_POR_CATEGORIA.items():
        indice_categoria = _ORDEM_CATEGORIAS.index(categoria)
        ids_da_categoria = [vid for vid in range(1, 106) if vid % len(_ORDEM_CATEGORIAS) == indice_categoria]
        mapa.update(zip(ids_da_categoria, nomes))
    return mapa


_NOMES_HEROIS = _construir_mapa_nomes()

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
    return f"Mestre de {nome_participante(tipo_heroi_dominado)}"


def nome_item(tipo_heroi: int) -> str:
    return f"Item de {nome_participante(tipo_heroi)}"
