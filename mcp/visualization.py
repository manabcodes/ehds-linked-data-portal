VIZ_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Knowledge Graph — EHDS Portal</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/dagre/0.8.5/dagre.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/cytoscape-dagre@2.5.0/cytoscape-dagre.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Space+Grotesk:wght@400;600;700&display=swap');

  :root {
    --bg:       #07090f;
    --surface:  #0c1018;
    --border:   #161e2e;
    --accent:   #4fffb0;
    --accent2:  #ff6b9d;
    --accent3:  #ffcd3c;
    --text:     #cdd6f4;
    --muted:    #45536b;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'Space Grotesk', sans-serif;
    background: var(--bg);
    color: var(--text);
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  header {
    display: flex;
    align-items: center;
    gap: 1.2rem;
    padding: 0.6rem 1.2rem;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }
  header a {
    color: var(--muted);
    text-decoration: none;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    transition: color 0.15s;
  }
  header a:hover { color: var(--accent); }
  header h1 {
    font-size: 0.9rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--accent);
  }
  #edge-count {
    margin-left: auto;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    color: var(--muted);
  }

  .controls {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    padding: 0.5rem 1.2rem;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
    flex-wrap: wrap;
  }
  .ctrl-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.12em;
  }
  .seg {
    display: flex;
    border: 1px solid var(--border);
    border-radius: 5px;
    overflow: hidden;
  }
  .seg button {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    background: transparent;
    color: var(--muted);
    border: none;
    border-right: 1px solid var(--border);
    padding: 0.3rem 0.75rem;
    cursor: pointer;
    transition: all 0.15s;
    letter-spacing: 0.04em;
  }
  .seg button:last-child { border-right: none; }
  .seg button.active { background: var(--accent); color: var(--bg); font-weight: 600; }
  .seg button:hover:not(.active) { background: var(--border); color: var(--text); }

  select {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 5px;
    padding: 0.3rem 0.6rem;
    cursor: pointer;
    min-width: 180px;
  }
  select:disabled { opacity: 0.35; cursor: not-allowed; }
  select:focus { outline: none; border-color: var(--accent); }

  .sep { width: 1px; height: 20px; background: var(--border); }

  .legend {
    display: flex;
    gap: 0.8rem;
    flex-wrap: wrap;
    align-items: center;
    margin-left: auto;
  }
  .li {
    display: flex;
    align-items: center;
    gap: 0.3rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.63rem;
    color: var(--muted);
  }
  .ld { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }

  .main { display: flex; flex: 1; overflow: hidden; }

  #cy {
    flex: 1;
    width: 100%;
    height: 100%;
    background: var(--bg);
    background-image:
      radial-gradient(circle at 20% 50%, #4fffb008 0%, transparent 50%),
      radial-gradient(circle at 80% 20%, #ff6b9d06 0%, transparent 40%);
    position: relative;
  }

  #loading {
    position: absolute;
    inset: 0;
    background: var(--bg);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    z-index: 50;
    transition: opacity 0.3s;
  }
  #loading.fade { opacity: 0; pointer-events: none; }
  #loading.hidden { display: none; }

  .spinner {
    width: 36px; height: 36px;
    border: 2px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .load-msg {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    color: var(--muted);
    letter-spacing: 0.08em;
  }

  #panel {
    width: 260px;
    background: var(--surface);
    border-left: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    flex-shrink: 0;
  }
  .panel-section {
    padding: 0.8rem;
    border-bottom: 1px solid var(--border);
  }
  .panel-head {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.6rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.14em;
    margin-bottom: 0.6rem;
  }
  .stat-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.4rem;
  }
  .stat {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 5px;
    padding: 0.5rem;
    text-align: center;
  }
  .stat .n { font-size: 1.3rem; font-weight: 700; color: var(--accent); line-height: 1; }
  .stat .l { font-family: 'IBM Plex Mono', monospace; font-size: 0.58rem; color: var(--muted); margin-top: 0.15rem; text-transform: uppercase; }

  #node-info {
    flex: 1;
    overflow-y: auto;
    padding: 0.8rem;
  }
  .kv { margin-bottom: 0.4rem; }
  .kv .k { font-family: 'IBM Plex Mono', monospace; font-size: 0.62rem; color: var(--muted); }
  .kv .v { font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; color: var(--text); word-break: break-all; }
  .kv .v.green  { color: var(--accent); }
  .kv .v.red    { color: var(--accent2); }
  .kv .v.yellow { color: var(--accent3); }

  .empty-msg {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    color: var(--muted);
    line-height: 1.7;
  }

  .toolbar {
    padding: 0.5rem 0.8rem;
    border-bottom: 1px solid var(--border);
    display: flex;
    gap: 0.4rem;
  }
  .tool-btn {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    background: var(--bg);
    color: var(--muted);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.25rem 0.5rem;
    cursor: pointer;
    transition: all 0.15s;
  }
  .tool-btn:hover { border-color: var(--accent); color: var(--accent); }

  ::-webkit-scrollbar { width: 3px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border); }
