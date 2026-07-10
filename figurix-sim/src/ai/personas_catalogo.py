"""Catálogo de IAs disponíveis para simulação (pedido do usuário: "no
mínimo 15 personalidades diferentes de IA já de cara").

Cada persona é uma combinação de parâmetros de `PersonaAI` — nenhuma
delas é uma classe nova, só um preset nomeado. `criar_ia(chave, seed)` é
o único ponto de entrada que o resto do sistema (webapp, scripts) deve
usar para instanciar qualquer IA por nome.
"""
from __future__ import annotations

from ai.heuristic_ai import HeuristicAI
from ai.mcts_ai import MCTSAI
from ai.persona_ai import PersonaAI
from ai.random_ai import RandomAI

PERSONAS: dict[str, dict] = {
    "certinho": {
        "rotulo": "Certinho (Equilibrada)",
        "descricao": "Segue a receita padrão: repõe herói, acumula invocação, "
        "ataca quando mata, evolui, monta múltiplo antes de atacar. Sem viés forte.",
        "parametros": {},
    },
    "agressiva": {
        "rotulo": "Agressiva",
        "descricao": "Ataca sempre que possível, mesmo sem matar, antes de se preocupar "
        "com montagem. Quase nunca barra (prefere gastar invocação atacando).",
        "parametros": {
            "ordem_prioridades": [
                "repor_heroi", "acumular_invocacao", "ataque_letal", "ataque_nao_letal",
                "evoluir", "juiz_vantagem", "mestre_proprio_tipo", "local_favoravel",
                "anexar_item", "guardiao_util",
            ],
            "limiar_barragem_forca": 320,
            "limiar_juiz": 150,
        },
    },
    "defensiva": {
        "rotulo": "Defensiva (Turtle)",
        "descricao": "Prioriza guardiões/mestre/local antes de atacar; só ataca sem "
        "matar como último recurso. Barra quase qualquer coisa que puder pagar.",
        "parametros": {
            "ordem_prioridades": [
                "repor_heroi", "acumular_invocacao", "guardiao_util", "mestre_proprio_tipo",
                "local_favoravel", "anexar_item", "evoluir", "juiz_vantagem",
                "ataque_letal", "ataque_nao_letal",
            ],
            "limiar_barragem_forca": 80,
            "barra_tudo_que_pode": True,
            "limiar_juiz": 60,
        },
    },
    "focada_em_juiz": {
        "rotulo": "Focada em Juiz",
        "descricao": "Invoca o Juiz assim que há qualquer vantagem de força, e guarda "
        "invocação o suficiente pra sempre poder pagá-lo.",
        "parametros": {
            "ordem_prioridades": [
                "repor_heroi", "acumular_invocacao", "juiz_vantagem", "ataque_letal",
                "evoluir", "mestre_proprio_tipo", "local_favoravel", "anexar_item",
                "guardiao_util", "ataque_nao_letal",
            ],
            "limiar_juiz": 10,
            "reserva_alvo_invocacoes": 6,
        },
    },
    "focada_em_evolucao": {
        "rotulo": "Focada em Evolução",
        "descricao": "Evolui assim que possível, antes até de atacar letalmente — "
        "prioriza ter heróis fortes em campo sobre fechar o combate rápido.",
        "parametros": {
            "ordem_prioridades": [
                "repor_heroi", "acumular_invocacao", "evoluir", "ataque_letal",
                "juiz_vantagem", "mestre_proprio_tipo", "local_favoravel", "anexar_item",
                "guardiao_util", "ataque_nao_letal",
            ],
        },
    },
    "focada_em_barragem": {
        "rotulo": "Focada em Barragem",
        "descricao": "Interrompe quase qualquer invocação do adversário que conseguir "
        "pagar — mantém uma reserva alta de invocação só pra isso.",
        "parametros": {
            "limiar_barragem_forca": 40,
            "barra_tudo_que_pode": True,
            "reserva_alvo_invocacoes": 10,
        },
    },
    "acumuladora": {
        "rotulo": "Acumuladora",
        "descricao": "Guarda uma reserva grande de invocação antes de se comprometer "
        "com qualquer jogada — prefere postergar pra ter recurso de sobra depois.",
        "parametros": {
            "ordem_prioridades": [
                "repor_heroi", "acumular_invocacao", "evoluir", "mestre_proprio_tipo",
                "local_favoravel", "anexar_item", "juiz_vantagem", "ataque_letal",
                "guardiao_util", "ataque_nao_letal",
            ],
            "reserva_alvo_invocacoes": 16,
        },
    },
    "gastadora": {
        "rotulo": "Gastadora (Impulsiva)",
        "descricao": "Nunca acumula invocação de propósito — ataca com o que tiver "
        "assim que possível, sem esperar montar recurso.",
        "parametros": {
            "ordem_prioridades": [
                "repor_heroi", "ataque_letal", "ataque_nao_letal", "evoluir",
                "juiz_vantagem", "mestre_proprio_tipo", "local_favoravel", "anexar_item",
                "guardiao_util", "acumular_invocacao",
            ],
            "reserva_alvo_invocacoes": 0,
        },
    },
    "guardia": {
        "rotulo": "Guardiã (Guardian-first)",
        "descricao": "Prioriza colocar guardiões em campo antes de quase tudo — quer "
        "sempre ter o máximo de efeitos de guardião ativos.",
        "parametros": {
            "ordem_prioridades": [
                "repor_heroi", "acumular_invocacao", "guardiao_util", "juiz_vantagem",
                "ataque_letal", "evoluir", "mestre_proprio_tipo", "local_favoravel",
                "anexar_item", "ataque_nao_letal",
            ],
            "guardioes_priorizados": ["Portais", "Restauracao", "Escudos", "Oprimidos", "Descanso"],
        },
    },
    "mestre_primeiro": {
        "rotulo": "Mestre em Primeiro Lugar",
        "descricao": "Garante o mestre do próprio tipo em campo antes de quase "
        "qualquer outra coisa (maximiza múltiplo de ataque principal).",
        "parametros": {
            "ordem_prioridades": [
                "repor_heroi", "acumular_invocacao", "mestre_proprio_tipo", "juiz_vantagem",
                "ataque_letal", "evoluir", "local_favoravel", "anexar_item",
                "guardiao_util", "ataque_nao_letal",
            ],
        },
    },
    "anti_juiz": {
        "rotulo": "Anti-Juiz",
        "descricao": "Só barra ameaças fortes em geral, mas SEMPRE tenta barrar Mestre "
        "e Juiz do adversário, não importa a força — nega a jogada mais perigosa do jogo.",
        "parametros": {
            "limiar_barragem_forca": 260,
            "sempre_barra_tipos": ["Juiz", "Mestre"],
            "reserva_alvo_invocacoes": 8,
        },
    },
    "comeback": {
        "rotulo": "Viradora (Comeback)",
        "descricao": "Joga como a Certinho enquanto está igual/na frente, mas fica bem "
        "mais agressiva com o Juiz assim que fica 2+ pontos atrás.",
        "parametros": {
            "vies_comeback": True,
            "limiar_comeback_pontos": 2,
        },
    },
    "rush_pontos": {
        "rotulo": "Rush de Pontos",
        "descricao": "Nunca perde turno com evolução/mestre/local/item/guardião — só "
        "repõe herói, guarda o mínimo de invocação e ataca sempre que possível.",
        "parametros": {
            "ordem_prioridades": ["repor_heroi", "acumular_invocacao", "ataque_letal", "ataque_nao_letal", "juiz_vantagem"],
            "reserva_alvo_invocacoes": 4,
        },
    },
    "randomica_com_vies": {
        "rotulo": "Randômica com Viés (nível 1.5)",
        "descricao": "Metade das decisões seguem a receita padrão; a outra metade é "
        "aleatória — um meio-termo entre a IA aleatória e a heurística.",
        "parametros": {"aleatoriedade": 0.5},
    },
    "oportunista": {
        "rotulo": "Oportunista",
        "descricao": "Só age quando há vantagem clara: nunca ataca sem matar, quase "
        "nunca barra, só usa o Juiz com vantagem esmagadora.",
        "parametros": {
            "ordem_prioridades": [
                "repor_heroi", "acumular_invocacao", "juiz_vantagem", "ataque_letal",
                "evoluir", "mestre_proprio_tipo", "local_favoravel", "anexar_item",
                "guardiao_util",
            ],
            "limiar_barragem_forca": 350,
            "limiar_juiz": 250,
        },
    },
}

