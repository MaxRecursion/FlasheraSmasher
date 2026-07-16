<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>GroupGL — Legal Entity Planning — Data Input</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{
  --ink:#0A1E64;            /* DB brand deep blue */
  --ink-2:#122B7E;
  --blue:#1D4FD7;           /* interactive */
  --blue-hover:#1743B8;
  --blue-soft:#EDF2FE;
  --blue-line:#C9D8F8;
  --surface:#F4F6FA;
  --card:#FFFFFF;
  --line:#E4E9F2;
  --line-strong:#D3DAE8;
  --text:#182238;
  --muted:#64708A;
  --faint:#8B96AD;
  --green:#0E8A5F;
  --green-soft:#E7F5EF;
  --amber:#D97C0B;
  --radius:10px;
  --shadow:0 1px 2px rgba(16,24,40,.05), 0 1px 3px rgba(16,24,40,.06);
}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1600px;height:1000px;overflow:hidden}
body{
  font-family:"IBM Plex Sans",system-ui,sans-serif;
  background:var(--surface);color:var(--text);
  font-size:14px;line-height:1.45;
  display:flex;flex-direction:column;
  -webkit-font-smoothing:antialiased;
}
.mono{font-family:"IBM Plex Mono",monospace}

/* ============ TOP BAR ============ */
.topbar{
  height:52px;flex:0 0 52px;background:var(--ink);color:#fff;
  display:flex;align-items:center;gap:16px;padding:0 20px;
}
.brand{display:flex;align-items:center;gap:10px}
.db-mark{width:26px;height:26px;border:2.5px solid #fff;position:relative;flex:0 0 auto}
.db-mark::after{content:"";position:absolute;left:2px;right:2px;top:50%;height:2.5px;background:#fff;transform:rotate(-45deg)}
.brand .name{font-weight:700;font-size:15px;letter-spacing:.2px}
.brand .name span{font-weight:400;opacity:.85}
.top-divider{width:1px;height:22px;background:rgba(255,255,255,.25)}
.app-title{font-size:13.5px;font-weight:500;color:rgba(255,255,255,.92)}
.topbar .spacer{flex:1}
.top-search{
  display:flex;align-items:center;gap:8px;width:300px;height:32px;
  background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.18);
  border-radius:8px;padding:0 12px;color:rgba(255,255,255,.75);font-size:13px;
}
.top-search{white-space:nowrap}
.top-search svg{width:15px;height:15px;flex:0 0 auto}
.top-search .kbd{margin-left:auto;font-size:11px;border:1px solid rgba(255,255,255,.3);border-radius:4px;padding:0 5px;line-height:16px}
.icon-btn{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;color:rgba(255,255,255,.85);position:relative}
.icon-btn.notif::after{content:"";position:absolute;top:6px;right:7px;width:7px;height:7px;border-radius:50%;background:#5FD4A0;border:1.5px solid var(--ink)}
.user{display:flex;align-items:center;gap:10px;margin-left:4px}
.avatar{width:30px;height:30px;border-radius:50%;background:#5FD4A0;color:#08341F;font-weight:600;font-size:12px;display:flex;align-items:center;justify-content:center}
.user .who{line-height:1.15}
.user .who .n{font-size:12.5px;font-weight:600}
.user .who .r{font-size:11px;color:rgba(255,255,255,.65)}

/* ============ SHELL ============ */
.shell{flex:1;display:flex;min-height:0}

/* ============ SIDEBAR ============ */
.side{
  width:236px;flex:0 0 236px;background:var(--card);border-right:1px solid var(--line);
  padding:16px 12px;display:flex;flex-direction:column;gap:4px;overflow:hidden;
}
.side .group{margin-bottom:14px}
.side .eyebrow{
  font-size:10.5px;font-weight:600;letter-spacing:.12em;color:var(--faint);
  padding:0 10px 6px;
}
.nav-item{
  display:flex;align-items:center;gap:10px;height:34px;padding:0 10px;
  border-radius:8px;color:#3D4A66;font-size:13.5px;font-weight:500;cursor:pointer;
}
.nav-item svg{width:16px;height:16px;flex:0 0 auto;color:var(--faint)}
.nav-item:hover{background:#F1F4FA}
.nav-item.active{background:var(--blue-soft);color:var(--blue);font-weight:600;box-shadow:inset 3px 0 0 var(--blue)}
.nav-item.active svg{color:var(--blue)}
.side .foot{margin-top:auto;border-top:1px solid var(--line);padding:12px 10px 2px;font-size:11.5px;color:var(--faint);display:flex;align-items:center;gap:8px}
.env-dot{width:7px;height:7px;border-radius:50%;background:var(--green)}

/* ============ MAIN ============ */
.main{flex:1;min-width:0;overflow:hidden;padding:20px 28px 0;display:flex;flex-direction:column}

.crumbs{font-size:12px;color:var(--faint);margin-bottom:6px}
.crumbs b{color:var(--muted);font-weight:500}
.page-head{display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:16px}
.page-head h1{font-size:21px;font-weight:700;letter-spacing:-.01em}
.page-head .sub{font-size:13px;color:var(--muted);margin-top:3px}
.saved-chip{display:flex;align-items:center;gap:7px;font-size:12.5px;color:#9A5B06;background:#FEF6E7;border:1px solid #F3DEB4;border-radius:999px;padding:5px 12px;font-weight:500}
.saved-chip .dot{width:7px;height:7px;border-radius:50%;background:var(--amber)}

/* ============ CONTEXT STRIP (signature) ============ */
.context{
  background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  box-shadow:var(--shadow);padding:14px 18px 15px;margin-bottom:14px;
}
.context .label{font-size:10.5px;font-weight:600;letter-spacing:.12em;color:var(--faint);margin-bottom:10px;display:flex;justify-content:space-between}
.context .label .hint{letter-spacing:0;font-weight:400;text-transform:none;color:var(--faint)}
.ctx-row{display:flex;align-items:stretch;gap:10px}
.token{
  flex:0 1 auto;border:1px solid var(--line-strong);border-radius:9px;background:#FBFCFE;
  padding:8px 12px 9px;min-width:170px;cursor:pointer;position:relative;
  display:flex;flex-direction:column;justify-content:center;
}
.token:hover{border-color:var(--blue-line);background:var(--blue-soft)}
.token .t-label{font-size:10.5px;font-weight:600;letter-spacing:.1em;color:var(--faint);margin-bottom:3px}
.token .t-val{display:flex;align-items:center;gap:8px;font-size:13.5px;font-weight:500;white-space:nowrap}
.token .code{font-family:"IBM Plex Mono",monospace;font-size:12px;font-weight:600;color:var(--blue);background:var(--blue-soft);border:1px solid var(--blue-line);border-radius:5px;padding:1px 6px}
.token .caret{margin-left:auto;color:var(--faint)}
.token.company{flex:0 1 460px}
.ctx-arrow{align-self:center;color:var(--line-strong);flex:0 0 auto}
.ctx-sep{width:1px;background:var(--line);margin:2px 4px}
.mini-field{display:flex;flex-direction:column;justify-content:center;gap:3px;padding:0 4px}
.mini-field .t-label{font-size:10.5px;font-weight:600;letter-spacing:.1em;color:var(--faint)}
.mini-field .val{font-size:13px;font-weight:500;color:var(--muted);display:flex;align-items:center;gap:6px}
.mini-field .val .chip{border:1px solid var(--line-strong);border-radius:6px;padding:2px 8px;background:#FBFCFE;font-size:12.5px;color:var(--text)}
.ctx-row .push{flex:1}
.btn{
  display:inline-flex;align-items:center;gap:8px;height:36px;padding:0 16px;border-radius:8px;
  font-size:13.5px;font-weight:600;border:1px solid transparent;cursor:pointer;white-space:nowrap;
}
.btn svg{width:15px;height:15px}
.btn.primary{background:var(--blue);color:#fff;box-shadow:0 1px 2px rgba(29,79,215,.35)}
.btn.primary:hover{background:var(--blue-hover)}
.btn.ghost{background:var(--card);border-color:var(--line-strong);color:#3D4A66}
.btn.ghost:hover{border-color:var(--blue-line);color:var(--blue)}
.btn.self-center{align-self:center}

/* ============ TOOLBAR ============ */
.toolbar{display:flex;align-items:center;gap:8px;margin-bottom:12px}
.toolbar .vlabel{font-size:12.5px;color:var(--muted);margin-right:2px}
.chip{
  display:inline-flex;align-items:center;gap:6px;height:28px;padding:0 11px;border-radius:999px;
  border:1px solid var(--line-strong);background:var(--card);font-size:12.5px;font-weight:500;color:var(--muted);cursor:pointer;
}
.chip svg{width:12px;height:12px}
.chip.on{background:var(--blue-soft);border-color:var(--blue-line);color:var(--blue)}
.toolbar .grow{flex:1}
.refreshed{font-size:12px;color:var(--faint);margin-right:6px}
.btn.sm{height:32px;padding:0 13px;font-size:13px;font-weight:500}
.btn .count{background:rgba(255,255,255,.25);border-radius:999px;font-size:11px;font-weight:600;padding:1px 7px}
.split-caret{margin-left:2px;opacity:.8}

/* ============ GRID CARD ============ */
.grid-card{
  background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  box-shadow:var(--shadow);flex:0 1 auto;display:flex;flex-direction:column;overflow:hidden;margin-bottom:22px;
}
table{width:100%;border-collapse:separate;border-spacing:0;font-size:13px}
thead th{
  position:sticky;top:0;background:#F8FAFD;border-bottom:1px solid var(--line-strong);
  text-align:right;padding:9px 16px 8px;font-weight:600;color:var(--text);font-size:12.5px;white-space:nowrap;
}
thead th:first-child{text-align:left;padding-left:20px}
thead .coltag{display:block;font-size:10px;font-weight:600;letter-spacing:.09em;color:var(--faint);margin-top:2px}
thead th.plan .coltag{color:var(--blue)}
thead th.plan{background:#F3F7FE}
tbody td{
  padding:0 16px;height:41px;border-bottom:1px solid var(--line);text-align:right;
  font-family:"IBM Plex Mono",monospace;font-size:13px;font-variant-numeric:tabular-nums;color:var(--text);
}
tbody td:first-child{
  font-family:"IBM Plex Sans",sans-serif;text-align:left;padding-left:20px;font-size:13.5px;color:#2A3652;
}
tbody td.plan{background:#FBFDFF}
tbody tr:hover td{background:#F4F7FC}
tbody tr:hover td.plan{background:#EFF4FD}
tbody td .yoy{display:block;font-size:10.5px;color:var(--faint);line-height:1;margin-top:2px;font-weight:400}
tbody tr.subtotal td{font-weight:600;border-top:1px solid var(--line-strong);background:#FAFBFE}
tbody tr.subtotal td:first-child{font-weight:600}
tbody tr.strong td{font-weight:600;background:#F5F8FD;border-top:2px solid var(--line-strong)}
tbody tr.divider td{border-top:2px solid var(--line-strong)}
tbody td .unit{color:var(--faint);font-size:11px;margin-left:4px;font-family:"IBM Plex Sans",sans-serif}
td.neg{color:#41507A}
td .cagr{background:#F1F4FA;border:1px solid var(--line);border-radius:6px;padding:2px 8px;font-size:12px;font-weight:500}
tr.strong td .cagr{background:var(--green-soft);border-color:#C6E9DA;color:var(--green);font-weight:600}

/* commentary corner triangle */
td.note{position:relative}
td.note::before{
  content:"";position:absolute;top:0;right:0;
  border-top:9px solid var(--amber);border-left:9px solid transparent;
}
/* focused editable cell */
td.editing{position:relative;background:#fff !important}
td.editing .cellbox{
  position:absolute;inset:4px 6px;border:2px solid var(--blue);border-radius:6px;background:#fff;
  display:flex;align-items:center;justify-content:flex-end;padding:0 9px;box-shadow:0 0 0 3px rgba(29,79,215,.15);
}
td.editing .cellbox .cursor{width:1.5px;height:16px;background:var(--blue);margin-left:2px}

/* grid footer */
.grid-foot{
  border-top:1px solid var(--line);padding:9px 20px;display:flex;align-items:center;gap:20px;
  font-size:12px;color:var(--muted);background:#FBFCFE;
}
.legend{display:flex;align-items:center;gap:6px}
.legend .tri{width:0;height:0;border-top:8px solid var(--amber);border-left:8px solid transparent}
.legend svg{width:12px;height:12px;color:var(--faint)}
.grid-foot .grow{flex:1}

/* ============ EMPTY STATE ============ */
.empty-card{display:none;flex:1;align-items:center;justify-content:center;flex-direction:column;gap:6px;padding:40px}
.empty-ill{display:flex;align-items:center;gap:10px;margin-bottom:18px}
.empty-ill .node{width:44px;height:44px;border-radius:10px;border:1.5px solid var(--blue-line);background:var(--blue-soft);display:flex;align-items:center;justify-content:center;color:var(--blue);font-family:"IBM Plex Mono",monospace;font-size:10px;font-weight:600}
.empty-ill .link{width:26px;height:1.5px;background:var(--blue-line)}
.empty-card h2{font-size:16.5px;font-weight:600}
.empty-card p{font-size:13.5px;color:var(--muted);max-width:400px;text-align:center;margin-bottom:16px}
body.state-empty .grid-card table,
body.state-empty .grid-foot,
body.state-empty .toolbar,
body.state-empty .saved-chip{display:none}
body.state-empty .empty-card{display:flex}
body.state-empty .grid-card{min-height:460px}
</style>
</head>
<body>

<svg width="0" height="0" style="position:absolute">
  <defs>
    <symbol id="i-search" viewBox="0 0 16 16"><circle cx="7" cy="7" r="4.5" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M10.5 10.5L14 14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></symbol>
    <symbol id="i-bell" viewBox="0 0 16 16"><path d="M8 2a4 4 0 0 0-4 4v3l-1.2 2.2h10.4L12 9V6a4 4 0 0 0-4-4Z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><path d="M6.5 13.4a1.6 1.6 0 0 0 3 0" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></symbol>
    <symbol id="i-help" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6.2" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M6.3 6.2A1.8 1.8 0 1 1 8.2 8c-.5.2-.7.6-.7 1.1" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/><circle cx="7.6" cy="11.4" r=".9" fill="currentColor"/></symbol>
    <symbol id="i-table" viewBox="0 0 16 16"><rect x="2" y="2.5" width="12" height="11" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M2 6h12M6.5 6v7.5" stroke="currentColor" stroke-width="1.4"/></symbol>
    <symbol id="i-pulse" viewBox="0 0 16 16"><path d="M1.5 8h3l2-4.5 3 9 2-4.5h3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></symbol>
    <symbol id="i-down" viewBox="0 0 16 16"><path d="M8 2.5v8m0 0 3-3m-3 3-3-3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M2.5 13.5h11" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></symbol>
    <symbol id="i-lock" viewBox="0 0 16 16"><rect x="3.5" y="7" width="9" height="6.5" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M5.5 7V5.5a2.5 2.5 0 0 1 5 0V7" fill="none" stroke="currentColor" stroke-width="1.4"/></symbol>
    <symbol id="i-doc" viewBox="0 0 16 16"><path d="M4 1.8h5.5L12.5 5v9.2h-8.5Z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><path d="M6 8h4.5M6 10.7h4.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></symbol>
    <symbol id="i-diff" viewBox="0 0 16 16"><rect x="2" y="2" width="5.5" height="12" rx="1.2" fill="none" stroke="currentColor" stroke-width="1.4"/><rect x="8.5" y="2" width="5.5" height="12" rx="1.2" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M4 6h1.5M10.5 6H12M4 9h1.5M10.5 9H12" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></symbol>
    <symbol id="i-bldg" viewBox="0 0 16 16"><path d="M3 14V3.5L8 1.8l5 1.7V14" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><path d="M1.5 14h13M6 6h1M9 6h1M6 9h1M9 9h1" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></symbol>
    <symbol id="i-bars" viewBox="0 0 16 16"><path d="M3 13.5V8M8 13.5V4M13 13.5V6.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></symbol>
    <symbol id="i-clockb" viewBox="0 0 16 16"><path d="M2.6 8a5.4 5.4 0 1 0 1.6-3.8M2.6 2.5v2.7h2.7" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/><path d="M8 5.4V8l1.9 1.3" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></symbol>
    <symbol id="i-sheet" viewBox="0 0 16 16"><rect x="2.5" y="2" width="11" height="12" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M2.5 5.5h11M6.2 5.5V14" stroke="currentColor" stroke-width="1.3"/></symbol>
    <symbol id="i-scale" viewBox="0 0 16 16"><path d="M8 2.5v11M4 4.5h8M3 13.5h10" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/><path d="M4 4.5 2.3 8.5a1.8 1.8 0 0 0 3.4 0Zm8 0-1.7 4a1.8 1.8 0 0 0 3.4 0Z" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/></symbol>
    <symbol id="i-clip" viewBox="0 0 16 16"><rect x="3" y="2.8" width="10" height="11.2" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.4"/><rect x="5.5" y="1.4" width="5" height="2.6" rx="1" fill="none" stroke="currentColor" stroke-width="1.3"/><path d="M5.5 7.5h5M5.5 10.3h3.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></symbol>
    <symbol id="i-refresh" viewBox="0 0 16 16"><path d="M13.4 8a5.4 5.4 0 1 1-1.6-3.8M13.4 2.5v2.7h-2.7" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></symbol>
    <symbol id="i-upload" viewBox="0 0 16 16"><path d="M8 11V3m0 0L5 6m3-3 3 3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M2.5 13.5h11" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></symbol>
    <symbol id="i-save" viewBox="0 0 16 16"><path d="M2.5 3.8c0-.7.6-1.3 1.3-1.3h7.4l2.3 2.3v7.4c0 .7-.6 1.3-1.3 1.3H3.8c-.7 0-1.3-.6-1.3-1.3Z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><path d="M5 2.7v3h5.5v-3M5 13.3V9.5h6v3.8" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/></symbol>
    <symbol id="i-check" viewBox="0 0 16 16"><path d="M3 8.5 6.5 12 13 4.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></symbol>
    <symbol id="i-caret" viewBox="0 0 16 16"><path d="m4.5 6.5 3.5 3.5 3.5-3.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></symbol>
    <symbol id="i-arrow" viewBox="0 0 16 16"><path d="M3 8h9m0 0L9 5m3 3-3 3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></symbol>
    <symbol id="i-snow" viewBox="0 0 16 16"><path d="M8 1.5v13M2.4 4.8l11.2 6.4M2.4 11.2 13.6 4.8" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></symbol>
  </defs>
</svg>

<!-- ======= TOP BAR ======= -->
<header class="topbar">
  <div class="brand">
    <div class="db-mark"></div>
    <div class="name">GroupGL <span>· Finance Planning Suite</span></div>
  </div>
  <div class="top-divider"></div>
  <div class="app-title">Legal Entity Planning</div>
  <div class="spacer"></div>
  <div class="top-search"><svg><use href="#i-search"/></svg> Search entities, scenarios… <span class="kbd">⌘K</span></div>
  <div class="icon-btn"><svg width="17" height="17"><use href="#i-help"/></svg></div>
  <div class="icon-btn notif"><svg width="17" height="17"><use href="#i-bell"/></svg></div>
  <div class="user">
    <div class="avatar">AK</div>
    <div class="who"><div class="n">Akshay Kulkarni</div><div class="r">Group Finance · Pune</div></div>
  </div>
</header>

<div class="shell">

  <!-- ======= SIDEBAR ======= -->
  <nav class="side">
    <div class="group">
      <div class="eyebrow">PLAN</div>
      <div class="nav-item active"><svg><use href="#i-table"/></svg>Data Input</div>
      <div class="nav-item"><svg><use href="#i-pulse"/></svg>Status</div>
      <div class="nav-item"><svg><use href="#i-down"/></svg>Retrieval</div>
      <div class="nav-item"><svg><use href="#i-snow"/></svg>Data Freeze</div>
      <div class="nav-item"><svg><use href="#i-clip"/></svg>Questionnaire</div>
    </div>
    <div class="group">
      <div class="eyebrow">COMPARE</div>
      <div class="nav-item"><svg><use href="#i-diff"/></svg>Version Comparison</div>
      <div class="nav-item"><svg><use href="#i-bldg"/></svg>Local vs Group Plan</div>
      <div class="nav-item"><svg><use href="#i-bars"/></svg>Plan vs Actuals</div>
      <div class="nav-item"><svg><use href="#i-clockb"/></svg>Current vs Prior Plan</div>
    </div>
    <div class="group">
      <div class="eyebrow">REPORTS</div>
      <div class="nav-item"><svg><use href="#i-sheet"/></svg>Financials Export</div>
      <div class="nav-item"><svg><use href="#i-scale"/></svg>Equity Reco</div>
      <div class="nav-item"><svg><use href="#i-doc"/></svg>15-Year Plan</div>
    </div>
    <div class="foot"><span class="env-dot"></span>All systems normal · v4.2</div>
  </nav>

  <!-- ======= MAIN ======= -->
  <main class="main">
    <div class="crumbs">Legal Entity Planning / <b>Data Input</b></div>
    <div class="page-head">
      <div>
        <h1>Data Input</h1>
        <div class="sub">Enter and maintain plan figures for the selected legal entity.</div>
      </div>
      <div class="saved-chip"><span class="dot"></span>2 unsaved edits · last saved 23:14</div>
    </div>

    <!-- Context strip -->
    <section class="context">
      <div class="label">PLANNING CONTEXT <span class="hint">Data loads for this scenario · company · period</span></div>
      <div class="ctx-row">
        <div class="token">
          <div class="t-label">SCENARIO</div>
          <div class="t-val"><span class="code">LE_PLAN_1</span> Legal entity plan 1 <svg class="caret" width="14" height="14"><use href="#i-caret"/></svg></div>
        </div>
        <svg class="ctx-arrow" width="16" height="16"><use href="#i-arrow"/></svg>
        <div class="token company">
          <div class="t-label">COMPANY</div>
          <div class="t-val"><span class="code">3101B</span> KEBA Gesellschaft für interne Services mbH <svg class="caret" width="14" height="14"><use href="#i-caret"/></svg></div>
        </div>
        <svg class="ctx-arrow" width="16" height="16"><use href="#i-arrow"/></svg>
        <div class="token">
          <div class="t-label">PLANNING PROCESS</div>
          <div class="t-val"><span class="code">2027</span> Annual plan <svg class="caret" width="14" height="14"><use href="#i-caret"/></svg></div>
        </div>
        <div class="ctx-sep"></div>
        <div class="mini-field">
          <div class="t-label">LFC</div>
          <div class="val"><span class="chip">—</span></div>
        </div>
        <div class="mini-field">
          <div class="t-label">CSV DELIMITER</div>
          <div class="val"><span class="chip">Comma ,</span></div>
        </div>
        <div class="push"></div>
        <button class="btn primary self-center"><svg><use href="#i-refresh"/></svg>Load data</button>
      </div>
    </section>

    <!-- Toolbar -->
    <div class="toolbar">
      <span class="vlabel">View</span>
      <span class="chip on"><svg><use href="#i-check"/></svg>ATI</span>
      <span class="chip">GC</span>
      <span class="chip on"><svg><use href="#i-check"/></svg>Actuals</span>
      <span class="chip on"><svg><use href="#i-check"/></svg>Growth rates</span>
      <span class="chip on"><svg><use href="#i-check"/></svg>€ millions</span>
      <div class="grow"></div>
      <span class="refreshed">Refreshed 23:19</span>
      <button class="btn ghost sm"><svg><use href="#i-down"/></svg>Template<svg class="split-caret" width="12" height="12"><use href="#i-caret"/></svg></button>
      <button class="btn ghost sm"><svg><use href="#i-upload"/></svg>Upload CSV</button>
      <button class="btn ghost sm"><svg><use href="#i-sheet"/></svg>Export to Excel</button>
      <button class="btn primary sm"><svg><use href="#i-save"/></svg>Save changes<span class="count">2</span></button>
    </div>

    <!-- Grid -->
    <section class="grid-card">
      <table>
        <thead>
          <tr>
            <th>P&amp;L line item</th>
            <th>FY 2025<span class="coltag">ACTUAL</span></th>
            <th>FY 2026<span class="coltag">FORECAST</span></th>
            <th class="plan">FY 2027<span class="coltag">PLAN · EDITABLE</span></th>
            <th class="plan">FY 2028<span class="coltag">PLAN · EDITABLE</span></th>
            <th class="plan">FY 2029<span class="coltag">PLAN · EDITABLE</span></th>
            <th>CAGR<span class="coltag">2027–29</span></th>
          </tr>
        </thead>
        <tbody id="rows"></tbody>
      </table>

      <div class="empty-card">
        <div class="empty-ill">
          <div class="node">SCN</div><div class="link"></div>
          <div class="node">CO</div><div class="link"></div>
          <div class="node">YR</div>
        </div>
        <h2>No data loaded yet</h2>
        <p>Choose a scenario, company and planning process above — then load data to start entering plan figures.</p>
        <button class="btn primary"><svg><use href="#i-refresh"/></svg>Load data</button>
      </div>

      <div class="grid-foot">
        <span>8 line items · <span class="mono">3101B</span> · Values in € millions</span>
        <div class="grow"></div>
        <span class="legend"><span class="tri"></span>Has commentary</span>
        <span class="legend"><svg><use href="#i-lock"/></svg>Actuals are read-only</span>
      </div>
    </section>
  </main>
</div>

<script>
const rows = [
  {n:"Net revenues", v:["48,2","51,0","53,6","55,8","58,1"], yoy:[null,null,"+5,1 %","+4,1 %","+4,1 %"], cagr:"+4,1 %", note:[3], cls:""},
  {n:"Compensation & benefits", v:["−22,4","−23,1","−23,9","−24,6","−25,3"], yoy:[null,null,"+3,5 %","+2,9 %","+2,8 %"], cagr:"+2,9 %", edit:2, cls:""},
  {n:"Non-compensation costs", v:["−14,8","−15,6","−16,1","−16,5","−17,0"], yoy:[null,null,"+3,2 %","+2,5 %","+3,0 %"], cagr:"+2,8 %", note:[2], cls:""},
  {n:"Total noninterest expenses", v:["−37,2","−38,7","−40,0","−41,1","−42,3"], yoy:[null,null,"+3,4 %","+2,8 %","+2,9 %"], cagr:"+2,8 %", cls:"subtotal"},
  {n:"Profit before tax", v:["11,0","12,3","13,6","14,7","15,8"], yoy:[null,null,"+10,6 %","+8,1 %","+7,5 %"], cagr:"+7,8 %", cls:"subtotal"},
  {n:"Income tax expense", v:["−3,3","−3,7","−4,1","−4,4","−4,7"], yoy:[null,null,"+10,8 %","+7,3 %","+6,8 %"], cagr:"+7,1 %", cls:""},
  {n:"Net income", v:["7,7","8,6","9,5","10,3","11,1"], yoy:[null,null,"+10,5 %","+8,4 %","+7,8 %"], cagr:"+8,1 %", cls:"strong"},
  {n:"Full-time equivalents", unit:"#", v:["214","220","226","231","235"], yoy:[null,null,"+2,7 %","+2,2 %","+1,7 %"], cagr:"+2,0 %", cls:"divider"},
];
const tb = document.getElementById("rows");
tb.innerHTML = rows.map(r=>{
  const cells = r.v.map((val,i)=>{
    const plan = i>=2 ? " plan":"";
    const neg = val.startsWith("−") ? " neg":"";
    const note = (r.note||[]).includes(i) ? " note":"";
    if(r.edit===i){
      return `<td class="plan editing"><div class="cellbox">${val}<span class="cursor"></span></div>&nbsp;</td>`;
    }
    const yoy = r.yoy[i] ? `<span class="yoy">${r.yoy[i]}</span>` : "";
    return `<td class="${plan}${neg}${note}">${val}${yoy}</td>`;
  }).join("");
  const unit = r.unit ? `<span class="unit">${r.unit}</span>`:"";
  return `<tr class="${r.cls}"><td>${r.n}${unit}</td>${cells}<td><span class="cagr">${r.cagr}</span></td></tr>`;
}).join("");
</script>
</body>
</html>