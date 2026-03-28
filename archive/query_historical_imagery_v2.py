"""
Query for pre-1984 imagery: early Landsat MSS (1972-1983) and declassified (CORONA/HEXAGON).
Fixes NASA CMR parameter names and extends STAC pagination.
"""

import json
import urllib.request
import urllib.parse
import urllib.error
import ssl

WEST, SOUTH, EAST, NORTH = -8.70, 41.13, -8.54, 41.19

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_peer = False

def fetch(url, data=None, method=None, headers=None, timeout=30):
    if headers is None:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if data and isinstance(data, dict):
        data = json.dumps(data).encode("utf-8")
    if method is None:
        method = "POST" if data else "GET"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body.strip() else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  HTTP {e.code}: {body[:200]}")
        return None
    except Exception as e:
        print(f"  Error: {e}")
        return None

# ─────────────────────────────────────
# A. USGS STAC - early Landsat (1972-1983)
# ─────────────────────────────────────
print("=" * 70)
print("A. USGS STAC - Landsat MSS 1972-1983")
print("=" * 70)

base = "https://landsatlook.usgs.gov/stac-server/search"
all_scenes = []

# Paginate through all results
next_link = None
payload = {
    "collections": ["landsat-c2l1"],
    "bbox": [WEST, SOUTH, EAST, NORTH],
    "datetime": "1972-01-01T00:00:00Z/1983-12-31T23:59:59Z",
    "limit": 250
}

page = 1
while True:
    print(f"\n  Page {page}...")
    if next_link:
        result = fetch(next_link, data=None, method="GET")
    else:
        result = fetch(base, data=payload)

    if not result or "features" not in result:
        print("  No more results.")
        break

    feats = result["features"]
    if not feats:
        break

    all_scenes.extend(feats)
    print(f"  Got {len(feats)} scenes (total so far: {len(all_scenes)})")

    # Check for next page
    links = result.get("links", [])
    next_link = None
    for link in links:
        if link.get("rel") == "next":
            next_link = link.get("href")
            # For POST-based pagination, handle the body/merge approach
            if link.get("method") == "POST":
                merge = link.get("merge", link.get("body", {}))
                if merge:
                    payload.update(merge)
                next_link = link.get("href", base)
                result2 = fetch(next_link, data=payload)
                if result2 and "features" in result2:
                    feats2 = result2["features"]
                    if feats2:
                        all_scenes.extend(feats2)
                        print(f"  Page {page+1}: Got {len(feats2)} more (total: {len(all_scenes)})")
                next_link = None  # handled
            break
    if not next_link:
        break
    page += 1

# Deduplicate and summarize
seen = set()
unique = []
for s in all_scenes:
    sid = s.get("id")
    if sid not in seen:
        seen.add(sid)
        unique.append(s)

print(f"\n  TOTAL UNIQUE Landsat scenes 1972-1983: {len(unique)}")

# Group by year
from collections import defaultdict
by_year = defaultdict(list)
for s in unique:
    dt = s.get("properties", {}).get("datetime", "")
    year = dt[:4] if dt else "?"
    by_year[year].append(s)

for year in sorted(by_year.keys()):
    scenes = by_year[year]
    print(f"\n  {year}: {len(scenes)} scenes")
    # Show best (lowest cloud) scenes
    scenes_sorted = sorted(scenes, key=lambda x: x.get("properties",{}).get("eo:cloud_cover", 100))
    for s in scenes_sorted[:5]:
        p = s.get("properties", {})
        print(f"    {s['id']} | cloud={p.get('eo:cloud_cover','?')}% | {p.get('instruments',['?'])} | path/row={p.get('landsat:wrs_path','?')}/{p.get('landsat:wrs_row','?')}")
    if len(scenes) > 5:
        print(f"    ... and {len(scenes)-5} more")


# ─────────────────────────────────────
# B. NASA CMR - correct parameter names
# ─────────────────────────────────────
print("\n" + "=" * 70)
print("B. NASA CMR - Declassified Imagery Collections")
print("=" * 70)

base_cmr = "https://cmr.earthdata.nasa.gov/search"

