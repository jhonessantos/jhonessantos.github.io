# Relatório completo M5 — regras_v1.json

## 1. Winrate por diferença de poder (deck_forte x deck_fraco, HeuristicAI)

- **n_partidas**: 2000
- **winrate_forte**: 0.369
- **veredito**: fora da faixa saudável (60-70%) — investigar

## 2. Skill gap — MCTS+deck_fraco x HeuristicAI+deck_forte

- **n_partidas**: 7
- **winrate_ia_esperta_com_deck_fraco**: 0.143
- **veredito**: cartas mais fortes dominam sobre estratégia
- **partidas_indecisas_no_limite_de_turnos**: 93
- **nota**: N=100 (não 2000) e MCTSAI com apenas 20 simulações/6 turnos de rollout — orçamento de tempo deste ambiente não permite N maior; partidas deste jogo são naturalmente longas (ver métrica 3), o que torna MCTS caro. Resultado é indicativo, não definitivo.

## 3. Duração das partidas (deck_medio x deck_medio, HeuristicAI)

- **n_partidas**: 2000
- **media**: 202.881
- **mediana**: 202.000
- **p95**: 275
- **pct_acima_40_turnos**: 1.000

## 4. Fator Juiz (deck_medio x deck_medio, HeuristicAI)

- **n_partidas**: 2000
- **pct_partidas_com_juiz_em_campo**: 0.199
- **winrate_de_quem_joga_o_juiz**: 0.657
- **pct_viradas_com_juiz_do_lado_vencedor**: 0.069

## 5. Uso de mecânicas (deck_medio x deck_medio, HeuristicAI)

- **atacar_principal**:
  - pct_partidas_com_uso: 1.000
  - media_por_partida: 7.694
- **atacar_secundario**:
  - pct_partidas_com_uso: 0.981
  - media_por_partida: 4.162
- **atacar_terciario**:
  - pct_partidas_com_uso: 1.000
  - media_por_partida: 190.290
- **barragem_cadeia**:
  - pct_partidas_com_uso: 0.050
  - media_por_partida: 0.050
- **colocar_local**:
  - pct_partidas_com_uso: 1.000
  - media_por_partida: 5.745
- **evoluir**:
  - pct_partidas_com_uso: 0.545
  - media_por_partida: 0.729
- **guardiao_Descanso**:
  - pct_partidas_com_uso: 0.542
  - media_por_partida: 0.754
- **guardiao_Escudos**:
  - pct_partidas_com_uso: 0.574
  - media_por_partida: 0.786
- **guardiao_Oprimidos**:
  - pct_partidas_com_uso: 0.569
  - media_por_partida: 0.777
- **guardiao_Portais**:
  - pct_partidas_com_uso: 0.575
  - media_por_partida: 0.801
- **guardiao_Restauracao**:
  - pct_partidas_com_uso: 0.554
  - media_por_partida: 0.769
- **invocar_guardiao**:
  - pct_partidas_com_uso: 0.997
  - media_por_partida: 3.933
- **invocar_juiz**:
  - pct_partidas_com_uso: 0.204
  - media_por_partida: 0.217
- **invocar_mestre**:
  - pct_partidas_com_uso: 0.038
  - media_por_partida: 0.041
- **_profundidade_media_cadeia_barragem**: 2.000

## 6. Comebacks — vitórias vindo de >= 4 pontos atrás (deck_medio x deck_medio, HeuristicAI)

- **n_partidas**: 2000
- **pct_comebacks**: 0.015

## 7. Vantagem do primeiro jogador (deck_medio x deck_medio, HeuristicAI)

- **n_partidas**: 2000
- **winrate_primeiro_jogador**: 0.468
