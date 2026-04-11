// Marathi Responder · Control Panel
const $ = (id) => document.getElementById(id);

const state = {
  lastActivityStatus: null,
  lastActivityTask: null,
  lastReplied: -1,
  eventCount: 0,
  sessionListSig: "",     // dedupe key: latest-session id + updated_at
  expandedSession: null,  // id of currently-expanded session card
  sessionDetails: {},     // id -> full session payload (cached)
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

// ---------- Sessions ----------
function fmtTime(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    return d.toLocaleString("en-GB", {
      month: "short", day: "2-digit",
      hour: "2-digit", minute: "2-digit", second: "2-digit",
      hour12: false,
    });
  } catch { return iso; }
}

function statusClass(s) {
  if (s === "posted") return "ok";
  if (s === "skipped" || s === "timeout") return "warn";
  if (s === "error" || s === "no_candidates") return "err";
  if (s === "running") return "running";
  return "";
}

function renderSessionSummary(s) {
  const cls = statusClass(s.status);
  const trig = s.trigger === "manual" ? "manual" : `slot #${s.slot_number}`;
  const parts = [
    `fetched <b>${s.fetched_count || 0}</b>`,
    `eligible <b>${s.candidates_after_filter || 0}</b> (${s.relaxation_label || "—"})`,
    `claude <b>${s.claude_calls_count || 0}</b>`,
  ];
  if (s.approval_response) parts.push(`reply <b>${esc(s.approval_response)}</b>`);
  if (s.posted_tweet_id) parts.push(`posted <b>${esc(s.posted_tweet_id)}</b>`);
  return `
    <div class="session-item ${cls}" data-session-id="${esc(s.id)}">
      <div class="session-head">
        <div class="session-head-left">
          <span class="session-status ${cls}">${esc(s.status || "?")}</span>
          <span class="session-time mono">${esc(fmtTime(s.started_at))}</span>
          <span class="session-trig">${esc(trig)}</span>
          ${s.selected_author ? `<span class="session-who">@${esc(s.selected_author)}</span>` : ""}
        </div>
        <div class="session-head-right mono">
          <svg class="chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
        </div>
      </div>
      <div class="session-summary">${parts.join(" &middot; ")}</div>
      ${s.outcome ? `<div class="session-outcome">${esc(s.outcome)}</div>` : ""}
      <div class="session-detail" data-detail-for="${esc(s.id)}"></div>
    </div>
  `;
}

function renderSessionDetail(d) {
  if (!d) return '<div class="muted">loading…</div>';
  const parts = [];

  // Filter stats
  if (d.filter_stats && Object.keys(d.filter_stats).length) {
    const rows = Object.entries(d.filter_stats)
      .map(([k, v]) => `<span class="kv"><span class="k">${esc(k)}</span><span class="v mono">${esc(v)}</span></span>`)
      .join("");
    parts.push(`
      <div class="detail-block">
        <div class="detail-label">Filter breakdown</div>
        <div class="kv-row">${rows}</div>
        <div class="muted" style="margin-top:6px;font-size:11px;">
          Relaxation: <b>${esc(d.relaxation_label || "—")}</b> (level ${esc(d.relaxation_level || 0)})
        </div>
      </div>
    `);
  }

  // Selected tweet
  if (d.selected_tweet) {
    const t = d.selected_tweet;
    const url = t.url ? `<a href="${esc(t.url)}" target="_blank" rel="noopener">open tweet ↗</a>` : "";
    parts.push(`
      <div class="detail-block">
        <div class="detail-label">Selected tweet</div>
        <div class="tweet-card">
          <div class="tweet-meta mono">
            <span>@${esc(t.author_username || "?")}</span>
            <span>likes ${esc(t.likes ?? 0)}</span>
            <span>rt ${esc(t.retweets ?? 0)}</span>
            <span>score ${esc(t.score ?? 0)}</span>
            ${url}
          </div>
          <div class="tweet-text">${esc(t.text || "")}</div>
        </div>
      </div>
    `);
  }

  // Claude calls
  if (d.claude_calls && d.claude_calls.length) {
    const calls = d.claude_calls.map((c, i) => `
      <details class="claude-call" ${i === d.claude_calls.length - 1 ? "open" : ""}>
        <summary>
          <span class="cc-kind ${esc(c.kind)}">${esc(c.kind)}</span>
          <span class="mono">#${esc(c.attempt)}</span>
          <span class="mono">${esc(c.ts || "")}</span>
          <span class="mono">${esc(c.response_chars)} chars</span>
          <span class="muted mono">${esc((c.model || "").replace("claude-", ""))}</span>
        </summary>
        <div class="cc-body">
          <div class="cc-label">System prompt</div>
          <pre class="cc-pre">${esc(c.system_prompt || "")}</pre>
          <div class="cc-label">User prompt</div>
          <pre class="cc-pre">${esc(c.user_prompt || "")}</pre>
          <div class="cc-label">Claude response</div>
          <pre class="cc-pre response">${esc(c.response || "")}</pre>
        </div>
      </details>
    `).join("");
    parts.push(`
      <div class="detail-block">
        <div class="detail-label">Claude calls (${d.claude_calls.length})</div>
        ${calls}
      </div>
    `);
  }

  // Fetched tweets preview
  if (d.fetched_tweets && d.fetched_tweets.length) {
    const rows = d.fetched_tweets.slice(0, 12).map((t) => `
      <div class="fetched-row">
        <span class="mono who">@${esc(t.author_username || "?")}</span>
        <span class="mono muted">followers ${esc(t.author_followers ?? 0)}</span>
        <span class="mono muted">likes ${esc(t.likes ?? 0)}</span>
        <span class="txt">${esc(t.text_preview || "")}</span>
      </div>
    `).join("");
    const extra = d.fetched_tweets.length > 12
      ? `<div class="muted" style="font-size:11px;padding-top:4px;">+${d.fetched_tweets.length - 12} more</div>`
      : "";
    parts.push(`
      <div class="detail-block">
        <div class="detail-label">Fetched from X (${d.fetched_count})</div>
        <div class="fetched-list">${rows}${extra}</div>
      </div>
    `);
  }

  // Events timeline
  if (d.events && d.events.length) {
    const rows = d.events.map((e) => `
      <div class="log-line ${esc(e.level || "info")}">
        <span class="ts">${esc(e.ts)}</span>
        <span class="text">${esc(e.text)}</span>
      </div>
    `).join("");
    parts.push(`
      <div class="detail-block">
        <div class="detail-label">Timeline</div>
        <div class="log" style="max-height:220px;">${rows}</div>
      </div>
    `);
  }

  return parts.join("") || '<div class="muted">no details</div>';
}

