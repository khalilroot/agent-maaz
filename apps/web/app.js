const state = { sid: null, toolsOn: true, busy: false };

const messagesEl = document.getElementById("messages");
const inputEl = document.getElementById("input");
const modelEl = document.getElementById("model");
const newBtn = document.getElementById("new-chat");
const toolsBtn = document.getElementById("toggle-tools");

function render(text) {
  const escape = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  let html = escape(text);
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) =>
    `<pre><code data-lang="${lang}">${escape(code)}</code></pre>`);
  html = html.replace(/`([^`\n]+)`/g, "<code>$1</code>");
  html = html.replace(/\n\n+/g, "</p><p>").replace(/\n/g, "<br>");
  if (!html.startsWith("<p>")) html = "<p>" + html;
  if (!html.endsWith("</p>")) html += "</p>";
  return html;
}

function addMessage(role, content, { toolCall = null } = {}) {
  const empty = messagesEl.querySelector(".welcome");
  if (empty) empty.remove();

  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "role";
  avatar.textContent = role === "user" ? "U" : "A";

  const body = document.createElement("div");
  body.className = "content";
  if (role === "assistant") {
    body.innerHTML = render(content);
  } else {
    body.textContent = content;
  }
  if (toolCall) {
    const el = document.createElement("div");
    el.className = "tool";
    el.innerHTML = `
      <div class="name">⚙ ${escapeHtml(toolCall.name)}</div>
      <div class="args">${escapeHtml(JSON.stringify(toolCall.args))}</div>
      <div class="result">→ ${escapeHtml((toolCall.result || "").slice(0, 240))}</div>
    `;
    body.appendChild(el);
  }

  wrap.appendChild(avatar);
  wrap.appendChild(body);
  messagesEl.appendChild(wrap);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return body;
}

function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

async function loadSessions() {
  const listEl = document.getElementById("session-list");
  listEl.innerHTML = "";
  try {
    const r = await fetch("/sessions/all");
    const data = await r.json();
    const sessions = data.sessions || [];
    if (sessions.length === 0) {
      listEl.innerHTML = '<div style="color:var(--fg-mute);font-size:13px;padding:8px;">no sessions yet</div>';
      return;
    }
    for (const s of sessions) {
      const item = document.createElement("div");
      item.className = "session-item" + (s.sid === state.sid ? " active" : "");
      const ts = new Date(s.started_at * 1000).toLocaleString();
      item.innerHTML = `<div>${s.sid.slice(0, 8)}</div><div class="ts">${ts} · ${s.turns} turns</div>`;
      item.addEventListener("click", () => loadSession(s.sid));
      listEl.appendChild(item);
    }
  } catch (e) {
    listEl.innerHTML = `<div style="color:var(--fg-mute);font-size:13px;padding:8px;">error: ${e.message}</div>`;
  }
}

async function loadSession(sid) {
  try {
    const r = await fetch(`/sessions/${sid}/messages`);
    const data = await r.json();
    if (!data.messages || data.messages.length === 0) return;
    state.sid = sid;
    document.getElementById("messages").innerHTML = "";
    for (const m of data.messages) {
      if (m.role === "system") continue;
      addMessage(m.role === "user" ? "user" : "assistant", m.content);
    }
    await loadSessions();
    inputEl.focus();
  } catch (e) {
    log.write(`\n[red]error: {e}[/]`);
  }
}

document.getElementById("refresh-sessions").addEventListener("click", loadSessions);

document.getElementById("toggle-sidebar").addEventListener("click", () => {
  const sb = document.getElementById("sidebar");
  const isHidden = sb.hasAttribute("hidden");
  if (isHidden) {
    sb.removeAttribute("hidden");
    document.getElementById("app").classList.add("with-sidebar");
    loadSessions();
  } else {
    sb.setAttribute("hidden", "");
    document.getElementById("app").classList.remove("with-sidebar");
  }
});
  try {
    const r = await fetch("/health");
    const h = await r.json();
    const t = await fetch("/tools");
    const tj = await t.json();
    modelEl.textContent = `${tj.tools.length} tools · primary live`;
  } catch (e) {
    modelEl.textContent = "server offline";
  }
}

function showWelcome() {
  messagesEl.innerHTML = `
    <div class="welcome">
      <h2>agent-maaz</h2>
      <p>free open-source AI agent · $0 cost · your machine</p>
      <p style="margin-top:14px;">اكتب رسالتك في الأسفل و Enter للإرسال.</p>
      <p>tools (search + fetch) controlled via ⚙ toggle.</p>
    </div>
  `;
}

newBtn.addEventListener("click", () => {
  state.sid = null;
  showWelcome();
  inputEl.focus();
});

toolsBtn.addEventListener("click", () => {
  state.toolsOn = !state.toolsOn;
  toolsBtn.classList.toggle("active", state.toolsOn);
  toolsBtn.textContent = `⚙ tools: ${state.toolsOn ? "on" : "off"}`;
});

const micBtn = document.getElementById("mic");
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.lang = "ar-EG";
  recognition.interimResults = false;
  recognition.continuous = false;
  recognition.onresult = (e) => {
    const text = e.results[0][0].transcript;
    inputEl.value = text;
    inputEl.focus();
    micBtn.classList.remove("recording");
    inputEl.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
  };
  recognition.onerror = () => micBtn.classList.remove("recording");
  recognition.onend = () => micBtn.classList.remove("recording");
  micBtn.addEventListener("click", () => {
    if (micBtn.classList.contains("recording")) {
      recognition.stop();
      micBtn.classList.remove("recording");
    } else {
      micBtn.classList.add("recording");
      recognition.start();
    }
  });
} else {
  micBtn.disabled = true;
  micBtn.title = "browser doesn't support Web Speech API";
}

inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    send();
  }
  setTimeout(() => {
    inputEl.style.height = "50px";
    inputEl.style.height = Math.min(inputEl.scrollHeight, 200) + "px";
  }, 0);
});

async function send() {
  const text = inputEl.value.trim();
  if (!text || state.busy) return;
  inputEl.value = "";
  inputEl.style.height = "50px";

  state.busy = true;
  addMessage("user", text);

  const placeholderBody = addMessage("assistant", "");
  placeholderBody.parentElement.classList.add("streaming");
  let renderedLength = 0;

  try {
    const endpoint = state.toolsOn ? "/chat/tools" : "/chat/stream";
    const r = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": state.toolsOn ? "application/json" : "text/plain" },
      body: JSON.stringify({ sid: state.sid, message: text, system: state.sid ? undefined : "انت مساعد ذكي اسمه agent-maaz. بترد بالعربي وبالإنجليزي. خلي ردك مفيد ومباشر." }),
    });

    if (state.toolsOn) {
      const data = await r.json();
      if (data.sid) state.sid = data.sid;
      placeholderBody.parentElement.classList.remove("streaming");
      placeholderBody.innerHTML = render(data.reply || "(no reply)");
      for (const entry of (data.tool_log || [])) {
        const toolDiv = document.createElement("div");
        toolDiv.className = "tool";
        toolDiv.innerHTML = `
          <div class="name">⚙ ${escapeHtml(entry.tool)}</div>
          <div class="args">${escapeHtml(JSON.stringify(entry.args))}</div>
          <div class="result">→ ${escapeHtml((entry.result_excerpt || "").slice(0, 240))}</div>
        `;
        placeholderBody.appendChild(toolDiv);
      }
      messagesEl.scrollTop = messagesEl.scrollHeight;
    } else {
      const sid = r.headers.get("X-Session-Id");
      if (sid) state.sid = sid;
      const reader = r.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let acc = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        acc += decoder.decode(value, { stream: true });
        if (acc.length > renderedLength) {
          placeholderBody.innerHTML = render(acc);
          renderedLength = acc.length;
          messagesEl.scrollTop = messagesEl.scrollHeight;
        }
      }
      placeholderBody.parentElement.classList.remove("streaming");
      placeholderBody.innerHTML = render(acc);
    }
  } catch (e) {
    placeholderBody.parentElement.classList.remove("streaming");
    placeholderBody.innerHTML = render(`[error: ${e.message || e}]`);
  }

  state.busy = false;
  inputEl.focus();
}

probe();
showWelcome();
