"""One-off: extract the six park boundaries from the WDPA Nigeria shapefile
into a small GeoJSON the frontend can render.

5 parks come from authoritative WDPA polygons. Chad Basin has NO published
boundary polygon anywhere (WDPA stores it as a point only; OSM/Nominatim and
Overpass have none), so we draw an equal-area approximation: a circle centred on
the official WDPA centroid (14.2E, 12.345N) sized to its reported 2,300 km².
Flagged approx=True so the UI can label it as an estimate.
"""
import json
import math
import os
import shapefile
from shapely.geometry import shape, mapping

BASE = "data/wdpa/WDPA_WDOECM_Jun2026_Public_NGA_shp/_extracted"
READERS = [f"{BASE}/shp_{i}/WDPA_WDOECM_Jun2026_Public_NGA_shp-polygons" for i in range(3)]

# (park_id, NAME exact, DESIG_ENG substring)
WANT = [
    ("yankari",       "Yankari",       "Game Reserve"),
    ("cross_river",   "Cross River",   "National Park"),
    ("gashaka_gumti", "Gashaka-Gumti", "National Park"),
    ("kainji_lake",   "Kainji Lake",   "National Park"),
    ("old_oyo",       "Old Oyo",       "National Park"),
]
# Chad Basin: official WDPA point + reported area (no polygon published anywhere)
CHAD_CENTROID = (14.2, 12.345)   # lon, lat
CHAD_AREA_KM2 = 2300.0
OUT = "frontend/src/data/parkBoundaries.json"


def equal_area_circle(lon, lat, area_km2, n=48):
    """Polygon ring approximating a circle of `area_km2` centred on (lon, lat),
    correcting longitude for latitude so it isn't squashed on the map."""
    r_km = math.sqrt(area_km2 / math.pi)
    dlat = r_km / 110.574
    dlon = r_km / (111.320 * math.cos(math.radians(lat)))
    ring = [[round(lon + dlon * math.cos(2 * math.pi * i / n), 5),
             round(lat + dlat * math.sin(2 * math.pi * i / n), 5)] for i in range(n)]
    ring.append(ring[0])
    return {"type": "Polygon", "coordinates": [ring]}


def round_coords(c, nd=5):
    if isinstance(c[0], (float, int)):
        return [round(c[0], nd), round(c[1], nd)]
    return [round_coords(x, nd) for x in c]


features, found = [], set()
for rp in READERS:
    r = shapefile.Reader(rp)
    flds = [f[0] for f in r.fields[1:]]
    ni, di = flds.index("NAME"), flds.index("DESIG_ENG")
    for sr in r.shapeRecords():
        name, desig = str(sr.record[ni]), str(sr.record[di])
        for pid, mn, md in WANT:
            if pid in found:
                continue
            if name == mn and md.lower() in desig.lower():
                geom = shape(sr.shape.__geo_interface__).simplify(0.004, preserve_topology=True)
                g = mapping(geom)
                g["coordinates"] = round_coords(g["coordinates"])
                features.append({"type": "Feature",
                                 "properties": {"park": pid, "name": mn},
                                 "geometry": g})
                found.add(pid)

# Chad Basin — no published polygon; equal-area circle on the WDPA centroid
features.append({"type": "Feature",
                 "properties": {"park": "chad_basin", "name": "Chad Basin", "approx": True,
                                "note": "Approximate extent: WDPA centroid + reported 2,300 km² (no boundary polygon published)"},
                 "geometry": equal_area_circle(*CHAD_CENTROID, CHAD_AREA_KM2)})

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump({"type": "FeatureCollection", "features": features}, open(OUT, "w"))
print("parks written:", [f["properties"]["park"] for f in features])
print("missing:", [p for p, _, _ in WANT if p not in found])
print("file KB:", round(os.path.getsize(OUT) / 1024, 1))
