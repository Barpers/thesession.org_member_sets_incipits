import json, html, datetime, sys


now = (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))


default_member_id = 179479 #barper's member ID
arg = sys.argv[1] if len(sys.argv) > 1 else str(default_member_id)


# Read the JSON
with open('./data/' + arg + '_sets_full.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Collect all unique tags (case-insensitive, preserve original for display)
member_name = data[0].get('member', {}).get('name', 'Unknown Member')
all_tags = {}
for item in data:
    for tag in item.get('tags', []):
        all_tags[tag.lower()] = tag

tag_options_html = ''
for lower, orig in sorted(all_tags.items()):
    tag_options_html += f'<label class="tag-option"><input type="checkbox" value="{html.escape(lower)}" onchange="applyFilters()"> {html.escape(orig)}</label>\n'

# Collect all unique keys from settings
all_keys = {}
for item in data:
    for setting in item.get('settings', []):
        key = setting.get('key', '').strip()
        if key:
            all_keys[key.lower()] = key

key_options_html = ''
for lower, orig in sorted(all_keys.items()):
    key_options_html += f'<label class="tag-option"><input type="checkbox" value="{html.escape(lower)}" onchange="applyFilters()"> {html.escape(orig)}</label>\n'

# Collect all unique tune types from settings
all_types = {}
for item in data:
    for setting in item.get('settings', []):
        tune_type = setting.get('type', '').strip()
        if tune_type:
            all_types[tune_type.lower()] = tune_type

type_options_html = ''
for lower, orig in sorted(all_types.items()):
    type_options_html += f'<label class="tag-option"><input type="checkbox" value="{html.escape(lower)}" onchange="applyFilters()"> {html.escape(orig)}</label>\n'

import re

def first_two_bars(abc):
    """Extract the first 2 complete bars from an ABC string, ignoring anacrusis."""
    abc = abc.replace('!', ' ')
    if 'V:' in abc:
        match = re.search(r'V:\s*\S+\s*(.*?)(?=V:\s*\S|\Z)', abc, re.DOTALL)
        abc = match.group(1).strip() if match else abc
    abc = abc.strip()
    segments = re.split(r'\|', abc)
    cleaned = [re.sub(r'^[:\s]+|[:\s]+$', '', s) for s in segments]
    has_notes = lambda s: bool(re.search(r'[A-Ga-gz]', s))
    if has_notes(cleaned[0]) if cleaned else False:
        bars = [s for s in cleaned[1:] if has_notes(s)]
    else:
        bars = [s for s in cleaned if has_notes(s)]
    return ' | '.join(bars[:2])

import copy
data_processed = copy.deepcopy(data)
for item in data_processed:
    for setting in item.get('settings', []):
        setting['abc_two_bars'] = setting.get('abc', '')

data_json = json.dumps(data_processed, ensure_ascii=False)

HTML = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Session Sets</title>
<script src="https://cdn.jsdelivr.net/npm/abcjs@6.4.3/dist/abcjs-basic-min.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;500&display=swap');

  :root {{
    --ink:       #1a1208;
    --parchment: #f5f0e8;
    --warm-mid:  #e8dfc8;
    --rule:      #c4a96a;
    --gold:      #9a7b2f;
    --fade:      #7a6a50;
    --accent:    #5c3d1e;
    --staff-bg:  #faf7f1;
    --sidebar-w: 320px;
  }}

  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    background: var(--parchment);
    color: var(--ink);
    font-family: 'EB Garamond', Georgia, serif;
    font-size: 17px;
    line-height: 1.55;
    display: flex;
    height: 100vh;
    overflow: hidden;
  }}

  /* ── Sidebar ── */
  #sidebar {{
    width: var(--sidebar-w);
    min-width: var(--sidebar-w);
    height: 100vh;
    overflow-y: auto;
    background: var(--warm-mid);
    border-right: 2px double var(--rule);
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    transition: width 0.28s ease, min-width 0.28s ease, opacity 0.22s ease;
  }}

  #sidebar.collapsed {{
    width: 0;
    min-width: 0;
    opacity: 0;
    overflow: hidden;
    border-right: none;
  }}

  /* ── Toggle button ── */
  #sidebar-toggle {{
    position: fixed;
    top: 12px;
    left: 12px;
    z-index: 200;
    width: 34px;
    height: 34px;
    border-radius: 4px;
    border: 1px solid var(--rule);
    background: var(--parchment);
    color: var(--accent);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    line-height: 1;
    box-shadow: 1px 1px 4px rgba(0,0,0,0.12);
    transition: background 0.15s, left 0.28s ease;
  }}

  #sidebar-toggle:hover {{ background: var(--warm-mid); }}

  #sidebar-toggle.open {{
    left: calc(var(--sidebar-w) + 8px);
  }}

  /* ── Sidebar header ── */
  .sidebar-header {{
    border-bottom: 3px double var(--rule);
    padding: 1.2rem 1rem 1rem 3rem;
    flex-shrink: 0;
  }}

  .sidebar-header h1 {{
    font-size: 1.45rem;
    font-weight: 600;
    letter-spacing: -.02em;
    color: var(--accent);
    font-style: italic;
  }}

  .sidebar-header h1 a {{ color: inherit; text-decoration: none; }}
  .sidebar-header h1 a:hover {{ text-decoration: underline; text-decoration-color: var(--gold); }}

  .sidebar-header h1 span {{
    display: block;
    font-style: normal;
    color: var(--gold);
    font-size: 0.72rem;
    font-weight: 400;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: .05em;
    margin-top: .15rem;
  }}

  .sidebar-header .dl-btn {{
    margin-top: 0.6rem;
    background: none;
    border: 1px solid var(--rule);
    border-radius: 3px;
    padding: .2rem .5rem;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
  }}

  .sidebar-header .dl-btn:hover {{ background: var(--parchment); }}
  .sidebar-header .dl-btn img {{ width: 18px; height: 18px; }}

  /* ── Controls ── */
  .controls {{
    padding: 0.9rem 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
  }}

  .control-group {{
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }}

  .control-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: .1em;
    color: var(--fade);
  }}

  /* Sort buttons */
  .sort-group {{
    display: flex;
    gap: .3rem;
    flex-wrap: wrap;
  }}

  .sort-btn {{
    background: none;
    border: 1px solid var(--rule);
    border-radius: 3px;
    padding: .28rem .65rem;
    font-family: 'EB Garamond', serif;
    font-size: .92rem;
    color: var(--ink);
    cursor: pointer;
    transition: background .15s, color .15s;
  }}

  .sort-btn.active {{
    background: var(--accent);
    color: var(--parchment);
    border-color: var(--accent);
  }}

  .sort-btn:hover:not(.active) {{ background: var(--rule); }}

  /* Tag / Key dropdown */
  .tag-dropdown-wrap {{ position: relative; }}

  .tag-toggle {{
    background: none;
    border: 1px solid var(--rule);
    border-radius: 3px;
    padding: .28rem .9rem .28rem .7rem;
    font-family: 'EB Garamond', serif;
    font-size: .92rem;
    color: var(--ink);
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: .4rem;
    width: 100%;
    transition: background .15s;
  }}

  .tag-toggle:hover {{ background: var(--parchment); }}
  .tag-toggle.has-active {{ background: var(--accent); color: var(--parchment); border-color: var(--accent); }}
  .tag-toggle::after {{ content: '▾'; font-size: .75rem; margin-left: auto; }}

  .tag-panel {{
    display: none;
    background: var(--parchment);
    border: 1px solid var(--rule);
    border-radius: 4px;
    padding: .6rem .8rem;
    max-height: 220px;
    overflow-y: auto;
    margin-top: 3px;
  }}

  .tag-panel.open {{ display: block; }}

  .tag-option {{
    display: flex;
    align-items: center;
    gap: .45rem;
    padding: .18rem 0;
    font-size: .92rem;
    cursor: pointer;
    white-space: nowrap;
  }}

  .tag-option input {{ accent-color: var(--accent); cursor: pointer; }}

  .clear-tags {{
    display: block;
    margin-bottom: .5rem;
    padding-bottom: .5rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: .68rem;
    color: var(--gold);
    cursor: pointer;
    text-transform: uppercase;
    letter-spacing: .08em;
    background: none;
    border: none;
    border-bottom: 1px solid var(--rule);
    width: 100%;
    text-align: left;
  }}

  .clear-tags:hover {{ color: var(--accent); }}

  .andor-row {{
    display: flex;
    align-items: center;
    gap: .25rem;
    margin-bottom: .5rem;
    padding-bottom: .5rem;
    border-bottom: 1px solid var(--rule);
  }}

  .andor-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: .65rem;
    text-transform: uppercase;
    letter-spacing: .08em;
    color: var(--fade);
    margin-right: .2rem;
  }}

  .andor-btn {{
    background: none;
    border: 1px solid var(--rule);
    border-radius: 3px;
    padding: .1rem .45rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: .65rem;
    text-transform: uppercase;
    letter-spacing: .06em;
    color: var(--ink);
    cursor: pointer;
    transition: background .12s, color .12s;
  }}

  .andor-btn.active {{ background: var(--gold); color: var(--parchment); border-color: var(--gold); }}
  .andor-btn:hover:not(.active) {{ background: var(--warm-mid); }}

  /* Name search */
  .search-wrap {{
    position: relative;
    display: flex;
    align-items: center;
  }}

  .search-wrap input {{
    background: var(--parchment);
    border: 1px solid var(--rule);
    border-radius: 3px;
    padding: .28rem 1.8rem .28rem .65rem;
    font-family: 'EB Garamond', serif;
    font-size: .92rem;
    color: var(--ink);
    width: 100%;
    outline: none;
    transition: border-color .15s;
  }}

  .search-wrap input:focus {{ border-color: var(--accent); }}
  .search-wrap input::placeholder {{ color: var(--fade); font-style: italic; }}

  .search-clear {{
    position: absolute;
    right: .45rem;
    background: none;
    border: none;
    color: var(--fade);
    font-size: .85rem;
    cursor: pointer;
    padding: 0;
    line-height: 1;
    display: none;
  }}

  .search-clear:hover {{ color: var(--accent); }}

  mark {{
    background: #f0d97a;
    color: var(--ink);
    border-radius: 2px;
    padding: 0 1px;
  }}

  /* Result count pinned to sidebar bottom */
  #result-count {{
    font-family: 'JetBrains Mono', monospace;
    font-size: .68rem;
    color: var(--fade);
    padding: 0.5rem 1rem 0.8rem;
    border-top: 1px solid var(--rule);
    margin-top: auto;
  }}

  /* ── Main content ── */
  #main {{
    flex: 1;
    overflow-y: auto;
  }}

  /* Sets list */
  #sets-list {{
    border: 2px solid #5c3d1e;
    border-radius: 0.5em;
    column-width: 18em;
    column-rule: 1px solid #5c3d1e;
    padding: 0 1rem;
  }}

  .set-card {{
    border-bottom: 1px solid var(--warm-mid);
    padding: 1.4rem 0 1.2rem;
    break-inside: avoid;
  }}

  .set-card:last-child {{ border-bottom: none; }}

  .set-name {{
    font-size: 1.2rem;
    font-weight: 600;
    color: var(--accent);
    text-decoration: none;
    letter-spacing: -.01em;
    display: inline-block;
    margin-bottom: .7rem;
  }}

  .set-name:hover {{ text-decoration: underline; text-decoration-color: var(--gold); }}

  .set-tags {{
    display: flex;
    gap: .35rem;
    flex-wrap: wrap;
    margin-bottom: .75rem;
  }}

  .tag-pill {{
    font-family: 'JetBrains Mono', monospace;
    font-size: .65rem;
    text-transform: uppercase;
    letter-spacing: .07em;
    background: var(--warm-mid);
    border: 1px solid var(--rule);
    border-radius: 2px;
    padding: .12rem .45rem;
    color: var(--fade);
  }}

  .tune-notation.key-hidden {{
    opacity: 0.22;
    filter: grayscale(0.6);
    pointer-events: none;
  }}

  .tunes-list {{ display: flex; flex-direction: column; gap: 0; }}

  .tune-notation {{
    background: var(--staff-bg);
    border-left: 1px solid var(--rule);
    padding: 0 .8rem;
    border-radius: 0 3px 3px 0;
    overflow-x: auto;
    transition: opacity .2s, filter .2s;
  }}

  .tune-notation svg {{ max-width: 100%; height: auto; display: block; margin: 0; }}

  .no-results {{
    text-align: center;
    padding: 4rem 2rem;
    color: var(--fade);
    font-style: italic;
    font-size: 1.1rem;
  }}

  @media (max-width: 600px) {{
    #sidebar {{ --sidebar-w: 85vw; }}
    #main {{ padding-left: 3rem; padding-right: 1rem; }}
  }}
