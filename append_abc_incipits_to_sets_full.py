#!/usr/bin/env python3
"""
enrich_sets_abc.py
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
from pathlib import Path

SETS_FILE  = Path("./data/sets_full.json")
CACHE_FILE = Path("./data/tune_id_url_abc.json")
API_DELAY  = 0.5  # seconds between outbound API calls


# ── incipit ────────────────────────────────────────────────────────────────────

def extract_incipit(abc_full, bars=2):
    """
    Return header lines + the first `bars` complete bars of the body.
    Notes before the first barline (anacrusis / pickup) are included
    in the output but do NOT count toward `bars`.
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

    # Remove inline fields [X:...] and % comments before tokenising
    body = re.sub(r'\[(?!\|)[A-Za-z]:[^\]]*\]', '', "\n".join(body_lines))
    body = re.sub(r'%[^\n]*', '', body)

    # Each token is either a barline symbol or a note/rest group
    tokens = re.findall(r'\|\||:\||\|:|\|]|\[|::|[|]|[^\s|]+', body)

    def is_barline(t):
        return bool(re.fullmatch(r'\|\||:\||\|:|\|]|\[|::|[|]', t))

    collected, bars_done, past_anacrusis = [], 0, False

    for tok in tokens:
        collected.append(tok)
        if is_barline(tok):
            if not past_anacrusis:
                past_anacrusis = True   # first barline ends anacrusis; don't count
            else:
                bars_done += 1
                if bars_done >= bars:
                    break

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