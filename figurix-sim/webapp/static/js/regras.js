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

function porCaminho(obj, caminho) {
  return caminho.split(".").reduce((acc, chave) => (acc == null ? undefined : acc[chave]), obj);
}

function preencherConfig(config) {
  document.querySelectorAll("[data-cfg]").forEach((el) => {
    const valor = porCaminho(config, el.dataset.cfg);
    el.textContent = valor === undefined ? "?" : valor;
  });
}

function configurarTabs() {
  const botoes = document.querySelectorAll(".tab-botao");
  botoes.forEach((btn) => {
    btn.onclick = () => {
      botoes.forEach((b) => b.classList.remove("ativo"));
      btn.classList.add("ativo");
      document.querySelectorAll(".tab-conteudo").forEach((c) => c.classList.add("oculto"));
      document.getElementById(btn.dataset.tab).classList.remove("oculto");
    };
  });
}

const CATEGORIA_EMOJI = {
  Conexao: "🤝",
  Coracao: "❤️",
  Acao: "⚡",
  Mente: "🧠",
  Criacao: "🎨",
};

function renderizarRodaCategorias(categorias) {
  const div = document.getElementById("roda-categorias");
  categorias.forEach((cat, i) => {
    const span = document.createElement("span");
    span.className = "cat-item";
    span.textContent = `${CATEGORIA_EMOJI[cat] || ""} ${cat}`;
    div.appendChild(span);
    const seta = document.createElement("span");
    seta.className = "seta";
    seta.textContent = "▶";
    div.appendChild(seta);
  });
  // fecha o ciclo apontando de volta pro primeiro
  const volta = document.createElement("span");
  volta.className = "cat-item";
  volta.textContent = `${CATEGORIA_EMOJI[categorias[0]] || ""} ${categorias[0]}`;
  div.appendChild(volta);
}

async function novaCartaExemplo(params) {
  const resultado = await api("/api/cartas/nova", { method: "POST", body: JSON.stringify(params) });
  return criarElementoCarta(resultado, {});
}

async function renderizarCartasExemplo() {
  const exemplos = [
    { alvo: "exemplo-heroi-comum", params: { tipo_carta: "heroi", raridade: "comum", seed: 10 } },
    { alvo: "exemplo-mestre", params: { tipo_carta: "mestre", raridade: "rara", seed: 20 } },
    { alvo: "exemplo-juiz", params: { tipo_carta: "juiz", raridade: "super_rara", seed: 30 } },
    { alvo: "exemplo-item", params: { tipo_carta: "item", raridade: "rara", seed: 40 } },
    { alvo: "exemplo-local", params: { tipo_carta: "local", raridade: "comum", seed: 50 } },
    { alvo: "exemplo-invocacao", params: { tipo_carta: "invocacao", categoria: "Acao", seed: 60 } },
    { alvo: "exemplo-guardiao-portais", params: { tipo_carta: "guardiao", tipo_guardiao: "Portais", seed: 70 } },
    { alvo: "exemplo-guardiao-restauracao", params: { tipo_carta: "guardiao", tipo_guardiao: "Restauracao", seed: 71 } },
    { alvo: "exemplo-guardiao-escudos", params: { tipo_carta: "guardiao", tipo_guardiao: "Escudos", seed: 72 } },
    { alvo: "exemplo-guardiao-oprimidos", params: { tipo_carta: "guardiao", tipo_guardiao: "Oprimidos", seed: 73 } },
    { alvo: "exemplo-guardiao-descanso", params: { tipo_carta: "guardiao", tipo_guardiao: "Descanso", seed: 74 } },
  ];
  for (const ex of exemplos) {
    const el = document.getElementById(ex.alvo);
    if (!el) continue;
    try {
      el.appendChild(await novaCartaExemplo(ex.params));
    } catch (e) {
      el.textContent = "?";
    }
  }
}

async function iniciar() {
  const [config, catalogo] = await Promise.all([api("/api/config"), api("/api/catalogo")]);
  preencherConfig(config);
  renderizarRodaCategorias(catalogo.roda_vantagens);
  configurarTabs();
  await renderizarCartasExemplo();
}

iniciar();
