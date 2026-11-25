// template.html 전용 스크립트 (CSP 때문에 HTML 안 인라인 스크립트 대신 파일로 둔다)
(async () => {
  const user = await App.header("home");
  const id = new URLSearchParams(location.search).get("id");
  const root = document.getElementById("detail");
  let t;
  try {
    t = await App.api(`/api/templates/${encodeURIComponent(id)}`);
  } catch (err) {
    root.innerHTML = `<div class="empty">${App.esc(err.message)}</div>`;
    return;
  }
  document.title = `${t.name} · 블루프린트`;
  // 재료 목록: 서버가 아이템 단위(한국어 이름 + 아이콘)로 계산. 에셋이 없으면 블록 id 로 대체
  const mats = t.materials || [];
  const matHTML = mats.map((m) => `<li>
      ${m.icon ? `<img class="swatch icon" src="${m.icon}" alt="" loading="lazy">` : `<span class="swatch"></span>`}
      <span style="flex:1">${App.esc(m.name)}</span><span>${m.count.toLocaleString()}</span></li>`).join("");

  root.innerHTML = `
    <div class="viewer">
      ${t.thumbnail ? `<img id="img" class="render" src="${t.thumbnail}" alt="${App.esc(t.name)} 미리보기">` : `<canvas id="cv"></canvas>`}
      <div class="layer">높이 <input type="range" id="layer" min="0" max="${t.size[1] - 1}" value="${t.size[1] - 1}"><span id="lv">${t.size[1]}</span></div>
      <div class="controls">
        <button class="btn ghost" id="rl" title="왼쪽으로 회전">⟲</button>
        <button class="btn ghost" id="rr" title="오른쪽으로 회전">⟳</button>
      </div>
    </div>
    <div>
      <span class="tag">${App.esc(t.category)}</span>
      <h1 style="margin:10px 0 6px">${App.esc(t.name)}</h1>
      <p class="hint" style="line-height:1.6">${App.esc(t.description) || "설명이 없습니다."}</p>
      <dl class="specs">
        <dt>크기 (X×Y×Z)</dt><dd>${t.size.join(" × ")}</dd>
        <dt>블록 수</dt><dd>${t.blockCount.toLocaleString()}</dd>
        <dt>제작자</dt><dd>${App.esc(t.author || "기본 제공")}</dd>
        <dt>보관한 사람</dt><dd>${t.saves}</dd>
      </dl>
      <div style="display:flex;gap:8px;flex-wrap:wrap" id="actions">${App.saveButton(t)}
        ${t.canEdit ? `<button class="btn ghost" id="edit">수정</button>` : ""}
        ${t.mine ? `<button class="btn ghost" id="del">삭제</button>` : ""}
        <button class="btn ghost" id="dl">JSON 다운로드</button></div>
      ${t.canEdit ? `<form class="panel edit-form" id="editForm" hidden>
        <h3 style="margin:0">템플릿 수정</h3>
        <label for="eName">이름</label>
        <input id="eName" maxlength="40" required value="${App.esc(t.name)}">
        <label for="eCat">분류</label>
        <input id="eCat" maxlength="20" list="eCats" value="${App.esc(t.category)}">
        <datalist id="eCats"><option>주거</option><option>방어</option><option>장식</option><option>상업</option><option>기타</option></datalist>
        <label for="eDesc">설명</label>
        <textarea id="eDesc" rows="3" maxlength="500">${App.esc(t.description)}</textarea>
        <label for="eFile">템플릿 파일 바꾸기 (선택)</label>
        <input id="eFile" type="file" accept=".json,application/json">
        <div class="hint">파일을 고르지 않으면 건물 내용은 그대로 두고 이름·분류·설명만 바꿔요.</div>
        <div style="display:flex;gap:8px;margin-top:14px">
          <button class="btn primary" type="submit">저장</button>
          <button class="btn ghost" type="button" id="editCancel">취소</button>
        </div>
        <div class="error" id="editErr" role="alert"></div>
      </form>` : ""}
      <h3 style="margin:24px 0 8px">재료 목록</h3>
      <ul class="palette">${matHTML}</ul>
    </div>`;

  const layer = document.getElementById("layer");
  const img = document.getElementById("img");
  let rotation = 0;
  let draw;
  if (img) {
    // 서버가 실제 블록 텍스처로 그린 이미지: 회전/높이를 바꾸면 다시 요청
    draw = () => {
      const top = +layer.value;
      document.getElementById("lv").textContent = top + 1;
      const params = new URLSearchParams({ rot: rotation });
      if (top < t.size[1] - 1) params.set("maxY", top);
      img.classList.add("loading");
      img.src = `${t.thumbnail}?${params}`;
    };
    img.onload = () => img.classList.remove("loading");
    layer.onchange = draw;
    layer.oninput = () => { document.getElementById("lv").textContent = +layer.value + 1; };
  } else {
    const cv = document.getElementById("cv");
    draw = () => {
      document.getElementById("lv").textContent = +layer.value + 1;
      App.render(cv, t.data, { rotation: (rotation + 2) % 4, maxY: +layer.value });
    };
    layer.oninput = draw;
    addEventListener("resize", draw);
    draw();
  }
  document.getElementById("rl").onclick = () => { rotation = (rotation + 3) % 4; draw(); };
  document.getElementById("rr").onclick = () => { rotation = (rotation + 1) % 4; draw(); };

  App.bindSaveButtons(document.getElementById("actions"), user, (_id, saved, btn) => {
    t.saved = saved;
    btn.outerHTML = App.saveButton(t);
  });
  document.getElementById("dl").onclick = () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(t.data)], { type: "application/json" }));
    a.download = `${t.name}.json`;
    a.click();
  };
  const editForm = document.getElementById("editForm");
  if (editForm) {
    document.getElementById("edit").onclick = () => { editForm.hidden = !editForm.hidden; };
    document.getElementById("editCancel").onclick = () => { editForm.hidden = true; };
    editForm.onsubmit = async (e) => {
      e.preventDefault();
      const errEl = document.getElementById("editErr");
      const body = { name: document.getElementById("eName").value, category: document.getElementById("eCat").value,
                     description: document.getElementById("eDesc").value };
      const file = document.getElementById("eFile").files[0];
      try {
        if (file) body.data = JSON.parse(await file.text());
      } catch {
        errEl.textContent = "JSON 파일을 읽지 못했어요. 형식을 확인해 주세요.";
        return;
      }
      try {
        await App.api(`/api/templates/${t.id}`, { method: "PUT", body });
        App.toast("수정했어요.");
        location.reload();
      } catch (err) {
        errEl.textContent = err.message;
      }
    };
  }
  document.getElementById("del")?.addEventListener("click", async () => {
    if (!confirm("이 템플릿을 삭제할까요? 다른 사람의 보관함에서도 사라집니다.")) return;
    await App.api(`/api/templates/${t.id}`, { method: "DELETE" });
    location.href = "/";
  });
})();