</style>
</head>
<body>

<!-- Toggle button — always visible -->
<button id="sidebar-toggle" onclick="toggleSidebar()" aria-label="Toggle sidebar" aria-expanded="true">✕</button>

<!-- Sidebar: title + controls -->
<aside id="sidebar">

  <div class="sidebar-header">
     <h1>   
      <button type="button" class="dl-btn" title="Download HTML sets file"
        onclick="download('https://barpers.github.io/thesession.org_member_sets_incipits/data/{member_name}_session_sets.html', '{member_name}_session_sets.html')">
        <img src="../images/download-icon-image.jpg" alt="Download">
      </button> 
      <a href="https://thesession.org/members/179479/sets" target="_blank">{member_name} Sets</a>
      <span>thesession.org</span>
    </h1>
 
  </div>

  <div class="controls">

    <div class="control-group">
      <span class="control-label">Sort</span>
      <div class="sort-group">
        <button class="sort-btn active" id="btn-name-asc" onclick="setSort('name','asc')">Name ↑</button>
        <button class="sort-btn" id="btn-name-desc" onclick="setSort('name','desc')">Name ↓</button>
        <button class="sort-btn" id="btn-date-asc" onclick="setSort('date','asc')">Date ↑</button>
        <button class="sort-btn" id="btn-date-desc" onclick="setSort('date','desc')">Date ↓</button>
      </div>
    </div>

    <div class="control-group">
      <span class="control-label">Tags</span>
      <div class="tag-dropdown-wrap" id="tag-wrap">
        <button class="tag-toggle" id="tag-toggle-btn" onclick="togglePanel('tag-panel', ['key-panel','type-panel'])">Tags</button>
        <div class="tag-panel" id="tag-panel">
          <div class="andor-row">
            <span class="andor-label">Match</span>
            <button class="andor-btn active" id="tag-and-btn" onclick="setAndOr('tags','and')">AND</button>
            <button class="andor-btn" id="tag-or-btn" onclick="setAndOr('tags','or')">OR</button>
          </div>
          <button class="clear-tags" onclick="clearTags()">Clear all</button>
          {tag_options_html}
        </div>
      </div>
    </div>

    <div class="control-group">
      <span class="control-label">Keys</span>
      <div class="tag-dropdown-wrap" id="key-wrap">
        <button class="tag-toggle" id="key-toggle-btn" onclick="togglePanel('key-panel', ['tag-panel','type-panel'])">Keys</button>
        <div class="tag-panel" id="key-panel">
          <div class="andor-row">
            <span class="andor-label">Match</span>
            <button class="andor-btn active" id="key-and-btn" onclick="setAndOr('keys','and')">AND</button>
            <button class="andor-btn" id="key-or-btn" onclick="setAndOr('keys','or')">OR</button>
          </div>
          <button class="clear-tags" onclick="clearKeys()">Clear all</button>
          {key_options_html}
        </div>
      </div>
    </div>

    <div class="control-group">
      <span class="control-label">Type</span>
      <div class="tag-dropdown-wrap" id="type-wrap">
        <button class="tag-toggle" id="type-toggle-btn" onclick="togglePanel('type-panel', ['tag-panel','key-panel'])">Type</button>
        <div class="tag-panel" id="type-panel">
          <div class="andor-row">
            <span class="andor-label">Match</span>
            <button class="andor-btn active" id="type-and-btn" onclick="setAndOr('types','and')">AND</button>
            <button class="andor-btn" id="type-or-btn" onclick="setAndOr('types','or')">OR</button>
          </div>
          <button class="clear-tags" onclick="clearTypes()">Clear all</button>
          {type_options_html}
        </div>
      </div>
    </div>

    <div class="control-group">
      <span class="control-label">Search</span>
      <div class="search-wrap">
        <input type="search" id="name-search" placeholder="tune name…" oninput="onSearch(this)" autocomplete="off">
        <button class="search-clear" id="search-clear-btn" onclick="clearSearch()" title="Clear">✕</button>
      </div>
    </div>

  </div><!-- /controls -->

  <div id="result-count"></div>

