// register.html 전용 스크립트 (CSP 때문에 HTML 안 인라인 스크립트 대신 파일로 둔다)
App.header();
// 전체 동의 ↔ 개별 동의 체크 맞추기
const agreeAll = document.getElementById("agreeAll");
const agreeEach = ["agreeTerms", "agreePrivacy", "agreeAge"].map((id) => document.getElementById(id));
agreeAll.onchange = () => agreeEach.forEach((c) => { c.checked = agreeAll.checked; });

// 비밀번호 추천: 입력칸 아래에 "비밀번호 추천 : ○○○" 로 보여 주기만 한다(자동 입력·복사 없음)
function makePassword() {
  const sets = ["abcdefghijkmnpqrstuvwxyz", "ABCDEFGHJKLMNPQRSTUVWXYZ", "23456789", "!?@#$%^&*"];
  const pick = (str) => str[crypto.getRandomValues(new Uint32Array(1))[0] % str.length];
  const id = document.getElementById("username").value.trim().toLowerCase();
  let pw;
  do {
    const chars = sets.map(pick);                                      // 종류마다 하나씩은 꼭
    while (chars.length < 12) chars.push(pick(sets.join("")));
    for (let i = chars.length - 1; i > 0; i--) {                        // 섞기
      const j = crypto.getRandomValues(new Uint32Array(1))[0] % (i + 1);
      [chars[i], chars[j]] = [chars[j], chars[i]];
    }
    pw = chars.join("");
  } while (id.length >= 3 && pw.toLowerCase().includes(id.slice(0, 3)));  // 아이디와 겹치면 다시
  return pw;
}
const suggestBtn = document.getElementById("suggestPw");
const refreshSuggest = () => { suggestBtn.textContent = makePassword(); };
refreshSuggest();
document.getElementById("suggestAgain").onclick = refreshSuggest;
agreeEach.forEach((c) => c.onchange = () => { agreeAll.checked = agreeEach.every((x) => x.checked); });
document.getElementById("form").onsubmit = async (e) => {
  e.preventDefault();
  const error = document.getElementById("error");
  const password = document.getElementById("password").value;
  if (password !== document.getElementById("password2").value) {
    error.textContent = "비밀번호가 서로 다릅니다.";
    return;
  }
  try {
    const r = await App.api("/api/auth/register", { method: "POST", body: {
      username: document.getElementById("username").value,
      email: document.getElementById("email").value, password,
      agreeTerms: document.getElementById("agreeTerms").checked,
      agreePrivacy: document.getElementById("agreePrivacy").checked,
      agreeAge: document.getElementById("agreeAge").checked,
    }});
    App.verifyForm(document.getElementById("form"),
      { username: document.getElementById("username").value.trim(), email: r.email, password });
  } catch (err) {
    error.textContent = err.message;
  }
};
