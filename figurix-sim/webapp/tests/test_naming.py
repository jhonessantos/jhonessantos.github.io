"""Nomes reais dos 105 heróis (webapp/naming.py): 5 categorias de 21, cada
21 dividido em 7 "tipos" de 3 variantes. A categoria que o nome sugere
precisa bater com a categoria de verdade que o motor calcula pra aquele
variacao_id (cardpool.categorias_da_variacao) — senão o emoji/cor da
categoria na carta e o nome do herói ficam incoerentes."""
from cardpool import N_TIPOS_HEROI, categorias_da_variacao, tipo_da_variacao, variacoes_do_tipo
from naming import _HEROIS_POR_CATEGORIA, _NOMES_HEROIS, _SUFIXOS_MESTRE, nome_mestre, nome_participante

_TIPOS_POR_CATEGORIA = {
    "Coracao": ["Anjo", "Curador", "Druida", "Fada", "Monge", "Pacificador", "Protetor"],
    "Mente": ["Androide", "Arcanista", "Estrategista", "Mago", "Oráculo", "Sábio", "Telepata"],
    "Criacao": ["Alquimista", "Artífice", "Bardo", "Ilusionista", "Inventor", "Modelador", "Viajante"],
    "Acao": ["Centurião", "Espadachim", "Gladiador", "Guerreiro", "Ninja", "Samurai", "Soldado"],
    "Conexao": ["Arquiduque", "Cavaleiro", "Conselheiro", "Diplomata", "Mensageiro", "Sacerdote", "Sentinela"],
}


def test_105_herois_nomeados_sem_duplicata():
    assert len(_NOMES_HEROIS) == 105
    assert set(_NOMES_HEROIS.keys()) == set(range(1, 106))
    assert len(set(_NOMES_HEROIS.values())) == 105


def test_cada_categoria_tem_21_nomes_em_7_tipos_de_3():
    for categoria, nomes in _HEROIS_POR_CATEGORIA.items():
        assert len(nomes) == 21
        tipos_presentes = [nome.split()[0] for nome in nomes]
        for tipo in _TIPOS_POR_CATEGORIA[categoria]:
            assert tipos_presentes.count(tipo) == 3, f"{categoria}/{tipo}: esperado 3 variantes"


def test_nome_bate_com_categoria_calculada_pelo_motor(config):
    for variacao_id, nome in _NOMES_HEROIS.items():
        categoria_real = categorias_da_variacao(variacao_id, config)[0]
        tipo_do_nome = nome.split()[0]
        assert tipo_do_nome in _TIPOS_POR_CATEGORIA[categoria_real], (
            f"variacao {variacao_id} ({nome}): motor calcula categoria {categoria_real!r}, "
            f"mas o tipo {tipo_do_nome!r} não pertence a essa categoria"
        )


def test_nome_participante_fora_do_range_nao_quebra():
    assert nome_participante(200) == "Herói #200"


def test_nome_participante_exemplo_conhecido():
    assert nome_participante(1) == "Anjo Vigilante"


# ------------------------------------------------------------------
# Mestre: domina um TIPO de herói (35 tipos), não uma variação (105) —
# "Mestre dos Protetores" tem que valer pras 3 variações de Protetor.
# ------------------------------------------------------------------

def test_35_tipos_com_sufixo_de_mestre_sem_duplicata():
    assert len(_SUFIXOS_MESTRE) == N_TIPOS_HEROI
    assert set(_SUFIXOS_MESTRE.keys()) == set(range(1, N_TIPOS_HEROI + 1))
    assert len(set(_SUFIXOS_MESTRE.values())) == N_TIPOS_HEROI


def test_nome_mestre_exemplo_conhecido(config):
    # acha a variação real de "Protetor" nos dados (não assume um ID fixo —
    # o exemplo "Protetor do Olhar Eterno" das regras é só ilustrativo, não
    # amarrado a nenhum variacao_id específico nesta implementação).
    variacao_protetor = next(vid for vid, nome in _NOMES_HEROIS.items() if nome.startswith("Protetor"))
    tipo_dos_protetores = tipo_da_variacao(variacao_protetor, config)
    assert nome_mestre(tipo_dos_protetores) == "Mestre dos Protetores"


def test_nome_mestre_vale_igual_para_as_3_variacoes_do_tipo(config):
    for tipo_id in range(1, N_TIPOS_HEROI + 1):
        tipos_base = {_NOMES_HEROIS[vid].split()[0] for vid in variacoes_do_tipo(tipo_id, config)}
        # as 3 variações do tipo compartilham a mesma primeira palavra (o
        # "tipo" de fato, ex.: "Protetor") — não importa qual das 3 o
        # jogador tenha em campo, é o mesmo Mestre que vale.
        assert len(tipos_base) == 1


def test_nome_mestre_fora_do_range_nao_quebra():
    assert nome_mestre(999) == "Mestre do Tipo #999"


def test_nome_mestre_pluralizacao_irregular_curada(config):
    # casos onde pluralização/gênero em português não seguem a regra
    # simples de "adicionar s" — confirma que a lista curada acertou.
    casos = {
        "Centurião": "Mestre dos Centuriões",
        "Fada": "Mestre das Fadas",
        "Sentinela": "Mestre das Sentinelas",
        "Espadachim": "Mestre dos Espadachins",
    }
    for tipo_singular, esperado in casos.items():
        variacao = next(vid for vid, nome in _NOMES_HEROIS.items() if nome.startswith(tipo_singular))
        tipo_id = tipo_da_variacao(variacao, config)
        assert nome_mestre(tipo_id) == esperado
