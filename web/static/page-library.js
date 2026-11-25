// library.html 전용 스크립트 (CSP 때문에 HTML 안 인라인 스크립트 대신 파일로 둔다)
(async () => {
  const user = await App.header("library");
  if (!App.requireLogin(user)) return;
  const grid = document.getElementById("grid");

  async function loadLibrary() {
    const list = await App.api("/api/library");
    grid.innerHTML = list.length
      ? list.map((t, i) => App.cardHTML(t).replace('<span class="tag">', `<span class="tag">#${i + 1} · `)
          .replace("</div></div>", `<div class="cmd">/tb build ${i + 1}</div></div></div>`)).join("")
      : `<div class="empty">보관함이 비었습니다. <a href="/">템플릿 둘러보기 →</a></div>`;
    App.observePreviews(grid);
  }
  if (new URLSearchParams(location.search).get("verified")) App.toast("이메일 인증이 끝났어요. 환영해요!");
  App.bindSaveButtons(grid, user, () => loadLibrary());
  loadLibrary();
})();
