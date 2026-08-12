from pathlib import Path
import argparse
import re, os, json, collections

parser = argparse.ArgumentParser(description='Generate an interactive cross-reference graph for the Placement Prep mdBook.')
parser.add_argument('--output', required=True, help='output HTML path, normally book/meta/cross-reference-graph-view.html')
args = parser.parse_args()
repo = Path(__file__).resolve().parents[1]
root = repo / 'src'
out = Path(args.output)

files = sorted(p for p in root.rglob('*.md') if p.name != 'SUMMARY.md')
paths = [p.relative_to(root).as_posix() for p in files]
path_set = set(paths)

heading_re = re.compile(r'^#{1,6}\s+(.+?)\s*#*\s*$', re.M)
link_re = re.compile(r'\[[^\]]*\]\(([^)]*)\)')
edges = set()
missing = 0
nodes = []

def title_for(p, rel):
    text = p.read_text(encoding='utf-8', errors='ignore')
    m = heading_re.search(text)
    if m:
        title = re.sub(r'[`*_]', '', m.group(1)).strip()
    else:
        title = Path(rel).stem.replace('-', ' ').replace('_', ' ').title()
    return title[:160]

def live_url(rel):
    parts = rel.split('/')
    if parts[-1].lower() == 'readme.md':
        path = '/'.join(parts[:-1])
        return 'https://vanos001.github.io/placement_prep/' + (path + '/' if path else '')
    return 'https://vanos001.github.io/placement_prep/' + rel[:-3] + '.html'

for p, rel in zip(files, paths):
    cat = rel.split('/')[0] if '/' in rel else 'root'
    nodes.append({
        'path': rel,
        'title': title_for(p, rel),
        'category': cat,
        'url': live_url(rel),
    })

index = {n['path']: i for i, n in enumerate(nodes)}
for p, rel in zip(files, paths):
    text = p.read_text(encoding='utf-8', errors='ignore')
    base = Path(rel).parent
    for raw in link_re.findall(text):
        raw = raw.strip()
        if raw.startswith(('http://', 'https://', 'mailto:', '#')):
            continue
        target = raw.split('#', 1)[0].split('?', 1)[0]
        if not target.endswith('.md'):
            continue
        resolved = os.path.normpath((base / target).as_posix())
        if resolved == 'SUMMARY.md':
            continue
        if resolved not in path_set:
            missing += 1
            continue
        if resolved == rel:
            continue
        edges.add((index[rel], index[resolved]))

out_counts = collections.Counter(a for a, b in edges)
in_counts = collections.Counter(b for a, b in edges)
for i, n in enumerate(nodes):
    n['id'] = i
    n['outbound'] = out_counts[i]
    n['inbound'] = in_counts[i]

categories = sorted({n['category'] for n in nodes})
category_counts = collections.Counter(n['category'] for n in nodes)
palette = [
    '#2563eb','#dc2626','#059669','#d97706','#7c3aed','#0891b2','#db2777',
    '#65a30d','#ea580c','#4f46e5','#0f766e','#9333ea','#be123c','#0369a1',
    '#15803d','#a16207','#c2410c','#6d28d9','#0e7490','#9f1239','#475569',
]
colors = {cat: palette[i % len(palette)] for i, cat in enumerate(categories)}
for n in nodes:
    n['color'] = colors[n['category']]

edge_data = [{'s': a, 't': b} for a, b in sorted(edges)]
data = {
    'generated': '2026-08-12',
    'nodes': nodes,
    'edges': edge_data,
    'categories': categories,
    'categoryCounts': dict(category_counts),
    'colors': colors,
    'missingLinksIgnored': missing,
}
json_data = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')