</style>
</head>
<body>

<header>
  <a href="/">← EHDS Portal</a>
  <h1>Knowledge Graph Explorer</h1>
  <span id="edge-count"></span>
</header>

<div class="controls">
  <span class="ctrl-label">View</span>
  <div class="seg">
    <button class="active" id="btn-overview" onclick="setMode('overview')">Overview</button>
    <button id="btn-cohort" onclick="setMode('cohort')">Cohort</button>
  </div>

  <div class="sep"></div>
  <span class="ctrl-label">Dataset</span>
  <select id="ds" onchange="onDsChange()" disabled>
    <option value="">— select cohort —</option>
    <option value="diabetes">Type 2 Diabetes</option>
    <option value="hypertension">Essential Hypertension</option>
    <option value="metabolic-syndrome">Metabolic Syndrome</option>
    <option value="obesity">Obesity</option>
    <option value="hyperlipidemia">Hyperlipidemia</option>
    <option value="prediabetes">Prediabetes</option>
    <option value="hypothyroidism">Hypothyroidism</option>
    <option value="anemia">Anemia</option>
    <option value="heart-failure">Heart Failure</option>
    <option value="stroke">Stroke</option>
    <option value="myocardial-infarction">Myocardial Infarction</option>
    <option value="ischemic-heart-disease">Ischaemic Heart Disease</option>
    <option value="atrial-fibrillation">Atrial Fibrillation</option>
    <option value="dementia">Dementia</option>
    <option value="anxiety">Anxiety</option>
    <option value="ptsd">PTSD</option>
    <option value="alzheimers">Alzheimer's Disease</option>
    <option value="osteoporosis">Osteoporosis</option>
    <option value="rheumatoid-arthritis">Rheumatoid Arthritis</option>
    <option value="chronic-kidney-disease">Chronic Kidney Disease</option>
    <option value="asthma">Asthma</option>
    <option value="copd">COPD</option>
    <option value="sleep-apnea">Sleep Apnea</option>
    <option value="uti">Urinary Tract Infection</option>
    <option value="breast-cancer">Breast Cancer</option>
    <option value="prostate-cancer">Prostate Cancer</option>
    <option value="colorectal-cancer">Colorectal Cancer</option>
    <option value="osteoarthritis">Osteoarthritis</option>
    <option value="substance-use-disorder">Substance Use Disorder</option>
    <option value="chronic-pain">Chronic Pain</option>
  </select>

  <div class="sep"></div>
  <span class="ctrl-label">Layer</span>
  <div class="seg">
    <button class="active" id="btn-policy" onclick="setLayer('policy')">Policy</button>
    <button id="btn-clinical" onclick="setLayer('clinical')">Clinical</button>
  </div>
  <div class="sep"></div>
  <input id="search" type="text" placeholder="Search nodes..." 
    oninput="highlightSearch(this.value)"
    style="font-family:'IBM Plex Mono',monospace;font-size:0.72rem;
           background:var(--bg);color:var(--text);border:1px solid var(--border);
           border-radius:5px;padding:0.3rem 0.6rem;width:160px;outline:none;"
    onfocus="this.style.borderColor='var(--accent)'"
    onblur="this.style.borderColor='var(--border)'">

  <div class="legend" id="legend"></div>
