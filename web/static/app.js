// 공통 유틸: API 호출, 헤더, 토스트, 아이소메트릭 미리보기
const App = (() => {
  async function api(path, { method = "GET", body } = {}) {
    const opts = { method, headers: {}, credentials: "same-origin" };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(path, opts);
    const data = await res.json().catch(() => null);
    if (!res.ok) throw Object.assign(new Error(data?.error || `요청 실패 (${res.status})`), { status: res.status });
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
    const box = el.querySelector(".userbox");
    const user = await me().catch(() => null);
    if (user) {
      box.innerHTML = `<span><span class="status-dot ${user.minecraft ? "on" : ""}"></span>${esc(user.username)}</span>
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

  return { api, me, esc, header, toast, requireLogin, render, blockColor, cardHTML, saveButton, bindSaveButtons, observePreviews, loadData };
})();