</aside>

<!-- Main scrollable area -->
<main id="main">
  <div id="sets-list"></div>
</main>

<script>
const RAW = {data_json};

let sortField = 'name';
let sortDir   = 'asc';
let activeTags  = new Set();
let activeKeys  = new Set();
let activeTypes = new Set();
let tagsMode  = 'and';
let keysMode  = 'and';
let typesMode = 'and';
let searchQuery = '';
let sidebarOpen = true;

function toggleSidebar() {{
  sidebarOpen = !sidebarOpen;
  const sidebar = document.getElementById('sidebar');
  const btn = document.getElementById('sidebar-toggle');
  sidebar.classList.toggle('collapsed', !sidebarOpen);
  btn.classList.toggle('open', sidebarOpen);
  btn.setAttribute('aria-expanded', sidebarOpen);
  btn.textContent = sidebarOpen ? '✕' : '☰';
}}

// Close all panels when clicking outside
document.addEventListener('click', e => {{
  ['tag-wrap', 'key-wrap', 'type-wrap'].forEach(id => {{
    const wrap = document.getElementById(id);
    if (wrap && !wrap.contains(e.target)) {{
      wrap.querySelector('.tag-panel').classList.remove('open');
    }}
  }});
}});

function togglePanel(openId, closeIds) {{
  (Array.isArray(closeIds) ? closeIds : [closeIds]).forEach(id => {{
    document.getElementById(id).classList.remove('open');
  }});
  document.getElementById(openId).classList.toggle('open');
}}