</div>

<div class="main">
  <div style="position:relative;flex:1;overflow:hidden;height:100%">
    <div id="cy"></div>
    <div id="loading">
      <div class="spinner"></div>
      <div class="load-msg" id="load-msg">Initialising...</div>
    </div>
  </div>

  <div id="panel">
    <div class="toolbar">
      <button class="tool-btn" onclick="cy && cy.fit()">Fit</button>
      <button class="tool-btn" onclick="cy && cy.zoom(cy.zoom()*1.3)">+</button>
      <button class="tool-btn" onclick="cy && cy.zoom(cy.zoom()*0.77)">−</button>
      <button class="tool-btn" onclick="rerun()">↺ Reload</button>
    </div>
    <div class="panel-section">
      <div class="panel-head">Graph Stats</div>
      <div class="stat-grid">
        <div class="stat"><div class="n" id="s-nodes">—</div><div class="l">Nodes</div></div>
        <div class="stat"><div class="n" id="s-edges">—</div><div class="l">Edges</div></div>
        <div class="stat"><div class="n">30</div><div class="l">Cohorts</div></div>
        <div class="stat"><div class="n">511</div><div class="l">Patients</div></div>
      </div>
    </div>
    <div class="panel-section">
      <div class="panel-head">Selected Node</div>
    </div>
    <div id="node-info">
      <p class="empty-msg">Click any node to inspect its properties.</p>
    </div>
  </div>
</div>

<script>
// ── Constants ────────────────────────────────────────────────────────────────
const SPARQL_URL = '/sparql';
const B = 'https://ehds-prototype.example.org/';
const GRAPH_CAT = B + 'graph/catalogue';

const CAT_COLOR = {
  metabolic:'#4fffb0', cardiovascular:'#ff6b9d', oncology:'#fab387',
  mental:'#cba6f7', respiratory:'#89dceb', musculoskeletal:'#ffcd3c', other:'#45536b'
};

const DS_CAT = {
  'diabetes':'metabolic','hypertension':'metabolic','metabolic-syndrome':'metabolic',
  'obesity':'metabolic','hyperlipidemia':'metabolic','prediabetes':'metabolic',
  'hypothyroidism':'metabolic','anemia':'metabolic',
  'heart-failure':'cardiovascular','stroke':'cardiovascular',
  'myocardial-infarction':'cardiovascular','ischemic-heart-disease':'cardiovascular',
  'atrial-fibrillation':'cardiovascular',
  'breast-cancer':'oncology','prostate-cancer':'oncology','colorectal-cancer':'oncology',
  'anxiety':'mental','ptsd':'mental','dementia':'mental','alzheimers':'mental',
  'asthma':'respiratory','copd':'respiratory','sleep-apnea':'respiratory',
  'osteoporosis':'musculoskeletal','rheumatoid-arthritis':'musculoskeletal','osteoarthritis':'musculoskeletal',
  'chronic-kidney-disease':'other','uti':'other','substance-use-disorder':'other','chronic-pain':'other',
};

