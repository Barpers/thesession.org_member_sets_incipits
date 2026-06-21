import json, html, datetime


now =( datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
  


# Read the JSON
with open('./data/sets_full.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Collect all unique tags (case-insensitive, preserve original for display)
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

#not the same as extract_incipit in append_abc_incipits_to_sets_full.py because here we want to handle anacrusis and V: voices more robustly for arbitrary ABC input, whereas the other function is just for cleaning up the specific ABC from the API which is mostly well-formed.
def first_two_bars(abc):
    """Extract the first 2 complete bars from an ABC string, ignoring anacrusis."""
    # Normalise thesession's ! line-break marker to a space
    abc = abc.replace('!', ' ')

    # If the ABC uses V: voice headers, extract only the first voice's content
    if 'V:' in abc:
        match = re.search(r'V:\s*\S+\s*(.*?)(?=V:\s*\S|\Z)', abc, re.DOTALL)
        abc = match.group(1).strip() if match else abc

    abc = abc.strip()

    # Split into segments on every | (including ||, |:, :|)
    segments = re.split(r'\|', abc)

    # Clean each segment: strip whitespace and bar-repeat chars (: only)
    cleaned = [re.sub(r'^[:\s]+|[:\s]+$', '', s) for s in segments]

    # The first segment is anacrusis if it contains notes but is shorter than a full bar
    # We define "has notes" as containing at least one letter (a note name)
    has_notes = lambda s: bool(re.search(r'[A-Ga-gz]', s))

    bars = [s for s in cleaned if has_notes(s)]

    # If the first segment was anacrusis (before the first |), it's already been
    # separated. We just want the first 2 note-bearing segments after any leading
    # anacrusis — but since re.split on | naturally separates them, we take
    # the first 2 that have notes, skipping the pre-bar anacrusis only if it
    # appears before the first real barline. 
    # 
    # Heuristic: if the original abc starts with notes before any |, that's anacrusis.
    # segments[0] is always pre-first-barline content. If it has notes, it's anacrusis — skip it.
    if has_notes(cleaned[0]) if cleaned else False:
        bars = [s for s in cleaned[1:] if has_notes(s)]
    else:
        bars = [s for s in cleaned if has_notes(s)]

    return ' | '.join(bars[:2])

# Pre-process: attach computed incipit (2 bars from full abc) to each setting
import copy
data_processed = copy.deepcopy(data)
for item in data_processed:
    for setting in item.get('settings', []):
        setting['abc_two_bars'] = setting.get('abc', '')
       # setting['abc_two_bars'] = first_two_bars(setting.get('abc', ''))

# Serialize data for JS
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
    --ink:     #1a1208;
    --parchment: #f5f0e8;
    --warm-mid: #e8dfc8;
    --rule:    #c4a96a;
    --gold:    #9a7b2f;
    --fade:    #7a6a50;
    --accent:  #5c3d1e;
    --staff-bg: #faf7f1;
  }}

  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    background: var(--parchment);
    color: var(--ink);
    font-family: 'EB Garamond', Georgia, serif;
    font-size: 17px;
    line-height: 1.55;
  }}

  header {{
    border-bottom: 3px double var(--rule);
    padding: 2rem 2.5rem 1.4rem;
    display: flex;
    align-items: baseline;
    gap: 1.5rem;
    flex-wrap: wrap;
  }}

  header h1 {{
    font-size: 2.2rem;
    font-weight: 600;
    letter-spacing: -.02em;
    color: var(--accent);
    flex: 1 1 auto;
    font-style: italic;
  }}

  header h1 span {{
    font-style: normal;
    color: var(--gold);
    font-size: 1rem;
    font-weight: 400;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: .05em;
  }}

  /* Controls bar */
  .controls {{
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.9rem 2.5rem;
    background: var(--warm-mid);
    border-bottom: 1px solid var(--rule);
    flex-wrap: wrap;
  }}

  .control-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: .1em;
    color: var(--fade);
  }}

  /* Sort buttons */
  .sort-group {{
    display: flex;
    gap: .3rem;
    align-items: center;
  }}

  .sort-btn {{
    background: none;
    border: 1px solid var(--rule);
    border-radius: 3px;
    padding: .28rem .7rem;
    font-family: 'EB Garamond', serif;
    font-size: .95rem;
    color: var(--ink);
    cursor: pointer;
    transition: background .15s, color .15s;
  }}

  .sort-btn.active {{
    background: var(--accent);
    color: var(--parchment);
    border-color: var(--accent);
  }}

  .sort-btn:hover:not(.active) {{
    background: var(--rule);
    color: var(--ink);
  }}

  /* Tag / Key dropdown — shared styles */
  .tag-dropdown-wrap {{
    position: relative;
  }}

  .tag-toggle {{
    background: none;
    border: 1px solid var(--rule);
    border-radius: 3px;
    padding: .28rem .9rem .28rem .7rem;
    font-family: 'EB Garamond', serif;
    font-size: .95rem;
    color: var(--ink);
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: .4rem;
    transition: background .15s;
  }}

  .tag-toggle:hover {{ background: var(--warm-mid); }}
  .tag-toggle.has-active {{ background: var(--accent); color: var(--parchment); border-color: var(--accent); }}

  .tag-toggle::after {{
    content: '▾';
    font-size: .75rem;
  }}

  .tag-panel {{
    display: none;
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    background: var(--parchment);
    border: 1px solid var(--rule);
    border-radius: 4px;
    padding: .6rem .8rem;
    min-width: 180px;
    max-height: 320px;
    overflow-y: auto;
    box-shadow: 0 4px 16px rgba(0,0,0,.12);
    z-index: 100;
  }}

  .tag-panel.open {{ display: block; }}

  .tag-option {{
    display: flex;
    align-items: center;
    gap: .45rem;
    padding: .18rem 0;
    font-size: .95rem;
    cursor: pointer;
    white-space: nowrap;
  }}

  .tag-option input {{ accent-color: var(--accent); cursor: pointer; }}

  .clear-tags {{
    display: block;
    margin-bottom: .5rem;
    padding-bottom: .5rem;
    border-bottom: 1px solid var(--rule);
    font-family: 'JetBrains Mono', monospace;
    font-size: .7rem;
    color: var(--gold);
    cursor: pointer;
    text-transform: uppercase;
    letter-spacing: .08em;
    background: none;
    border: none;
    border-bottom: 1px solid var(--rule);
    padding-left: 0;
    width: 100%;
    text-align: left;
  }}

  .clear-tags:hover {{ color: var(--accent); }}

  /* AND / OR toggle row inside each panel */
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

  .andor-btn.active {{
    background: var(--gold);
    color: var(--parchment);
    border-color: var(--gold);
  }}

  .andor-btn:hover:not(.active) {{
    background: var(--warm-mid);
  }}

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
    font-size: .95rem;
    color: var(--ink);
    width: 180px;
    outline: none;
    transition: border-color .15s, width .25s;
  }}

  .search-wrap input:focus {{
    border-color: var(--accent);
    width: 240px;
  }}

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

  /* Result count */
  #result-count {{
    font-family: 'JetBrains Mono', monospace;
    font-size: .75rem;
    color: var(--fade);
    margin-left: auto;
  }}

  /* Sets list */
  #sets-list {{
    padding: 1.5rem 2.5rem 3rem;
    display: flex;
    flex-direction: column;
    gap: 0;
  }}

  .set-card {{
    border-bottom: 1px solid var(--warm-mid);
    padding: 1.4rem 0 1.2rem;
  }}

  .set-card:last-child {{ border-bottom: none; }}

  .set-name {{
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--accent);
    text-decoration: none;
    letter-spacing: -.01em;
    display: inline-block;
    margin-bottom: .7rem;
  }}

  .set-name:hover {{
    text-decoration: underline;
    text-decoration-color: var(--gold);
  }}

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

  /* Key pill — slightly distinct colour so it reads differently from tags */
  .key-pill {{
    font-family: 'JetBrains Mono', monospace;
    font-size: .65rem;
    letter-spacing: .07em;
    background: #ede3cc;
    border: 1px solid var(--gold);
    border-radius: 2px;
    padding: .12rem .45rem;
    color: var(--accent);
  }}

  /* Dim tunes that are filtered out by key */
  .tune-notation.key-hidden {{
    opacity: 0.22;
    filter: grayscale(0.6);
    pointer-events: none;
  }}

  .tunes-list {{
    display: flex;
    flex-direction: column;
    gap: 0;
  }}

  .tune-notation {{
    background: var(--staff-bg);
    border-left: 3px solid var(--rule);
    padding: 0 .8rem;
    border-radius: 0 3px 3px 0;
    overflow-x: auto;
    transition: opacity .2s, filter .2s;
  }}

  /* abcjs SVG overrides */
  .tune-notation svg {{
    max-width: 100%;
    height: auto;
    display: block;
    margin: 0;
  }}

  .no-results {{
    text-align: center;
    padding: 4rem 2rem;
    color: var(--fade);
    font-style: italic;
    font-size: 1.1rem;
  }}

  @media (max-width: 600px) {{
    header, .controls, #sets-list {{ padding-left: 1rem; padding-right: 1rem; }}
    header h1 {{ font-size: 1.5rem; }}
  }}