html_doc = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Placement Prep Cross-Reference Graph</title>
<style>
:root { color-scheme: light; --ink:#172033; --muted:#64748b; --panel:#ffffffee; --line:#dbe3ef; --accent:#2563eb; }
* { box-sizing:border-box; }
html,body { margin:0; height:100%; overflow:hidden; font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; color:var(--ink); background:#f4f7fb; }
body { display:flex; flex-direction:column; }
header { flex:0 0 auto; padding:14px 18px 10px; background:var(--panel); border-bottom:1px solid var(--line); box-shadow:0 2px 12px #23395d12; z-index:5; }
h1 { margin:0; font-size:20px; letter-spacing:-.02em; }
.subtitle { margin:3px 0 10px; color:var(--muted); font-size:12px; }
.controls { display:flex; flex-wrap:wrap; align-items:center; gap:8px; }
input,select,button { font:inherit; font-size:12px; border:1px solid #cbd5e1; border-radius:7px; padding:7px 9px; background:white; color:var(--ink); }
input { width:min(340px,42vw); }
button { cursor:pointer; }
button:hover { border-color:var(--accent); color:var(--accent); }
label.check { display:flex; align-items:center; gap:5px; color:#475569; font-size:12px; }
label.check input { width:auto; }
.stats { margin-left:auto; color:var(--muted); font-size:11px; white-space:nowrap; }
main { min-height:0; flex:1; position:relative; }
canvas { width:100%; height:100%; display:block; cursor:grab; }
canvas.dragging { cursor:grabbing; }
#info { position:absolute; right:14px; top:14px; width:min(340px,calc(100vw - 28px)); max-height:calc(100% - 28px); overflow:auto; background:var(--panel); border:1px solid var(--line); border-radius:10px; box-shadow:0 6px 24px #17203318; padding:12px; font-size:12px; backdrop-filter:blur(8px); }
#info h2 { margin:0 0 5px; font-size:15px; line-height:1.25; }
#info .path { color:var(--muted); word-break:break-word; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:10px; }
#info p { margin:8px 0; line-height:1.45; }
#info a { color:var(--accent); text-decoration:none; }
#info a:hover { text-decoration:underline; }
.badge { display:inline-block; padding:3px 6px; border-radius:999px; color:white; font-size:10px; margin:7px 4px 0 0; }
#results { margin-top:8px; display:flex; flex-direction:column; gap:3px; }
.result { border:0; text-align:left; background:#f8fafc; padding:5px 6px; border-radius:5px; cursor:pointer; }
.result:hover { background:#e8f0ff; }
.result strong { display:block; font-size:11px; }
.result span { display:block; color:var(--muted); font:10px ui-monospace,SFMono-Regular,Menlo,monospace; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.legend { display:flex; flex-wrap:wrap; gap:5px 10px; margin-top:8px; }
.legend span { display:inline-flex; align-items:center; gap:4px; color:#475569; font-size:10px; }
.dot { width:8px; height:8px; border-radius:50%; display:inline-block; }
.hint { color:var(--muted); font-size:10px; border-top:1px solid var(--line); padding-top:8px; margin-top:10px; }
@media (max-width:700px) { .stats { width:100%; margin-left:0; } #info { top:8px; right:8px; width:calc(100vw - 16px); max-height:38vh; } }
</style>
</head>
<body>
<header>
  <h1>Placement Prep Cross-Reference Graph</h1>
  <div class="subtitle">A local, interactive map of Markdown pages and their internal cross-references. Generated from the current repository; nothing here is pushed.</div>
  <div class="controls">
    <input id="search" type="search" placeholder="Search page title or path…" aria-label="Search pages">
    <select id="category" aria-label="Filter category"><option value="all">All sections</option></select>
    <label class="check"><input id="allEdges" type="checkbox"> show all edges</label>
    <label class="check"><input id="labels" type="checkbox"> labels</label>
    <button id="reset">reset view</button>
    <div id="stats" class="stats"></div>
  </div>
</header>
<main>
  <canvas id="graph" aria-label="Cross-reference graph"></canvas>
  <aside id="info">
    <h2>How to read this</h2>
    <p>Each dot is a Markdown page. Lines are internal Markdown cross-links. Colors identify top-level sections. By default, faint internal links are suppressed so the cross-section relationships remain visible.</p>
    <p>Drag to pan, scroll to zoom, click a node to inspect it, or search for a page. Double-click a selected node to open its deployed page.</p>
    <div id="selection"><span class="path">No page selected.</span></div>
    <div id="results"></div>
    <div id="legend" class="legend"></div>
    <div class="hint">Graph data includes all content Markdown under <code>src/</code> except <code>SUMMARY.md</code>. Self-links and SUMMARY navigation links are omitted.</div>
  </aside>
</main>
<script id="graph-data" type="application/json">__GRAPH_DATA__</script>
<script>
(() => {
  const data = JSON.parse(document.getElementById('graph-data').textContent);
  const canvas = document.getElementById('graph');
  const ctx = canvas.getContext('2d');
  const info = document.getElementById('selection');
  const results = document.getElementById('results');
  const search = document.getElementById('search');
  const category = document.getElementById('category');
  const allEdges = document.getElementById('allEdges');
  const labels = document.getElementById('labels');
  const stats = document.getElementById('stats');
  const legend = document.getElementById('legend');
  const nodes = data.nodes;
  const edges = data.edges;
  const byPath = new Map(nodes.map(n => [n.path, n]));
  const adjacency = new Map(nodes.map(n => [n.id, []]));
  edges.forEach(e => { adjacency.get(e.s).push(e.t); adjacency.get(e.t).push(e.s); });
  const state = { cx:0, cy:0, zoom:.72, selected:-1, hover:-1, query:'', cat:'all', showAll:false, showLabels:false, dragging:false, moved:false, lastX:0, lastY:0 };
  let width=0, height=0, dpr=1;

  data.categories.forEach(cat => {
    const opt = document.createElement('option'); opt.value=cat; opt.textContent = cat + ' (' + data.categoryCounts[cat] + ')'; category.appendChild(opt);
    const item = document.createElement('span'); item.innerHTML = '<i class="dot"></i>' + cat; item.querySelector('.dot').style.background = data.colors[cat]; legend.appendChild(item);
  });
  stats.textContent = nodes.length.toLocaleString() + ' pages · ' + edges.length.toLocaleString() + ' links';

  // Deterministic clustered layout: the graph remains stable between opens and
  // the category structure stays visible even before a force simulation starts.
  function layout() {
    const cats = data.categories;
    const centers = {};
    const clusterRadius = Math.max(600, cats.length * 30);
    cats.forEach((cat, j) => {
      const a = -Math.PI / 2 + j * Math.PI * 2 / cats.length;
      centers[cat] = { x: Math.cos(a) * clusterRadius, y: Math.sin(a) * clusterRadius };
    });
    const grouped = new Map(cats.map(c => [c, []]));
    nodes.forEach(n => grouped.get(n.category).push(n));
    for (const cat of cats) {
      const arr = grouped.get(cat), c = centers[cat];
      arr.forEach((n, i) => {
        const r = 42 + Math.sqrt(i + 1) * 11;
        const a = i * 2.3999632297 + (cat.length % 7) * .17;
        n.x = c.x + Math.cos(a) * r;
        n.y = c.y + Math.sin(a) * r;
      });
    }
    data.centers = centers;
  }
  layout();

  function resize() {
    const rect = canvas.getBoundingClientRect(); width = rect.width; height = rect.height; dpr = Math.max(1, window.devicePixelRatio || 1);
    canvas.width = Math.floor(width * dpr); canvas.height = Math.floor(height * dpr); draw();
  }
  window.addEventListener('resize', resize); resize();

  function worldToScreen(x,y) { return { x: width/2 + (x - state.cx) * state.zoom, y: height/2 + (y - state.cy) * state.zoom }; }
  function screenToWorld(x,y) { return { x: state.cx + (x-width/2)/state.zoom, y: state.cy + (y-height/2)/state.zoom }; }
  function queryMatches(n) { const q=state.query.toLowerCase(); return !q || n.title.toLowerCase().includes(q) || n.path.toLowerCase().includes(q); }
  function categoryVisible(n) { return state.cat === 'all' || n.category === state.cat; }
  function edgeVisible(e) {
    if (state.selected >= 0) return e.s === state.selected || e.t === state.selected;
    if (state.showAll) return true;
    return nodes[e.s].category !== nodes[e.t].category;
  }
  function draw() {
    ctx.setTransform(dpr,0,0,dpr,0,0); ctx.clearRect(0,0,width,height);
    ctx.fillStyle='#f4f7fb'; ctx.fillRect(0,0,width,height);
    ctx.save(); ctx.translate(width/2,height/2); ctx.scale(state.zoom,state.zoom); ctx.translate(-state.cx,-state.cy);
    // Edges first. Cross-section edges are intentionally more visible at overview scale.
    ctx.lineWidth = 0.65 / Math.max(.55,state.zoom);
    edges.forEach(e => {
      if (!edgeVisible(e)) return;
      const a=nodes[e.s], b=nodes[e.t]; const active=state.selected>=0; const cross=a.category!==b.category;
      const related = !active || e.s===state.selected || e.t===state.selected;
      ctx.globalAlpha = active ? (related ? 0.72 : 0) : (cross ? 0.16 : 0.035);
      ctx.strokeStyle = active ? (related ? data.colors[a.category] : '#94a3b8') : (cross ? '#64748b' : '#94a3b8');
      ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
    });
    // Category labels make the cluster layout understandable.
    if (state.zoom > .28) {
      ctx.textAlign='center'; ctx.textBaseline='middle'; ctx.font='600 15px system-ui';
      Object.entries(data.centers).forEach(([cat,c]) => { ctx.globalAlpha = state.cat==='all'||state.cat===cat ? .82 : .18; ctx.fillStyle=data.colors[cat]; ctx.fillText(cat,c.x,c.y-48); });
    }
    nodes.forEach(n => {
      const visible=categoryVisible(n), match=queryMatches(n), selected=n.id===state.selected, hovered=n.id===state.hover;
      const dim = (!visible || (state.query && !match)) && !selected;
      const r = selected ? 7/state.zoom : (hovered ? 5/state.zoom : 2.7/state.zoom);
      ctx.globalAlpha = dim ? .08 : (match && state.query ? 1 : .82);
      ctx.fillStyle = data.colors[n.category]; ctx.beginPath(); ctx.arc(n.x,n.y,Math.max(1.6,r),0,Math.PI*2); ctx.fill();
      if (selected || hovered || (state.showLabels && state.zoom>1.0 && visible && match)) {
        ctx.globalAlpha = selected ? 1 : .78; ctx.fillStyle='#172033'; ctx.font=(selected?'700 ':'')+'10px system-ui'; ctx.textAlign='left'; ctx.textBaseline='bottom'; ctx.fillText(n.title.slice(0,55),n.x+7/state.zoom,n.y-5/state.zoom);
      }
    });
    ctx.restore(); ctx.globalAlpha=1;
  }

  function showNode(n) {
    if (!n) { info.innerHTML='<span class="path">No page selected.</span>'; return; }
    const out=n.outbound, inc=n.inbound;
    info.innerHTML = '<h2>'+escapeHtml(n.title)+'</h2><div class="path">'+escapeHtml(n.path)+'</div><span class="badge" style="background:'+n.color+'">'+escapeHtml(n.category)+'</span><p>'+inc+' inbound link'+(inc===1?'':'s')+' · '+out+' outbound link'+(out===1?'':'s')+'</p><p><a href="'+n.url+'" target="_blank" rel="noopener">Open deployed page ↗</a></p>';
  }
  function escapeHtml(s) { return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
  function renderResults() {
    const q=state.query.toLowerCase(); results.innerHTML=''; if (!q) return;
    const matches=nodes.filter(n=>queryMatches(n)&&categoryVisible(n)).sort((a,b)=>(b.inbound+b.outbound)-(a.inbound+a.outbound)).slice(0,30);
    const cap=document.createElement('div'); cap.style.cssText='color:#64748b;font-size:10px;margin:6px 0 2px'; cap.textContent=matches.length+' matching page'+(matches.length===1?'':'s')+(nodes.filter(n=>queryMatches(n)&&categoryVisible(n)).length>30?' (top 30)':''); results.appendChild(cap);
    matches.forEach(n=>{ const b=document.createElement('button'); b.className='result'; const strong=document.createElement('strong'); strong.textContent=n.title; const span=document.createElement('span'); span.textContent=n.path; b.append(strong,span); b.onclick=()=>{state.selected=n.id; state.cx=n.x; state.cy=n.y; state.zoom=Math.max(state.zoom,1.25); showNode(n); draw();}; results.appendChild(b); });
  }
  function hitTest(x,y) { const p=screenToWorld(x,y); let best=-1, bd=Infinity; nodes.forEach(n=>{ if(!categoryVisible(n)) return; const d=Math.hypot(n.x-p.x,n.y-p.y); const limit=Math.max(10/state.zoom,5); if(d<limit&&d<bd){best=n.id;bd=d;} }); return best; }
  canvas.addEventListener('pointerdown',e=>{state.dragging=true;state.moved=false;state.lastX=e.clientX;state.lastY=e.clientY;canvas.classList.add('dragging');canvas.setPointerCapture(e.pointerId);});
  canvas.addEventListener('pointermove',e=>{ if(!state.dragging){const id=hitTest(e.offsetX,e.offsetY);if(id!==state.hover){state.hover=id;canvas.style.cursor=id>=0?'pointer':'grab';draw();}return;} const dx=e.clientX-state.lastX,dy=e.clientY-state.lastY; if(Math.abs(dx)+Math.abs(dy)>2)state.moved=true; state.cx-=dx/state.zoom;state.cy-=dy/state.zoom;state.lastX=e.clientX;state.lastY=e.clientY;draw(); });
  canvas.addEventListener('pointerup',e=>{state.dragging=false;canvas.classList.remove('dragging');if(!state.moved){const id=hitTest(e.offsetX,e.offsetY);if(id>=0){state.selected=id;showNode(nodes[id]);draw();}}});
  canvas.addEventListener('dblclick',e=>{const id=hitTest(e.offsetX,e.offsetY);if(id>=0)window.open(nodes[id].url,'_blank','noopener');});
  canvas.addEventListener('wheel',e=>{e.preventDefault();const before=screenToWorld(e.offsetX,e.offsetY);const factor=Math.exp(-e.deltaY*.001);state.zoom=Math.max(.08,Math.min(5,state.zoom*factor));const after=screenToWorld(e.offsetX,e.offsetY);state.cx+=before.x-after.x;state.cy+=before.y-after.y;draw();},{passive:false});
  search.addEventListener('input',()=>{state.query=search.value.trim();renderResults();draw();});
  category.addEventListener('change',()=>{state.cat=category.value;renderResults();draw();});
  allEdges.addEventListener('change',()=>{state.showAll=allEdges.checked;draw();});
  labels.addEventListener('change',()=>{state.showLabels=labels.checked;draw();});
  document.getElementById('reset').onclick=()=>{state.selected=-1;state.query='';search.value='';state.cat='all';category.value='all';state.showAll=false;allEdges.checked=false;state.showLabels=false;labels.checked=false;layout();state.cx=0;state.cy=0;state.zoom=.72;showNode(null);renderResults();draw();};
  showNode(null); renderResults(); draw();
})();
</script>
</body>
</html>'''.replace('__GRAPH_DATA__', json_data)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(html_doc, encoding='utf-8')
print(f'created {out} ({out.stat().st_size/1024/1024:.2f} MiB)')
print(f'nodes={len(nodes)} edges={len(edges)} missing_ignored={missing}')
