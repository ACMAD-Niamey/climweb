"""Server-side Google Shared Drive operations for the staff workspace."""

import io
import re
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.db import transaction
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from .models import StaffDriveAudit, StaffDriveFolder


DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
GOOGLE_EXPORTS = {
    "application/vnd.google-apps.document": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".docx",
    ),
    "application/vnd.google-apps.spreadsheet": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xlsx",
    ),
    "application/vnd.google-apps.presentation": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".pptx",
    ),
    "application/vnd.google-apps.drawing": ("application/pdf", ".pdf"),
}
FILE_FIELDS = "id,name,mimeType,size,modifiedTime,webViewLink,parents,driveId,trashed"
DRIVE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,255}$")


class StaffDriveConfigurationError(ImproperlyConfigured):
    pass


class StaffDriveOperationError(RuntimeError):
    pass


def drive_is_configured():
    return bool(
        getattr(settings, "GOOGLE_DRIVE_ENABLED", False)
        and getattr(settings, "GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE", "")
        and getattr(settings, "GOOGLE_DRIVE_SHARED_DRIVE_ID", "")
        and getattr(settings, "GOOGLE_DRIVE_ROOT_FOLDER_ID", "")
    )


def validate_drive_id(value, label="Google Drive item"):
    value = (value or "").strip()
    if not DRIVE_ID_PATTERN.fullmatch(value):
        raise PermissionDenied(f"Invalid {label} identifier.")
    return value


def get_drive_service():
    if not drive_is_configured():
        raise StaffDriveConfigurationError("The Google Drive integration is not fully configured.")
    credentials_file = Path(settings.GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE)
    if not credentials_file.is_file():
        raise StaffDriveConfigurationError(
            "The Google Drive service-account credential file is not readable inside the application container."
        )
    credentials = service_account.Credentials.from_service_account_file(
        credentials_file,
        scopes=[DRIVE_SCOPE],
    )
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def _execute(request, operation):
    try:
        return request.execute()
    except HttpError as exc:
        status = getattr(getattr(exc, "resp", None), "status", None)
        if status in {401, 403}:
            raise PermissionDenied("Google Drive denied this operation.") from exc
        if status == 404:
            raise PermissionDenied("The requested Google Drive item was not found or is outside your workspace.") from exc
        raise StaffDriveOperationError(f"Google Drive could not {operation}. Please try again.") from exc


def get_item(service, file_id):
    file_id = validate_drive_id(file_id)
    return _execute(
        service.files().get(
            fileId=file_id,
            supportsAllDrives=True,
            fields=FILE_FIELDS,
        ),
        "read the item",
    )


def assert_within_root(service, file_id, allowed_root_id):
    file_id = validate_drive_id(file_id)
    allowed_root_id = validate_drive_id(allowed_root_id, "workspace root")
    shared_drive_id = settings.GOOGLE_DRIVE_SHARED_DRIVE_ID
    current_id = file_id
    visited = set()
    item = None
    while current_id and current_id not in visited and len(visited) < 100:
        visited.add(current_id)
        item = get_item(service, current_id)
        if item.get("trashed"):
            raise PermissionDenied("This Google Drive item is in the trash.")
        if item.get("driveId") and item["driveId"] != shared_drive_id:
            raise PermissionDenied("This item is outside the configured Shared Drive.")
        if current_id == allowed_root_id:
            return item
        parents = item.get("parents") or []
        current_id = parents[0] if parents else None
    raise PermissionDenied("This item is outside your permitted Google Drive folder.")


def create_folder(service, parent_id, name):
    parent_id = validate_drive_id(parent_id, "parent folder")
    return _execute(
        service.files().create(
            body={"name": name, "mimeType": FOLDER_MIME_TYPE, "parents": [parent_id]},
            supportsAllDrives=True,
            fields=FILE_FIELDS,
        ),
        "create the folder",
    )


def ensure_staff_folder(service, member, actor=None):
    folder_name = member.name.strip() or f"Staff {member.pk}"
    existing = StaffDriveFolder.objects.filter(member=member).first()
    if existing:
        try:
            item = get_item(service, existing.folder_id)
            assert_within_root(service, existing.folder_id, settings.GOOGLE_DRIVE_ROOT_FOLDER_ID)
            if item.get("mimeType") == FOLDER_MIME_TYPE:
                if item.get("name") != folder_name:
                    old_name = item.get("name", "")
                    item = rename_item(service, existing.folder_id, folder_name)
                    record_audit(
                        actor,
                        member,
                        StaffDriveAudit.Action.ITEM_RENAMED,
                        item,
                        old_name=old_name,
                        source="staff_folder_name_sync",
                    )
                return existing.folder_id
        except (PermissionDenied, StaffDriveOperationError):
            pass

    folder = create_folder(
        service,
        settings.GOOGLE_DRIVE_ROOT_FOLDER_ID,
        folder_name,
    )
    with transaction.atomic():
        record, created = StaffDriveFolder.objects.select_for_update().get_or_create(
            member=member,
            defaults={"folder_id": folder["id"]},
        )
        if not created:
            record.folder_id = folder["id"]
            record.save(update_fields=["folder_id", "updated_at"])
        StaffDriveAudit.objects.create(
            actor=actor,
            member=member,
            action=StaffDriveAudit.Action.STAFF_FOLDER_CREATED,
            file_id=folder["id"],
            file_name=folder.get("name", ""),
        )
    return folder["id"]


