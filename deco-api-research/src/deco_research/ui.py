"""Self-contained Home Assistant Ingress UI for FREE THE DECO."""

UI_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>FREE THE DECO</title>
  <style>
    :root {
      color-scheme: dark; --bg:#071018; --panel:#101c27; --panel2:#142433;
      --line:#263847; --text:#edf6fb; --muted:#8fa6b5; --cyan:#39d9e6;
      --green:#55df91; --amber:#ffc861; --red:#ff6b6b;
    }
    * { box-sizing:border-box; }
    body { margin:0; background:radial-gradient(circle at 80% -20%,#12374b 0,transparent 36%),var(--bg); color:var(--text); font:14px/1.45 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
    main { width:min(1400px,100%); margin:auto; padding:22px; }
    header { display:flex; gap:18px; align-items:center; justify-content:space-between; margin-bottom:18px; }
    .brand { display:flex; gap:14px; align-items:center; }
    .logo { width:48px; height:48px; border:1px solid #2a6873; border-radius:14px; display:grid; place-items:center; background:#0b2732; color:var(--cyan); font-size:25px; }
    h1 { font-size:clamp(22px,4vw,34px); line-height:1; margin:0 0 6px; letter-spacing:.04em; }
    h2 { font-size:17px; margin:0 0 12px; letter-spacing:.02em; }
    .subtitle,.muted { color:var(--muted); }
    button { border:1px solid #2d6974; background:#103541; color:var(--text); border-radius:10px; padding:10px 15px; cursor:pointer; font-weight:650; min-width:126px; }
    button:hover { background:#164956; } button:disabled { opacity:.62; cursor:wait; }
    .statusbar,.card,.node,.alert,.health { border:1px solid var(--line); background:rgba(16,28,39,.94); border-radius:14px; }
    .statusbar { display:flex; gap:16px; align-items:center; padding:12px 15px; margin-bottom:16px; flex-wrap:wrap; }
    .dot { width:10px; height:10px; border-radius:50%; background:var(--muted); box-shadow:0 0 12px currentColor; }
    .dot.healthy { color:var(--green); background:var(--green); }
    .dot.error,.dot.stale { color:var(--red); background:var(--red); }
    .dot.degraded,.dot.polling { color:var(--amber); background:var(--amber); }
    .pill,.badge { padding:3px 8px; border-radius:999px; background:#20313f; color:#bad0dc; font-size:12px; }
    .badge.good { background:#143b2b; color:var(--green); } .badge.warn { background:#44351b; color:var(--amber); } .badge.bad { background:#472024; color:var(--red); }
    .grid { display:grid; gap:14px; grid-template-columns:repeat(12,minmax(0,1fr)); margin-bottom:18px; }
    .card { grid-column:span 3; padding:16px; min-height:112px; }
    .card.wide { grid-column:span 6; } .card.full { grid-column:1/-1; }
    .label { color:var(--muted); text-transform:uppercase; font-size:11px; font-weight:700; letter-spacing:.11em; }
    .value { font-size:29px; font-weight:760; margin-top:7px; }
    .detail { color:#b8cad4; margin-top:4px; }
    section { margin-top:22px; }
    .alerts { display:grid; gap:9px; margin-bottom:18px; }
    .alert { padding:12px 14px; border-left-width:4px; } .alert.good { border-left-color:var(--green); } .alert.warn { border-left-color:var(--amber); } .alert.bad { border-left-color:var(--red); }
    .healthgrid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin-bottom:14px; }
    .health { padding:14px; min-width:0; }
    .healthhead { display:flex; justify-content:space-between; gap:8px; align-items:center; margin-bottom:9px; }
    .health strong { overflow:hidden; text-overflow:ellipsis; }
    .nodes { display:grid; grid-template-columns:repeat(auto-fit,minmax(245px,1fr)); gap:12px; }
    .node { padding:14px; } .nodehead { display:flex; justify-content:space-between; gap:8px; align-items:center; margin-bottom:11px; }
    .node h3 { margin:0; font-size:15px; } .online { color:var(--green); } .offline { color:var(--red); }
    .rows { display:grid; gap:6px; } .row { display:flex; justify-content:space-between; gap:14px; color:var(--muted); }
    .row strong { color:var(--text); text-align:right; font-weight:600; }
    .bars { display:grid; gap:10px; margin-top:12px; } .barrow { display:grid; grid-template-columns:76px 1fr 35px; align-items:center; gap:10px; }
    .bar { height:9px; border-radius:99px; background:#233541; overflow:hidden; } .bar span { display:block; height:100%; background:linear-gradient(90deg,#24a9bd,var(--cyan)); border-radius:inherit; }
    table { width:100%; border-collapse:collapse; margin-top:8px; } th,td { text-align:left; padding:9px 7px; border-bottom:1px solid var(--line); }
    th { color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.08em; }
    .diag { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px 18px; margin-top:12px; }
    .diag .row { padding:7px 0; border-bottom:1px solid var(--line); }
    .labhead { display:flex; justify-content:space-between; align-items:flex-start; gap:14px; margin-bottom:12px; }
    .labstate { padding:8px 11px; border:1px solid #6d5428; border-radius:10px; background:#392f1d; color:var(--amber); font-weight:750; white-space:nowrap; }
    .risk-high,.risk-primary_overlap { color:var(--red); } .risk-elevated,.risk-possible_40mhz_extension,.risk-adjacent,.risk-guarded { color:var(--amber); } .risk-separated,.risk-lower { color:var(--green); }
    .candidate-note { max-width:430px; color:var(--muted); }
    .tablewrap { overflow-x:auto; }
    #error { display:none; color:var(--red); margin-top:8px; }
    @media (max-width:900px) { .card { grid-column:span 6; } .card.wide { grid-column:1/-1; } .healthgrid { grid-template-columns:repeat(2,minmax(0,1fr)); } .diag { grid-template-columns:repeat(2,minmax(0,1fr)); } }
    @media (max-width:560px) { main { padding:14px; } header { align-items:flex-start; } .card { grid-column:1/-1; } .healthgrid,.diag { grid-template-columns:1fr; } .hide-mobile { display:none; } button { min-width:112px; } }
  </style>
</head>
<body><main>
  <header>
    <div class="brand"><div class="logo">⌁</div><div><h1>FREE THE DECO</h1><div class="subtitle">Pine Haven mesh observatory</div></div></div>
    <button id="refresh">Refresh now</button>
  </header>
  <div class="statusbar">
    <span id="status-dot" class="dot"></span><strong id="mode">Loading…</strong>
    <span class="pill" id="version">App</span><span class="muted" id="timing">Contacting monitor…</span>
  </div>
  <div id="alerts" class="alerts"></div>

  <section><h2>Operational health</h2><div class="healthgrid">
    <div class="health"><div class="healthhead"><span>Deco reads</span><span id="read-badge" class="badge">—</span></div><div id="read-detail" class="muted">Awaiting first cycle</div></div>
    <div class="health"><div class="healthhead"><span>Deco session</span><span id="session-badge" class="badge">—</span></div><div id="session-detail" class="muted">Awaiting authentication</div></div>
    <div class="health"><div class="healthhead"><span>HA publishing</span><span id="publisher-badge" class="badge">—</span></div><div id="publisher-detail" class="muted">Awaiting publish</div></div>
    <div class="health"><div class="healthhead"><span>Recovery</span><span id="recovery-badge" class="badge">—</span></div><div id="recovery-detail" class="muted">No recovery needed</div></div>
  </div></section>

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
  <section><div class="card full">
    <div class="labhead"><div><div class="label">2.4 GHz coexistence laboratory</div><h2 style="margin-top:7px">Channel and width preflight</h2><div id="lab-summary" class="muted">Awaiting radio data</div></div><div id="lab-state" class="labstate">DISARMED</div></div>
    <div class="tablewrap"><table><thead><tr><th>Plan</th><th>Wi-Fi</th><th>CORE 15</th><th>AMBIENCE 20</th><th>PERIMETER 11</th><th>Trade-off</th></tr></thead><tbody id="candidate-table"></tbody></table></div>
    <div id="lab-contract" class="alert warn" style="margin-top:14px"></div>
  </div></section>
  <section class="grid"><div class="card full">
    <div class="label">Monitor diagnostics</div><div id="diagnostics" class="diag"></div>
  </div></section>
  <div id="error"></div>
</main>
<script>
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '—').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = value => value === null || value === undefined ? '—' : value;
  const api = path => `${path}`;
  let refreshWatcher = null;

  function alertBox(kind,title,detail) { const div=document.createElement('div'); div.className=`alert ${kind}`; div.innerHTML=`<strong>${esc(title)}</strong><div class="muted">${esc(detail)}</div>`; return div; }
  function badgeKind(value) { const text=String(value||'').toLowerCase(); if (['healthy','authenticated','recovered','not_needed','succeeded'].includes(text)) return 'good'; if (['error','authentication_failed','unavailable','failed','stale'].includes(text)) return 'bad'; return 'warn'; }
  function riskLabel(value) { return String(value||'unknown').replace('primary_overlap','DIRECT').replace('possible_40mhz_extension','40 MHz POSSIBLE').replace('adjacent','ADJACENT').replace('separated','SEPARATED').replaceAll('_',' ').toUpperCase(); }
  function setHealth(prefix,value,detail) { const badge=$(`${prefix}-badge`); badge.textContent=String(value||'unknown').replaceAll('_',' '); badge.className=`badge ${badgeKind(value)}`; $(`${prefix}-detail`).textContent=detail; }
  function age(seconds) { if (seconds === null || seconds === undefined) return 'never'; if (seconds < 60) return `${Math.round(seconds)}s`; if (seconds < 3600) return `${Math.round(seconds/60)}m`; return `${Math.round(seconds/3600)}h`; }

  function render(data) {
    const mesh=data.mesh||{}, mode=data.mode||'unknown', health=data.health||{}, pub=data.publisher||{}, recovery=data.recovery||{}, refresh=data.manual_refresh||{};
    $('mode').textContent=mode.toUpperCase(); $('version').textContent=`v${data.app_version||'?'}`; $('status-dot').className=`dot ${mode}`;
    const next=data.next_poll_in_seconds===null||data.next_poll_in_seconds===undefined?'not scheduled':`next in ${age(data.next_poll_in_seconds)}`;
    $('timing').textContent=data.last_success_at?`Last success ${new Date(data.last_success_at).toLocaleString()} · age ${age(data.poll_age_seconds)} · ${next}`:`No successful read yet · ${next}`;

    const read=health.deco_read||{}, session=health.session||{};
    setHealth('read',read.status,read.error_code?`Safe category: ${read.error_code}`:`${data.successful_cycles||0} successful · ${data.failed_cycles||0} failed`);
    setHealth('session',session.status,session.error_code?`Safe category: ${session.error_code}`:'Authenticated local owner session');
    setHealth('publisher',pub.status,pub.error_code?`Safe category: ${pub.error_code}`:`${pub.total_entities||0} durable entities · last publish ${pub.last_publish_at?new Date(pub.last_publish_at).toLocaleTimeString():'pending'}`);
    setHealth('recovery',recovery.status,recovery.last_recovery_at?`Recovered ${new Date(recovery.last_recovery_at).toLocaleString()}`:`${data.consecutive_failures||0} consecutive failures`);

    const alerts=$('alerts'); alerts.replaceChildren();
    if (data.data_stale) alerts.append(alertBox('bad','Monitor data is stale',`No successful Deco read inside the ${data.stale_after_seconds}s freshness window.`));
    else if (mode==='error') alerts.append(alertBox('bad','Monitor read failed',`Safe error category: ${data.error_code||'unknown'}`));
    if (mesh.offline_count>0) alerts.append(alertBox('warn',`${mesh.offline_count} Deco offline`,'Use the mesh cards below to identify the affected location.'));
    const band2=mesh.wireless_radio?.band2_4||{};
    const coexistence=mesh.coexistence||{}, current=coexistence.current||{}, control=coexistence.control_readiness||{};
    if (current.risk==='high'||current.risk==='elevated') alerts.append(alertBox('warn','Elevated 2.4 GHz coexistence risk',`Channel ${fmt(current.channel)} at ${fmt(current.width_mhz)} MHz has ${current.risk} modeled contention with Pine Haven Zigbee.`));
    if (!alerts.children.length&&mode==='healthy') alerts.append(alertBox('good','Mesh monitor healthy','Deco reads, session health and Home Assistant publishing are within the freshness window.'));

    $('nodes-total').textContent=fmt(mesh.node_count); $('nodes-detail').textContent=mesh.node_count===undefined?'Awaiting data':`${mesh.online_count} online · ${mesh.offline_count} offline`;
    const clients=mesh.connected_clients||{}; $('clients-total').textContent=fmt(clients.reported_count); $('clients-detail').textContent=`${clients.interfaces?.main||0} main · ${clients.interfaces?.iot||0} IoT`;
    $('radio-channel').textContent=band2.channel?`Ch ${band2.channel}`:'—'; $('radio-width').textContent=band2.configured_width_mhz?`${band2.configured_width_mhz} MHz configured width`:'Width unavailable';
    const perf=mesh.controller_performance||{}; $('controller-cpu').textContent=perf.cpu_percent===null||perf.cpu_percent===undefined?'—':`${perf.cpu_percent}%`; $('controller-memory').textContent=perf.memory_percent===null||perf.memory_percent===undefined?'Memory unavailable':`${perf.memory_percent}% memory`;

    const nodes=$('nodes'); nodes.replaceChildren();
    for (const node of mesh.nodes||[]) { const div=document.createElement('div'); div.className='node'; const backhaul=(node.connection_types||[]).join(' + ')||'not reported'; div.innerHTML=`<div class="nodehead"><h3>${esc(node.name)}</h3><strong class="${node.online?'online':'offline'}">${node.online?'ONLINE':'OFFLINE'}</strong></div><div class="rows"><div class="row"><span>Role</span><strong>${esc(node.role)}</strong></div><div class="row"><span>Internet</span><strong>${esc(node.internet)}</strong></div><div class="row"><span>Backhaul</span><strong>${esc(backhaul)}</strong></div><div class="row"><span>Link</span><strong>${node.backhaul_speed_mbps?esc(node.backhaul_speed_mbps)+' Mbit/s':'—'}</strong></div><div class="row"><span>Signal 2.4 / 5</span><strong>${fmt(node.signal_2_4)} / ${fmt(node.signal_5)}</strong></div><div class="row"><span>Firmware</span><strong>${esc(node.firmware_version||'—')}</strong></div></div>`; nodes.append(div); }
    if (!nodes.children.length) nodes.append(alertBox('warn','No mesh snapshot','Monitoring is disabled or the first poll has not completed.'));

    const connections=clients.connection_types||{}, entries=[['2.4 GHz',connections.band2_4||0],['5 GHz',connections.band5||0],['Wired',connections.wired||0],['Unknown',connections.unknown||0]], total=Math.max(1,...entries.map(x=>x[1]),clients.reported_count||1), bars=$('client-bars'); bars.replaceChildren();
    for (const [label,count] of entries) { const row=document.createElement('div'); row.className='barrow'; row.innerHTML=`<span>${esc(label)}</span><div class="bar"><span style="width:${Math.max(1,count/total*100)}%"></span></div><strong>${count}</strong>`; bars.append(row); }
    const tbody=$('radio-table'); tbody.replaceChildren();
    for (const [key,label] of [['band2_4','2.4 GHz'],['band5_1','5 GHz primary'],['band5_2','5 GHz secondary']]) { const band=mesh.wireless_radio?.[key]||{}, tr=document.createElement('tr'); tr.innerHTML=`<td>${label}</td><td>${fmt(band.channel)}</td><td>${band.configured_width_mhz?band.configured_width_mhz+' MHz':'—'}</td><td>${band.automatic_channel===null||band.automatic_channel===undefined?'—':band.automatic_channel?'Yes':'No'}</td>`; tbody.append(tr); }

    $('lab-state').textContent=String(control.state||'disarmed').toUpperCase();
    const widthOnly=coexistence.width_only_20mhz||{};
    $('lab-summary').textContent=current.channel?`Current channel ${current.channel} / ${current.width_mhz} MHz${current.firmware_width_token?' ('+current.firmware_width_token+')':''} is ${current.risk||'unknown'} risk. A width-only move to 20 MHz removes ${widthOnly.possible_extension_exposures_removed||0} modeled extension exposure(s)${widthOnly.core_direct_overlap_remains?' but leaves direct CORE overlap.':'.'} Rankings are geometry only, not spectrum measurements.`:'No current 2.4 GHz channel available.';
    const candidateBody=$('candidate-table'); candidateBody.replaceChildren();
    for (const candidate of coexistence.candidate_plans||[]) { const byId=Object.fromEntries((candidate.zigbee_networks||[]).map(row=>[row.id,row])); const tr=document.createElement('tr'); const cell=id=>`<strong class="risk-${esc(byId[id]?.risk)}">${esc(riskLabel(byId[id]?.risk))}</strong>`; tr.innerHTML=`<td><strong>#${fmt(candidate.geometry_rank)} ${esc(candidate.name)}</strong></td><td>Ch ${fmt(candidate.channel)} / ${fmt(candidate.width_mhz)} MHz</td><td>${cell('core')}</td><td>${cell('ambience')}</td><td>${cell('perimeter')}</td><td class="candidate-note">${esc(candidate.tradeoff)}</td>`; candidateBody.append(tr); }
    if (!candidateBody.children.length) { const tr=document.createElement('tr'); tr.innerHTML='<td colspan="6" class="muted">Candidate geometry is unavailable.</td>'; candidateBody.append(tr); }
    const contract=control.firmware_contract||{}; $('lab-contract').innerHTML=`<strong>No radio write can run from this release.</strong><div class="muted">Firmware mapping: ${esc(contract.endpoint||'—')} / ${esc(contract.form||'—')} with ${esc((contract.known_bandwidth_tokens||[]).join(' and ')||'unconfirmed')} bandwidth tokens. Live behaviour is ${esc(control.live_validation||'unknown')}; a commit may restart the mesh. Next gate: ${esc(control.required_next_step||'not defined')}</div>`;

    const diag=$('diagnostics'); diag.replaceChildren();
    for (const [label,value] of [['App uptime',age(data.app_uptime_seconds)],['Poll interval',`${data.poll_interval_seconds}s`],['Freshness window',`${data.stale_after_seconds}s`],['Last trigger',data.last_poll_trigger||'—'],['Last cycle',data.last_cycle_duration_ms===null?'—':`${data.last_cycle_duration_ms} ms`],['Manual refresh',refresh.status||'idle'],['Successful cycles',data.successful_cycles||0],['Failed cycles',data.failed_cycles||0],['Consecutive failures',data.consecutive_failures||0]]) { const row=document.createElement('div'); row.className='row'; row.innerHTML=`<span>${esc(label)}</span><strong>${esc(value)}</strong>`; diag.append(row); }
    updateRefreshButton(refresh.status||'idle'); $('error').style.display='none';
  }

  function updateRefreshButton(status) { const button=$('refresh'), pending=['queued','running'].includes(status); button.disabled=pending; button.textContent=status==='queued'?'Refresh queued':status==='running'?'Refreshing…':status==='succeeded'?'Refresh complete':status==='failed'?'Refresh failed':'Refresh now'; if (!pending&&status!=='idle') setTimeout(()=>{ if (!button.disabled) button.textContent='Refresh now'; },2500); }
  async function load() { try { const response=await fetch(api('api/v1/status'),{cache:'no-store'}); if (!response.ok) throw new Error(`HTTP ${response.status}`); const data=await response.json(); render(data); return data; } catch (error) { $('error').textContent=`Status refresh failed: ${error.message}`; $('error').style.display='block'; return null; } }
  async function watchRefresh() { clearInterval(refreshWatcher); refreshWatcher=setInterval(async()=>{ const data=await load(); const state=data?.manual_refresh?.status; if (state&&!['queued','running'].includes(state)) { clearInterval(refreshWatcher); refreshWatcher=null; } },750); }
  $('refresh').addEventListener('click',async()=>{ updateRefreshButton('queued'); try { const response=await fetch(api('api/v1/refresh'),{method:'POST'}); const result=await response.json(); if (!response.ok) { $('error').textContent=`Refresh not accepted: ${result.reason||'unknown'}`; $('error').style.display='block'; await load(); return; } watchRefresh(); } catch (error) { $('error').textContent=`Refresh request failed: ${error.message}`; $('error').style.display='block'; updateRefreshButton('idle'); } });
  load(); setInterval(load,15000);
</script></body></html>"""
