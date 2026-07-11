let IAS = [];
let DECKS = [];
const RESUMOS_CACHE = {}; // lote_id -> resumo_vitorias (só preciso buscar 1x depois de concluído)
const ESTATISTICAS_CACHE = {}; // lote_id -> estatísticas detalhadas (só busca quando o usuário abre o relatório)
const RELATORIOS_ABERTOS = new Set(); // lote_ids com o painel de relatório expandido
const GRUPOS_COLAPSADOS = new Set(); // grupo_ids com a lista de combinações recolhida

async function api(caminho, opcoes) {
  const resposta = await fetch(caminho, {
    headers: { "Content-Type": "application/json" },
    ...opcoes,
  });
  if (!resposta.ok) {
    const erro = await resposta.json().catch(() => ({ detail: resposta.statusText }));
    throw new Error(erro.detail || "Erro na requisição");
  }
  return resposta.json();
}

async function iniciar() {
  [IAS, DECKS] = await Promise.all([api("/api/ias"), api("/api/decks")]);
  preencherSelectMultiplo("select-ia-a", IAS, (ia) => ia.chave, (ia) => `${ia.rotulo} (${ia.categoria})`);
  preencherSelectMultiplo("select-ia-b", IAS, (ia) => ia.chave, (ia) => `${ia.rotulo} (${ia.categoria})`);
  preencherSelectMultiplo("select-deck-a", DECKS, (d) => d.id, (d) => `${d.nome} (${d.n_cartas} cartas)`);
  preencherSelectMultiplo("select-deck-b", DECKS, (d) => d.id, (d) => `${d.nome} (${d.n_cartas} cartas)`);

  document.getElementById("btn-rodar").onclick = rodarLote;
  for (const id of ["select-ia-a", "select-ia-b", "select-deck-a", "select-deck-b", "input-n-partidas"]) {
    document.getElementById(id).addEventListener("change", atualizarPreviewCombinacoes);
  }
  atualizarPreviewCombinacoes();

  await atualizarListaLotes();
  setInterval(atualizarListaLotes, 1500);
}

function preencherSelectMultiplo(id, itens, valorDe, rotuloDe) {
  const select = document.getElementById(id);
  select.innerHTML = "";
  for (const item of itens) {
    const opt = document.createElement("option");
    opt.value = valorDe(item);
    opt.textContent = rotuloDe(item);
    select.appendChild(opt);
  }
  if (select.options.length > 0) select.options[0].selected = true;
}

function valoresSelecionados(id) {
  return [...document.getElementById(id).selectedOptions].map((o) => o.value);
}

function mostrarErro(mensagem) {
  const div = document.getElementById("mensagem-erro");
  if (!mensagem) {
    div.style.display = "none";
    div.textContent = "";
    return;
  }
  div.style.display = "block";
  div.className = "violacoes";
  div.textContent = mensagem;
}

function atualizarPreviewCombinacoes() {
  const nIaA = valoresSelecionados("select-ia-a").length;
  const nIaB = valoresSelecionados("select-ia-b").length;
  const nDeckA = valoresSelecionados("select-deck-a").length;
  const nDeckB = valoresSelecionados("select-deck-b").length;
  const nPartidas = parseInt(document.getElementById("input-n-partidas").value, 10) || 0;
  const totalCombinacoes = nIaA * nIaB * nDeckA * nDeckB;

  const div = document.getElementById("preview-combinacoes");
  if (totalCombinacoes === 0) {
    div.innerHTML = "Selecione ao menos uma IA e um deck para cada lado.";
    return;
  }
  div.innerHTML = `
    Isso vai gerar <strong>${totalCombinacoes}</strong> lote(s)
    (${nIaA} IA(s) A × ${nIaB} IA(s) B × ${nDeckA} deck(s) A × ${nDeckB} deck(s) B),
    ${nPartidas} partida(s) cada — <strong>${totalCombinacoes * nPartidas}</strong> partidas no total.
  `;
}