MCTS_VARIANTES: dict[str, dict] = {
    "mcts_rapida": {
        "rotulo": "MCTS Rápida",
        "descricao": "Orçamento bem enxuto (15 simulações, 4 turnos de rollout) — "
        "rápida o bastante pra rodar em lote, mas com busca rasa.",
        "n_simulacoes": 15,
        "profundidade_rollout": 4,
    },
    "mcts_padrao": {
        "rotulo": "MCTS Padrão",
        "descricao": "50 simulações, 8 turnos de rollout — equilíbrio entre "
        "qualidade de decisão e tempo de execução.",
        "n_simulacoes": 50,
        "profundidade_rollout": 8,
    },
    "mcts_profunda": {
        "rotulo": "MCTS Profunda",
        "descricao": "150 simulações, 12 turnos de rollout — decisão mais robusta, "
        "bem mais lenta (use para poucas partidas, não lotes grandes).",
        "n_simulacoes": 150,
        "profundidade_rollout": 12,
    },
}


def listar_ias() -> list[dict]:
    """Catálogo completo pra exibir na UI: chave, rótulo, descrição, categoria."""
    resultado = [
        {
            "chave": "aleatoria",
            "rotulo": "Aleatória (nível 1)",
            "descricao": "Escolhe uniformemente entre as ações legais — baseline e teste de robustez do motor.",
            "categoria": "baseline",
        },
        {
            "chave": "certinho_v2",
            "rotulo": "Certinho (referência M4/M5)",
            "descricao": "A HeuristicAI original, usada nos relatórios M4/M5 — mantida à parte do catálogo "
            "de personas pra não mudar o comportamento já testado nos relatórios anteriores.",
            "categoria": "baseline",
        },
    ]
    for chave, dados in PERSONAS.items():
        resultado.append(
            {"chave": chave, "rotulo": dados["rotulo"], "descricao": dados["descricao"], "categoria": "persona"}
        )
    for chave, dados in MCTS_VARIANTES.items():
        resultado.append(
            {"chave": chave, "rotulo": dados["rotulo"], "descricao": dados["descricao"], "categoria": "mcts"}
        )
    return resultado


def criar_ia(chave: str, seed: int | None = None):
    """Fábrica única: instancia qualquer IA do catálogo pelo nome."""
    if chave == "aleatoria":
        return RandomAI(seed=seed)
    if chave == "certinho_v2":
        return HeuristicAI(seed=seed)
    if chave in PERSONAS:
        return PersonaAI(PERSONAS[chave]["parametros"], seed=seed)
    if chave in MCTS_VARIANTES:
        variante = MCTS_VARIANTES[chave]
        return MCTSAI(
            n_simulacoes=variante["n_simulacoes"],
            profundidade_rollout=variante["profundidade_rollout"],
            seed=seed,
        )
    raise ValueError(f"IA desconhecida: {chave!r}")