function setAndOr(filter, mode) {{
  if (filter === 'tags')  {{ tagsMode  = mode; }}
  if (filter === 'keys')  {{ keysMode  = mode; }}
  if (filter === 'types') {{ typesMode = mode; }}
  ['and','or'].forEach(m => {{
    const btn = document.getElementById(`${{filter.slice(0,-1)}}-${{m}}-btn`);
    if (btn) btn.classList.toggle('active', m === mode);
  }});
  render();
}}

function setSort(field, dir) {{
  sortField = field;
  sortDir   = dir;
  ['name-asc','name-desc','date-asc','date-desc'].forEach(id => {{
    document.getElementById('btn-' + id).classList.remove('active');
  }});
  document.getElementById(`btn-${{field}}-${{dir}}`).classList.add('active');
  render();
}}

function applyFilters() {{
  activeTags = new Set();
  document.querySelectorAll('#tag-panel .tag-option input:checked').forEach(cb => {{
    activeTags.add(cb.value);
  }});
  const tagBtn = document.getElementById('tag-toggle-btn');
  tagBtn.classList.toggle('has-active', activeTags.size > 0);
  tagBtn.textContent = activeTags.size > 0 ? `Tags (${{activeTags.size}})` : 'Tags';

  activeKeys = new Set();
  document.querySelectorAll('#key-panel .tag-option input:checked').forEach(cb => {{
    activeKeys.add(cb.value);
  }});
  const keyBtn = document.getElementById('key-toggle-btn');
  keyBtn.classList.toggle('has-active', activeKeys.size > 0);
  keyBtn.textContent = activeKeys.size > 0 ? `Keys (${{activeKeys.size}})` : 'Keys';

  activeTypes = new Set();
  document.querySelectorAll('#type-panel .tag-option input:checked').forEach(cb => {{
    activeTypes.add(cb.value);
  }});
  const typeBtn = document.getElementById('type-toggle-btn');
  typeBtn.classList.toggle('has-active', activeTypes.size > 0);
  typeBtn.textContent = activeTypes.size > 0 ? `Type (${{activeTypes.size}})` : 'Type';

  render();
}}