async function rodarLote() {
  mostrarErro(null);
  const payload = {
    ia_a_chaves: valoresSelecionados("select-ia-a"),
    ia_b_chaves: valoresSelecionados("select-ia-b"),
    deck_a_ids: valoresSelecionados("select-deck-a").map((v) => parseInt(v, 10)),
    deck_b_ids: valoresSelecionados("select-deck-b").map((v) => parseInt(v, 10)),
    n_partidas: parseInt(document.getElementById("input-n-partidas").value, 10),
  };
  const seedTxt = document.getElementById("input-seed-base").value;
  if (seedTxt) payload.seed_base = parseInt(seedTxt, 10);
  const nomeTxt = document.getElementById("input-nome-lote").value;
  if (nomeTxt) payload.nome_grupo = nomeTxt;

  try {
    await api("/api/lotes/combinacoes", { method: "POST", body: JSON.stringify(payload) });
    document.getElementById("input-nome-lote").value = "";
    await atualizarListaLotes();
  } catch (e) {
    mostrarErro(e.message);
  }
}

async function atualizarListaLotes() {
  const lotes = await api("/api/lotes");
  document.getElementById("total-lotes").textContent = lotes.length;

  for (const lote of lotes) {
    if (lote.status === "concluido" && !RESUMOS_CACHE[lote.id]) {
      const detalhe = await api(`/api/lotes/${lote.id}`);
      RESUMOS_CACHE[lote.id] = detalhe.resumo_vitorias;
    }
    if (RELATORIOS_ABERTOS.has(lote.id) && !ESTATISTICAS_CACHE[lote.id] && lote.status === "concluido") {
      ESTATISTICAS_CACHE[lote.id] = await api(`/api/lotes/${lote.id}/estatisticas`);
    }
  }

  const lista = document.getElementById("lista-lotes");
  lista.innerHTML = "";

  const avulsos = lotes.filter((l) => !l.grupo_id);
  const grupos = new Map();
  for (const lote of lotes) {
    if (!lote.grupo_id) continue;
    if (!grupos.has(lote.grupo_id)) grupos.set(lote.grupo_id, []);
    grupos.get(lote.grupo_id).push(lote);
  }

  for (const [grupoId, lotesDoGrupo] of grupos) {
    lista.appendChild(criarCardGrupo(grupoId, lotesDoGrupo));
  }
  for (const lote of avulsos) {
    lista.appendChild(criarCardLote(lote));
  }
}

function criarCardGrupo(grupoId, lotesDoGrupo) {
  const div = document.createElement("div");
  div.className = "grupo-lotes";

  const concluidos = lotesDoGrupo.filter((l) => l.status === "concluido").length;
  const colapsado = GRUPOS_COLAPSADOS.has(grupoId);
  const nomeBase = lotesDoGrupo[0].nome.includes(" — ") ? lotesDoGrupo[0].nome.split(" — ")[0] : "Combinações";

  const cabecalho = document.createElement("div");
  cabecalho.className = "grupo-cabecalho";
  cabecalho.innerHTML = `
    <span class="grupo-titulo"><span class="grupo-seta ${colapsado ? "colapsada" : ""}">▾</span> ${nomeBase} (${lotesDoGrupo.length} combinações)</span>
    <span class="grupo-progresso">${concluidos} / ${lotesDoGrupo.length} concluídos</span>
  `;
  cabecalho.onclick = () => {
    if (GRUPOS_COLAPSADOS.has(grupoId)) GRUPOS_COLAPSADOS.delete(grupoId);
    else GRUPOS_COLAPSADOS.add(grupoId);
    atualizarListaLotes();
  };

  const corpo = document.createElement("div");
  corpo.className = "grupo-corpo" + (colapsado ? " colapsado" : "");
  for (const lote of lotesDoGrupo) {
    corpo.appendChild(criarCardLote(lote));
  }

  div.appendChild(cabecalho);
  div.appendChild(corpo);
  return div;
}

function pct(fracao, casas = 1) {
  if (fracao === null || fracao === undefined) return "—";
  return (fracao * 100).toFixed(casas) + "%";
}

function num(valor, casas = 1) {
  if (valor === null || valor === undefined) return "—";
  return Number(valor).toFixed(casas);
}

