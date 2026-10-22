"""Regenerate ``base/static/base/data/africa.json`` from Natural Earth.

The bundled file is the default boundary source for the participant choropleth
(``ParticipantMapBlock`` / the OJT page). Editors can override it at runtime by
uploading their own GeoJSON or zipped shapefile in
Settings -> Participant map settings; this script only rebuilds the fallback.

Usage (needs network access, no extra dependencies)::

    python climweb/src/climweb/base/data/build_africa_boundaries.py

Source: Natural Earth 1:50m Admin 0 - Countries (public domain).
We keep the 50m resolution (not 110m) so small island states - Comoros, Cabo
Verde, Mauritius, Seychelles, Sao Tome - stay visible, then round coordinates to
2 decimal places (~1 km) to keep the payload small (~185 KB). Somaliland is
folded into Somalia because participants select "Somalia".

Output feature properties are normalised to ``iso_a3`` (upper), ``iso_a2``
(upper) and ``name`` - the keys the frontend and the boundary view expect.
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

SOURCE_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "master/geojson/ne_50m_admin_0_countries.geojson"
)
OUTPUT = Path(__file__).resolve().parents[1] / "static" / "base" / "data" / "africa.json"
PRECISION = 2


def _round(value):
    if isinstance(value, (int, float)):
        return round(value, PRECISION)
    return [_round(item) for item in value]


def _dedupe(ring):
    out = []
    for point in ring:
        if not out or out[-1] != point:
            out.append(point)
    return out


def _clean_geometry(geometry: dict) -> dict:
    geom_type = geometry["type"]
    coords = _round(geometry["coordinates"])
    if geom_type == "Polygon":
        coords = [r for r in (_dedupe(ring) for ring in coords) if len(r) >= 4]
    elif geom_type == "MultiPolygon":
        polygons = []
        for polygon in coords:
            rings = [r for r in (_dedupe(ring) for ring in polygon) if len(r) >= 4]
            if rings:
                polygons.append(rings)
        coords = polygons
    return {"type": geom_type, "coordinates": coords}


def _as_multipolygon(geometry: dict) -> list:
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"]]
    return list(geometry["coordinates"])


def build() -> None:
    with urllib.request.urlopen(SOURCE_URL, timeout=60) as response:
        source = json.load(response)

    features: dict[str, dict] = {}
    order: list[str] = []

    for feature in source["features"]:
        props = feature["properties"]
        if props.get("CONTINENT") != "Africa":
            continue

        name = props.get("ADMIN") or props.get("NAME")
        iso_a3 = props.get("ISO_A3")
        iso_a2 = props.get("ISO_A2")

        if name == "Somaliland":
            iso_a3, iso_a2, name = "SOM", "SO", "Somalia"
        if not iso_a3 or iso_a3 == "-99":
            iso_a3 = props.get("ISO_A3_EH") or props.get("ADM0_A3")
        if not iso_a2 or iso_a2 == "-99":
            iso_a2 = ""

        iso_a3 = iso_a3.upper()
        geometry = _clean_geometry(feature["geometry"])

        if iso_a3 in features:
            features[iso_a3]["geometry"]["coordinates"].extend(_as_multipolygon(geometry))
        else:
            order.append(iso_a3)
            features[iso_a3] = {
                "type": "Feature",
                "properties": {"iso_a3": iso_a3, "iso_a2": iso_a2.upper(), "name": name},
                "geometry": {"type": "MultiPolygon", "coordinates": _as_multipolygon(geometry)},
            }

    collection = {"type": "FeatureCollection", "features": [features[i] for i in order]}
    OUTPUT.write_text(json.dumps(collection, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {OUTPUT} ({OUTPUT.stat().st_size} bytes, {len(order)} countries)")


if __name__ == "__main__":
    build()