# CMR uses different param names: free_text, not keyword
# For collections
print("\n  Searching collections with free_text...")
for kw in ["declassified", "CORONA", "HEXAGON", "KH-4", "KH-9", "declass"]:
    url = f"{base_cmr}/collections.json?free_text={urllib.parse.quote(kw)}&page_size=10"
    result = fetch(url)
    if result and "feed" in result and "entry" in result["feed"]:
        entries = result["feed"]["entry"]
        if entries:
            for e in entries:
                short = e.get("short_name", "?")
                title = e.get("title", "?")
                t1 = e.get("time_start", "?")
                t2 = e.get("time_end", "?")
                cid = e.get("id", "?")
                print(f"    [{kw}] {short} — {title[:100]}")
                print(f"           Time: {t1} to {t2} | concept_id: {cid}")

# Search CMR granules for declassified imagery over Porto
print("\n  Searching CMR granules over Porto for declassified imagery...")

# First find the specific collection concept IDs for declassified
declass_collections = []
for kw in ["declassified satellite", "CORONA KH", "HEXAGON KH"]:
    url = f"{base_cmr}/collections.json?free_text={urllib.parse.quote(kw)}&page_size=20"
    result = fetch(url)
    if result and "feed" in result and "entry" in result["feed"]:
        for e in result["feed"]["entry"]:
            cid = e.get("id", "?")
            short = e.get("short_name", "?")
            if cid not in [c[0] for c in declass_collections]:
                declass_collections.append((cid, short, e.get("title","")))

print(f"\n  Found {len(declass_collections)} potentially relevant collections")

for cid, short, title in declass_collections:
    # Granule search with correct CMR parameter names
    url = (
        f"{base_cmr}/granules.json?"
        f"collection_concept_id={cid}"
        f"&bounding_box[]={WEST},{SOUTH},{EAST},{NORTH}"
        f"&temporal[]=1957-01-01T00:00:00Z,1984-12-31T23:59:59Z"
        f"&page_size=50"
    )
    result = fetch(url)
    if result and "feed" in result:
        entries = result["feed"].get("entry", [])
        if entries:
            print(f"\n  Collection '{short}': {len(entries)} granules over Porto!")
            for g in entries[:15]:
                gid = g.get("producer_granule_id", g.get("title", "?"))
                t1 = g.get("time_start", "?")
                print(f"    - {gid} | {t1}")
        # else no output to keep it clean

# Also try a wider bounding box for declassified imagery
# (CORONA frames are huge, ~14x190 km)
print("\n  Trying wider bounding box for CORONA/HEXAGON...")
WIDE_WEST, WIDE_SOUTH, WIDE_EAST, WIDE_NORTH = -10.0, 40.0, -7.0, 42.5

for cid, short, title in declass_collections:
    if "declass" in short.lower() or "corona" in short.lower() or "kh" in short.lower() or "hexagon" in short.lower() or "declass" in title.lower():
        url = (
            f"{base_cmr}/granules.json?"
            f"collection_concept_id={cid}"
            f"&bounding_box[]={WIDE_WEST},{WIDE_SOUTH},{WIDE_EAST},{WIDE_NORTH}"
            f"&temporal[]=1957-01-01T00:00:00Z,1984-12-31T23:59:59Z"
            f"&page_size=50"
        )
        result = fetch(url)
        if result and "feed" in result:
            entries = result["feed"].get("entry", [])
            if entries:
                print(f"\n  Collection '{short}' (wide bbox): {len(entries)} granules!")
                for g in entries[:10]:
                    gid = g.get("producer_granule_id", g.get("title", "?"))
                    t1 = g.get("time_start", "?")
                    # Try to get spatial info
                    boxes = g.get("boxes", [])
                    print(f"    - {gid} | {t1} | bbox={boxes[:1] if boxes else 'N/A'}")


# ─────────────────────────────────────
# C. NASA CMR - Landsat MSS granules
# ─────────────────────────────────────
print("\n" + "=" * 70)
print("C. NASA CMR - Landsat MSS granules 1972-1983")
print("=" * 70)