function clearTags()  {{ document.querySelectorAll('#tag-panel .tag-option input').forEach(cb => cb.checked = false); applyFilters(); }}
function clearKeys()  {{ document.querySelectorAll('#key-panel .tag-option input').forEach(cb => cb.checked = false); applyFilters(); }}
function clearTypes() {{ document.querySelectorAll('#type-panel .tag-option input').forEach(cb => cb.checked = false); applyFilters(); }}

function onSearch(input) {{
  searchQuery = input.value.trim().toLowerCase();
  document.getElementById('search-clear-btn').style.display = searchQuery ? 'block' : 'none';
  render();
}}

function clearSearch() {{
  document.getElementById('name-search').value = '';
  searchQuery = '';
  document.getElementById('search-clear-btn').style.display = 'none';
  render();
}}

function highlight(text, query) {{
  if (!query) return document.createTextNode(text);
  const idx = text.toLowerCase().indexOf(query);
  if (idx === -1) return document.createTextNode(text);
  const frag = document.createDocumentFragment();
  frag.appendChild(document.createTextNode(text.slice(0, idx)));
  const mark = document.createElement('mark');
  mark.textContent = text.slice(idx, idx + query.length);
  frag.appendChild(mark);
  frag.appendChild(document.createTextNode(text.slice(idx + query.length)));
  return frag;
}}

// Source - https://stackoverflow.com/a/76101203
// Posted by enisn
// Retrieved 2026-06-22, License - CC BY-SA 4.0
async function download(dataurl, fileName) {{
  const response = await fetch(dataurl);
  const blob = await response.blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = fileName;
  link.click();
}}