</style>
</head>
<body>
<a onclick="this.href='data:text/html;charset=UTF-8,' + encodeURIComponent(document.documentElement.outerHTML)" 
   href="#" 
   download="barpers_sets_incipits.html">
   Download
</a>
<header>
  <h1><a href="https://thesession.org/members/179479/sets" target="_blank">Barpers Sets</a> <span>thesession.org</span></h1>
</header>

<div class="controls">
  <span class="control-label">Sort</span>
  <div class="sort-group">
    <button class="sort-btn active" id="btn-name-asc" onclick="setSort('name','asc')">Name ↑</button>
    <button class="sort-btn" id="btn-name-desc" onclick="setSort('name','desc')">Name ↓</button>
    <button class="sort-btn" id="btn-date-asc" onclick="setSort('date','asc')">Date ↑</button>
    <button class="sort-btn" id="btn-date-desc" onclick="setSort('date','desc')">Date ↓</button>
  </div>

  <span class="control-label" style="margin-left:.5rem">Filter</span>

  <!-- Tags dropdown (unchanged) -->
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

  <!-- Keys dropdown -->
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

  <!-- Type dropdown (new) -->
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

  <span class="control-label" style="margin-left:.5rem">Search</span>
  <div class="search-wrap">
    <input type="search" id="name-search" placeholder="tune name…" oninput="onSearch(this)" autocomplete="off">
    <button class="search-clear" id="search-clear-btn" onclick="clearSearch()" title="Clear">✕</button>
  </div>

  <span id="result-count"></span>
