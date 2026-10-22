"""Bounded, streamed mirroring of the ACMAD EIN15 NetCDF archive."""

import hashlib
import re
import tempfile
from urllib.parse import urlsplit
from xml.etree import ElementTree

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.storage import storages
from django.db import transaction
from django.utils import timezone
from django_celery_beat.models import IntervalSchedule, PeriodicTask

from .models import RCCEIN15Asset


CATALOGUE_URL = "http://sgbd.acmad.org:8080/thredds/catalog/ein15output/catalog.xml"
CATALOGUE_PATH = "/thredds/catalog/ein15output/catalog.xml"
SOURCE_PREFIX = "ein15output/"
FILE_NAME = re.compile(r"WAfr50_(?:STS|SRF|SAV|RAD|ATM)\.\d{10}\.nc\Z")
MAX_CATALOGUE_BYTES = 2 * 1024 * 1024
MAX_FILE_BYTES = 3 * 1024 * 1024 * 1024
SCHEDULE_NAME = "rcc-ein15-import"


def validate_catalogue_url(url):
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise ValidationError("Invalid EIN15 catalogue URL.") from exc
    allowed = getattr(settings, "RCC_EIN15_ALLOWED_SOURCE_HOSTS", ("sgbd.acmad.org",))
    if isinstance(allowed, str):
        allowed = [part.strip() for part in allowed.split(",")]
    if (
        parsed.scheme not in {"http", "https"} or parsed.hostname not in allowed
        or parsed.path != CATALOGUE_PATH or port not in {None, 80, 443, 8080}
        or parsed.username or parsed.password or parsed.query or parsed.fragment
    ):
        raise ValidationError("Use the approved EIN15 THREDDS root catalogue URL.")
    return parsed


def validate_filename(filename):
    if not isinstance(filename, str) or not FILE_NAME.fullmatch(filename):
        raise ValidationError("Unrecognized EIN15 NetCDF filename.")
    return filename


def source_url_for(catalogue_url, filename):
    parsed = validate_catalogue_url(catalogue_url)
    validate_filename(filename)
    return f"{parsed.scheme}://{parsed.netloc}/thredds/fileServer/{SOURCE_PREFIX}{filename}"


def discover_files(catalogue_url=CATALOGUE_URL):
    validate_catalogue_url(catalogue_url)
    with requests.get(catalogue_url, stream=True, timeout=(15, 45), allow_redirects=False) as response:
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError("The EIN15 catalogue did not return a direct response.")
        content = bytearray()
        for chunk in response.iter_content(chunk_size=64 * 1024):
            content.extend(chunk)
            if len(content) > MAX_CATALOGUE_BYTES:
                raise ValueError("The EIN15 catalogue exceeds the size limit.")
    root = ElementTree.fromstring(content)
    files = {}
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] != "dataset":
            continue
        path = node.attrib.get("urlPath", "")
        if not path.startswith(SOURCE_PREFIX):
            continue
        filename = path[len(SOURCE_PREFIX):]
        try:
            validate_filename(filename)
        except ValidationError:
            continue
        size = next((child for child in node if child.tag.rsplit("}", 1)[-1] == "dataSize"), None)
        modified = next((child for child in node if child.tag.rsplit("}", 1)[-1] == "date" and child.attrib.get("type") == "modified"), None)
        files[filename] = {
            "filename": filename,
            "size": f"{size.text} {size.attrib.get('units', '')}" if size is not None else "",
            "modified": modified.text if modified is not None else "",
        }
    if not files:
        raise ValueError("No recognized NetCDF files were found in the EIN15 catalogue.")
    return [files[name] for name in sorted(files)]


def sync_file(catalogue_url, filename):
    source_url = source_url_for(catalogue_url, filename)
    storage = storages["rcc_data"]
    existing = RCCEIN15Asset.objects.filter(filename=filename).first()
    headers = {}
    if existing and existing.source_url == source_url and existing.source_last_modified and storage.exists(existing.object_name):
        headers["If-Modified-Since"] = existing.source_last_modified
    with requests.get(source_url, stream=True, timeout=(15, 120), allow_redirects=False, headers=headers) as response:
        if response.status_code == 304 and headers:
            return existing
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError("The EIN15 file did not return a direct response.")
        length = response.headers.get("Content-Length", "")
        if length.isdecimal() and int(length) > MAX_FILE_BYTES:
            raise ValueError("The NetCDF file exceeds the 3 GiB size limit.")
        checksum = hashlib.sha256()
        size = 0
        signature = bytearray()
        with tempfile.TemporaryFile() as temporary:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                size += len(chunk)
                if size > MAX_FILE_BYTES:
                    raise ValueError("The NetCDF file exceeds the 3 GiB size limit.")
                if len(signature) < 8:
                    signature.extend(chunk[:8 - len(signature)])
                checksum.update(chunk)
                temporary.write(chunk)
            if not (signature.startswith((b"CDF\x01", b"CDF\x02", b"CDF\x05")) or signature == b"\x89HDF\r\n\x1a\n"):
                raise ValueError("The source is not a NetCDF file.")
            if length.isdecimal() and size != int(length):
                raise ValueError("The NetCDF download is incomplete.")
            digest = checksum.hexdigest()
            object_name = f"ein15/{filename[:-3]}/{digest[:16]}.nc"
            if not storage.exists(object_name):
                temporary.seek(0)
                object_name = storage.save(object_name, File(temporary, name=filename))
    with transaction.atomic():
        asset, _ = RCCEIN15Asset.objects.update_or_create(
            filename=filename,
            defaults={
                "source_url": source_url, "object_name": object_name,
                "checksum_sha256": digest, "size_bytes": size,
                "source_last_modified": response.headers.get("Last-Modified", "")[:100],
                "synced_at": timezone.now(),
            },
        )
    return asset


def sync_schedule(config):
    interval, _ = IntervalSchedule.objects.get_or_create(
        every=config.interval_hours, period=IntervalSchedule.HOURS
    )
    task, _ = PeriodicTask.objects.update_or_create(
        name=SCHEDULE_NAME,
        defaults={
            "task": "climweb.pages.services.tasks.run_scheduled_rcc_ein15_import",
            "interval": interval, "crontab": None, "solar": None, "clocked": None,
            "args": "[]", "enabled": config.enabled and bool(config.selected_files),
            "one_off": False,
        },
    )
    return task