const PT_COUNTS = {
  'diabetes':40,'hypertension':40,'metabolic-syndrome':40,'obesity':40,'hyperlipidemia':40,
  'prediabetes':40,'hypothyroidism':40,'anemia':40,'heart-failure':15,'stroke':40,
  'myocardial-infarction':40,'ischemic-heart-disease':40,'atrial-fibrillation':40,'dementia':0,
  'anxiety':10,'ptsd':10,'alzheimers':40,'osteoporosis':40,'rheumatoid-arthritis':38,
  'chronic-kidney-disease':40,'asthma':28,'copd':40,'sleep-apnea':40,'uti':40,
  'breast-cancer':10,'prostate-cancer':10,'colorectal-cancer':10,'osteoarthritis':40,
  'substance-use-disorder':10,'chronic-pain':10,
};

let cy = null;
let mode = 'overview';
let layer = 'policy';
let dataset = null;

// ── Utilities ────────────────────────────────────────────────────────────────
function sh(uri) {
  return uri
    .replace(B, 'ehds:')
    .replace('http://hl7.org/fhir/', 'fhir:')
    .replace('http://www.w3.org/ns/odrl/2/', 'odrl:')
    .replace('http://www.w3.org/ns/dcat#', 'dcat:')
    .replace('http://snomed.info/id/', 'snomed:')
    .replace('http://purl.org/dc/terms/', 'dct:')
    .replace('https://w3id.org/dpv#', 'dpv:');
}

async function sq(q) {
  const r = await fetch(SPARQL_URL + '?query=' + encodeURIComponent(q),
    { headers: { Accept: 'application/sparql-results+json' } });
  const d = await r.json();
  return d.results.bindings;
}

function loading(msg) {
  const el = document.getElementById('loading');
  el.classList.remove('hidden', 'fade');
  document.getElementById('load-msg').textContent = msg || 'Loading...';
}

function done() {
  const el = document.getElementById('loading');
  el.classList.add('fade');
  setTimeout(() => el.classList.add('hidden'), 350);
}

function stats(n, e) {
  document.getElementById('s-nodes').textContent = n;
  document.getElementById('s-edges').textContent = e;
  document.getElementById('edge-count').textContent = n + ' nodes · ' + e + ' edges';
}

function setLegend(items) {
  document.getElementById('legend').innerHTML = items
    .map(([c, l]) => `<div class="li"><div class="ld" style="background:${c}"></div>${l}</div>`)
    .join('');
}

function nodeInfo(data) {
  if (!data) {
    document.getElementById('node-info').innerHTML =
      '<p class="empty-msg">Click any node to inspect its properties.</p>';
    return;
  }
  const colors = { permission: 'green', prohibition: 'red', obligation: 'yellow' };
  const html = Object.entries(data)
    .filter(([k]) => k !== 'id')
    .map(([k, v]) => {
      const cls = colors[v] || '';
      return `<div class="kv"><div class="k">${k}</div><div class="v ${cls}">${v}</div></div>`;
    }).join('');
  document.getElementById('node-info').innerHTML =
    html || '<p class="empty-msg">No properties.</p>';
}

