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

  document.getElementById("btn-abrir-modal-lote").onclick = () => abrirModalLote(true);
  document.getElementById("btn-fechar-modal-lote").onclick = () => abrirModalLote(false);
  document.getElementById("btn-add-linha-lote").onclick = () => adicionarLinhaLote();
  document.getElementById("btn-gerar-lote").onclick = gerarLote;
  document.getElementById("btn-salvar-preset-lote").onclick = salvarPresetLoteAtual;
  document.getElementById("btn-excluir-preset-lote").onclick = excluirPresetLoteSelecionado;
  document.getElementById("select-preset-lote").onchange = (e) => {
    const valor = e.target.value;
    if (!valor) return;
    const separador = valor.indexOf(":");
    const tipo = valor.slice(0, separador);
    const nome = valor.slice(separador + 1);
    const preset = tipo === "exemplo" ? PRESETS_EXEMPLO_LOTE[nome] : carregarPresetsLoteSalvos()[nome];
    if (preset) carregarLinhasDoPreset(preset);
  };

  renderizarTudo();
}

function preencherFormularioGeracao() {
  preencherSelect("select-faixa-forca", CATALOGO.faixas_forca);
  preencherSelect("select-arquetipo", CATALOGO.arquetipos);
  preencherSelect("select-perfil-invocacao", CATALOGO.perfis_invocacao);
  preencherSelect("select-categoria-preferida", CATALOGO.categorias, true);
}

function preencherSelect(id, opcoes, comBranco) {
  preencherSelectEl(document.getElementById(id), opcoes, comBranco);
}

function preencherSelectEl(select, opcoes, comBranco) {
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
  const categoriaPreferida = document.getElementById("select-categoria-preferida").value;
  if (categoriaPreferida) params.categoria_preferida = categoriaPreferida;
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
  try {
    if (ESTADO.deckId) {
      resultado = await api(`/api/decks/${ESTADO.deckId}`, { method: "PUT", body: JSON.stringify(payload) });
    } else {
      resultado = await api("/api/decks", { method: "POST", body: JSON.stringify(payload) });
    }
  } catch (e) {
    alert(e.message);
    return;
  }
  ESTADO.deckId = resultado.id;
  await recarregarListaDecks();
  alert("Deck salvo: " + resultado.nome);
}

