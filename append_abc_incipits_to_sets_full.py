#!/usr/bin/env python3
"""
append_abc_incipits_to_sets_full.py
==================
Structure of sets_full.json:
  [                          <- top-level array of set objects
    {
      "settings": [          <- array of setting objects
        {
          "id":  456,
          "url": "https://thesession.org/tunes/123#setting456",
          ...
        }
      ]
    }
  ]

For each setting object:
  - Match setting["url"] against tune_id_url_abc.json entries by "url" key.
  - Hit  → copy cached "abc" value onto setting["abc"].
  - Miss → call thesession.org API:
      1. Split setting["url"] into base URL and #fragment.
      2. GET base?format=json
      3. In returned JSON "settings" array, match entry whose "id" equals
         the numeric part of the fragment (strip leading "setting" text).
      4. From that matched entry take "id", "url" (= original full URL),
         and "abc" (trimmed to a 2-bar incipit, anacrusis ignored).
      5. Append { id, url, abc } to tune_id_url_abc.json.
      6. Append incipit abc to setting["abc"] in sets_full.json.
"""

import json
import re
import time
import urllib.request
import urllib.error
from fractions import Fraction
from pathlib import Path
import sys


default_member_id = 179479 #barper's member ID
arg = sys.argv[1] if len(sys.argv) > 1 else str(default_member_id)


SETS_FILE  = Path("./data/" + arg + "_sets_full.json")
#SETS_FILE  = Path("./data/sets_test.json")  # for testing
CACHE_FILE = Path("./data/tune_id_url_abc.json")
#CACHE_FILE = Path("./data/tune_id_url_abc_test.json")  # for testing
CACHE_FILE.touch(exist_ok=True)  # ensure it exists before reading
API_DELAY  = 0.3  # seconds between outbound API calls


# ── incipit ────────────────────────────────────────────────────────────────────

BARLINE_RE = re.compile(r'\|\||:\||\|:|\|\]|\[|::|[|]')

def _is_barline(t):
    return bool(BARLINE_RE.fullmatch(t))

def _note_dur(s):
    """Duration of a single ABC note string such as 'G2', 'A', 'B/', 'z4'."""
    dm = re.match(r"[a-gA-GzxZ][,']*(\d*)(/*\d*)", s)
    if not dm:
        return Fraction(1)
    num_s, den_s = dm.group(1), dm.group(2)
    num = int(num_s) if num_s else 1
    if den_s.startswith('/') and den_s[1:].isdigit():
        den = int(den_s[1:])
    elif den_s.startswith('/'):
        den = 2 ** den_s.count('/')
    else:
        den = 1
    return Fraction(num, den)

def _token_duration(token):
    """
    Sum durations of all notes/rests in a token.
    For chords [abc], returns duration of the first note (they sound together).
    """
    # Chord: [note note ...]
    if (token.startswith('[') and token.endswith(']')
            and not re.match(r'\[[\|:]', token)):
        inner = token[1:-1]
        notes = re.findall(r'[a-gA-GzxZ][^a-gA-GzxZ]*', inner)
        return _note_dur(notes[0]) if notes else Fraction(0)
    # Note group: G2AB, cBAG, z4, etc. — each letter starts a new note
    notes = re.findall(r'[a-gA-GzxZ][^a-gA-GzxZ]*', token)
    return sum(_note_dur(n) for n in notes) if notes else Fraction(0)

def _parse_bar_len(header_lines):
    """
    Return the length of one bar expressed in L: units (the default note length).
    E.g. M:4/4, L:1/8  →  bar = 4/4 ÷ 1/8 = 8 (eighth-note units per bar).
    """
    meter, unit = "4/4", Fraction(1, 8)
    for line in header_lines:
        m = re.match(r'^\s*M:\s*(\S+)', line)
        if m:
            meter = m.group(1)
        u = re.match(r'^\s*L:\s*(\d+)/(\d+)', line)
        if u:
            unit = Fraction(int(u.group(1)), int(u.group(2)))
    if meter == 'C':
        meter = '4/4'
    elif meter == 'C|':
        meter = '2/2'
    try:
        num, den = meter.split('/')
        return Fraction(int(num), int(den)) / unit
    except Exception:
        return Fraction(8)   # fallback: 4/4 in 1/8 units


def extract_incipit(abc_full, bars=2):
    """
    Return the first `bars` complete bars of the ABC body, preceded by any
    anacrusis (pickup notes) and all header lines.

    An anacrusis is detected by measuring the total note duration before the
    first barline (skipping any leading barline such as |:).  If that duration
    is strictly between zero and one full bar, it is an anacrusis and is
    included in the output without counting toward `bars`.

    Leading barlines (|:, ||, [|) that appear before any notes are never
    counted as closing a bar.
    """
    header_lines, body_lines, in_body = [], [], False
    for line in abc_full.splitlines():
        if in_body:
            body_lines.append(line)
        else:
            header_lines.append(line)
            if re.match(r'^\s*K:', line):
                in_body = True

    if not body_lines:
        return abc_full

    bar_len = _parse_bar_len(header_lines)

    # Remove inline fields [X:...] and % comments before tokenising
    body = re.sub(r'\[(?!\|)[A-Za-z]:[^\]]*\]', '', "\n".join(body_lines))
    body = re.sub(r'%[^\n]*', '', body)

    tokens = re.findall(r'\|\||:\||\|:|\|\]|\[|::|[|]|[^\s|]+', body)

    # ── detect anacrusis ───────────────────────────────────────────────────────
    # Measure note duration before the first barline, skipping any leading
    # barlines (e.g. |: at the very start of the body).
    pre_bar_dur = Fraction(0)
    seen_notes_pre = False
    for tok in tokens:
        if _is_barline(tok):
            if seen_notes_pre:
                break           # first barline after notes — stop scanning
            # else: leading barline, skip it
        else:
            seen_notes_pre = True
            pre_bar_dur += _token_duration(tok)

    has_anacrusis = Fraction(0) < pre_bar_dur < bar_len

    # ── collect tokens ─────────────────────────────────────────────────────────
    # past_anacrusis starts True when there is no anacrusis, so bar counting
    # begins immediately.  Leading barlines (before any notes) are ignored.
    past_anacrusis = not has_anacrusis
    collected, bars_done = [], 0
    seen_notes_collect = False

    for tok in tokens:
        collected.append(tok)
        if _is_barline(tok):
            if not seen_notes_collect:
                pass            # leading barline before any notes — don't count
            elif not past_anacrusis:
                past_anacrusis = True   # first barline after notes ends anacrusis
            else:
                bars_done += 1
                if bars_done >= bars:
                    break
        else:
            seen_notes_collect = True

    return " ".join(collected)