// ── Cytoscape init ───────────────────────────────────────────────────────────
function makeCy(elements, layoutOpts) {
  if (cy) { cy.destroy(); cy = null; }

  cy = cytoscape({
    container: document.getElementById('cy'),
    elements,
    style: [
      {
        selector: 'node',
        style: {
          'background-color': 'data(color)',
          'label': 'data(label)',
          'color': '#cdd6f4',
          'font-size': '7px',
          'font-family': 'IBM Plex Mono, monospace',
          'text-valign': 'bottom',
          'text-margin-y': '2px',
          'min-zoomed-font-size': '5px',
          'text-outline-width': '2px',
          'text-outline-color': '#07090f',
          'width': 'data(size)',
          'height': 'data(size)',
          'border-width': '1.5px',
          'border-color': 'data(color)',
          'border-opacity': 0.6,
        }
      },
      {
        selector: 'node[shape]',
        style: { 'shape': 'data(shape)' }
      },
      {
        selector: 'node:selected',
        style: { 'border-width': '3px', 'border-opacity': 1, 'border-color': '#ffffff' }
      },
      {
        selector: 'node:hover',
        style: { 'border-opacity': 1, 'border-width': '2px' }
      },
      {
        selector: 'edge',
        style: {
          'line-color': 'data(color)',
          'target-arrow-color': 'data(color)',
          'target-arrow-shape': 'triangle',
          'arrow-scale': 0.6,
          'curve-style': 'bezier',
          'width': 'data(width)',
          'opacity': 0.55,
          'label': 'data(label)',
          'font-size': '8px',
          'font-family': 'IBM Plex Mono, monospace',
          'color': '#45536b',
          'text-rotation': 'autorotate',
        }
      },
      {
        selector: 'edge[dashed]',
        style: { 'line-style': 'dashed', 'line-dash-pattern': [4, 3] }
      },
    ],
    layout: layoutOpts,
    minZoom: 0.05,
    maxZoom: 5,
    wheelSensitivity: 0.3,
  });

  cy.on('tap', 'node', e => {
    nodeInfo(e.target.data('meta') || null);
    const node = e.target;
    const connected = node.closedNeighborhood();
    cy.elements().style('opacity', 0.06);
    connected.style('opacity', 1);
  });

  cy.on('tap', evt => {
    if (evt.target === cy) {
      nodeInfo(null);
      cy.elements().style('opacity', 1);
    }
  });
  cy.one('layoutstop', () => {
    cy.fit(undefined, 40);
    stats(cy.nodes().length, cy.edges().length);
    done();
  });

  setTimeout(() => {
    stats(cy ? cy.nodes().length : 0, cy ? cy.edges().length : 0);
    done();
  }, 5000);
}

// ── Overview ─────────────────────────────────────────────────────────────────
async function loadOverview() {
  loading('Querying catalogue...');
  setLegend([
    ['#4fffb0', 'Metabolic'], ['#ff6b9d', 'Cardiovascular'], ['#fab387', 'Oncology'],
    ['#cba6f7', 'Mental Health'], ['#89dceb', 'Respiratory'], ['#ffcd3c', 'Musculoskeletal'],
  ]);

  const rows = await sq(`
SELECT ?ds ?title ?policy WHERE {
  GRAPH <${GRAPH_CAT}> {
    ?ds a <http://www.w3.org/ns/dcat#Dataset> ;
        <http://purl.org/dc/terms/title> ?title ;
        <http://www.w3.org/ns/odrl/2/hasPolicy> ?policy .
  }
}`);

  const elements = [];
  const seenDs = new Set();
  const seenPol = new Set();
  const polDs = {};

  for (const r of rows) {
    const uri   = r.ds.value;
    const title = r.title.value;
    const pol   = r.policy.value;
    const slug  = uri.replace(B + 'dataset-', '');
    const cat   = DS_CAT[slug] || 'other';
    const color = CAT_COLOR[cat];
    const count = PT_COUNTS[slug] || 0;
    const size  = Math.max(18, 14 + Math.sqrt(count) * 2);

    if (!seenDs.has(uri)) {
      seenDs.add(uri);
      elements.push({ data: {
        id: uri,
        label: title.replace('Synthetic ', '').replace(' Cohort', ''),
        color, size, shape: 'ellipse',
        meta: { uri: sh(uri), category: cat, patients: count, policy: sh(pol) }
      }});
      if (!polDs[pol]) polDs[pol] = [];
      polDs[pol].push(uri);
    }
  }

  for (const [pol, dss] of Object.entries(polDs)) {
    if (!seenPol.has(pol)) {
      seenPol.add(pol);
      const label = sh(pol).replace('ehds:policy-', '').replace('ehds:', '');
      elements.push({ data: {
        id: pol, label, color: '#ff6b9d', size: 16, shape: 'diamond',
        meta: { uri: sh(pol), type: 'ODRL Policy', datasets: dss.length }
      }});
    }
    for (const ds of dss) {
      elements.push({ data: {
        id: ds + '_' + pol, source: ds, target: pol,
        label: 'hasPolicy', color: '#ff6b9d44', width: 1
      }});
    }
  }

  makeCy(elements, {
    name: 'cose',
    animate: true,
    animationDuration: 800,
    nodeRepulsion: () => 8000,
    nodeOverlap: 20,
    idealEdgeLength: () => 100,
    edgeElasticity: () => 100,
    nestingFactor: 1.2,
    gravity: 80,
    numIter: 1000,
    initialTemp: 200,
    coolingFactor: 0.95,
    minTemp: 1.0,
  });
}

