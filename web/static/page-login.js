// login.html 전용 스크립트 (CSP 때문에 HTML 안 인라인 스크립트 대신 파일로 둔다)
App.header();
// 같은 사이트 주소로만 이동 (/\evil.com 같은 우회 차단)
const safeNext = (() => {
  try {
    const u = new URL(new URLSearchParams(location.search).get("next") || "/", location.origin);
    return u.origin === location.origin ? u.href : "/";  // 경로만 다시 쓰면 //외부주소 로 빠져나갈 수 있어 전체 주소를 쓴다
  } catch { return "/"; }
})();
if (new URLSearchParams(location.search).get("verify") === "invalid") {
  document.getElementById("error").textContent =
    "인증 링크가 잘못됐거나 만료됐어요. 로그인하면 인증 메일을 다시 보내 드려요.";
}
document.getElementById("form").onsubmit = async (e) => {
  e.preventDefault();
  try {
    await App.api("/api/auth/login", { method: "POST", body: {
      username: document.getElementById("username").value,
      password: document.getElementById("password").value,
      remember: document.getElementById("remember").checked,
    }});
    location.href = safeNext;
  } catch (err) {
    if (err.data?.needsVerify) {
      App.verifyForm(document.getElementById("form"), { username: err.data.username, email: err.data.email,
        password: document.getElementById("password").value, notice: err.message });
      return;
    }
    document.getElementById("error").textContent = err.message;
  }
};
