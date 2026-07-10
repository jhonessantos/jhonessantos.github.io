let CATALOGO = null;
let ESTADO = { deckId: null, nome: "Novo deck", parametros: null, cartas: [] };

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
  CATALOGO = await api("/api/catalogo");
  preencherFormularioGeracao();
  preencherFormularioCartaManual();
  await recarregarListaDecks();

  document.getElementById("btn-gerar").onclick = gerarDeck;
  document.getElementById("btn-salvar").onclick = salvarDeck;
  document.getElementById("btn-novo").onclick = novoDeckEmBranco;
  document.getElementById("btn-abrir-modal-carta").onclick = () => abrirModal(true);
  document.getElementById("btn-fechar-modal").onclick = () => abrirModal(false);
  document.getElementById("btn-adicionar-carta").onclick = adicionarCartaManual;
  document.getElementById("select-tipo-carta").onchange = atualizarCamposModal;
  document.getElementById("input-nome-deck").oninput = (e) => (ESTADO.nome = e.target.value);

  renderizarTudo();
}

function preencherFormularioGeracao() {
  preencherSelect("select-faixa-forca", CATALOGO.faixas_forca);
  preencherSelect("select-arquetipo", CATALOGO.arquetipos);
  preencherSelect("select-perfil-invocacao", CATALOGO.perfis_invocacao);
}

function preencherSelect(id, opcoes, comBranco) {
  const select = document.getElementById(id);
  select.innerHTML = "";
  if (comBranco) {
    const optBranco = document.createElement("option");
    optBranco.value = "";
    optBranco.textContent = "(aleatório)";
    select.appendChild(optBranco);
  }
  for (const op of opcoes) {
    const el = document.createElement("option");
    el.value = op;
    el.textContent = op;
    select.appendChild(el);
  }
}

async function gerarDeck() {
  const params = {
    faixa_forca: document.getElementById("select-faixa-forca").value,
    arquetipo: document.getElementById("select-arquetipo").value,
    perfil_invocacoes: document.getElementById("select-perfil-invocacao").value,
  };
  const seedTxt = document.getElementById("input-seed").value;
  if (seedTxt) params.seed = parseInt(seedTxt, 10);

  const resultado = await api("/api/decks/gerar", { method: "POST", body: JSON.stringify(params) });
  ESTADO.deckId = null;
  ESTADO.parametros = resultado.parametros;
  ESTADO.cartas = resultado.cartas;
  renderizarTudo(resultado.violacoes, resultado.contagens);
}

function novoDeckEmBranco() {
  ESTADO = { deckId: null, nome: "Novo deck", parametros: null, cartas: [] };
  document.getElementById("input-nome-deck").value = ESTADO.nome;
  renderizarTudo();
}

async function revalidar() {
  const resultado = await api("/api/decks/validar", {
    method: "POST",
    body: JSON.stringify({ cartas: ESTADO.cartas.map((c) => c.serializada) }),
  });
  renderizarViolacoes(resultado.violacoes);
  renderizarContagens(resultado.contagens);
}

function renderizarTudo(violacoes, contagens) {
  renderizarGrade();
  if (violacoes) renderizarViolacoes(violacoes);
  if (contagens) renderizarContagens(contagens);
  if (!violacoes || !contagens) revalidar();
}

function renderizarGrade() {
  const grade = document.getElementById("grade-cartas");
  grade.innerHTML = "";
  for (const carta of ESTADO.cartas) {
    const el = criarElementoCarta(carta, {
      removivel: true,
      aoRemover: (c) => {
        ESTADO.cartas = ESTADO.cartas.filter((x) => x.serializada !== c.serializada);
        renderizarGrade();
        revalidar();
      },
    });
    grade.appendChild(el);
  }
  document.getElementById("total-cartas").textContent = ESTADO.cartas.length;
}

function renderizarViolacoes(violacoes) {
  const div = document.getElementById("violacoes");
  if (!violacoes || violacoes.length === 0) {
    div.className = "violacoes ok";
    div.innerHTML = "✓ Deck válido conforme as regras de construção.";
    return;
  }
  div.className = "violacoes";
  div.innerHTML = "<strong>Deck inválido:</strong><ul>" + violacoes.map((v) => `<li>${v}</li>`).join("") + "</ul>";
}

function renderizarContagens(contagens) {
  const div = document.getElementById("contagens");
  div.innerHTML = Object.entries(contagens)
    .map(([tipo, n]) => `<span class="pill">${tipo}: ${n}</span>`)
    .join("");
}

async function salvarDeck() {
  const payload = {
    nome: document.getElementById("input-nome-deck").value || "Sem nome",
    cartas: ESTADO.cartas.map((c) => c.serializada),
    parametros: ESTADO.parametros,
  };
  let resultado;
  if (ESTADO.deckId) {
    resultado = await api(`/api/decks/${ESTADO.deckId}`, { method: "PUT", body: JSON.stringify(payload) });
  } else {
    resultado = await api("/api/decks", { method: "POST", body: JSON.stringify(payload) });
  }
  ESTADO.deckId = resultado.id;
  await recarregarListaDecks();
  alert("Deck salvo: " + resultado.nome);
}