// ── Cohort / Policy ──────────────────────────────────────────────────────────
async function loadPolicy(slug) {
  loading('Loading ODRL policy graph...');
  setLegend([
    ['#4fffb0', 'Dataset'], ['#ff6b9d', 'Policy'],
    ['#ffcd3c', 'Permission'], ['#f38ba8', 'Prohibition'],
    ['#89dceb', 'Obligation'], ['#cba6f7', 'Constraint'],
  ]);

  const dsUri = B + 'dataset-' + slug;
  const rows = await sq(`
SELECT ?policy ?type ?action ?constraint WHERE {
  GRAPH <${GRAPH_CAT}> {
    <${dsUri}> <http://www.w3.org/ns/odrl/2/hasPolicy> ?policy .
    {
      ?policy <http://www.w3.org/ns/odrl/2/permission> ?rule .
      BIND("permission" AS ?type)
    } UNION {
      ?policy <http://www.w3.org/ns/odrl/2/prohibition> ?rule .
      BIND("prohibition" AS ?type)
    } UNION {
      ?policy <http://www.w3.org/ns/odrl/2/obligation> ?rule .
      BIND("obligation" AS ?type)
    }
    ?rule <http://www.w3.org/ns/odrl/2/action> ?action .
    OPTIONAL {
      ?rule <http://www.w3.org/ns/odrl/2/constraint> ?c .
      ?c <http://www.w3.org/ns/odrl/2/rightOperand> ?constraint .
    }
  }
}`);

  const elements  = [];
  const seenPol   = new Set();
  const seenRule  = new Set();
  const typeColor = { permission: '#ffcd3c', prohibition: '#f38ba8', obligation: '#89dceb' };

  elements.push({ data: {
    id: dsUri,
    label: slug.replace(/-/g, ' '),
    color: '#4fffb0', size: 36, shape: 'star',
    meta: { uri: sh(dsUri), type: 'Dataset' }
  }});

  for (const r of rows) {
    const pol = r.policy.value;
    const typ = r.type.value;
    const act = r.action.value;
    const con = r.constraint ? r.constraint.value : null;
    const tc  = typeColor[typ] || '#cba6f7';

    if (!seenPol.has(pol)) {
      seenPol.add(pol);
      const pl = sh(pol).replace('ehds:policy-', '').replace('ehds:', '');
      elements.push({ data: {
        id: pol, label: pl, color: '#ff6b9d', size: 22, shape: 'diamond',
        meta: { uri: sh(pol), type: 'ODRL Policy' }
      }});
      elements.push({ data: {
        id: dsUri + '->' + pol, source: dsUri, target: pol,
        label: 'hasPolicy', color: '#ff6b9d88', width: 2
      }});
    }

    const ruleId = pol + '_' + typ + '_' + act;
    if (!seenRule.has(ruleId)) {
      seenRule.add(ruleId);
      const al = sh(act).replace('odrl:', '').replace('ehds:', '');
      elements.push({ data: {
        id: ruleId, label: al, color: tc, size: 16, shape: 'ellipse',
        meta: { uri: sh(act), type: typ }
      }});
      elements.push({ data: {
        id: pol + '->' + ruleId, source: pol, target: ruleId,
        label: typ, color: tc + '88', width: 1.5
      }});
    }

    if (con) {
      const cId = ruleId + '_con_' + con;
      const cl  = sh(con).replace('dpv:', '').replace('odrl:', '').replace('ehds:', '');
      elements.push({ data: {
        id: cId, label: cl, color: '#cba6f7', size: 12, shape: 'rectangle',
        meta: { uri: sh(con), type: 'Constraint', parent: typ }, dashed: true
      }});
      elements.push({ data: {
        id: ruleId + '->' + cId, source: ruleId, target: cId,
        label: '', color: '#cba6f755', width: 1, dashed: true
      }});
    }
  }

  makeCy(elements, {
    name: 'dagre',
    rankDir: 'LR',
    nodeSep: 60,
    rankSep: 120,
    animate: true,
    animationDuration: 600,
    padding: 40,
  });
}

