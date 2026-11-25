// index.html 전용 스크립트 (CSP 때문에 HTML 안 인라인 스크립트 대신 파일로 둔다)
(async () => {
  const user = await App.header("home");
  const grid = document.getElementById("grid");
  const q = document.getElementById("q");
  const sort = document.getElementById("sort");
  const cats = document.getElementById("cats");
  let category = "";

  async function load() {
    const params = new URLSearchParams({ q: q.value, sort: sort.value, category });
    const { templates, categories } = await App.api(`/api/templates?${params}`);
    cats.innerHTML = ["", ...categories].map((c) =>
      `<button class="chip ${c === category ? "on" : ""}" data-cat="${App.esc(c)}">${c ? App.esc(c) : "전체"}</button>`).join("");
    grid.innerHTML = templates.length
      ? templates.map((t) => App.cardHTML(t)).join("")
      : `<div class="empty">조건에 맞는 템플릿이 없습니다.</div>`;
    App.observePreviews(grid);
  }

  cats.onclick = (e) => {
    const b = e.target.closest("[data-cat]");
    if (b) { category = b.dataset.cat; load(); }
  };
  let t;
  q.oninput = () => { clearTimeout(t); t = setTimeout(load, 250); };
  sort.onchange = load;
  App.bindSaveButtons(grid, user, (id, saved, btn) => {
    btn.outerHTML = App.saveButton({ id, saved });
  });
  load();
})();
