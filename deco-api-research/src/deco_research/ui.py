"""Self-contained Home Assistant Ingress UI for FREE THE DECO."""

UI_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>FREE THE DECO</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #081018;
      --panel: #101c27;
      --panel2: #142433;
      --line: #263847;
      --text: #edf6fb;
      --muted: #8fa6b5;
      --cyan: #39d9e6;
      --green: #55df91;
      --amber: #ffc861;
      --red: #ff6b6b;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: radial-gradient(circle at 80% -20%, #12374b 0, transparent 36%), var(--bg);
      color: var(--text);
      font: 14px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    main { width: min(1400px, 100%); margin: auto; padding: 22px; }
    header { display: flex; gap: 18px; align-items: center; justify-content: space-between; margin-bottom: 18px; }
    .brand { display: flex; gap: 14px; align-items: center; }
    .logo { width: 48px; height: 48px; border: 1px solid #2a6873; border-radius: 14px; display: grid; place-items: center; background: #0b2732; color: var(--cyan); font-size: 25px; }
    h1 { font-size: clamp(22px, 4vw, 34px); line-height: 1; margin: 0 0 6px; letter-spacing: .04em; }
    .subtitle, .muted { color: var(--muted); }
    button { border: 1px solid #2d6974; background: #103541; color: var(--text); border-radius: 10px; padding: 10px 15px; cursor: pointer; font-weight: 650; }
    button:hover { background: #164956; }
    button:disabled { opacity: .5; cursor: wait; }
    .statusbar, .card, .node, .alert { border: 1px solid var(--line); background: rgba(16, 28, 39, .94); border-radius: 14px; }
    .statusbar { display: flex; gap: 16px; align-items: center; padding: 12px 15px; margin-bottom: 16px; flex-wrap: wrap; }
    .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--muted); box-shadow: 0 0 12px currentColor; }
    .dot.healthy { color: var(--green); background: var(--green); }
    .dot.error { color: var(--red); background: var(--red); }
    .dot.degraded { color: var(--amber); background: var(--amber); }
    .pill { padding: 3px 8px; border-radius: 999px; background: #20313f; color: #bad0dc; font-size: 12px; }
    .grid { display: grid; gap: 14px; grid-template-columns: repeat(12, minmax(0, 1fr)); margin-bottom: 18px; }
    .card { grid-column: span 3; padding: 16px; min-height: 112px; }
    .card.wide { grid-column: span 6; }
    .card.full { grid-column: 1 / -1; }
    .label { color: var(--muted); text-transform: uppercase; font-size: 11px; font-weight: 700; letter-spacing: .11em; }
    .value { font-size: 29px; font-weight: 760; margin-top: 7px; }
    .detail { color: #b8cad4; margin-top: 4px; }
    section { margin-top: 22px; }
    h2 { font-size: 17px; margin: 0 0 12px; letter-spacing: .02em; }
    .alerts { display: grid; gap: 9px; margin-bottom: 18px; }
    .alert { padding: 12px 14px; border-left-width: 4px; }
    .alert.good { border-left-color: var(--green); }
    .alert.warn { border-left-color: var(--amber); }
    .alert.bad { border-left-color: var(--red); }
    .nodes { display: grid; grid-template-columns: repeat(auto-fit, minmax(245px, 1fr)); gap: 12px; }
    .node { padding: 14px; }
    .nodehead { display: flex; justify-content: space-between; gap: 8px; align-items: center; margin-bottom: 11px; }
    .node h3 { margin: 0; font-size: 15px; }
    .online { color: var(--green); }
    .offline { color: var(--red); }
    .rows { display: grid; gap: 6px; }
    .row { display: flex; justify-content: space-between; gap: 14px; color: var(--muted); }
    .row strong { color: var(--text); text-align: right; font-weight: 600; }
    .bars { display: grid; gap: 10px; margin-top: 12px; }
    .barrow { display: grid; grid-template-columns: 76px 1fr 35px; align-items: center; gap: 10px; }
    .bar { height: 9px; border-radius: 99px; background: #233541; overflow: hidden; }
    .bar span { display: block; height: 100%; background: linear-gradient(90deg, #24a9bd, var(--cyan)); border-radius: inherit; }
    table { width: 100%; border-collapse: collapse; margin-top: 8px; }
    th, td { text-align: left; padding: 9px 7px; border-bottom: 1px solid var(--line); }
    th { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .08em; }
    .capabilities { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 9px; }
    .cap { background: var(--panel2); border-radius: 9px; padding: 10px; }
    .cap strong { color: var(--green); }
    .cap.future strong { color: var(--muted); }
    #error { display: none; color: var(--red); margin-top: 8px; }
    @media (max-width: 900px) { .card { grid-column: span 6; } .card.wide { grid-column: 1 / -1; } }
    @media (max-width: 560px) { main { padding: 14px; } header { align-items: flex-start; } .card { grid-column: 1 / -1; } .hide-mobile { display: none; } }
  </style>
</head>
<body>
<main>
  <header>
    <div class="brand"><div class="logo">⌁</div><div><h1>FREE THE DECO</h1><div class="subtitle">Pine Haven mesh observatory</div></div></div>
    <button id="refresh">Refresh now</button>
  </header>
  <div class="statusbar">
    <span id="status-dot" class="dot"></span>
    <strong id="mode">Loading…</strong>
    <span class="pill" id="version">App</span>
    <span class="muted" id="timing">Contacting monitor…</span>
  </div>
  <div id="alerts" class="alerts"></div>
  <div class="grid">
    <div class="card"><div class="label">Mesh nodes</div><div id="nodes-total" class="value">—</div><div id="nodes-detail" class="detail">Awaiting data</div></div>
    <div class="card"><div class="label">Connected clients</div><div id="clients-total" class="value">—</div><div id="clients-detail" class="detail">Awaiting data</div></div>
    <div class="card"><div class="label">2.4 GHz radio</div><div id="radio-channel" class="value">—</div><div id="radio-width" class="detail">Awaiting data</div></div>
    <div class="card"><div class="label">Controller load</div><div id="controller-cpu" class="value">—</div><div id="controller-memory" class="detail">Awaiting data</div></div>
  </div>

  <section><h2>Deco mesh</h2><div id="nodes" class="nodes"></div></section>

  <section class="grid">
    <div class="card wide"><div class="label">Client distribution</div><div id="client-bars" class="bars"></div></div>
    <div class="card wide"><div class="label">Radio status</div><table><thead><tr><th>Band</th><th>Channel</th><th>Width</th><th>Auto channel</th></tr></thead><tbody id="radio-table"></tbody></table></div>
  </section>

  <section class="grid">
    <div class="card full"><div class="label">Capability map</div><h2 style="margin-top:8px">What the App can do today</h2><div class="capabilities">
      <div class="cap"><strong>LIVE</strong><br>Mesh inventory and online health</div>
      <div class="cap"><strong>LIVE</strong><br>Backhaul, signal and internet state</div>
      <div class="cap"><strong>LIVE</strong><br>Anonymous client and traffic totals</div>
      <div class="cap"><strong>LIVE</strong><br>Wi-Fi channel and configured width</div>
      <div class="cap"><strong>LIVE</strong><br>Home Assistant telemetry publishing</div>
      <div class="cap future"><strong>R&amp;D</strong><br>Configuration writes remain disabled</div>
    </div></div>
  </section>
  <div id="error"></div>
</main>
<script>
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '—').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = value => value === null || value === undefined ? '—' : value;
  const api = path => `${path}`;

  function alertBox(kind, title, detail) {
    const div = document.createElement('div'); div.className = `alert ${kind}`;
    div.innerHTML = `<strong>${esc(title)}</strong><div class="muted">${esc(detail)}</div>`;
    return div;
  }

  function render(data) {
    const mesh = data.mesh || {};
    const mode = data.mode || 'unknown';
    $('mode').textContent = mode.toUpperCase();
    $('version').textContent = `v${data.app_version || '?'}`;
    $('status-dot').className = `dot ${mode === 'healthy' ? 'healthy' : mode === 'degraded' ? 'degraded' : mode === 'error' ? 'error' : ''}`;
    $('timing').textContent = data.last_success_at ? `Last successful read ${new Date(data.last_success_at).toLocaleString()} · polling every ${data.poll_interval_seconds}s` : 'No successful read yet';

    const alerts = $('alerts'); alerts.replaceChildren();
    if (mode === 'error') alerts.append(alertBox('bad', 'Monitor read failed', `Safe error category: ${data.error_code || 'unknown'}`));
    if (mesh.offline_count > 0) alerts.append(alertBox('warn', `${mesh.offline_count} Deco offline`, 'Open the mesh cards below to identify the affected location.'));
    const band2 = mesh.wireless_radio?.band2_4 || {};
    if (band2.channel === 4 && band2.configured_width_mhz === 40) alerts.append(alertBox('warn', 'Known Zigbee overlap remains', '2.4 GHz Wi-Fi channel 4 at 40 MHz overlaps Pine Haven Zigbee channels 15 and 20.'));
    if (!alerts.children.length && mode === 'healthy') alerts.append(alertBox('good', 'Mesh monitor healthy', 'All approved read operations and Home Assistant publishing are working.'));

    $('nodes-total').textContent = fmt(mesh.node_count);
    $('nodes-detail').textContent = mesh.node_count === undefined ? 'Awaiting data' : `${mesh.online_count} online · ${mesh.offline_count} offline`;
    const clients = mesh.connected_clients || {};
    $('clients-total').textContent = fmt(clients.reported_count);
    $('clients-detail').textContent = `${clients.interfaces?.main || 0} main · ${clients.interfaces?.iot || 0} IoT`;
    $('radio-channel').textContent = band2.channel ? `Ch ${band2.channel}` : '—';
    $('radio-width').textContent = band2.configured_width_mhz ? `${band2.configured_width_mhz} MHz configured width` : 'Width unavailable';
    const perf = mesh.controller_performance || {};
    $('controller-cpu').textContent = perf.cpu_percent === null || perf.cpu_percent === undefined ? '—' : `${perf.cpu_percent}%`;
    $('controller-memory').textContent = perf.memory_percent === null || perf.memory_percent === undefined ? 'Memory unavailable' : `${perf.memory_percent}% memory`;

    const nodes = $('nodes'); nodes.replaceChildren();
    for (const node of mesh.nodes || []) {
      const div = document.createElement('div'); div.className = 'node';
      const backhaul = (node.connection_types || []).join(' + ') || 'not reported';
      div.innerHTML = `<div class="nodehead"><h3>${esc(node.name)}</h3><strong class="${node.online ? 'online' : 'offline'}">${node.online ? 'ONLINE' : 'OFFLINE'}</strong></div>
        <div class="rows"><div class="row"><span>Role</span><strong>${esc(node.role)}</strong></div><div class="row"><span>Internet</span><strong>${esc(node.internet)}</strong></div><div class="row"><span>Backhaul</span><strong>${esc(backhaul)}</strong></div><div class="row"><span>Link</span><strong>${node.backhaul_speed_mbps ? esc(node.backhaul_speed_mbps) + ' Mbit/s' : '—'}</strong></div><div class="row"><span>Signal 2.4 / 5</span><strong>${fmt(node.signal_2_4)} / ${fmt(node.signal_5)}</strong></div><div class="row"><span>Firmware</span><strong>${esc(node.firmware_version || '—')}</strong></div></div>`;
      nodes.append(div);
    }
    if (!nodes.children.length) nodes.append(alertBox('warn', 'No mesh snapshot', 'Monitoring is disabled or the first poll has not completed.'));

    const connections = clients.connection_types || {};
    const entries = [['2.4 GHz', connections.band2_4 || 0], ['5 GHz', connections.band5 || 0], ['Wired', connections.wired || 0], ['Unknown', connections.unknown || 0]];
    const total = Math.max(1, ...entries.map(x => x[1]), clients.reported_count || 1);
    const bars = $('client-bars'); bars.replaceChildren();
    for (const [label, count] of entries) {
      const row = document.createElement('div'); row.className = 'barrow';
      row.innerHTML = `<span>${esc(label)}</span><div class="bar"><span style="width:${Math.max(1, count / total * 100)}%"></span></div><strong>${count}</strong>`;
      bars.append(row);
    }

    const tbody = $('radio-table'); tbody.replaceChildren();
    for (const [key, label] of [['band2_4','2.4 GHz'],['band5_1','5 GHz primary'],['band5_2','5 GHz secondary']]) {
      const band = mesh.wireless_radio?.[key] || {}; const tr = document.createElement('tr');
      tr.innerHTML = `<td>${label}</td><td>${fmt(band.channel)}</td><td>${band.configured_width_mhz ? band.configured_width_mhz + ' MHz' : '—'}</td><td>${band.automatic_channel === null || band.automatic_channel === undefined ? '—' : band.automatic_channel ? 'Yes' : 'No'}</td>`;
      tbody.append(tr);
    }
    $('error').style.display = 'none';
  }

  async function load() {
    try { const response = await fetch(api('api/v1/status'), {cache:'no-store'}); if (!response.ok) throw new Error(`HTTP ${response.status}`); render(await response.json()); }
    catch (error) { $('error').textContent = `Status refresh failed: ${error.message}`; $('error').style.display = 'block'; }
  }
  $('refresh').addEventListener('click', async event => {
    const button = event.currentTarget; button.disabled = true; button.textContent = 'Refreshing…';
    try { await fetch(api('api/v1/refresh'), {method:'POST'}); setTimeout(load, 1500); }
    finally { setTimeout(() => { button.disabled = false; button.textContent = 'Refresh now'; }, 1800); }
  });
  load(); setInterval(load, 15000);
</script>
</body></html>"""