// ── Cohort / Clinical ────────────────────────────────────────────────────────
async function loadClinical(slug) {
  loading('Querying clinical graph...');
  setLegend([
    ['#4fffb0', 'Dataset'], ['#89b4fa', 'Patient (M)'], ['#f38ba8', 'Patient (F)'],
    ['#fab387', 'Condition'], ['#cba6f7', 'Medication'],
  ]);

  const graphUri = B + 'graph/' + slug;

  const ptRows = await sq(`
SELECT DISTINCT ?patient ?gender WHERE {
  GRAPH <${graphUri}> {
    ?patient a <http://hl7.org/fhir/Patient> .
    OPTIONAL { ?patient <http://hl7.org/fhir/gender> ?gender . }
  }
}`);

  const condRows = await sq(`
SELECT DISTINCT ?patient ?condDisplay WHERE {
  GRAPH <${graphUri}> {
    ?cond a <http://hl7.org/fhir/Condition> ;
          <http://hl7.org/fhir/subject> ?patient ;
          <http://hl7.org/fhir/code> ?cc .
    ?cc <http://hl7.org/fhir/display> ?condDisplay .
  }
} LIMIT 400`);

  const medRows = await sq(`
SELECT DISTINCT ?patient ?medDisplay WHERE {
  GRAPH <${graphUri}> {
    ?med a <http://hl7.org/fhir/MedicationRequest> ;
         <http://hl7.org/fhir/subject> ?patient ;
         <http://hl7.org/fhir/medicationCode> ?mc .
    ?mc <http://hl7.org/fhir/display> ?medDisplay .
  }
} LIMIT 400`);

  const elements  = [];
  const seenPt    = new Map();
  const seenCon   = new Set();
  const seenMed   = new Set();
  const edgeSeen  = new Set();
  let ptIdx = 0;

  const hub = B + 'hub-' + slug;
  elements.push({ data: {
    id: hub, label: slug.replace(/-/g, ' '),
    color: '#4fffb0', size: 40, shape: 'star',
    meta: { type: 'Dataset', cohort: slug, patients: PT_COUNTS[slug] || 0 }
  }});

  for (const r of ptRows) {
    const ptUri  = r.patient.value;
    const gender = r.gender ? r.gender.value : 'unknown';
    const ptColor = gender === 'female' ? '#f38ba8' : '#89b4fa';
    if (!seenPt.has(ptUri)) {
      ptIdx++;
      seenPt.set(ptUri, 'P' + ptIdx);
      elements.push({ data: {
        id: ptUri, label: 'P' + ptIdx,
        color: ptColor, size: 10, shape: 'ellipse',
        meta: { type: 'Patient', id: 'P' + ptIdx, gender }
      }});
      elements.push({ data: {
        id: hub + '->' + ptUri, source: hub, target: ptUri,
        label: '', color: '#4fffb022', width: 0.5
      }});
    }
  }

  for (const r of condRows) {
    const ptUri = r.patient.value;
    const cond  = r.condDisplay.value;
    if (!seenCon.has(cond)) {
      seenCon.add(cond);
      const cl = cond.length > 24 ? cond.slice(0, 22) + '\u2026' : cond;
      elements.push({ data: {
        id: 'cond:' + cond, label: cl,
        color: '#fab387', size: 13, shape: 'triangle',
        meta: { type: 'Condition', display: cond }
      }});
    }
    if (seenPt.has(ptUri)) {
      const eid = ptUri + '->cond:' + cond;
      if (!edgeSeen.has(eid)) {
        edgeSeen.add(eid);
        elements.push({ data: {
          id: eid, source: ptUri, target: 'cond:' + cond,
          label: '', color: '#fab38733', width: 0.5
        }});
      }
    }
  }

  for (const r of medRows) {
    const ptUri = r.patient.value;
    const med   = r.medDisplay.value;
    if (!seenMed.has(med)) {
      seenMed.add(med);
      const ml = med.length > 24 ? med.slice(0, 22) + '\u2026' : med;
      elements.push({ data: {
        id: 'med:' + med, label: ml,
        color: '#cba6f7', size: 11, shape: 'rectangle',
        meta: { type: 'Medication', display: med }
      }});
    }
    if (seenPt.has(ptUri)) {
      const eid = ptUri + '->med:' + med;
      if (!edgeSeen.has(eid)) {
        edgeSeen.add(eid);
        elements.push({ data: {
          id: eid, source: ptUri, target: 'med:' + med,
          label: '', color: '#cba6f733', width: 0.5
        }});
      }
    }
  }

  makeCy(elements, {
    name: 'cose',
    animate: true,
    animationDuration: 600,
    nodeRepulsion: () => 4000,
    nodeOverlap: 10,
    idealEdgeLength: () => 60,
    edgeElasticity: () => 80,
    gravity: 120,
    numIter: 800,
    initialTemp: 150,
    coolingFactor: 0.95,
    minTemp: 1.0,
  });
}

