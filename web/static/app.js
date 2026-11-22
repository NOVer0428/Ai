// 공통 유틸: API 호출, 헤더, 토스트, 아이소메트릭 미리보기

// 우클릭·텍스트 선택·끌기 막기 (입력칸과 복사용 코드 칸은 예외). 화면 보호용이며 개발자 도구까지 막지는 못한다
(() => {
  const editable = (node) => {
    const el = node?.nodeType === 3 ? node.parentElement : node;  // 글자 노드면 부모 요소로
    return el?.closest?.("input, textarea, select, [contenteditable], .cmd, .link-code, .fresh-key .mono, .suggest-code");
  };
  document.addEventListener("contextmenu", (e) => { if (!editable(e.target)) e.preventDefault(); });
  document.addEventListener("selectstart", (e) => { if (!editable(e.target)) e.preventDefault(); });
  document.addEventListener("dragstart", (e) => { if (!editable(e.target)) e.preventDefault(); });
})();

const App = (() => {
  async function api(path, { method = "GET", body } = {}) {
    const opts = { method, headers: {}, credentials: "same-origin" };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(path, opts);
    const data = await res.json().catch(() => null);
    if (!res.ok) throw Object.assign(new Error(data?.error || `요청 실패 (${res.status})`), { status: res.status, data });
    return data;
  }

  let mePromise;
  const me = () => (mePromise ??= api("/api/auth/me"));

  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  }

  async function header(active) {
    const el = document.createElement("header");
    el.className = "site";
    el.innerHTML = `<div class="wrap">
      <a class="logo" href="/"><span class="mark"></span><span>블루프린트</span></a>
      <nav class="main">
        <a href="/" data-k="home">템플릿</a>
        <a href="/library" data-k="library">내 보관함</a>
        <a href="/upload" data-k="upload">업로드</a>
      </nav>
      <div class="userbox"></div></div>`;
    el.querySelector(`[data-k="${active}"]`)?.classList.add("active");
    document.body.prepend(el);
    // 모든 페이지 아래쪽: 약관·처리방침·저작권 링크와 마인크래프트 비공식 고지
    if (!document.querySelector("footer.site")) {
      const ft = document.createElement("footer");
      ft.className = "site";
      ft.innerHTML = `<div class="wrap">
        <nav aria-label="사이트 정책"><a href="/terms">이용약관</a><a href="/privacy"><b>개인정보 처리방침</b></a><a href="/copyright">게시물·저작권 정책</a></nav>
        <p>문의 modagi1222@gmail.com</p>
        <p class="mc-notice">NOT AN OFFICIAL MINECRAFT PRODUCT. NOT APPROVED BY OR ASSOCIATED WITH MOJANG OR MICROSOFT.<br>
          블루프린트는 Minecraft 공식 제품이 아니며 Mojang·Microsoft와 관련이 없습니다.</p></div>`;
      document.body.append(ft);
    }
    passwordToggles();  // 로그인·회원가입처럼 처음부터 있는 비밀번호 칸
    const box = el.querySelector(".userbox");
    const user = await me().catch(() => null);
    if (user) {
      if (user.isStaff) {  // 메인·부 관리자 모두 관리자 메뉴
        el.querySelector("nav.main").insertAdjacentHTML("beforeend", `<a href="/admin" data-k="admin">관리자</a>`);
        el.querySelector(`[data-k="${active}"]`)?.classList.add("active");
      }
      const face = user.avatar
        ? `<img class="mini-avatar" src="${esc(user.avatar)}" alt="">`
        : `<span class="mini-avatar" aria-hidden="true">${esc(user.username.slice(0, 1).toUpperCase())}</span>`;
      box.innerHTML = `<a href="/profile" title="내 프로필" style="color:inherit;text-decoration:none;font-weight:700;display:flex;align-items:center;gap:8px">${face}<span>${user.isAdmin ? "" : `<span class="status-dot ${user.linkedServers ? "on" : ""}"></span>`}${esc(user.username)}</span></a>
        <button class="btn ghost" id="logout">로그아웃</button>`;
      box.querySelector("#logout").onclick = async () => {
        await api("/api/auth/logout", { method: "POST" });
        location.href = "/";
      };
    } else {
      box.innerHTML = `<a class="btn ghost" href="/login">로그인</a><a class="btn primary" href="/register">회원가입</a>`;
    }
    return user;
  }

  function toast(msg) {
    let t = document.querySelector(".toast");
    if (!t) {
      t = document.createElement("div");
      t.className = "toast";
      document.body.append(t);
    }
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(t._h);
    t._h = setTimeout(() => t.classList.remove("show"), 2200);
  }

  function requireLogin(user) {
    if (!user) location.href = `/login?next=${encodeURIComponent(location.pathname + location.search)}`;
    return !!user;
  }

  // ---------------------------------------------------------------- 블록 색상
  const COLORS = [
    ["water_cauldron", "#3a3a3e"], ["lava_cauldron", "#3a3a3e"], ["cauldron", "#3a3a3e"],
    ["water", "#3f76e4"], ["lava", "#e5641c"], ["glass", "#bfe3ec"], ["iron_bars", "#8c8f93"],
    ["calcite", "#e3e1da"], ["white_terracotta", "#d6c2b3"], ["deepslate_tile", "#3e4553"],
    ["mossy", "#6c7a55"], ["cracked_stone", "#767676"], ["campfire", "#7a5a36"],
    ["red_bed", "#a12722"], ["bookshelf", "#7b5a36"], ["anvil", "#47474b"], ["grindstone", "#8a8a8a"],
    ["blast_furnace", "#5a5a5e"], ["smoker", "#5e4d3c"], ["smithing", "#3c3b4a"], ["dirt_path", "#947a45"],
    ["potted", "#c2412d"],
    ["torch", "#ffcf4a"], ["lantern", "#f2b63c"], ["ladder", "#a07c45"],
    ["red_wool", "#b02e26"], ["white_wool", "#e9ecec"], ["wool", "#d8d8d8"],
    ["moss", "#5a7d2b"], ["azalea", "#6c9b35"], ["leaves", "#3f7a2a"], ["grass", "#6aa84f"],
    ["birch", "#d7c98d"], ["spruce", "#6b4f2f"], ["dark_oak", "#4a3221"], ["jungle", "#a8754f"],
    ["acacia", "#b2603a"], ["cherry", "#e3b3ab"], ["mangrove", "#773b34"],
    ["oak_log", "#6d5432"], ["oak", "#b08a52"],
    ["stone_brick", "#7d7d7d"], ["cobblestone", "#808080"], ["smooth_stone", "#a3a3a3"],
    ["deepslate", "#4d4d50"], ["sandstone", "#d9cc93"], ["sand", "#dbcf9c"], ["brick", "#975a4a"],
    ["quartz", "#ece6df"], ["terracotta", "#a0624a"], ["concrete", "#9e9e9e"],
    ["barrel", "#7d5b35"], ["crafting", "#9c7448"], ["furnace", "#6e6e6e"], ["chest", "#a9772f"],
    ["gold", "#f3d045"], ["iron", "#d8d8d8"], ["diamond", "#5fd9d0"], ["dirt", "#86603e"],
    ["stone", "#8f8f8f"],
  ];
  const colorCache = new Map();
  function blockColor(name) {
    if (colorCache.has(name)) return colorCache.get(name);
    const id = name.replace(/^minecraft:/, "").replace(/\[.*$/, "");
    let c = COLORS.find(([k]) => id.includes(k))?.[1];
    if (!c) {
      let h = 0;
      for (const ch of id) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
      c = `hsl(${h % 360} 30% 55%)`;
    }
    colorCache.set(name, c);
    return c;
  }

  function shade(hex, f) {
    if (!hex.startsWith("#")) return hex.replace(/(\d+)%\)$/, (_, l) => `${Math.round(l * f)}%)`);
    const n = parseInt(hex.slice(1), 16);
    const ch = (v) => Math.max(0, Math.min(255, Math.round(v * f)));
    return `rgb(${ch(n >> 16)}, ${ch((n >> 8) & 255)}, ${ch(n & 255)})`;
  }

  function shapeOf(name) {
    const id = name.replace(/\[.*$/, "");
    if (/slab|carpet|pressure_plate/.test(id) && !/type=double/.test(name)) return { h: 0.5, w: 1 };
    if (/torch|lantern|flower|sapling|button|lever|rail/.test(id)) return { h: 0.6, w: 0.35 };
    if (/pane|bars|fence|wall|ladder|door/.test(id)) return { h: 1, w: 0.4 };
    return { h: 1, w: 1 };
  }

  // ---------------------------------------------------------------- 아이소메트릭 렌더러
  // rotation 2 = 정면(z = 0, 입구 쪽)이 보이는 기본 각도
  function render(canvas, data, { rotation = 2, maxY = Infinity, zoom = 1 } = {}) {
    const dpr = window.devicePixelRatio || 1;
    const W = canvas.clientWidth, H = canvas.clientHeight;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);

    const [sx, sy, sz] = data.size;
    const rot = (x, z) => {
      switch (rotation & 3) {
        case 0: return [x, z];
        case 1: return [sz - 1 - z, x];
        case 2: return [sx - 1 - x, sz - 1 - z];
        default: return [z, sx - 1 - x];
      }
    };
    const occ = new Set();
    const list = [];
    for (const [x, y, z, i] of data.blocks) {
      if (y > maxY) continue;
      const [rx, rz] = rot(x, z);
      const name = data.palette[i];
      const shape = shapeOf(name);
      if (shape.w === 1 && shape.h === 1 && !/glass|water/.test(name)) occ.add(`${rx},${y},${rz}`);
      list.push({ x: rx, y, z: rz, name, shape });
    }
    // 세 방향(+x, +y, +z)이 모두 막힌 블록은 보이지 않으므로 생략
    const visible = list.filter((b) => !(occ.has(`${b.x + 1},${b.y},${b.z}`) && occ.has(`${b.x},${b.y + 1},${b.z}`) && occ.has(`${b.x},${b.y},${b.z + 1}`)));
    visible.sort((a, b) => a.x + a.y + a.z - (b.x + b.y + b.z) || a.y - b.y);

    const [rsx, rsz] = rotation & 1 ? [sz, sx] : [sx, sz];
    const proj = (x, y, z) => [(x - z) * 0.866, (x + z) * 0.5 - y];
    const corners = [[0, 0, 0], [rsx, 0, 0], [0, 0, rsz], [rsx, 0, rsz], [0, sy, 0], [rsx, sy, 0], [0, sy, rsz], [rsx, sy, rsz]].map((c) => proj(...c));
    const minX = Math.min(...corners.map((c) => c[0])), maxX = Math.max(...corners.map((c) => c[0]));
    const minY = Math.min(...corners.map((c) => c[1])), maxYp = Math.max(...corners.map((c) => c[1]));
    const scale = Math.min((W - 24) / (maxX - minX), (H - 24) / (maxYp - minY)) * zoom;
    const ox = W / 2 - ((minX + maxX) / 2) * scale;
    const oy = H / 2 - ((minY + maxYp) / 2) * scale;
    const P = (x, y, z) => { const [px, py] = proj(x, y, z); return [ox + px * scale, oy + py * scale]; };

    const poly = (pts, fill) => {
      ctx.beginPath();
      ctx.moveTo(...pts[0]);
      for (const p of pts.slice(1)) ctx.lineTo(...p);
      ctx.closePath();
      ctx.fillStyle = fill;
      ctx.fill();
      ctx.stroke();
    };
    ctx.lineWidth = Math.max(0.3, scale * 0.03);
    ctx.lineJoin = "round";
    ctx.strokeStyle = "rgba(0,0,0,0.25)";

    for (const b of visible) {
      const { w, h } = b.shape;
      const pad = (1 - w) / 2;
      const x0 = b.x + pad, x1 = b.x + 1 - pad, z0 = b.z + pad, z1 = b.z + 1 - pad;
      const y0 = b.y, y1 = b.y + h;
      const base = blockColor(b.name);
      ctx.globalAlpha = /glass|water/.test(b.name) ? 0.55 : 1;
      if (!occ.has(`${b.x},${b.y},${b.z + 1}`) || w < 1) poly([P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)], shade(base, 0.72));
      if (!occ.has(`${b.x + 1},${b.y},${b.z}`) || w < 1) poly([P(x1, y0, z0), P(x1, y0, z1), P(x1, y1, z1), P(x1, y1, z0)], shade(base, 0.86));
      if (!occ.has(`${b.x},${b.y + 1},${b.z}`) || h < 1) poly([P(x0, y1, z0), P(x1, y1, z0), P(x1, y1, z1), P(x0, y1, z1)], shade(base, 1.08));
    }
    ctx.globalAlpha = 1;
  }

  function cardHTML(t, { showSave = true } = {}) {
    return `<div class="card" data-id="${t.id}">
      <a href="/template?id=${t.id}" class="thumb-link">${thumbHTML(t)}</a>
      <div class="body">
        <span class="tag">${esc(t.category)}</span>
        <h3><a href="/template?id=${t.id}" style="text-decoration:none">${esc(t.name)}</a></h3>
        <div class="meta"><span>${t.size.join("×")}</span><span>${t.blockCount.toLocaleString()} 블록</span><span>♥ ${t.saves}</span></div>
        <p class="desc">${esc(t.description)}</p>
        ${showSave ? `<div class="actions">${saveButton(t)}</div>` : ""}
      </div></div>`;
  }

  // 실제 블록 텍스처 썸네일 (서버 렌더링). 에셋이 없거나 실패하면 단순 미리보기 캔버스로 대체
  function thumbHTML(t) {
    if (!t.thumbnail) return `<canvas data-preview="${t.id}"></canvas>`;
    return `<img class="thumb" src="${t.thumbnail}" alt="${esc(t.name)} 미리보기" loading="lazy"
      onerror="this.outerHTML='<canvas data-preview=&quot;${t.id}&quot;></canvas>'; App.observePreviews(document)">`;
  }

  function saveButton(t) {
    return t.saved
      ? `<button class="btn saved" data-save="${t.id}" data-saved="1">✓ 보관됨</button>`
      : `<button class="btn primary" data-save="${t.id}">보관함에 담기</button>`;
  }

  // 카드 목록 안의 저장 버튼 위임 처리
  function bindSaveButtons(root, user, onChange) {
    root.addEventListener("click", async (e) => {
      const btn = e.target.closest("[data-save]");
      if (!btn) return;
      if (!requireLogin(user)) return;
      const id = btn.dataset.save;
      const saved = btn.dataset.saved === "1";
      btn.disabled = true;
      try {
        await api(`/api/library/${id}`, { method: saved ? "DELETE" : "POST" });
        toast(saved ? "보관함에서 뺐습니다." : "보관함에 담았습니다. 인게임에서 /tb list 로 확인하세요.");
        onChange?.(id, !saved, btn);
      } catch (err) {
        toast(err.message);
      } finally {
        btn.disabled = false;
      }
    });
  }

  // 카드 미리보기는 화면에 보일 때 템플릿 데이터를 받아서 그린다
  const dataCache = new Map();
  function loadData(id) {
    if (!dataCache.has(id)) dataCache.set(id, api(`/api/templates/${id}`).then((t) => t.data));
    return dataCache.get(id);
  }
  const io = new IntersectionObserver((entries) => {
    for (const en of entries) {
      if (!en.isIntersecting) continue;
      io.unobserve(en.target);
      loadData(en.target.dataset.preview).then((d) => render(en.target, d)).catch(() => {});
    }
  }, { rootMargin: "200px" });
  const observePreviews = (root) => root.querySelectorAll("canvas[data-preview]").forEach((c) => io.observe(c));

  // 비밀번호 칸마다 눈 버튼을 붙인다: 감은 눈 = 숨김, 뜬 눈 = 보임. 움직임은 눈 아이콘에만 (style.css .eye)
  const EYE_SVG = `<svg class="eye is-closed" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <g class="eye-shut"><path d="M3 11c2.5 3.2 5.6 4.8 9 4.8s6.5-1.6 9-4.8"/><path d="M5.6 13.9 4.3 16"/><path d="M9.3 15.4 8.8 17.8"/><path d="M14.7 15.4l.5 2.4"/><path d="M18.4 13.9l1.3 2.1"/></g>
    <g class="eye-open"><path d="M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12z"/><circle class="eye-pupil" cx="12" cy="12" r="3.2" fill="currentColor" stroke="none"/></g>
  </svg>`;
  function passwordToggles(root = document) {
    root.querySelectorAll('input[type="password"]:not([data-eye])').forEach((input) => {
      input.dataset.eye = "1";
      const wrap = document.createElement("div");
      wrap.className = "pw-wrap";
      input.replaceWith(wrap);
      wrap.append(input);
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "eye-btn";
      if (input.id) btn.setAttribute("aria-controls", input.id);
      btn.innerHTML = EYE_SVG;
      const sync = () => {
        const shown = input.type === "text";
        const label = shown ? "비밀번호 숨기기" : "비밀번호 보기";
        btn.setAttribute("aria-label", label);
        btn.title = label;
        btn.setAttribute("aria-pressed", shown);
        btn.classList.toggle("on", shown);
        btn.firstElementChild.setAttribute("class", `eye ${shown ? "is-open" : "is-closed"}`);
        input.classList.toggle("pw-shown", shown);
      };
      btn.onclick = () => {
        input.type = input.type === "password" ? "text" : "password";
        sync();
      };
      sync();
      wrap.append(btn);
    });
  }

  // 프로필의 "서버 연동" / "내 마인크래프트 서버" 접이식 목록 (container 안에 그린다)
  function serverPanels(container) {
    container.innerHTML = `
      <details class="panel fold" id="linkFold" open>
        <summary id="linkSummary"><b>서버 연동</b></summary>
        <div class="link-box" id="link"></div>
      </details>
      <details class="panel server-key fold" id="serverKey">
        <summary><b id="serverSummary">내 마인크래프트 서버</b> <span class="hint">서버를 직접 운영할 때만 필요해요</span></summary>
        <div id="serverKeyBody"></div>
      </details>`;
    const linkEl = container.querySelector("#link");
    const App = { api, esc, toast };
      // 인게임 연동은 서버마다 따로: 새 서버에서 /tb link 할 때마다 목록이 늘어난다
    const ago = (t) => t ? new Date(t * 1000).toLocaleDateString("ko-KR") : "—";
    let links = [], code = null;
    async function renderLink() {
      links = await App.api("/api/links");
      container.querySelector("#linkSummary").innerHTML = `<span class="status-dot ${links.length ? "on" : ""}"></span><b>${links.length ? `연동된 서버 ${links.length}곳` : "아직 연동한 서버가 없어요"}</b>`;
      linkEl.innerHTML = `<div style="min-width:0">
          <p class="hint">연동 코드를 받아 서버에서 입력하면 그 서버가 목록에 추가돼요. 서버마다 한 번씩 연동해요.</p>
          ${links.length ? `<ul class="server-list">${links.map((l) => `
            <li><span><b>${App.esc(l.serverName)}</b> <span class="hint">· ${App.esc(l.minecraft.name || "")} · ${ago(l.linkedAt)} 연동</span></span>
              <button class="btn ghost" data-unlink="${l.serverId}" aria-label="${App.esc(l.serverName)} 연동 해제">해제</button></li>`).join("")}</ul>` : ""}
          ${code ? `<p class="hint">연동할 서버에 접속해서 아래 명령어를 입력하세요. 코드는 10분 동안, 한 번만 쓸 수 있어요.</p>
               <div class="link-code">${code}</div>
               <div class="cmd">/tb link ${code}</div>` : ""}
        </div>
        <div style="display:flex;flex-direction:column;gap:8px">
          <button class="btn primary" id="gen">${code ? "새 코드 발급" : "연동 코드 발급"}</button>
        </div>`;
      linkEl.querySelector("#gen").onclick = async () => {
        code = (await App.api("/api/link/code", { method: "POST" })).code;
        renderLink();
        poll(links.length);
      };
      linkEl.querySelectorAll("[data-unlink]").forEach((b) => b.onclick = async () => {
        const l = links.find((x) => x.serverId === Number(b.dataset.unlink));
        if (!confirm(`${l.serverName} 서버와의 연동을 해제할까요?`)) return;
        await App.api(`/api/links/${l.serverId}`, { method: "DELETE" });
        renderLink();
      });
    }

    // 코드 발급 후 새 서버가 목록에 생길 때까지 잠깐 동안 자동 확인
    let pollTimer;
    function poll(before) {
      clearInterval(pollTimer);
      let n = 0;
      pollTimer = setInterval(async () => {
        if (++n > 120) return clearInterval(pollTimer);
        const u = await App.api("/api/auth/me");
        if (u.linkedServers > before) {
          clearInterval(pollTimer);
          code = null;
          App.toast("서버 연동이 완료됐어요!");
          renderLink();
        }
      }, 5000);
    }
      // 내 서버: 서버마다 키가 따로. 키 원문은 발급 직후 한 번만 보여 준다
    const keyEl = container.querySelector("#serverKeyBody");
    async function renderServers(fresh) {
      const servers = await App.api("/api/servers");
      container.querySelector("#serverSummary").textContent = `내 마인크래프트 서버${servers.length ? ` · ${servers.length}곳` : ""}`;
      keyEl.innerHTML = `
        <p class="hint">서버마다 키를 따로 받아 그 서버 플러그인의 <code>config.yml</code> 에 넣어요. 키로는 <b>그 서버에서 연동한 플레이어</b>만 조회할 수 있어요.
          서버 이름은 config 의 <code>server-name</code> 을 따르고, 비워 두면 <b>Minecraft Server (번호)</b>로 보여요.</p>
        ${fresh ? `<div class="fresh-key"><p><b>${App.esc(fresh.name)} 키 · 지금만 보여요. 복사해서 안전한 곳에 두세요.</b></p>
            <div class="cmd mono">api-url: "${App.esc(location.origin)}"<br>api-key: "${App.esc(fresh.key)}"<br>server-name: ""</div>
            <button class="btn primary" id="copyKey">키 복사</button></div>` : ""}
        ${servers.length ? `<ul class="server-list">${servers.map((s) => `
          <li><span><b>${App.esc(s.name)}</b> <span class="hint">· <span class="mono">${App.esc(s.prefix)}…</span> · 연동 ${s.players}명 · 마지막 접속 ${ago(s.lastSeenAt)}</span></span>
            <span class="row-actions"><button class="btn ghost" data-rekey="${s.id}">키 재발급</button>
            <button class="btn danger" data-del="${s.id}" aria-label="${App.esc(s.name)} 삭제">삭제</button></span></li>`).join("")}</ul>`
          : `<p class="hint">아직 등록한 서버가 없어요.</p>`}
        <button class="btn ${fresh ? "ghost" : "primary"}" id="addServer">서버 추가</button>`;
      keyEl.querySelector("#copyKey")?.addEventListener("click", async () => {
        await navigator.clipboard.writeText(fresh.key);
        App.toast("키를 복사했어요.");
      });
      keyEl.querySelector("#addServer").onclick = async () => {
        try { renderServers(await App.api("/api/servers", { method: "POST" })); }
        catch (err) { App.toast(err.message); }
      };
      keyEl.querySelectorAll("[data-rekey]").forEach((b) => b.onclick = async () => {
        if (!confirm("새 키를 받으면 지금 키는 바로 못 쓰게 돼요. 그 서버의 config.yml 도 바꿔야 해요. 계속할까요?")) return;
        renderServers(await App.api(`/api/servers/${b.dataset.rekey}/key`, { method: "POST" }));
      });
      keyEl.querySelectorAll("[data-del]").forEach((b) => b.onclick = async () => {
        if (!confirm("이 서버를 삭제할까요? 키가 막히고 이 서버의 플레이어 연동도 모두 사라져요.")) return;
        await App.api(`/api/servers/${b.dataset.del}`, { method: "DELETE" });
        renderServers();
      });
    }
    // 접고 편 상태를 이 브라우저에 기억한다 (저장이 막힌 브라우저면 기본값)
    for (const id of ["linkFold", "serverKey"]) {
      const el = container.querySelector("#" + id);
      try {
        const saved = localStorage.getItem("fold:" + id);
        if (saved !== null) el.open = saved === "1";
      } catch {}
      el.addEventListener("toggle", () => { try { localStorage.setItem("fold:" + id, el.open ? "1" : "0"); } catch {} });
    }
    if (location.hash === "#serverKey") container.querySelector("#serverKey").open = true;
    renderLink();
    renderServers();
  }

  // 가입·로그인 폼 자리에 6자리 인증 코드 입력 화면을 띄운다. 재전송은 같은 아이디·비밀번호로 로그인을 다시 시도한다.
  function verifyForm(form, { username, email, password, notice }) {
    form.innerHTML = `<h1>인증 코드 입력</h1>
      <p><b>${esc(email)}</b>(으)로 보낸 6자리 코드를 입력하세요.</p>
      <p class="hint">${esc(notice || "코드는 30분 동안 유효해요. 메일이 안 보이면 스팸함도 확인해 주세요. 메일의 링크를 눌러도 돼요.")}</p>
      <label for="code">인증 코드</label>
      <input id="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}" maxlength="6" required
        style="font-family:var(--mono);font-size:26px;letter-spacing:.4em;text-align:center">
      <button class="btn primary" type="submit">인증하고 시작하기</button>
      ${password ? `<button class="btn ghost" type="button" id="resend">코드 다시 받기</button>` : ""}
      <div class="error" id="error" role="alert"></div>`;
    const error = form.querySelector("#error");
    const input = form.querySelector("#code");
    input.oninput = () => { input.value = input.value.replace(/\D/g, "").slice(0, 6); };
    input.focus();
    form.onsubmit = async (e) => {
      e.preventDefault();
      try {
        await api("/api/auth/verify-code", { method: "POST", body: { username, code: input.value } });
        location.href = "/";  // 가입·인증이 끝나면 템플릿 목록으로
      } catch (err) {
        error.textContent = err.message;
      }
    };
    form.querySelector("#resend")?.addEventListener("click", async () => {
      try {
        await api("/api/auth/login", { method: "POST", body: { username, password } });
        location.href = "/";  // 그사이 인증을 마친 경우
      } catch (err) {
        error.textContent = err.message;
      }
    });
  }

  return { api, me, esc, header, toast, requireLogin, verifyForm, passwordToggles, serverPanels, render, blockColor, cardHTML, saveButton, bindSaveButtons, observePreviews, loadData };
})();
