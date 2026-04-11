// Marathi Responder · Control Panel
const $ = (id) => document.getElementById(id);

const state = {
  lastActivityStatus: null,
  lastActivityTask: null,
  lastReplied: -1,
  eventCount: 0,
};

// ---------- API helpers ----------
async function api(path, method = "GET", body = null) {
  const opts = { method, headers: {} };
  if (body) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok && data.ok !== true) {
    throw new Error(data.error || `${res.status} ${res.statusText}`);
  }
  return data;
}

// ---------- Toast ----------
function toast(message, kind = "info", ttl = 4200) {
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.innerHTML = `<span class="dot"></span><span></span>`;
  el.querySelector("span:last-child").textContent = message;
  $("toasts").appendChild(el);
  setTimeout(() => {
    el.classList.add("leaving");
    setTimeout(() => el.remove(), 320);
  }, ttl);
}

// ---------- HTML escape ----------
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

function fmtClock(iso) {
  try {
    const d = new Date(iso);
    if (isNaN(d)) return "--:--:--";
    return d.toLocaleTimeString("en-GB", { hour12: false });
  } catch { return "--:--:--"; }
}

// ---------- Status ----------
function renderStatus(s) {
  $("clock").textContent = fmtClock(s.now);

  const svc = s.service || {};
  const pill = $("servicePill");
  const label = pill.querySelector(".label");
  if (svc.loaded && svc.pid) {
    pill.className = "service-pill running";
    label.textContent = `running · pid ${svc.pid}`;
  } else if (svc.loaded) {
    pill.className = "service-pill stopped";
    label.textContent = "loaded · not running";
  } else if (svc.plist_installed) {
    pill.className = "service-pill stopped";
    label.textContent = "service stopped";
  } else {
    pill.className = "service-pill stopped";
    label.textContent = "plist not installed";
  }

  $("svcStatus").textContent = svc.loaded
    ? (svc.pid ? "Running" : "Loaded")
    : "Not loaded";
  $("svcPid").textContent = svc.pid ?? "—";
  $("svcExit").textContent = svc.exit ?? "—";
  $("svcPlist").textContent = svc.plist_installed ? "installed" : "missing";

  const c = s.config || {};
  $("cfgDaily").textContent = c.daily_reply_count ?? "—";
  $("cfgWindow").textContent = c.window
    ? `${c.window} ${(c.timezone || "").split("/")[1] || ""}`
    : "—";
  $("cfgTz").textContent = c.timezone || "—";
  $("cfgFollowers").textContent = (c.min_author_followers || 0).toLocaleString();
  $("cfgLikes").textContent = c.min_tweet_likes ?? "—";

  if (state.lastReplied !== s.replied_count) {
    const el = $("stRepliedCount");
    el.textContent = s.replied_count;
    el.animate(
      [{ transform: "scale(1.14)", color: "#ffa84d" }, { transform: "scale(1)" }],
      { duration: 500, easing: "cubic-bezier(0.16, 1, 0.3, 1)" }
    );
    state.lastReplied = s.replied_count;
  }

  const a = s.activity || {};
  const statusEl = $("activityStatus");
  const messageEl = $("activityMessage");
  const labelMap = {
    idle: "Idle",
    running: a.task === "run_now" ? "Running slot" : a.task === "health_check" ? "Checking health" : "Running",
    done: "Done",
    error: "Error",
  };
  statusEl.textContent = labelMap[a.status] || "—";
  statusEl.className = `hero-status ${a.status || ""}`;
  messageEl.textContent = a.message || (a.status === "idle" ? "No task running" : "");

  // Transition toasts
  if (
    state.lastActivityStatus &&
    (state.lastActivityStatus !== a.status || state.lastActivityTask !== a.task)
  ) {
    if (a.status === "done") {
      const kind = a.task === "run_now" ? "Slot" : "Health check";
      toast(`${kind} complete`, "ok");
      if (a.task === "health_check") fetchHealthResult();
    } else if (a.status === "error") {
      toast(a.message || "Task failed", "err");
      if (a.task === "health_check") fetchHealthResult();
    }
  }
  state.lastActivityStatus = a.status;
  state.lastActivityTask = a.task;

  const busy = a.status === "running";
  $("runNowBtn").disabled = busy;
  $("healthBtn").disabled = busy;
}

async function pollStatus() {
  try {
    renderStatus(await api("/api/status"));
  } catch (e) {
    console.error("status:", e);
  }
}