// ── Controls ──────────────────────────────────────────────────────────────────
function setMode(m) {
  mode = m;
  document.getElementById('btn-overview').classList.toggle('active', m === 'overview');
  document.getElementById('btn-cohort').classList.toggle('active', m === 'cohort');
  document.getElementById('ds').disabled = (m === 'overview');
  if (m === 'overview') loadOverview();
  else if (dataset) rerun();
}

function setLayer(l) {
  layer = l;
  document.getElementById('btn-policy').classList.toggle('active', l === 'policy');
  document.getElementById('btn-clinical').classList.toggle('active', l === 'clinical');
  if (mode === 'cohort' && dataset) rerun();
}

function onDsChange() {
  const v = document.getElementById('ds').value;
  if (!v) return;
  dataset = v;
  mode = 'cohort';
  document.getElementById('btn-overview').classList.remove('active');
  document.getElementById('btn-cohort').classList.add('active');
  rerun();
}

function rerun() {
  if (mode === 'overview') loadOverview();
  else if (dataset) {
    if (layer === 'policy') loadPolicy(dataset);
    else loadClinical(dataset);
  }
}

function highlightSearch(term) {
  if (!cy) return;
  term = term.trim().toLowerCase();
  if (!term) {
    cy.elements().removeClass('faded highlighted');
    cy.elements().style('opacity', 1);
    return;
  }
  cy.elements().style('opacity', 0.08);
  const matched = cy.nodes().filter(n => {
    const label = (n.data('label') || '').toLowerCase();
    const meta  = n.data('meta') || {};
    const disp  = (meta.display || '').toLowerCase();
    return label.includes(term) || disp.includes(term);
  });
  matched.style('opacity', 1);
  matched.connectedEdges().style('opacity', 0.6);
  matched.connectedEdges().connectedNodes().style('opacity', 0.5);
}

// ── Boot ──────────────────────────────────────────────────────────────────────
loadOverview();
</script>
</body>
</html>"""