# Find Landsat MSS collection IDs
landsat_mss_colls = []
for kw in ["Landsat 1 MSS", "Landsat 2 MSS", "Landsat 3 MSS", "LANDSAT_MSS"]:
    url = f"{base_cmr}/collections.json?free_text={urllib.parse.quote(kw)}&page_size=10"
    result = fetch(url)
    if result and "feed" in result and "entry" in result["feed"]:
        for e in result["feed"]["entry"]:
            cid = e.get("id")
            short = e.get("short_name", "?")
            title = e.get("title", "?")
            if cid not in [c[0] for c in landsat_mss_colls] and "mss" in title.lower():
                landsat_mss_colls.append((cid, short, title))
                print(f"  {short}: {title[:80]}")

for cid, short, title in landsat_mss_colls[:5]:
    url = (
        f"{base_cmr}/granules.json?"
        f"collection_concept_id={cid}"
        f"&bounding_box[]={WEST},{SOUTH},{EAST},{NORTH}"
        f"&temporal[]=1972-01-01T00:00:00Z,1983-12-31T23:59:59Z"
        f"&page_size=100"
    )
    result = fetch(url)
    if result and "feed" in result:
        entries = result["feed"].get("entry", [])
        if entries:
            print(f"\n  '{short}': {len(entries)} granules")
            for g in entries[:10]:
                gid = g.get("producer_granule_id", g.get("title", "?"))
                t1 = g.get("time_start", "?")
                cloud = "N/A"
                # Check additional attributes
                for attr in g.get("additional_attributes", []):
                    if "cloud" in attr.get("name", "").lower():
                        cloud = attr.get("values", ["?"])
                print(f"    - {gid} | {t1} | cloud={cloud}")
            if len(entries) > 10:
                print(f"    ... and {len(entries)-10} more")


# ─────────────────────────────────────
# D. Direct EarthExplorer catalog search
# ─────────────────────────────────────
print("\n" + "=" * 70)
print("D. USGS EarthExplorer - known datasets for Portugal area")
print("=" * 70)

# The USGS has a machine-to-machine inventory API
# Try the public catalog metadata endpoint
print("\n  Checking USGS public catalog for declassified datasets...")
url = "https://earthexplorer.usgs.gov/inventory/datasets"
headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
result = fetch(url, headers=headers)
if result:
    print(f"  Got response: {str(result)[:300]}")
else:
    print("  EarthExplorer inventory endpoint not accessible.")

# Try to get Landsat MSS scene list via WRS path/row lookup
# Porto falls in WRS-2 path 204, row 031/032 and WRS-1 path 217/218, row 031/032
print("\n  Porto WRS path/row coverage:")
print("    WRS-2 (Landsat 4+): Path 204, Rows 031-032; Path 205, Row 031")
print("    WRS-1 (Landsat 1-3): Path 217-218, Rows 031-032")

# Summary of GEE availability
print("\n" + "=" * 70)
print("E. Summary of GEE Landsat MSS collections for Porto")
print("=" * 70)
print("""
  Available in Google Earth Engine:

  LANDSAT/LM01/C02/T1 - Landsat 1 MSS (Jul 1972 - Jan 1978)
  LANDSAT/LM01/C02/T2 - Landsat 1 MSS Tier 2
  LANDSAT/LM02/C02/T1 - Landsat 2 MSS (Jan 1975 - Feb 1982)
  LANDSAT/LM02/C02/T2 - Landsat 2 MSS Tier 2
  LANDSAT/LM03/C02/T1 - Landsat 3 MSS (Mar 1978 - Mar 1983)
  LANDSAT/LM03/C02/T2 - Landsat 3 MSS Tier 2
  LANDSAT/LM04/C02/T1 - Landsat 4 MSS (Jul 1982 - Dec 1993)
  LANDSAT/LM04/C02/T2 - Landsat 4 MSS Tier 2
  LANDSAT/LM05/C02/T1 - Landsat 5 MSS (Mar 1984 - Oct 2012)
  LANDSAT/LM05/C02/T2 - Landsat 5 MSS Tier 2

  Resolution: ~60m (MSS), 4 bands (Green, Red, NIR1, NIR2)
  WRS-1 path/row for Porto: 217/031, 217/032, 218/031, 218/032
  WRS-2 path/row for Porto: 204/031, 204/032, 205/031

  For declassified imagery (CORONA/HEXAGON), use USGS EarthExplorer:
    https://earthexplorer.usgs.gov/
    Datasets: Declassified Data I (CORONA), Declassified Data II (HEXAGON)
    These require manual browsing or authenticated M2M API access.
""")

print("Done.")