async function recarregarListaDecks() {
  const decks = await api("/api/decks");
  const lista = document.getElementById("lista-decks");
  lista.innerHTML = "";
  for (const d of decks) {
    const item = document.createElement("div");
    item.className = "item-deck";
    item.innerHTML = `
      <div class="nome">${d.nome}</div>
      <div class="meta">${d.n_cartas} cartas ${d.parametros ? "· " + d.parametros.arquetipo : ""}</div>
    `;
    item.onclick = () => abrirDeck(d.id);
    lista.appendChild(item);
  }
}

async function abrirDeck(deckId) {
  const resultado = await api(`/api/decks/${deckId}`);
  ESTADO.deckId = resultado.id;
  ESTADO.nome = resultado.nome;
  ESTADO.parametros = resultado.parametros;
  ESTADO.cartas = resultado.cartas;
  document.getElementById("input-nome-deck").value = resultado.nome;
  renderizarTudo(resultado.violacoes, resultado.contagens);
}

// ---- modal de carta manual ----

const CAMPOS_POR_TIPO = {
  heroi: ["raridade", "variacao_id", "participante_id", "forca"],
  mestre: ["raridade", "tipo_heroi_dominado", "categoria", "forca"],
  guardiao: ["tipo_guardiao", "categoria", "raridade", "forca"],
  juiz: ["categoria", "raridade", "forca"],
  item: ["tipo_heroi", "raridade_item"],
  local: ["categoria", "raridade_item"],
  invocacao: ["categoria"],
};

function preencherFormularioCartaManual() {
  preencherSelect("select-tipo-carta", Object.keys(CAMPOS_POR_TIPO));
  preencherSelect("campo-raridade", CATALOGO.raridades, true);
  preencherSelect("campo-raridade_item", ["comum", "rara"], true);
  preencherSelect("campo-categoria", CATALOGO.categorias, true);
  preencherSelect("campo-tipo_guardiao", CATALOGO.tipos_guardiao, true);
  atualizarCamposModal();
}

function atualizarCamposModal() {
  const tipo = document.getElementById("select-tipo-carta").value;
  const camposAtivos = CAMPOS_POR_TIPO[tipo] || [];
  for (const linha of document.querySelectorAll(".campo-modal")) {
    linha.classList.toggle("oculto", !camposAtivos.includes(linha.dataset.campo));
  }
}

function abrirModal(mostrar) {
  document.getElementById("modal-carta").classList.toggle("oculto", !mostrar);
}

async function adicionarCartaManual() {
  const tipo = document.getElementById("select-tipo-carta").value;
  const params = { tipo_carta: tipo };

  const lerNumero = (id) => {
    const v = document.getElementById(id).value;
    return v === "" ? null : parseInt(v, 10);
  };
  const lerTexto = (id) => {
    const v = document.getElementById(id).value;
    return v === "" ? null : v;
  };

  if (tipo === "heroi") {
    params.raridade = lerTexto("campo-raridade") || "comum";
    params.variacao_id = lerNumero("campo-variacao_id");
    params.participante_id = lerNumero("campo-participante_id");
    params.forca = lerNumero("campo-forca");
  } else if (tipo === "mestre") {
    params.raridade = lerTexto("campo-raridade") || "comum";
    params.tipo_heroi_dominado = lerNumero("campo-tipo_heroi_dominado");
    params.categoria = lerTexto("campo-categoria");
    params.forca = lerNumero("campo-forca");
  } else if (tipo === "guardiao") {
    params.tipo_guardiao = lerTexto("campo-tipo_guardiao");
    params.categoria = lerTexto("campo-categoria");
    params.raridade = lerTexto("campo-raridade");
    params.forca = lerNumero("campo-forca");
  } else if (tipo === "juiz") {
    params.categoria = lerTexto("campo-categoria");
    params.raridade = lerTexto("campo-raridade");
    params.forca = lerNumero("campo-forca");
  } else if (tipo === "item") {
    params.tipo_heroi = lerNumero("campo-tipo_heroi");
    params.raridade = lerTexto("campo-raridade_item");
  } else if (tipo === "local") {
    params.categoria = lerTexto("campo-categoria");
    params.raridade = lerTexto("campo-raridade_item");
  } else if (tipo === "invocacao") {
    params.categoria = lerTexto("campo-categoria");
  }

  const resultado = await api("/api/cartas/nova", { method: "POST", body: JSON.stringify(params) });
  ESTADO.cartas.push(resultado);
  renderizarGrade();
  revalidar();
  abrirModal(false);
}

iniciar();
