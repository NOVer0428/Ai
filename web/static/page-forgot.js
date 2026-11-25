// forgot.html 전용 스크립트 (CSP 때문에 HTML 안 인라인 스크립트 대신 파일로 둔다)
App.header();
const form = document.getElementById("form");
const PW_HINT = "8~15자 · 숫자, 영어 소문자, 영어 대문자, 특수문자(! ? / \\ | @ # $ % ^ & *)를 모두 넣어 주세요 · 아이디와 같거나 비슷하면 안 돼요";

function codeStep(email, masked) {
  form.innerHTML = `<h1>새 비밀번호 설정</h1>
    <p>가입된 이메일이라면 <b>${App.esc(masked)}</b>(으)로 6자리 재설정 코드를 보냈어요.</p>
    <p class="hint">코드는 30분 동안 유효해요. 메일이 안 보이면 스팸함도 확인해 주세요.</p>
    <label for="code">재설정 코드</label>
    <input id="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}" maxlength="6" required
      style="font-family:var(--mono);font-size:26px;letter-spacing:.4em;text-align:center">
    <label for="pw1">새 비밀번호</label>
    <input id="pw1" type="password" autocomplete="new-password" required minlength="8" maxlength="15">
    <div class="hint">${App.esc(PW_HINT)}</div>
    <label for="pw2">새 비밀번호 확인</label>
    <input id="pw2" type="password" autocomplete="new-password" required minlength="8" maxlength="15">
    <button class="btn primary" type="submit">비밀번호 바꾸기</button>
    <button class="btn ghost" type="button" id="again">코드 다시 받기</button>
    <div class="error" id="error" role="alert"></div>`;
  App.passwordToggles(form);
  const error = form.querySelector("#error");
  form.querySelector("#again").onclick = () => requestCode(email);
  form.onsubmit = async (e) => {
    e.preventDefault();
    const pw = form.querySelector("#pw1").value;
    if (pw !== form.querySelector("#pw2").value) { error.textContent = "비밀번호가 서로 다릅니다."; return; }
    try {
      const r = await App.api("/api/auth/reset/confirm", { method: "POST",
        body: { email, code: form.querySelector("#code").value, password: pw } });
      form.innerHTML = `<h1>비밀번호를 바꿨어요</h1>
        <p>아이디 <b>${App.esc(r.username)}</b> 의 비밀번호가 새로 설정됐어요. 다른 기기의 로그인은 모두 끊겼어요.</p>
        <a class="btn primary" href="/login">로그인하기</a>`;
    } catch (err) {
      error.textContent = err.message;
    }
  };
}

async function requestCode(email) {
  const error = form.querySelector("#error");
  try {
    const r = await App.api("/api/auth/reset/request", { method: "POST", body: { email } });
    codeStep(email, r.email);
  } catch (err) {
    error.textContent = err.message;
  }
}

form.onsubmit = (e) => {
  e.preventDefault();
  requestCode(document.getElementById("email").value.trim());
};
