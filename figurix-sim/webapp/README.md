# Figurix Studio (webapp)

Ambiente gráfico local para o simulador Figurix Card Game. Roda um servidor
web na sua máquina (`localhost`) — você abre no navegador, sem precisar
subir nada em nuvem.

## Fase atual: Deck Builder

- Gera decks por parâmetros (faixa de força / arquétipo / perfil de
  invocações) e mostra o resultado como cartas visuais.
- Permite editar manualmente: adicionar uma carta específica (herói de uma
  variação/raridade exata, guardião de um tipo específico, etc.) ou remover
  qualquer carta do deck.
- Salva decks num banco local (SQLite, arquivo único em `webapp/data/figurix.db`)
  para você acumular sua biblioteca de decks.

As próximas fases (rodar simulações em massa, navegar replays partida a
partida, dashboard de estatísticas, jogar contra a IA) ainda não estão
prontas — ver `figurix-sim` no rastreador de tarefas da sessão.

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
