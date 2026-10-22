"""Helpers for turning an uploaded country-boundary file into a normalised
GeoJSON FeatureCollection the participant choropleth can consume.

"Normalised" means every feature ends up with exactly these properties:

* ``iso_a3`` - ISO-3166-1 alpha-3 code, upper-cased (the join key)
* ``iso_a2`` - ISO-3166-1 alpha-2 code, upper-cased (may be empty)
* ``name``   - human readable country name

Accepts either a GeoJSON file (``.geojson`` / ``.json``) or a zipped shapefile
(``.zip``). Shapefile reading needs ``fiona`` (already a project dependency via
geomanager); the ImportError is surfaced as a friendly ValidationError.
"""
from __future__ import annotations

import json
import tempfile
import zipfile

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

# Property names commonly used for the alpha-3 code across public datasets,
# tried in order when the configured property is absent on a feature.
_ISO3_FALLBACKS = ("iso_a3", "ISO_A3", "ISO_A3_EH", "ADM0_A3", "adm0_a3", "gid_0", "GID_0", "id")
_NAME_FALLBACKS = ("name", "NAME", "admin", "ADMIN", "name_0", "NAME_0", "COUNTRY", "country")

BOUNDARY_UPLOAD_EXTENSIONS = ("geojson", "json", "zip")


def _first_present(props: dict, preferred: str, fallbacks: tuple) -> str:
    for key in (preferred, *fallbacks):
        if key and props.get(key) not in (None, "", "-99"):
            return str(props[key])
    return ""


def normalise_feature_collection(raw: dict, iso3_property: str, name_property: str) -> dict:
    """Return a new FeatureCollection with only the three canonical properties."""
    if not isinstance(raw, dict) or raw.get("type") != "FeatureCollection":
        raise ValidationError(_("The boundary file is not a GeoJSON FeatureCollection."))

    features = []
    for feature in raw.get("features", []):
        geometry = feature.get("geometry")
        if not geometry or not (geometry.get("coordinates") or geometry.get("geometries")):
            # A feature with no drawable geometry is useless on the map - skip it.
            continue
        props = feature.get("properties") or {}
        iso_a3 = _first_present(props, iso3_property, _ISO3_FALLBACKS).upper()
        if not iso_a3:
            # A feature we cannot key is useless for a choropleth - skip it.
            continue
        iso_a2 = _first_present(props, "iso_a2", ("ISO_A2", "ISO_A2_EH")).upper()
        name = _first_present(props, name_property, _NAME_FALLBACKS) or iso_a3
        features.append({
            "type": "Feature",
            "properties": {"iso_a3": iso_a3, "iso_a2": iso_a2, "name": name},
            "geometry": geometry,
        })

    if not features:
        raise ValidationError(
            _("No usable country features were found. Check the ISO alpha-3 property name.")
        )

    return {"type": "FeatureCollection", "features": features}


def _load_zipped_shapefile(raw_bytes: bytes) -> dict:
    try:
        import fiona
        from fiona.transform import transform_geom
    except ImportError as exc:  # pragma: no cover - depends on runtime image
        raise ValidationError(
            _("Reading zipped shapefiles is not available on this server. "
              "Please upload a GeoJSON file instead.")
        ) from exc

    with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
        tmp.write(raw_bytes)
        tmp.flush()

        with zipfile.ZipFile(tmp.name) as archive:
            shp_names = [n for n in archive.namelist() if n.lower().endswith(".shp")]
        if not shp_names:
            raise ValidationError(_("The zip file does not contain a .shp shapefile."))

        features = []
        with fiona.open(f"zip://{tmp.name}!{shp_names[0]}") as src:
            src_crs = src.crs
            needs_reproject = src_crs and str(src_crs).upper() not in ("EPSG:4326", "OGC:CRS84")
            for record in src:
                geom = record["geometry"]
                if needs_reproject:
                    geom = transform_geom(src_crs, "EPSG:4326", geom)
                features.append({
                    "type": "Feature",
                    "properties": dict(record["properties"]),
                    "geometry": geom,
                })
    return {"type": "FeatureCollection", "features": features}


def load_boundary_upload(file_field, iso3_property: str, name_property: str) -> dict:
    """Read a Django FieldFile (GeoJSON or zipped shapefile) -> normalised GeoJSON."""
    name = (file_field.name or "").lower()
    file_field.open("rb")
    try:
        data = file_field.read()
    finally:
        file_field.close()

    if name.endswith(".zip"):
        raw = _load_zipped_shapefile(data)
    else:
        try:
            raw = json.loads(data)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValidationError(_("The uploaded file is not valid JSON/GeoJSON.")) from exc

    return normalise_feature_collection(raw, iso3_property, name_property)