# ── URL helpers ────────────────────────────────────────────────────────────────

def split_url_fragment(full_url):
    """
    'https://thesession.org/tunes/123#setting456'
      -> base       = 'https://thesession.org/tunes/123'
         setting_id = 456  (int)

    Returns (base_url, setting_id_int) or (full_url, None) if no fragment.
    """
    if '#' not in full_url:
        return full_url, None
    base, fragment = full_url.split('#', 1)
    digits = re.sub(r'^\D+', '', fragment)  # strip 'setting' prefix
    return base, int(digits) if digits else None


# ── API fetch ──────────────────────────────────────────────────────────────────

def fetch_setting(setting_url, setting_id_from_obj):
    """
    GET base_url?format=json, find the settings entry whose id matches
    the numeric part of the URL fragment (cross-checked against setting_id_from_obj).

    Returns dict(id, url, abc) where abc is a 2-bar incipit, or None.
    """
    base_url, fragment_id = split_url_fragment(setting_url)

    # Prefer the fragment id; fall back to the id value on the setting object
    target_id = fragment_id if fragment_id is not None else setting_id_from_obj

    api_url = base_url + "?format=json"
    print(f"    GET {api_url}  (looking for id={target_id})")

    try:
        req = urllib.request.Request(
            api_url,
            headers={"Accept": "application/json",
                     "User-Agent": "EAsyABC-enricher/1.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"    HTTP error {e.code}")
        return None
    except Exception as e:
        print(f"    Request failed: {e}")
        return None

    # Find the matching entry in the API's "settings" array
    api_settings = data.get("settings", [])
    matched = next((s for s in api_settings if s.get("id") == target_id), None)

    if matched is None:
        print(f"    id {target_id} not found in API response "
              f"(available: {[s.get('id') for s in api_settings[:5]]})")
        return None

    raw_abc = (matched.get("abc") or "").strip()
    if not raw_abc:
        print(f"    matched entry has empty abc")
        return None

    # Build a minimal ABC header so extract_incipit can work
    tune_name = data.get("name", "")
    meter     = data.get("meter", "4/4")
    key       = matched.get("key", "")
    abc_full  = f"X:1\nT:{tune_name}\nM:{meter}\nL:1/8\nK:{key}\n{raw_abc}"

    incipit = extract_incipit(abc_full, bars=2)

    return {
        "id":  matched["id"],   # integer, as returned by the API
        "url": setting_url,     # full original URL with #fragment
        "abc": incipit,
    }


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    print(f"Loading {SETS_FILE}")
    sets_data = json.loads(SETS_FILE.read_text(encoding="utf-8"))

    print(f"Loading {CACHE_FILE}")
    cache_data = json.loads(CACHE_FILE.read_text(encoding="utf-8")) \
                 if CACHE_FILE.exists() else []

    # Index by exact URL string, lowercased for comparison
    cache_index = {(e.get("url") or "").lower(): e for e in cache_data}
    print(f"Cache: {len(cache_index)} entries\n")

    if not isinstance(sets_data, list):
        print("ERROR: sets_full.json top level must be an array")
        return

    hits = misses = errors = 0

    for set_i, set_obj in enumerate(sets_data):
        settings_list = set_obj.get("settings")
        if not isinstance(settings_list, list):
            continue

        for j, setting in enumerate(settings_list):
            setting_url = (setting.get("url") or "").strip()
            if not setting_url:
                print(f"  [set {set_i}][{j}] no url — skipped")
                continue

            #print(f"  [set {set_i}][{j}] {setting_url}")
            lookup_key = setting_url.lower()

            # ── cache hit ──────────────────────────────────────────────
            if lookup_key in cache_index:
                setting["abc"] = cache_index[lookup_key].get("abc", "")
                hits += 1
                #print(f"    cache hit")
                continue

            # ── API lookup ─────────────────────────────────────────────
            time.sleep(API_DELAY)
            setting_id_from_obj = setting.get("id")
            result = fetch_setting(setting_url, setting_id_from_obj)

            if result:
                # Write incipit abc onto the setting in sets_full.json
                setting["abc"] = result["abc"]

                # Append new entry to cache file data (avoid duplicates)
                if result["url"].lower() not in cache_index:
                    cache_data.append(result)
                    cache_index[result["url"].lower()] = result

                misses += 1
                print(f"    ok")
            else:
                errors += 1
                print(f"    FAILED — no abc written")

    # ── persist both files ─────────────────────────────────────────────
    print(f"\nWriting {SETS_FILE}")
    SETS_FILE.write_text(
        json.dumps(sets_data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Writing {CACHE_FILE}")
    CACHE_FILE.write_text(
        json.dumps(cache_data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nDone  hits={hits}  api={misses}  errors={errors}  "
          f"cache_size={len(cache_data)}")


if __name__ == "__main__":
    main()