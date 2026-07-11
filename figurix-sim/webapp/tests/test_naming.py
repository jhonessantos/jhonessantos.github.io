"""Nomes reais dos 105 heróis (webapp/naming.py): 5 categorias de 21, cada
21 dividido em 7 "tipos" de 3 variantes. A categoria que o nome sugere
precisa bater com a categoria de verdade que o motor calcula pra aquele
variacao_id (cardpool.categorias_da_variacao) — senão o emoji/cor da
categoria na carta e o nome do herói ficam incoerentes."""
from cardpool import categorias_da_variacao
from naming import _HEROIS_POR_CATEGORIA, _NOMES_HEROIS, nome_participante

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