function render() {{
  let items = RAW.slice();

  if (activeTags.size > 0) {{
    items = items.filter(item => {{
      const itemTags = (item.tags || []).map(t => t.toLowerCase());
      return tagsMode === 'and'
        ? [...activeTags].every(t => itemTags.includes(t))
        : [...activeTags].some(t => itemTags.includes(t));
    }});
  }}

  if (activeKeys.size > 0) {{
    items = items.filter(item => {{
      const settingKeys = (item.settings || []).map(s => (s.key || '').toLowerCase());
      return keysMode === 'and'
        ? [...activeKeys].every(k => settingKeys.includes(k))
        : [...activeKeys].some(k => settingKeys.includes(k));
    }});
  }}

  if (activeTypes.size > 0) {{
    items = items.filter(item => {{
      const settingTypes = (item.settings || []).map(s => (s.type || '').toLowerCase());
      return typesMode === 'and'
        ? [...activeTypes].every(t => settingTypes.includes(t))
        : [...activeTypes].some(t => settingTypes.includes(t));
    }});
  }}

  if (searchQuery) {{
    items = items.filter(item => {{
      if (item.name.toLowerCase().includes(searchQuery)) return true;
      return (item.settings || []).some(s => s.name.toLowerCase().includes(searchQuery));
    }});
  }}

  items.sort((a, b) => {{
    let va = sortField === 'name' ? a.name.toLowerCase() : a.date;
    let vb = sortField === 'name' ? b.name.toLowerCase() : b.date;
    if (va < vb) return sortDir === 'asc' ? -1 : 1;
    if (va > vb) return sortDir === 'asc' ? 1 : -1;
    return 0;
  }});

  document.getElementById('result-count').textContent = `${{items.length}} of ${{RAW.length}} sets · {now}`;
  const container = document.getElementById('sets-list');
  container.innerHTML = '';

  if (items.length === 0) {{
    container.innerHTML = '<div class="no-results">No sets match the current search or filters.</div>';
    return;
  }}

  items.forEach((item, si) => {{
    const card = document.createElement('div');
    card.className = 'set-card';

    const a = document.createElement('a');
    a.className = 'set-name';
    a.href = item.url;
    a.target = '_blank';
    a.rel = 'noopener';
    a.appendChild(highlight(item.name, searchQuery));
    card.appendChild(a);

    if (item.tags && item.tags.length > 0) {{
      const tagsDiv = document.createElement('div');
      tagsDiv.className = 'set-tags';
      item.tags.forEach(t => {{
        const pill = document.createElement('span');
        pill.className = 'tag-pill';
        pill.textContent = t;
        tagsDiv.appendChild(pill);
      }});
      card.appendChild(tagsDiv);
    }}

    const tunesDiv = document.createElement('div');
    tunesDiv.className = 'tunes-list';

    (item.settings || []).forEach((setting, ti) => {{
      const notationDiv = document.createElement('div');
      notationDiv.className = 'tune-notation';

      const tuneKey  = (setting.key  || '').toLowerCase();
      const tuneType = (setting.type || '').toLowerCase();
      const keyDim  = activeKeys.size  > 0 && !activeKeys.has(tuneKey);
      const typeDim = activeTypes.size > 0 && !activeTypes.has(tuneType);
      if (keyDim || typeDim) {{
        notationDiv.classList.add('key-hidden');
      }}

      const divId = `notation-${{si}}-${{ti}}`;
      notationDiv.id = divId;
      tunesDiv.appendChild(notationDiv);

      const abcStr = [
        `X:${{ti + 1}}`,
        `T: `,
        `M:${{setting.meter}}`,
        `K:${{setting.key}}`,
        setting.abc_two_bars || ''
      ].join('\\n');

      setTimeout(() => {{
        try {{
          ABCJS.renderAbc(divId, abcStr, {{
            responsive: 'resize',
            staffwidth: 520,
            scale: 0.95,
            paddingright: 0,
            paddingleft: 0,
            wrap: {{ minSpacing: 1.8, maxSpacing: 2.8, preferredMeasuresPerLine: 4 }},
            add_classes: true,
          }});
        }} catch(e) {{ console.warn('ABC render error', e); }}
      }}, 0);
    }});

    card.appendChild(tunesDiv);
    container.appendChild(card);
  }});
}}

// Sidebar toggle button starts in open state
document.getElementById('sidebar-toggle').classList.add('open');
render();
</script>
</body>
</html>'''

output_path = f'./data/{member_name}_session_sets.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(HTML)

print(f"Written to {output_path}")