async function excluirDeck(deckId, nome) {
  if (!confirm(`Excluir o deck "${nome}"? Essa ação não pode ser desfeita.`)) return;
  await api(`/api/decks/${deckId}`, { method: "DELETE" });
  if (ESTADO.deckId === deckId) {
    novoDeckEmBranco();
  }
  await recarregarListaDecks();
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
      <span class="item-deck-excluir" title="Excluir deck">✕</span>
    `;
    item.querySelector(".item-deck-excluir").onclick = (ev) => {
      ev.stopPropagation();
      excluirDeck(d.id, d.nome);
    };
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
  heroi: ["raridade", "categoria", "variacao_id", "participante_id", "forca"],
  mestre: ["raridade", "tipo_heroi_dominado", "categoria", "forca"],
  guardiao: ["tipo_guardiao", "categoria", "raridade", "forca"],
  juiz: ["categoria", "raridade", "forca"],
  item: ["tipo_heroi", "raridade_item"],
  local: ["categoria", "raridade_item"],
  invocacao: ["categoria"],
  misto: [], // "misto balanceado" — só existe no preenchimento em lote, não no modal de carta única
};

function preencherFormularioCartaManual() {
  preencherSelect(
    "select-tipo-carta",
    Object.keys(CAMPOS_POR_TIPO).filter((tipo) => tipo !== "misto")
  );
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
    params.categoria = lerTexto("campo-categoria");
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

// ---- preenchimento em lote: N regras dinâmicas ("X cartas de Y tipo de Z categoria"),
// com uma regra opcional que completa o restante do deck automaticamente ----

const ROTULOS_TIPO_LOTE = {
  heroi: "Herói",
  mestre: "Mestre",
  guardiao: "Guardião",
  juiz: "Juiz",
  item: "Item",
  local: "Local",
  invocacao: "Invocação",
  misto: "🎲 Misto balanceado (recomendado p/ o restante)",
};

function preencherSelectRotulos(select, mapaRotulos) {
  select.innerHTML = "";
  for (const [valor, rotulo] of Object.entries(mapaRotulos)) {
    const opt = document.createElement("option");
    opt.value = valor;
    opt.textContent = rotulo;
    select.appendChild(opt);
  }
}

function abrirModalLote(mostrar) {
  const modal = document.getElementById("modal-lote");
  modal.classList.toggle("oculto", !mostrar);
  preencherSelectPresets();
  if (mostrar && document.querySelectorAll("#linhas-lote .linha-lote").length === 0) {
    adicionarLinhaLote();
  }
}

function adicionarLinhaLote() {
  const template = document.getElementById("template-linha-lote");
  const linha = template.content.firstElementChild.cloneNode(true);

  preencherSelectRotulos(linha.querySelector(".campo-lote-tipo"), ROTULOS_TIPO_LOTE);
  preencherSelectEl(linha.querySelector(".campo-lote-raridade"), CATALOGO.raridades, true);
  preencherSelectEl(linha.querySelector(".campo-lote-raridade_item"), ["comum", "rara"], true);
  preencherSelectEl(linha.querySelector(".campo-lote-categoria"), CATALOGO.categorias, true);
  preencherSelectEl(linha.querySelector(".campo-lote-tipo_guardiao"), CATALOGO.tipos_guardiao, true);

  linha.querySelector(".campo-lote-tipo").onchange = () => {
    atualizarCamposLinha(linha);
    atualizarResumoLote();
  };
  linha.querySelector(".campo-lote-resto").onchange = (e) => {
    if (e.target.checked) {
      // só 1 regra de "restante" por vez, pra manter a resolução simples e previsível
      document.querySelectorAll(".campo-lote-resto").forEach((chk) => {
        if (chk !== e.target) chk.checked = false;
      });
    }
    atualizarLinhaResto(linha);
    atualizarResumoLote();
  };
  linha.querySelector(".campo-lote-quantidade").oninput = atualizarResumoLote;
  linha.querySelector(".btn-remover-linha").onclick = () => {
    linha.remove();
    atualizarResumoLote();
  };

  document.getElementById("linhas-lote").appendChild(linha);
  atualizarCamposLinha(linha);
  atualizarResumoLote();
}

function atualizarCamposLinha(linha) {
  const tipo = linha.querySelector(".campo-lote-tipo").value;
  const camposAtivos = CAMPOS_POR_TIPO[tipo] || [];
  for (const bloco of linha.querySelectorAll(".campo-modal")) {
    bloco.classList.toggle("oculto", !camposAtivos.includes(bloco.dataset.campo));
  }
}

function atualizarLinhaResto(linha) {
  const resto = linha.querySelector(".campo-lote-resto").checked;
  linha.querySelector(".campo-lote-quantidade").disabled = resto;
  if (resto) {
    // "misto balanceado" é o valor mais útil por padrão pra quem só quer
    // completar o deck sem pensar em mais nenhum filtro
    linha.querySelector(".campo-lote-tipo").value = "misto";
    atualizarCamposLinha(linha);
  }
}

function lerRegraDaLinha(linha) {
  const tipo = linha.querySelector(".campo-lote-tipo").value;
  const lerNumeroEl = (el) => (el.value === "" ? null : parseInt(el.value, 10));
  const lerTextoEl = (el) => (el.value === "" ? null : el.value);

  const regra = { tipo_carta: tipo };
  if (tipo === "heroi") {
    regra.raridade = lerTextoEl(linha.querySelector(".campo-lote-raridade")) || "comum";
    regra.categoria = lerTextoEl(linha.querySelector(".campo-lote-categoria"));
    regra.variacao_id = lerNumeroEl(linha.querySelector(".campo-lote-variacao_id"));
    regra.participante_id = lerNumeroEl(linha.querySelector(".campo-lote-participante_id"));
    regra.forca = lerNumeroEl(linha.querySelector(".campo-lote-forca"));
  } else if (tipo === "mestre") {
    regra.raridade = lerTextoEl(linha.querySelector(".campo-lote-raridade")) || "comum";
    regra.tipo_heroi_dominado = lerNumeroEl(linha.querySelector(".campo-lote-tipo_heroi_dominado"));
    regra.categoria = lerTextoEl(linha.querySelector(".campo-lote-categoria"));
    regra.forca = lerNumeroEl(linha.querySelector(".campo-lote-forca"));
  } else if (tipo === "guardiao") {
    regra.tipo_guardiao = lerTextoEl(linha.querySelector(".campo-lote-tipo_guardiao"));
    regra.categoria = lerTextoEl(linha.querySelector(".campo-lote-categoria"));
    regra.raridade = lerTextoEl(linha.querySelector(".campo-lote-raridade"));
    regra.forca = lerNumeroEl(linha.querySelector(".campo-lote-forca"));
  } else if (tipo === "juiz") {
    regra.categoria = lerTextoEl(linha.querySelector(".campo-lote-categoria"));
    regra.raridade = lerTextoEl(linha.querySelector(".campo-lote-raridade"));
    regra.forca = lerNumeroEl(linha.querySelector(".campo-lote-forca"));
  } else if (tipo === "item") {
    regra.tipo_heroi = lerNumeroEl(linha.querySelector(".campo-lote-tipo_heroi"));
    regra.raridade = lerTextoEl(linha.querySelector(".campo-lote-raridade_item"));
  } else if (tipo === "local") {
    regra.categoria = lerTextoEl(linha.querySelector(".campo-lote-categoria"));
    regra.raridade = lerTextoEl(linha.querySelector(".campo-lote-raridade_item"));
  } else if (tipo === "invocacao") {
    regra.categoria = lerTextoEl(linha.querySelector(".campo-lote-categoria"));
  }

  return {
    regra,
    resto: linha.querySelector(".campo-lote-resto").checked,
    quantidade: parseInt(linha.querySelector(".campo-lote-quantidade").value, 10) || 0,
  };
}

function resolverQuantidadesLote() {
  const linhas = [...document.querySelectorAll("#linhas-lote .linha-lote")].map(lerRegraDaLinha);
  const fixas = linhas.filter((l) => !l.resto);
  const restos = linhas.filter((l) => l.resto);

  const somaFixas = fixas.reduce((acc, l) => acc + Math.max(0, l.quantidade), 0);
  const tamanhoAlvo = CATALOGO.tamanho_deck;
  const faltam = Math.max(0, tamanhoAlvo - ESTADO.cartas.length - somaFixas);

  const resolvidas = fixas.filter((l) => l.quantidade > 0).map((l) => ({ ...l.regra, quantidade: l.quantidade }));
  if (restos.length > 0 && faltam > 0) {
    resolvidas.push({ ...restos[0].regra, quantidade: faltam });
  }

  return { resolvidas, somaFixas, faltam, temResto: restos.length > 0, tamanhoAlvo };
}

function atualizarResumoLote() {
  const div = document.getElementById("lote-resumo");
  if (!CATALOGO) return;
  const { somaFixas, faltam, temResto, tamanhoAlvo } = resolverQuantidadesLote();
  const totalDepois = ESTADO.cartas.length + somaFixas + (temResto ? faltam : 0);

  let texto = `Deck atual: ${ESTADO.cartas.length} carta(s). Regras fixas somam ${somaFixas}.`;
  if (temResto) {
    texto += ` A regra de "restante" vai gerar ${faltam} carta(s).`;
  }
  texto += ` Total após gerar: ${totalDepois} / ${tamanhoAlvo}.`;

  div.textContent = texto;
  div.classList.toggle("completo", totalDepois === tamanhoAlvo);
  div.classList.toggle("excedente", totalDepois > tamanhoAlvo);
}

async function gerarLote() {
  const { resolvidas } = resolverQuantidadesLote();
  if (resolvidas.length === 0) {
    alert('Defina ao menos uma regra com quantidade maior que 0 (ou marque "preencher o restante").');
    return;
  }

  const resultado = await api("/api/cartas/lote", {
    method: "POST",
    body: JSON.stringify({ regras: resolvidas, cartas_existentes: ESTADO.cartas.map((c) => c.serializada) }),
  });
  ESTADO.cartas.push(...resultado.cartas);
  renderizarGrade();
  revalidar();
  abrirModalLote(false);
  document.getElementById("linhas-lote").innerHTML = "";
  document.getElementById("select-preset-lote").value = "";
}

// ---- estratégias predefinidas: salva o conjunto de regras atual com um
// nome, pra reusar depois sem remontar tudo na mão. Guardado no navegador
// (localStorage) — não precisa de servidor/banco pra isso. ----

const CHAVE_PRESETS_LOTE = "figurix_presets_lote_v1";

const PRESETS_EXEMPLO_LOTE = {
  "Abundante em invocação + resto balanceado": {
    regras: [
      { tipo: "invocacao", quantidade: 30, resto: false, campos: {} },
      { tipo: "misto", quantidade: 1, resto: true, campos: {} },
    ],
  },
  "Invocação de Ação + Heróis de Coração": {
    regras: [
      { tipo: "invocacao", quantidade: 20, resto: false, campos: { categoria: "Acao" } },
      { tipo: "heroi", quantidade: 15, resto: false, campos: { raridade: "comum", categoria: "Coracao" } },
      { tipo: "misto", quantidade: 1, resto: true, campos: {} },
    ],
  },
};

function carregarPresetsLoteSalvos() {
  try {
    return JSON.parse(localStorage.getItem(CHAVE_PRESETS_LOTE) || "{}");
  } catch (e) {
    return {};
  }
}

function salvarPresetsLoteSalvos(presets) {
  localStorage.setItem(CHAVE_PRESETS_LOTE, JSON.stringify(presets));
}

function preencherSelectPresets() {
  const select = document.getElementById("select-preset-lote");
  const valorAtual = select.value;
  select.innerHTML = "";

  const optVazio = document.createElement("option");
  optVazio.value = "";
  optVazio.textContent = "— construir do zero —";
  select.appendChild(optVazio);

  const grupoExemplos = document.createElement("optgroup");
  grupoExemplos.label = "Exemplos prontos";
  for (const nome of Object.keys(PRESETS_EXEMPLO_LOTE)) {
    const opt = document.createElement("option");
    opt.value = "exemplo:" + nome;
    opt.textContent = nome;
    grupoExemplos.appendChild(opt);
  }
  select.appendChild(grupoExemplos);

  const salvos = carregarPresetsLoteSalvos();
  const nomesSalvos = Object.keys(salvos);
  if (nomesSalvos.length > 0) {
    const grupoSalvos = document.createElement("optgroup");
    grupoSalvos.label = "Minhas estratégias";
    for (const nome of nomesSalvos) {
      const opt = document.createElement("option");
      opt.value = "salvo:" + nome;
      opt.textContent = nome;
      grupoSalvos.appendChild(opt);
    }
    select.appendChild(grupoSalvos);
  }

  select.value = valorAtual;
}

// pro tipo "item"/"local" o filtro de raridade mora num campo com classe
// diferente (campo-lote-raridade_item) do resto (campo-lote-raridade) —
// só esses dois precisam desse desvio ao restaurar um preset.
function _classeDoCampoLote(tipo, campo) {
  if (campo === "raridade" && (tipo === "item" || tipo === "local")) return "raridade_item";
  return campo;
}

function carregarLinhasDoPreset(preset) {
  document.getElementById("linhas-lote").innerHTML = "";
  for (const r of preset.regras) {
    adicionarLinhaLote();
    const linhas = document.querySelectorAll("#linhas-lote .linha-lote");
    const linha = linhas[linhas.length - 1];

    linha.querySelector(".campo-lote-quantidade").value = r.quantidade;
    linha.querySelector(".campo-lote-tipo").value = r.tipo;
    atualizarCamposLinha(linha);

    for (const [campo, valor] of Object.entries(r.campos || {})) {
      if (valor === null || valor === undefined) continue;
      const el = linha.querySelector(`.campo-lote-${_classeDoCampoLote(r.tipo, campo)}`);
      if (el) el.value = valor;
    }

    if (r.resto) {
      linha.querySelector(".campo-lote-resto").checked = true;
      atualizarLinhaResto(linha);
    }
  }
  atualizarResumoLote();
}

function extrairPresetAtual() {
  const linhas = [...document.querySelectorAll("#linhas-lote .linha-lote")];
  return {
    regras: linhas.map((linha) => {
      const lida = lerRegraDaLinha(linha);
      const campos = {};
      for (const [chave, valor] of Object.entries(lida.regra)) {
        if (chave === "tipo_carta" || valor === null || valor === undefined) continue;
        campos[chave] = valor;
      }
      return { tipo: lida.regra.tipo_carta, quantidade: lida.quantidade, resto: lida.resto, campos };
    }),
  };
}

function salvarPresetLoteAtual() {
  if (document.querySelectorAll("#linhas-lote .linha-lote").length === 0) {
    alert("Adicione ao menos uma regra antes de salvar como estratégia.");
    return;
  }
  const nome = prompt("Nome da estratégia:");
  if (!nome) return;
  const presets = carregarPresetsLoteSalvos();
  presets[nome] = extrairPresetAtual();
  salvarPresetsLoteSalvos(presets);
  preencherSelectPresets();
  document.getElementById("select-preset-lote").value = "salvo:" + nome;
}

function excluirPresetLoteSelecionado() {
  const select = document.getElementById("select-preset-lote");
  if (!select.value.startsWith("salvo:")) {
    alert("Selecione uma estratégia salva sua pra excluir (os exemplos prontos não podem ser removidos).");
    return;
  }
  const nome = select.value.slice("salvo:".length);
  const presets = carregarPresetsLoteSalvos();
  delete presets[nome];
  salvarPresetsLoteSalvos(presets);
  preencherSelectPresets();
}

iniciar();
