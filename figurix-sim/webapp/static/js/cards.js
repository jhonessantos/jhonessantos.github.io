// Renderiza o view model de uma carta (produzido por card_view.py) como um
// elemento DOM, seguindo a convenção visual definida com o usuário:
//   - Herói/Mestre/Guardião/Juiz: emoji de categoria + letra (H/M/G/J) +
//     força no canto superior direito + nome embaixo.
//   - Item de herói: "I" + emoji do herói vinculado + nome do herói embaixo.
//   - Local: emoji da categoria + "L".
//   - Invocação: emoji grande centralizado, fundo na cor da categoria.

function criarElementoCarta(carta, opcoes) {
  opcoes = opcoes || {};
  const view = carta.view;
  const div = document.createElement("div");
  div.className = "carta carta-" + view.tipo_carta;
  div.title = tituloCarta(view);

  if (view.tipo_carta === "invocacao") {
    div.style.background = view.cor_categoria;
    div.innerHTML = `<span class="carta-emoji carta-emoji-grande">${view.emoji}</span>`;
  } else if (view.tipo_carta === "local") {
    div.style.borderColor = view.cor_raridade || "#666";
    div.innerHTML = `
      ${raridadeBadge(view)}
      <span class="carta-emoji">${view.emoji}</span>
      <span class="carta-letra">${view.letra}</span>
    `;
  } else if (view.tipo_carta === "item") {
    div.style.borderColor = view.cor_raridade || "#666";
    div.innerHTML = `
      ${raridadeBadge(view)}
      <div class="carta-emoji-linha">
        <span class="carta-letra">${view.letra}</span>
        <span class="carta-emoji">${view.emoji}</span>
      </div>
      <div class="carta-nome">${view.nome || ""}</div>
    `;
  } else {
    // heroi | mestre | guardiao | juiz
    div.style.borderColor = view.cor_raridade || "#666";
    div.innerHTML = `
      ${view.forca !== null ? `<div class="carta-forca">${view.forca}</div>` : ""}
      ${view.especial ? `<div class="carta-especial-badge">★</div>` : ""}
      ${raridadeBadge(view)}
      <div class="carta-emoji-linha">
        <span class="carta-emoji">${view.emoji}</span>
        <span class="carta-letra">${view.letra}</span>
      </div>
      <div class="carta-nome">${view.nome || ""}</div>
    `;
  }

  if (opcoes.removivel) {
    const btn = document.createElement("span");
    btn.className = "carta-remover";
    btn.textContent = "remover";
    btn.onclick = (ev) => {
      ev.stopPropagation();
      opcoes.aoRemover(carta);
    };
    div.appendChild(btn);
  }

  if (opcoes.aoClicar) {
    div.addEventListener("click", () => opcoes.aoClicar(carta));
  }

  return div;
}

function raridadeBadge(view) {
  return view.raridade_emoji ? `<div class="carta-raridade-badge">${view.raridade_emoji}</div>` : "";
}

function tituloCarta(view) {
  const partes = [view.nome || view.tipo_carta];
  if (view.raridade) partes.push(view.raridade);
  if (view.forca !== null && view.forca !== undefined) partes.push(`força ${view.forca}`);
  if (view.extra && view.extra.poder_principal !== undefined) {
    partes.push(`poderes ${view.extra.poder_principal}/${view.extra.poder_secundario}/${view.extra.poder_terciario}`);
  }
  return partes.join(" — ");
}