def list_items(service, folder_id, *, search="", page_token=None, page_size=50):
    folder_id = validate_drive_id(folder_id, "folder")
    query = [f"'{folder_id}' in parents", "trashed = false"]
    if search:
        safe_search = search.replace("\\", "\\\\").replace("'", "\\'")[:100]
        query.append(f"name contains '{safe_search}'")
    response = _execute(
        service.files().list(
            q=" and ".join(query),
            corpora="drive",
            driveId=settings.GOOGLE_DRIVE_SHARED_DRIVE_ID,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            orderBy="folder,name_natural",
            pageSize=min(page_size, 100),
            pageToken=page_token or None,
            fields=f"nextPageToken,files({FILE_FIELDS})",
        ),
        "list files",
    )
    return response.get("files", []), response.get("nextPageToken", "")


def breadcrumbs(service, folder_id, allowed_root_id):
    folder_id = validate_drive_id(folder_id, "folder")
    allowed_root_id = validate_drive_id(allowed_root_id, "workspace root")
    crumbs = []
    current_id = folder_id
    visited = set()
    while current_id and current_id not in visited and len(visited) < 100:
        visited.add(current_id)
        item = get_item(service, current_id)
        crumbs.append({"id": current_id, "name": item.get("name") or "Shared Drive"})
        if current_id == allowed_root_id:
            return list(reversed(crumbs))
        parents = item.get("parents") or []
        current_id = parents[0] if parents else None
    raise PermissionDenied("This folder is outside your permitted Google Drive workspace.")


def upload_file(service, parent_id, upload):
    media = MediaIoBaseUpload(
        upload.file,
        mimetype=getattr(upload, "content_type", None) or "application/octet-stream",
        resumable=True,
    )
    return _execute(
        service.files().create(
            body={"name": upload.name, "parents": [validate_drive_id(parent_id)]},
            media_body=media,
            supportsAllDrives=True,
            fields=FILE_FIELDS,
        ),
        "upload the file",
    )


def rename_item(service, file_id, new_name):
    return _execute(
        service.files().update(
            fileId=validate_drive_id(file_id),
            body={"name": new_name},
            supportsAllDrives=True,
            fields=FILE_FIELDS,
        ),
        "rename the item",
    )


def move_item(service, file_id, destination_id, current_parents):
    return _execute(
        service.files().update(
            fileId=validate_drive_id(file_id),
            addParents=validate_drive_id(destination_id, "destination folder"),
            removeParents=",".join(current_parents),
            supportsAllDrives=True,
            fields=FILE_FIELDS,
        ),
        "move the item",
    )


def trash_item(service, file_id):
    return _execute(
        service.files().update(
            fileId=validate_drive_id(file_id),
            body={"trashed": True},
            supportsAllDrives=True,
            fields=FILE_FIELDS,
        ),
        "move the item to trash",
    )


def download_item(service, file_id):
    item = get_item(service, file_id)
    mime_type = item.get("mimeType", "application/octet-stream")
    if mime_type == FOLDER_MIME_TYPE:
        raise StaffDriveOperationError("Folders cannot be downloaded as files.")
    filename = item.get("name") or "download"
    if mime_type in GOOGLE_EXPORTS:
        output_type, extension = GOOGLE_EXPORTS[mime_type]
        request = service.files().export_media(fileId=file_id, mimeType=output_type)
        if not filename.lower().endswith(extension):
            filename += extension
    else:
        output_type = mime_type
        request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    try:
        while not done:
            _, done = downloader.next_chunk()
    except HttpError as exc:
        raise StaffDriveOperationError("Google Drive could not download this file.") from exc
    buffer.seek(0)
    return buffer, filename, output_type, item


def list_folder_tree(service, root_id, limit=500):
    result = []
    queue = [(root_id, "")]
    seen = set()
    while queue and len(result) < limit:
        parent_id, prefix = queue.pop(0)
        if parent_id in seen:
            continue
        seen.add(parent_id)
        folders, token = list_items(service, parent_id, page_size=100)
        while True:
            for folder in folders:
                if folder.get("mimeType") != FOLDER_MIME_TYPE:
                    continue
                label = f"{prefix}{folder['name']}"
                result.append((folder["id"], label))
                queue.append((folder["id"], f"{label} / "))
                if len(result) >= limit:
                    break
            if not token or len(result) >= limit:
                break
            folders, token = list_items(service, parent_id, page_token=token, page_size=100)
    return result


def record_audit(actor, member, action, item, **details):
    return StaffDriveAudit.objects.create(
        actor=actor,
        member=member,
        action=action,
        file_id=item["id"],
        file_name=item.get("name", ""),
        details=details,
    )
