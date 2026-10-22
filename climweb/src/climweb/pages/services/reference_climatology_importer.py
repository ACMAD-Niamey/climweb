"""Mirror station reference climatologies from the legacy African RCC tool."""

import time
import xml.etree.ElementTree as ElementTree
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError

from .models import RCCReferenceClimatology


SOURCE_ROOT = "https://rcc.acmad.org/African-RCC/"
COUNTRY_URL = urljoin(SOURCE_ROOT, "rcc_country_selection.php")
STATION_URL = urljoin(SOURCE_ROOT, "rcc_climatology_station_output.php")
DISPLAY_URL = urljoin(SOURCE_ROOT, "rcc_climatology_data_display.php")
DATA_URL = urljoin(SOURCE_ROOT, "xml_output.xml")

PERIODS = {
    "1981-1990": ("mean_1981_90", 1981, 1990),
    "1991-2000": ("mean_1991_2000", 1991, 2000),
    "2001-2010": ("mean_2001_2010", 2001, 2010),
    "1981-2010": ("mean_1981_2010", 1981, 2010),
}

MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def validate_source_root(source_root):
    parsed = urlparse(source_root)
    if parsed.scheme != "https" or parsed.hostname != "rcc.acmad.org":
        raise ValidationError("Reference climatologies must be imported from rcc.acmad.org over HTTPS.")
    if not parsed.path.rstrip("/").endswith("/African-RCC"):
        raise ValidationError("Unexpected reference-climatology source path.")
    return source_root.rstrip("/") + "/"


def parse_options(html, select_name):
    soup = BeautifulSoup(html, "html.parser")
    select = soup.find("select", attrs={"name": select_name})
    if not select:
        raise ValueError(f"The legacy response did not contain {select_name} options.")
    return [
        {"code": option.get("value", "").strip(), "name": option.get_text(" ", strip=True)}
        for option in select.find_all("option")
        if option.get("value", "").strip()
    ]


def parse_climatology_xml(xml_content, station_id, period_start, period_end):
    try:
        root = ElementTree.fromstring(xml_content)
    except ElementTree.ParseError as exc:
        raise ValueError("The legacy climatology response was not valid XML.") from exc

    rows = []
    station_name = ""
    for record in root.findall("./rec"):
        returned_station = (record.findtext("station_id") or "").strip()
        returned_start = int(record.findtext("Beginning_Year") or 0)
        returned_end = int(record.findtext("End_Year") or 0)
        if (
            returned_station != str(station_id)
            or returned_start != period_start
            or returned_end != period_end
        ):
            raise ValueError("The legacy service returned a different station or period.")
        month = int(record.findtext("mm") or 0)
        if month not in range(1, 13):
            continue
        station_name = (record.findtext("station_name") or station_name).strip()
        rows.append(
            {
                "month": month,
                "month_name": MONTH_NAMES[month - 1],
                "precipitation": _number(record.findtext("precip")),
                "rainy_days": _number(record.findtext("rainy_days")),
                "tmax": _number(record.findtext("tmax")),
                "tmean": _number(record.findtext("tmean")),
                "tmin": _number(record.findtext("tmin")),
            }
        )
    if not rows:
        raise ValueError("The legacy service returned no monthly climatology records.")
    return station_name, sorted(rows, key=lambda row: row["month"])


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class ReferenceClimatologyClient:
    def __init__(self, source_root=SOURCE_ROOT, session=None):
        self.source_root = validate_source_root(source_root)
        self.session = session or requests.Session()
        self.country_url = urljoin(self.source_root, "rcc_country_selection.php")
        self.station_url = urljoin(self.source_root, "rcc_climatology_station_output.php")
        self.display_url = urljoin(self.source_root, "rcc_climatology_data_display.php")
        self.data_url = urljoin(self.source_root, "xml_output.xml")

    def countries(self):
        response = self.session.get(self.country_url, timeout=(15, 60))
        response.raise_for_status()
        return parse_options(response.text, "select_ctry")

    def stations(self, country_code):
        response = self.session.post(
            self.station_url,
            data={"select_ctry": country_code, "submit": "List Stations>>"},
            timeout=(15, 60),
        )
        response.raise_for_status()
        return parse_options(response.text, "station_name")

    def climatology(self, station_id, period_key, attempts=3):
        parameter, period_start, period_end = PERIODS[period_key]
        for attempt in range(attempts):
            response = self.session.post(
                self.display_url,
                data={"station_name": station_id, parameter: period_key},
                timeout=(15, 60),
            )
            response.raise_for_status()
            response = self.session.get(self.data_url, timeout=(15, 60))
            response.raise_for_status()
            try:
                return parse_climatology_xml(
                    response.content,
                    station_id,
                    period_start,
                    period_end,
                )
            except ValueError:
                if attempt + 1 == attempts:
                    raise
                time.sleep(0.4)


def sync_climatology(client, country, station, period_key):
    _, period_start, period_end = PERIODS[period_key]
    returned_name, monthly_data = client.climatology(station["code"], period_key)
    asset, created = RCCReferenceClimatology.objects.update_or_create(
        country_code=country["code"],
        station_id=station["code"],
        period_start=period_start,
        period_end=period_end,
        defaults={
            "country": country["name"],
            "station_name": returned_name or station["name"],
            "monthly_data": monthly_data,
            "source_url": client.data_url,
        },
    )
    return asset, created
