// upload.html 전용 스크립트 (CSP 때문에 HTML 안 인라인 스크립트 대신 파일로 둔다)
(async () => {
  const user = await App.header("upload");
  if (!App.requireLogin(user)) return;
  const error = document.getElementById("error");
  let data = null;
  document.getElementById("file").onchange = async (e) => {
    error.textContent = "";
    data = null;
    const f = e.target.files[0];
    if (!f) return;
    try {
      data = JSON.parse(await f.text());
      App.render(document.getElementById("cv"), data);
      const name = document.getElementById("name");
      if (!name.value) name.value = f.name.replace(/\.json$/i, "").slice(0, 40);
    } catch (err) {
      error.textContent = "JSON을 읽을 수 없습니다: " + err.message;
    }
  };
  document.getElementById("form").onsubmit = async (e) => {
    e.preventDefault();
    if (!data) { error.textContent = "템플릿 파일을 선택하세요."; return; }
    try {
      const r = await App.api("/api/templates", { method: "POST", body: {
        name: document.getElementById("name").value,
        category: document.getElementById("category").value,
        description: document.getElementById("description").value,
        data,
      }});
      location.href = `/template?id=${r.id}`;
    } catch (err) {
      error.textContent = err.message;
    }
  };
})();
