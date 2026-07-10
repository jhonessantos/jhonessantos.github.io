let IAS = [];
let DECKS = [];
const RESUMOS_CACHE = {}; // lote_id -> resumo_vitorias (só preciso buscar 1x depois de concluído)

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
  preencherSelect("select-ia-a", IAS, (ia) => ia.chave, (ia) => `${ia.rotulo} (${ia.categoria})`);
  preencherSelect("select-ia-b", IAS, (ia) => ia.chave, (ia) => `${ia.rotulo} (${ia.categoria})`);
  preencherSelect("select-deck-a", DECKS, (d) => d.id, (d) => `${d.nome} (${d.n_cartas} cartas)`);
  preencherSelect("select-deck-b", DECKS, (d) => d.id, (d) => `${d.nome} (${d.n_cartas} cartas)`);

  document.getElementById("btn-rodar").onclick = rodarLote;

  await atualizarListaLotes();
  setInterval(atualizarListaLotes, 1500);
}

function preencherSelect(id, itens, valorDe, rotuloDe) {
  const select = document.getElementById(id);
  select.innerHTML = "";
  for (const item of itens) {
    const opt = document.createElement("option");
    opt.value = valorDe(item);
    opt.textContent = rotuloDe(item);
    select.appendChild(opt);
  }
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

async function rodarLote() {
  mostrarErro(null);
  const payload = {
    ia_a_chave: document.getElementById("select-ia-a").value,
    ia_b_chave: document.getElementById("select-ia-b").value,
    deck_a_id: parseInt(document.getElementById("select-deck-a").value, 10),
    deck_b_id: parseInt(document.getElementById("select-deck-b").value, 10),
    n_partidas: parseInt(document.getElementById("input-n-partidas").value, 10),
  };
  const seedTxt = document.getElementById("input-seed-base").value;
  if (seedTxt) payload.seed_base = parseInt(seedTxt, 10);
  const nomeTxt = document.getElementById("input-nome-lote").value;
  if (nomeTxt) payload.nome = nomeTxt;

  try {
    await api("/api/lotes", { method: "POST", body: JSON.stringify(payload) });
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
  }

  const lista = document.getElementById("lista-lotes");
  lista.innerHTML = "";
  for (const lote of lotes) {
    lista.appendChild(criarCardLote(lote));
  }
}

function criarCardLote(lote) {
  const div = document.createElement("div");
  div.className = "card-lote";

  const pct = lote.n_partidas > 0 ? Math.round((100 * lote.progresso) / lote.n_partidas) : 0;

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

  div.innerHTML = `
    <div class="cabecalho">
      <div class="titulo">${lote.nome}</div>
      <div class="status ${lote.status}">${lote.status}</div>
    </div>
    <div class="meta">${lote.deck_a_nome} vs ${lote.deck_b_nome} · seed base ${lote.seed_base}</div>
    <div class="barra-progresso"><div class="preenchimento" style="width:${pct}%"></div></div>
    <div class="meta">${lote.progresso} / ${lote.n_partidas} partidas</div>
    ${resumoHtml}
    ${lote.erro_mensagem ? `<div class="erro-mensagem">${lote.erro_mensagem}</div>` : ""}
    <div class="acoes"><button class="perigo" data-id="${lote.id}">Excluir</button></div>
  `;

  div.querySelector(".acoes button").onclick = async () => {
    await api(`/api/lotes/${lote.id}`, { method: "DELETE" });
    delete RESUMOS_CACHE[lote.id];
    await atualizarListaLotes();
  };

  return div;
}

iniciar();
