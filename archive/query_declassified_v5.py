"""
Final query: search CMR granules for CORONA and Declassified-2 over Porto,
plus Landsat MSS summary.
"""

import json
import urllib.request
import urllib.parse
import urllib.error
import ssl
import sys
import io

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_peer = False

WEST, SOUTH, EAST, NORTH = -8.70, 41.13, -8.54, 41.19
WIDE_W, WIDE_S, WIDE_E, WIDE_N = -10.0, 40.0, -7.0, 42.5

def cmr_post(endpoint, params, timeout=30):
    """POST to CMR with form-encoded data."""
    data = urllib.parse.urlencode(params, doseq=True).encode("utf-8")
    req = urllib.request.Request(
        f"https://cmr.earthdata.nasa.gov/search/{endpoint}",
        data=data,
        headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  HTTP {e.code}: {body[:250]}")
        return None
    except Exception as e:
        print(f"  Error: {e}")
        return None


# Known collection concept IDs from previous discovery
declass_collections = [
    ("C1220566377-USGS_LTA", "CORONA_SATELLITE_PHOTOS", "CORONA Satellite Photographs (1960-1972)"),
    ("C1220566178-USGS_LTA", "DISP", "CORONA Satellite Photography (1960-1972)"),
    ("C1220567575-USGS_LTA", "Declassified_Satellite_Imagery_2_2002", "Declassified Satellite Imagery 2 (HEXAGON/GAMBIT, from 1970)"),
]

# -----------------------------------------------
# A. Search CORONA/HEXAGON granules over Porto
# -----------------------------------------------
print("=" * 70)
print("A. DECLASSIFIED IMAGERY - Granule search over Porto area")
print("=" * 70)

for cid, short, desc in declass_collections:
    print(f"\n--- {desc} ---")
    print(f"    Collection: {short} ({cid})")

    # Try with and without bounding box, and without temporal
    for label, params in [
        ("Porto bbox", {"collection_concept_id": cid,
                        "bounding_box[]": f"{WEST},{SOUTH},{EAST},{NORTH}",
                        "page_size": "50"}),
        ("Wide bbox", {"collection_concept_id": cid,
                       "bounding_box[]": f"{WIDE_W},{WIDE_S},{WIDE_E},{WIDE_N}",
                       "page_size": "50"}),
        ("No spatial filter (first 10)", {"collection_concept_id": cid,
                                          "page_size": "10"}),
    ]:
        result = cmr_post("granules.json", params)
        if result and "feed" in result:
            entries = result["feed"].get("entry", [])
            total = result["feed"].get("hits", str(len(entries)))
            if entries:
                print(f"\n  [{label}] {total} granules total!")
                for g in entries[:10]:
                    gid = g.get("producer_granule_id", g.get("title", "?"))
                    t1 = g.get("time_start", "?")[:10] if g.get("time_start") else "?"
                    boxes = g.get("boxes", [])
                    polys = g.get("polygons", [])
                    spatial = f"bbox={boxes[0]}" if boxes else (f"poly=yes" if polys else "no_spatial")
                    print(f"    {gid} | date={t1} | {spatial}")
                if int(total) > 10:
                    print(f"    ... total: {total} granules")
                break  # found results, stop trying looser filters
            else:
                print(f"  [{label}] 0 granules (hits={total})")

# Also try NASA Landsat Data Collection
print(f"\n--- NASA Landsat Data Collection (NLDC) ---")
params = {
    "collection_concept_id": "C1220566355-USGS_LTA",
    "bounding_box[]": f"{WEST},{SOUTH},{EAST},{NORTH}",
    "temporal[]": "1972-01-01T00:00:00Z,1984-12-31T23:59:59Z",
    "page_size": "100"
}
result = cmr_post("granules.json", params)
if result and "feed" in result:
    entries = result["feed"].get("entry", [])
    total = result["feed"].get("hits", str(len(entries)))
    print(f"  {total} granules")
    for g in entries[:10]:
        gid = g.get("producer_granule_id", g.get("title", "?"))
        t1 = g.get("time_start", "?")[:10] if g.get("time_start") else "?"
        print(f"    {gid} | {t1}")


# -----------------------------------------------
# COMPREHENSIVE SUMMARY
# -----------------------------------------------
print("\n" + "=" * 70)
print("COMPREHENSIVE SUMMARY: Historical Imagery for Porto 1957-1984")
print("=" * 70)

print("""
1. LANDSAT MSS (1974-1984)
   Source: USGS STAC API (landsatlook.usgs.gov)
   Resolution: ~60m, 4 bands (Green, Red, NIR1, NIR2)
   Total scenes over Porto: 188 unique scenes (1974-1983)
   + 140 scenes from 1984 (Landsat 4+5 MSS and TM)

   Coverage by year:
     1974:  2 scenes (Landsat 1)
     1975: 13 scenes (Landsat 1+2)
     1976: 14 scenes (Landsat 1+2)
     1977: 16 scenes (Landsat 2)
     1978: 18 scenes (Landsat 2+3)
     1979: 19 scenes (Landsat 2+3)
     1980: 17 scenes (Landsat 2+3)
     1981: 16 scenes (Landsat 2)
     1982: 14 scenes (Landsat 2+4)
     1983: 59 scenes (Landsat 4)
     1984: 140 scenes (Landsat 4+5, MSS+TM)

   WRS-1 (Landsat 1-3): Path 219-221, Row 031-032
   WRS-2 (Landsat 4+): Path 204-205, Row 031-032

   Best cloud-free scenes (cloud < 5%):
     - 1975-07-04: LM01_L1TP_219031, 0% cloud
     - 1976-08-03: LM01_L1GS_219031, 0% cloud
     - 1977-09-13: LM02_L1TP_220031, 0% cloud
     - 1977-06-15: LM02_L1TP_220031, 0% cloud
     - 1979-09-03: LM02_L1TP_220031, 0% cloud
     - 1979-02-26: LM03_L1TP_220031, 0% cloud
     - 1980-08-10: LM02_L1TP_220031, 0% cloud
     - 1980-06-08: LM03_L1TP_220031, 0% cloud
     - 1981-11-21: LM02_L1TP_220031, 0% cloud
     - 1982-09-02: LM04_L1TP_205031, 0% cloud
     - 1983-11-01: LM04_L1TP_204031+032, 0% cloud
     - 1983-09-05: LM04_L1TP_205031, 0% cloud
     - 1983-06-17: LM04_L1TP_205031, 0% cloud

   GEE collections:
     LANDSAT/LM01/C02/T2 (Landsat 1, 1972-1978)
     LANDSAT/LM02/C02/T2 (Landsat 2, 1975-1982)
     LANDSAT/LM03/C02/T2 (Landsat 3, 1978-1983)
     LANDSAT/LM04/C02/T2 (Landsat 4, 1982-1993)
     LANDSAT/LM05/C02/T2 (Landsat 5, 1984-2012)

2. CORONA Satellite Photography (1960-1972)
   Source: NASA CMR / USGS EarthExplorer
   Collections:
     - CORONA_SATELLITE_PHOTOS (C1220566377-USGS_LTA)
     - DISP (C1220566178-USGS_LTA)
   Resolution: ~2-8m (KH-4/KH-4A/KH-4B panoramic film)
   Note: CMR granule search returned 0 results for Porto area.
   The spatial metadata may not be indexed in CMR.
   Must use USGS EarthExplorer to search manually.

3. Declassified Satellite Imagery 2 - HEXAGON/GAMBIT (1970+)
   Source: NASA CMR / USGS EarthExplorer
   Collection: Declassified_Satellite_Imagery_2_2002 (C1220567575-USGS_LTA)
   Resolution: ~0.6-1.2m (KH-9 HEXAGON), ~0.6m (KH-7 GAMBIT)
   Coverage: 1970-1984
   Note: CMR granule search returned 0 results. Must use EarthExplorer.

4. NO SATELLITE COVERAGE (1957-1959)
   No publicly available satellite imagery exists before 1960.
   The first CORONA missions (KH-1) began in June 1959, but
   usable imagery starts from August 1960.
   For 1957-1959, aerial photography is the only option.

RECOMMENDED NEXT STEPS:
  1. For Landsat MSS: Use GEE Python API to query/download scenes.
     Filter by cloud cover < 20%. Earliest useful: 1974.
  2. For CORONA/HEXAGON: Create a free USGS EarthExplorer account at
     https://ers.cr.usgs.gov/register and search:
       - Dataset: "Declassified Data I (1996)" for CORONA
       - Dataset: "Declassified Data II (2002)" for HEXAGON
     These datasets require manual browsing as their spatial
     metadata is not fully indexed in public APIs.
  3. The USGS M2M API requires authentication for scene searches.
""")

print("Done.")
