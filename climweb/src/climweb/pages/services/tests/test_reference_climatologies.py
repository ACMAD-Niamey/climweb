from unittest.mock import Mock

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from climweb.pages.services.models import RCCReferenceClimatology
from climweb.pages.services.reference_climatology_importer import (
    parse_climatology_xml,
    parse_options,
    sync_climatology,
    validate_source_root,
)


SAMPLE_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<station>
  <rec><station_id>61052</station_id><station_name>NIAMEY-AERO</station_name><mm>1</mm>
    <precip>0.5</precip><rainy_days>1</rainy_days><tmax>32.2</tmax><tmean>24.7</tmean><tmin>17.4</tmin>
    <Beginning_Year>1991</Beginning_Year><End_Year>2000</End_Year></rec>
  <rec><station_id>61052</station_id><station_name>NIAMEY-AERO</station_name><mm>2</mm>
    <precip>1.5</precip><rainy_days>2</rainy_days><tmax>35.0</tmax><tmean>27.0</tmean><tmin>19.0</tmin>
    <Beginning_Year>1991</Beginning_Year><End_Year>2000</End_Year></rec>
</station>"""


class ReferenceClimatologyTests(TestCase):
    def make_record(self, **overrides):
        values = {
            "country_code": "NE",
            "country": "NIGER",
            "station_id": "61052",
            "station_name": "NIAMEY-AERO",
            "period_start": 1991,
            "period_end": 2000,
            "monthly_data": [
                {
                    "month": 1,
                    "month_name": "January",
                    "precipitation": 0.5,
                    "rainy_days": 1.0,
                    "tmax": 32.2,
                    "tmean": 24.7,
                    "tmin": 17.4,
                }
            ],
            "source_url": "https://rcc.acmad.org/African-RCC/xml_output.xml",
        }
        values.update(overrides)
        return RCCReferenceClimatology.objects.create(**values)

    def test_legacy_options_and_xml_are_parsed_and_validated(self):
        html = """<select name="select_ctry"><option value="NE">NIGER</option></select>
        <select name="station_name"><option value="61052">NIAMEY-AERO</option></select>"""
        self.assertEqual(parse_options(html, "select_ctry"), [{"code": "NE", "name": "NIGER"}])
        self.assertEqual(parse_options(html, "station_name"), [{"code": "61052", "name": "NIAMEY-AERO"}])
        name, rows = parse_climatology_xml(SAMPLE_XML, "61052", 1991, 2000)
        self.assertEqual(name, "NIAMEY-AERO")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["precipitation"], 0.5)
        with self.assertRaisesMessage(ValueError, "different station or period"):
            parse_climatology_xml(SAMPLE_XML, "61024", 1991, 2000)
        with self.assertRaises(ValidationError):
            validate_source_root("http://127.0.0.1/African-RCC/")

    def test_sync_is_idempotent(self):
        client = Mock()
        client.data_url = "https://rcc.acmad.org/African-RCC/xml_output.xml"
        client.climatology.return_value = parse_climatology_xml(
            SAMPLE_XML, "61052", 1991, 2000
        )
        country = {"code": "NE", "name": "NIGER"}
        station = {"code": "61052", "name": "NIAMEY-AERO"}
        first, created = sync_climatology(client, country, station, "1991-2000")
        second, created_again = sync_climatology(client, country, station, "1991-2000")
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(RCCReferenceClimatology.objects.count(), 1)

    def test_availability_uses_stored_monthly_data(self):
        record = self.make_record()
        self.assertTrue(record.is_available)

        record.monthly_data = []
        self.assertFalse(record.is_available)

    def test_country_station_and_period_pages(self):
        self.make_record()
        self.make_record(period_start=2001, period_end=2010)
        self.make_record(
            country_code="NG",
            country="NIGERIA",
            station_id="65125",
            station_name="ABUJA",
        )

        countries = self.client.get(reverse("rcc_reference_climatology_countries"))
        self.assertEqual(countries.status_code, 200)
        self.assertContains(countries, "NIGER")
        self.assertContains(countries, "NIGERIA")
        self.assertContains(countries, "Climate Monitoring")
        self.assertContains(countries, 'data-country-select')
        self.assertContains(countries, 'data-station-select')
        self.assertContains(countries, "NIAMEY-AERO")
        self.assertContains(countries, "ABUJA")
        self.assertEqual(len(countries.context["station_selector"]), 2)
        self.assertNotContains(countries, "rcc-reference-country-card")
        self.assertNotContains(countries, "Search countries")

        country = self.client.get(
            reverse("rcc_reference_climatology_country", args=["niger"])
        )
        self.assertContains(country, "NIAMEY-AERO")
        self.assertContains(country, "2 reference periods")
        self.assertContains(country, "Climate Monitoring")

        station = self.client.get(
            reverse(
                "rcc_reference_climatology_station",
                args=["niger", "61052"],
            )
        )
        self.assertEqual(station.status_code, 200)
        self.assertContains(station, "Climate Monitoring")
        self.assertContains(station, "1991–2000")
        self.assertContains(station, "2001–2010")
        self.assertContains(station, 'name="period"')
        self.assertContains(station, 'name="parameter"')
        self.assertContains(station, "Precipitation")
        self.assertContains(station, "Mean maximum temperature (°C)")
        self.assertEqual(station.content.count(b'class="rcc-reference-chart"'), 1)
        self.assertEqual(station.content.count(b'class="rcc-reference-table"'), 1)

        selected = self.client.get(
            reverse(
                "rcc_reference_climatology_station",
                args=["niger", "61052"],
            ),
            {"period": "2001-2010", "parameter": "tmax"},
        )
        self.assertContains(selected, "2001–2010")
        self.assertContains(selected, "Mean maximum temperature")
        self.assertContains(selected, "32.2")
        self.assertNotContains(station, 'href="https://rcc.acmad.org')
