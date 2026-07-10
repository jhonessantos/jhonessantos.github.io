# Figurix Studio (webapp)

Ambiente gráfico local para o simulador Figurix Card Game. Roda um servidor
web na sua máquina (`localhost`) — você abre no navegador, sem precisar
subir nada em nuvem.

## O que já tem

- **Deck Builder** (`/`): gera decks por parâmetros (faixa de força /
  arquétipo / perfil de invocações), edita manualmente carta por carta, e
  tem um **preenchimento em lote** por regras dinâmicas ("X cartas de tipo
  Y de categoria Z" + uma regra opcional de "misto balanceado" que completa
  o resto do deck sozinha) — inclusive com estratégias predefinidas
  salváveis. Decks ficam num banco local (SQLite).
- **IAs** (`/ias`): catálogo com 20 personalidades de IA (2 baselines + 15
  personas parametrizáveis + 3 variantes de MCTS).
- **Regras** (`/regras`): enciclopédia de cada tipo de carta + tutorial
  passo a passo de como jogar — todos os números vêm do config oficial.
- **Simulações** (`/simulacoes`): motor de simulação em massa — escolhe IA
  A/B, deck A/B, quantas partidas, e roda em segundo plano (dá pra rodar
  milhares/milhões de partidas e ver o progresso/resultado depois).

Próximas fases (replay passo a passo, dashboard de estatísticas, jogar
contra a IA) ainda não estão prontas.

## Como rodar na sua máquina

Pré-requisitos: Python 3.11+ (o mesmo usado pelo resto do `figurix-sim`).

```bash
cd figurix-sim/webapp
pip install -r requirements-webapp.txt
python3 -m uvicorn app:app --reload --port 8765
```

Depois abra **http://localhost:8765** no navegador.

`--reload` reinicia o servidor sozinho quando você (ou eu, numa próxima
sessão) editar os arquivos Python — útil durante o desenvolvimento; pode
tirar esse parâmetro para rodar "em produção" local.

Os decks ficam salvos em `webapp/data/figurix.db` entre uma sessão e
outra (esse arquivo não vai para o git — é seu banco local).