</div>
</body>
<body  style="border:2px solid  #5c3d1e; border-radius: 0.5em; padding: -5px;
    column-width: 28em; 
    column-rule: 1px solid  #5c3d1e;
    padding-left: 0px;">
<div id="sets-list"></div>

<script>
const RAW = {data_json};

let sortField = 'name';
let sortDir   = 'asc';
let activeTags = new Set();
let activeKeys = new Set();
let activeTypes = new Set();
let tagsMode  = 'and'; // 'and' | 'or'
let keysMode  = 'and';
let typesMode = 'and';
let searchQuery = '';

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
  // Update button highlight
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
  // Tags
  activeTags = new Set();
  document.querySelectorAll('#tag-panel .tag-option input:checked').forEach(cb => {{
    activeTags.add(cb.value);
  }});
  const tagBtn = document.getElementById('tag-toggle-btn');
  tagBtn.classList.toggle('has-active', activeTags.size > 0);
  tagBtn.textContent = activeTags.size > 0 ? `Tags (${{activeTags.size}})` : 'Tags';

  // Keys
  activeKeys = new Set();
  document.querySelectorAll('#key-panel .tag-option input:checked').forEach(cb => {{
    activeKeys.add(cb.value);
  }});
  const keyBtn = document.getElementById('key-toggle-btn');
  keyBtn.classList.toggle('has-active', activeKeys.size > 0);
  keyBtn.textContent = activeKeys.size > 0 ? `Keys (${{activeKeys.size}})` : 'Keys';

  // Types
  activeTypes = new Set();
  document.querySelectorAll('#type-panel .tag-option input:checked').forEach(cb => {{
    activeTypes.add(cb.value);
  }});
  const typeBtn = document.getElementById('type-toggle-btn');
  typeBtn.classList.toggle('has-active', activeTypes.size > 0);
  typeBtn.textContent = activeTypes.size > 0 ? `Type (${{activeTypes.size}})` : 'Type';

  render();
}}