async function pollSessions() {
  try {
    const { sessions } = await api("/api/sessions");
    const list = sessions || [];
    const el = $("sessionsList");
    const badge = $("sessionBadge");
    badge.textContent = list.length ? `${list.length}` : "—";
    badge.className = "badge" + (list.length ? " ok" : "");

    // Signature avoids re-rendering when nothing changed (keeps the
    // expanded detail pane from collapsing while the user is reading)
    const sig = list.map((s) => `${s.id}:${s.status}:${s.ended_at || ""}:${s.claude_calls_count}:${s.approval_response || ""}`).join("|");
    if (sig === state.sessionListSig && el.children.length) return;
    state.sessionListSig = sig;

    if (list.length === 0) {
      el.innerHTML = '<div class="muted">No sessions yet. Click <strong>Run Now</strong> to create one.</div>';
      return;
    }
    el.innerHTML = list.map(renderSessionSummary).join("");

    el.querySelectorAll(".session-item").forEach((node) => {
      node.addEventListener("click", (ev) => {
        if (ev.target.closest("a")) return;
        toggleSession(node.dataset.sessionId);
      });
    });

    // Re-open the previously-expanded session so poll cycles don't close it
    if (state.expandedSession) {
      const n = el.querySelector(`[data-session-id="${CSS.escape(state.expandedSession)}"]`);
      if (n) {
        n.classList.add("expanded");
        const det = n.querySelector(".session-detail");
        const cached = state.sessionDetails[state.expandedSession];
        if (cached) det.innerHTML = renderSessionDetail(cached);
        // Force a re-fetch in case it's live (running session)
        fetchSessionDetail(state.expandedSession, det);
      }
    }
  } catch (e) {
    console.error("sessions:", e);
  }
}

async function fetchSessionDetail(id, targetEl) {
  try {
    const d = await api(`/api/sessions/${encodeURIComponent(id)}`);
    state.sessionDetails[id] = d;
    if (targetEl) targetEl.innerHTML = renderSessionDetail(d);
  } catch (e) {
    if (targetEl) targetEl.innerHTML = `<div class="muted">failed to load: ${esc(e.message)}</div>`;
  }
}

async function toggleSession(id) {
  const el = $("sessionsList");
  const node = el.querySelector(`[data-session-id="${CSS.escape(id)}"]`);
  if (!node) return;
  const detailEl = node.querySelector(".session-detail");
  if (node.classList.contains("expanded")) {
    node.classList.remove("expanded");
    state.expandedSession = null;
    return;
  }
  // Collapse any other expanded sibling
  el.querySelectorAll(".session-item.expanded").forEach((n) => n.classList.remove("expanded"));
  node.classList.add("expanded");
  state.expandedSession = id;
  detailEl.innerHTML = '<div class="muted">loading…</div>';
  await fetchSessionDetail(id, detailEl);
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

(async function sessionsLoop() {
  while (true) {
    await pollSessions();
    // Poll more frequently when a session is expanded/running so
    // the live timeline updates without user interaction
    const fast = state.expandedSession != null;
    await new Promise((r) => setTimeout(r, fast ? 2500 : 5000));
  }
})();

fetchHealthResult();