// ---------- Events ----------
async function pollEvents() {
  try {
    const { events } = await api("/api/events");
    if (!events || events.length === state.eventCount) return;
    state.eventCount = events.length;
    const log = $("eventLog");
    if (events.length === 0) {
      log.innerHTML = '<div class="muted">Waiting for events…</div>';
      return;
    }
    log.innerHTML = events
      .map((e) => {
        const lvl = e.level || "info";
        return `<div class="log-line ${lvl}"><span class="ts">${esc(e.ts)}</span><span class="text">${esc(e.text)}</span></div>`;
      })
      .join("");
    log.scrollTop = log.scrollHeight;
  } catch (e) {
    console.error("events:", e);
  }
}

// ---------- Replied ----------
async function pollReplied() {
  try {
    const r = await api("/api/replied");
    const el = $("repliedList");
    if (!r.items || r.items.length === 0) {
      el.innerHTML = '<div class="muted">None yet.</div>';
      return;
    }
    el.innerHTML = r.items
      .map((it) => `
        <div class="reply-item">
          <div class="meta">
            <span class="who">@${esc(it.author_username || "?")}</span>
            <span>${esc((it.replied_at || "").slice(0, 19).replace("T", " "))}</span>
            <span>score ${esc(it.score ?? "-")}</span>
          </div>
          <div class="text">${esc(it.reply_text || "")}</div>
          <div class="original">↳ ${esc((it.original_text || "").slice(0, 160))}${(it.original_text || "").length > 160 ? "…" : ""}</div>
        </div>
      `)
      .join("");
  } catch (e) {
    console.error("replied:", e);
  }
}

// ---------- Health ----------
async function fetchHealthResult() {
  try {
    const res = await api("/api/health-check/result");
    const grid = $("healthGrid");
    const badge = $("healthBadge");
    const keys = Object.keys(res || {});
    if (keys.length === 0) {
      grid.innerHTML = '<div class="muted">Click <strong>Health Check</strong> to run diagnostics.</div>';
      badge.textContent = "not run";
      badge.className = "badge";
      return;
    }
    const failed = keys.filter((k) => !res[k].ok);
    badge.textContent = failed.length ? `${failed.length} failed` : "all passing";
    badge.className = `badge ${failed.length ? "err" : "ok"}`;
    grid.innerHTML = keys
      .map((k) => {
        const r = res[k];
        const detail = String(r.detail || "").slice(0, 90);
        return `
          <div class="health-item ${r.ok ? "ok" : "err"}">
            <span class="icon"></span>
            <span class="name">${esc(k)}</span>
            <span class="detail" title="${esc(r.detail || "")}">${esc(detail)}</span>
          </div>
        `;
      })
      .join("");
  } catch (e) {
    console.error("health:", e);
  }
}

// ---------- Actions ----------
async function runNow() {
  try {
    await api("/api/run-now", "POST");
    toast("Slot started — reply on ntfy to approve", "info");
    pollStatus();
  } catch (e) {
    toast(`Run failed: ${e.message}`, "err");
  }
}

async function runHealth() {
  try {
    await api("/api/health-check", "POST");
    toast("Health check started", "info");
    pollStatus();
  } catch (e) {
    toast(`Health check failed: ${e.message}`, "err");
  }
}

async function serviceAction(action) {
  try {
    const r = await api(`/api/service/${action}`, "POST");
    toast(`${action}: ${r.ok ? "ok" : r.message}`, r.ok ? "ok" : "err");
    pollStatus();
  } catch (e) {
    toast(`${action} failed: ${e.message}`, "err");
  }
}

// ---------- Wire up ----------
$("runNowBtn").addEventListener("click", runNow);
$("healthBtn").addEventListener("click", runHealth);
document.querySelectorAll("[data-action]").forEach((btn) => {
  btn.addEventListener("click", () => serviceAction(btn.dataset.action));
});

// ---------- Polling loops ----------
(async function statusLoop() {
  while (true) {
    await pollStatus();
    await new Promise((r) => setTimeout(r, 2500));
  }
})();

(async function eventLoop() {
  while (true) {
    await pollEvents();
    await new Promise((r) => setTimeout(r, 1800));
  }
})();

(async function repliedLoop() {
  while (true) {
    await pollReplied();
    await new Promise((r) => setTimeout(r, 10000));
  }
})();

fetchHealthResult();
