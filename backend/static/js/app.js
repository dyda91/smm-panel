async function apiGet(url) {
  const r = await fetch(url);
  return r.json();
}

async function apiPost(url, data) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data)
  });
  return r.json();
}

function $(id) {
  return document.getElementById(id);
}

function el(tag, attrs, ...children) {
  const e = document.createElement(tag);
  if (attrs) Object.entries(attrs).forEach(([k, v]) => e.setAttribute(k, v));
  children.forEach(c => e.append(c));
  return e;
}

// =============================================
// TOGGLE MONITOR
// =============================================
$("toggleMonitor").addEventListener("change", async function () {
  const endpoint = this.checked ? "/api/monitor/start" : "/api/monitor/stop";
  const result = await apiPost(endpoint);
  if (result.success) {
    updateStatusBadge(result.monitor);
  } else {
    this.checked = !this.checked;
  }
});

function updateStatusBadge(enabled) {
  const badge = $("statusBadge");
  if (enabled) {
    badge.className = "badge online";
    badge.textContent = "● Monitorando";
  } else {
    badge.className = "badge offline";
    badge.textContent = "● Desligado";
  }
}

// =============================================
// RANGE SLIDER SYNC
// =============================================
["followers", "likes", "views", "shares", "saves"].forEach(key => {
  const slider = $(`${key}_pct`);
  const display = $(`${key}_pct_val`);
  if (slider && display) {
    slider.addEventListener("input", () => {
      display.textContent = slider.value + "%";
    });
  }
});

// =============================================
// SAVE / RUN
// =============================================
async function saveConfig() {
  const instagram_id = $("instagram_id").value.trim();
  if (!instagram_id) {
    alert("Digite o ID do Instagram");
    return;
  }

  const payload = {
    instagram_id,
    interval_minutes: Number($("interval").value),
    followers_service: $("followers_service").value.trim(),
    followers_pct: Number($("followers_pct").value),
    followers_enabled: $("followers_enabled").checked,
    likes_service: $("likes_service").value.trim(),
    likes_pct: Number($("likes_pct").value),
    likes_enabled: $("likes_enabled").checked,
    views_service: $("views_service").value.trim(),
    views_pct: Number($("views_pct").value),
    views_enabled: $("views_enabled").checked,
    shares_service: $("shares_service").value.trim(),
    shares_pct: Number($("shares_pct").value),
    shares_enabled: $("shares_enabled").checked,
    saves_service: $("saves_service").value.trim(),
    saves_pct: Number($("saves_pct").value),
    saves_enabled: $("saves_enabled").checked
  };

  const result = await apiPost("/api/account", payload);
  if (result.success) {
    alert("Configuração salva com sucesso!");
  } else {
    alert("Erro ao salvar: " + (result.error || "desconhecido"));
  }
}

async function runNow() {
  const result = await apiGet("/api/run-now");
  if (result.success) {
    await loadDashboard();
    alert("Verificação executada!");
  } else {
    alert("Erro: " + (result.error || "desconhecido"));
  }
}

// =============================================
// LOAD SAVED CONFIG
// =============================================
async function loadSaved() {
  const data = await apiGet("/api/account");
  if (!data || data.error) return;

  Object.keys(data).forEach(key => {
    const el = $(key);
    if (!el) return;
    if (el.type === "checkbox") {
      el.checked = Boolean(data[key]);
    } else if (el.type === "range") {
      el.value = data[key] ?? 0;
      const display = $(`${key}_val`);
      if (display) display.textContent = el.value + "%";
    } else {
      el.value = data[key] ?? "";
    }
  });
}

// =============================================
// DASHBOARD
// =============================================
async function loadDashboard() {
  const d = await apiGet("/api/dashboard");

  const set = (id, val) => {
    const el = $(id);
    if (el) el.textContent = val ?? "-";
  };

  set("dFollowers", d.last_followers ? d.last_followers.toLocaleString() : "-");
  set("dPosts", d.posts_seen ?? 0);
  set("dOrders", d.orders ?? 0);
  set("dErrors", d.errors ?? 0);
  set("dChecks", d.checks ?? 0);
  set("dBalance", d.balance != null ? "$" + Number(d.balance).toFixed(2) : "-");

  updateStatusBadge(d.monitor);
  $("toggleMonitor").checked = d.monitor;

  const meta = $("metaInfo");
  if (d.last_username) {
    meta.style.display = "flex";
    $("lastUsername").textContent = "@" + d.last_username;
    $("lastRun").textContent = d.last_run
      ? new Date(d.last_run + "Z").toLocaleString("pt-BR")
      : "nunca";
  } else {
    meta.style.display = "none";
  }
}

// =============================================
// LOGS
// =============================================
async function loadLogs() {
  const logs = await apiGet("/api/logs");
  const container = $("logs");
  if (!container) return;

  if (!logs.length) {
    container.innerHTML = '<div class="log-empty">Nenhum log ainda</div>';
    return;
  }

  container.innerHTML = logs.map(log => {
    const ts = log.ts
      ? new Date(log.ts + "Z").toLocaleString("pt-BR")
      : "";
    return `<div class="log-entry">
      <span class="ts">${ts}</span>
      <span class="level-${log.level}">[${log.level}]</span>
      ${log.message}
    </div>`;
  }).join("");

  container.scrollTop = container.scrollHeight;
}

// =============================================
// RESET POSTS
// =============================================
async function resetPosts() {
  if (!confirm("Reprocessar os 5 posts mais recentes com os serviços atuais?")) return;
  const result = await apiPost("/api/reset-posts");
  if (result.success) {
    alert("Posts resetados! Clique em Verificar Agora para reprocessar.");
  } else {
    alert("Erro: " + (result.error || "desconhecido"));
  }
}

// =============================================
// INIT
// =============================================
window.onload = function () {
  loadSaved();
  loadDashboard();
  loadLogs();
  setInterval(loadDashboard, 5000);
  setInterval(loadLogs, 3000);
};