function clearTags() {{
  document.querySelectorAll('#tag-panel .tag-option input').forEach(cb => cb.checked = false);
  applyFilters();
}}

function clearKeys() {{
  document.querySelectorAll('#key-panel .tag-option input').forEach(cb => cb.checked = false);
  applyFilters();
}}

function clearTypes() {{
  document.querySelectorAll('#type-panel .tag-option input').forEach(cb => cb.checked = false);
  applyFilters();
}}

function onSearch(input) {{
  searchQuery = input.value.trim().toLowerCase();
  document.getElementById('search-clear-btn').style.display = searchQuery ? 'block' : 'none';
  render();
}}

function clearSearch() {{
  const input = document.getElementById('name-search');
  input.value = '';
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

function render() {{
  let items = RAW.slice();

  // Filter by tags
  // AND: set must carry every active tag
  // OR:  set must carry at least one active tag
  if (activeTags.size > 0) {{
    items = items.filter(item => {{
      const itemTags = (item.tags || []).map(t => t.toLowerCase());
      return tagsMode === 'and'
        ? [...activeTags].every(t => itemTags.includes(t))
        : [...activeTags].some(t => itemTags.includes(t));
    }});
  }}

  // Filter by keys
  // AND: set must contain tunes covering every active key
  // OR:  set must contain at least one tune matching any active key
  if (activeKeys.size > 0) {{
    items = items.filter(item => {{
      const settingKeys = (item.settings || []).map(s => (s.key || '').toLowerCase());
      return keysMode === 'and'
        ? [...activeKeys].every(k => settingKeys.includes(k))
        : [...activeKeys].some(k => settingKeys.includes(k));
    }});
  }}

  // Filter by type
  // AND: set must contain tunes covering every active type
  // OR:  set must contain at least one tune matching any active type
  if (activeTypes.size > 0) {{
    items = items.filter(item => {{
      const settingTypes = (item.settings || []).map(s => (s.type || '').toLowerCase());
      return typesMode === 'and'
        ? [...activeTypes].every(t => settingTypes.includes(t))
        : [...activeTypes].some(t => settingTypes.includes(t));
    }});
  }}

  // Filter by search query (matches set name OR any tune name)
  if (searchQuery) {{
    items = items.filter(item => {{
      if (item.name.toLowerCase().includes(searchQuery)) return true;
      return (item.settings || []).some(s => s.name.toLowerCase().includes(searchQuery));
    }});
  }}

  // Sort
  items.sort((a, b) => {{
    let va = sortField === 'name' ? a.name.toLowerCase() : a.date;
    let vb = sortField === 'name' ? b.name.toLowerCase() : b.date;
    if (va < vb) return sortDir === 'asc' ? -1 : 1;
    if (va > vb) return sortDir === 'asc' ? 1 : -1;
    return 0;
  }});

  document.getElementById('result-count').textContent = `${{items.length}} of ${{RAW.length}} sets.  {now}`;
  const container = document.getElementById('sets-list');
  container.innerHTML = '';

  if (items.length === 0) {{
    container.innerHTML = '<div class="no-results">No sets match the current search or filters.</div>';
    return;
  }}

  items.forEach((item, si) => {{
    const card = document.createElement('div');
    card.className = 'set-card';

    // Name link
    const a = document.createElement('a');
    a.className = 'set-name';
    a.href = item.url;
    a.target = '_blank';
    a.rel = 'noopener';
    a.appendChild(highlight(item.name, searchQuery));
    card.appendChild(a);

    // Tags row
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

    // Tunes
    const tunesDiv = document.createElement('div');
    tunesDiv.className = 'tunes-list';

    (item.settings || []).forEach((setting, ti) => {{
      const notationDiv = document.createElement('div');
      notationDiv.className = 'tune-notation';

      // Dim tunes that don't contribute to the active key/type filters.
      // In OR mode a tune is relevant if it matches any selected value.
      // In AND mode a tune is relevant if it matches all selected values
      // (a single tune can only be in one key/type, so AND across >1 value
      // always dims it — which is correct: no single tune satisfies both).
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

render();
</script>
</body>
</html>'''

output_path = './data/barpers_session_sets.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(HTML)

print(f"Written to {output_path}")