function escapeAttr(texto) {
  return String(texto).replace(/&/g, "&amp;").replace(/"/g, "&quot;");
}

function item(valor, rotulo, explicacao) {
  return `
    <div class="relatorio-item" title="${escapeAttr(explicacao)}">
      <div class="valor">${valor}</div><div class="rotulo">${rotulo}</div>
    </div>
  `;
}

function criarRelatorioDetalhado(stats) {
  if (!stats || stats.total === 0) {
    return `<div class="relatorio-detalhado">Sem partidas registradas ainda.</div>`;
  }
  const eventosOrdenados = Object.entries(stats.eventos_media_por_partida || {}).sort((a, b) => b[1] - a[1]);
  const analise = stats.analise || [];

  return `
    <div class="relatorio-detalhado">
      ${analise.length > 0 ? `
      <div class="relatorio-secao relatorio-analise">
        <div class="rotulo-secao">Análise automática</div>
        ${analise.map((paragrafo) => `<p>${paragrafo}</p>`).join("")}
      </div>
      ` : ""}

      <div class="relatorio-secao">
        <div class="rotulo-secao">Duração (turnos)</div>
        <div class="relatorio-grade">
          ${item(num(stats.turnos.media), "média", "Número médio de turnos (1 turno = a vez de UM jogador) até a partida terminar.")}
          ${item(num(stats.turnos.mediana, 0), "mediana", "Valor central: metade das partidas teve menos turnos que isso, metade teve mais.")}
          ${item(`${stats.turnos.min}–${stats.turnos.max}`, "min–max", "A partida mais curta e a mais longa do lote, em turnos.")}
          ${item(num(stats.turnos.media_metade_mais_curta), "média partidas curtas", "Média de turnos considerando só a metade das partidas mais curtas (abaixo da mediana).")}
          ${item(num(stats.turnos.media_metade_mais_longa), "média partidas longas", "Média de turnos considerando só a metade das partidas mais longas (acima da mediana).")}
        </div>
      </div>

      <div class="relatorio-secao">
        <div class="rotulo-secao">Duração (rodadas)</div>
        <div class="relatorio-grade">
          ${item(num(stats.rodadas.media), "média", "Número médio de rodadas (1 rodada = 1 turno de cada jogador) até a partida terminar.")}
          ${item(num(stats.rodadas.mediana, 0), "mediana", "Valor central das rodadas: metade das partidas teve menos, metade teve mais.")}
          ${item(`${stats.rodadas.min}–${stats.rodadas.max}`, "min–max", "A partida mais curta e a mais longa do lote, em rodadas.")}
        </div>
      </div>

      <div class="relatorio-secao">
        <div class="rotulo-secao">Pontuação</div>
        <div class="relatorio-grade">
          ${item(num(stats.pontos.media_pontos_a), "média pontos A", "Pontuação média do lado A ao final das partidas (vence quem chega a 10 pontos).")}
          ${item(num(stats.pontos.media_pontos_b), "média pontos B", "Pontuação média do lado B ao final das partidas (vence quem chega a 10 pontos).")}
          ${item(num(stats.pontos.media_diferenca), "diferença média", "Diferença média de pontos entre os dois lados em cada partida — quanto maior, mais lopsided o confronto tende a ser.")}
          ${item(stats.pontos.maior_margem, "maior margem", "A maior diferença de pontos observada numa única partida do lote.")}
        </div>
      </div>

      <div class="relatorio-secao">
        <div class="rotulo-secao">Mecânicas</div>
        <div class="relatorio-grade">
          ${item(pct(stats.taxa_comeback), "partidas com virada", "Em quantas partidas o vencedor já esteve perdendo por uma margem grande antes de virar o jogo.")}
          ${item(pct(stats.vantagem_primeiro_jogador.taxa_vitoria_jogando_primeiro), "vitória jogando 1º", "Entre as partidas com vencedor definido, em quantas o lado que jogou primeiro venceu — mede a vantagem de agir primeiro.")}
          ${item(`${pct(stats.taxa_juiz.a)} / ${pct(stats.taxa_juiz.b)}`, "Juiz invocado (A / B)", "Em quantas partidas o lado A/B conseguiu invocar o Juiz com sucesso — cura o herói, equaliza a força do adversário a seu favor e remove itens/guardiões/mestre do oponente.")}
          ${item(`${pct(stats.taxa_espiral.a)} / ${pct(stats.taxa_espiral.b)}`, "espiral de busca (A / B)", "Em quantas partidas o lado A/B ficou sem herói comum pra repor um derrotado, caindo na espiral de busca (mecânica punitiva, pode custar pontos de graça).")}
          ${item(`${pct(stats.taxa_mulligan_desistencia.a)} / ${pct(stats.taxa_mulligan_desistencia.b)}`, "desistência de mão (A / B)", "Em quantas partidas o lado A/B desistiu voluntariamente da mão inicial — dá 1 compra extra e, da 2ª vez em diante, 1 ponto de graça ao adversário.")}
        </div>
      </div>

      ${eventosOrdenados.length > 0 ? `
      <div class="relatorio-secao">
        <div class="rotulo-secao">Eventos em média por partida</div>
        <div class="relatorio-eventos">
          ${eventosOrdenados.map(([chave, media]) => `<span class="pill-evento" title="Quantas vezes '${escapeAttr(chave)}' aconteceu, em média, por partida (somando os dois lados).">${chave}: ${num(media, 2)}</span>`).join("")}
        </div>
      </div>
      ` : ""}
    </div>
  `;
}

function criarCardLote(lote) {
  const div = document.createElement("div");
  div.className = "card-lote";

  const pctProgresso = lote.n_partidas > 0 ? Math.round((100 * lote.progresso) / lote.n_partidas) : 0;

  let resumoHtml = "";
  const resumo = RESUMOS_CACHE[lote.id];
  if (lote.status === "concluido" && resumo && resumo.total > 0) {
    const pctA = Math.round((100 * resumo.vitorias_a) / resumo.total);
    const pctB = Math.round((100 * resumo.vitorias_b) / resumo.total);
    resumoHtml = `
      <div class="resumo-vitorias">
        <div class="barra-a">A: ${resumo.vitorias_a} (${pctA}%)</div>
        <div class="barra-b">B: ${resumo.vitorias_b} (${pctB}%)</div>
      </div>
      ${resumo.indecisas > 0 ? `<div class="meta">${resumo.indecisas} indecisas</div>` : ""}
    `;
  }

  const relatorioAberto = RELATORIOS_ABERTOS.has(lote.id);
  const relatorioHtml = relatorioAberto ? criarRelatorioDetalhado(ESTATISTICAS_CACHE[lote.id]) : "";

  div.innerHTML = `
    <div class="cabecalho">
      <div class="titulo">${lote.nome}</div>
      <div class="status ${lote.status}">${lote.status}</div>
    </div>
    <div class="meta">${lote.deck_a_nome} vs ${lote.deck_b_nome} · seed base ${lote.seed_base}</div>
    <div class="barra-progresso"><div class="preenchimento" style="width:${pctProgresso}%"></div></div>
    <div class="meta">${lote.progresso} / ${lote.n_partidas} partidas</div>
    ${resumoHtml}
    ${lote.erro_mensagem ? `<div class="erro-mensagem">${lote.erro_mensagem}</div>` : ""}
    <div class="acoes">
      ${lote.status === "concluido" ? `<button class="secundario" data-acao="relatorio" data-id="${lote.id}">${relatorioAberto ? "Ocultar relatório" : "Ver relatório"}</button>` : ""}
      <button class="perigo" data-acao="excluir" data-id="${lote.id}">Excluir</button>
    </div>
    ${relatorioHtml}
  `;

  const btnRelatorio = div.querySelector('[data-acao="relatorio"]');
  if (btnRelatorio) {
    btnRelatorio.onclick = async () => {
      if (RELATORIOS_ABERTOS.has(lote.id)) {
        RELATORIOS_ABERTOS.delete(lote.id);
      } else {
        RELATORIOS_ABERTOS.add(lote.id);
        if (!ESTATISTICAS_CACHE[lote.id]) {
          ESTATISTICAS_CACHE[lote.id] = await api(`/api/lotes/${lote.id}/estatisticas`);
        }
      }
      atualizarListaLotes();
    };
  }

  div.querySelector('[data-acao="excluir"]').onclick = async () => {
    await api(`/api/lotes/${lote.id}`, { method: "DELETE" });
    delete RESUMOS_CACHE[lote.id];
    delete ESTATISTICAS_CACHE[lote.id];
    RELATORIOS_ABERTOS.delete(lote.id);
    await atualizarListaLotes();
  };

  return div;
}

iniciar();
