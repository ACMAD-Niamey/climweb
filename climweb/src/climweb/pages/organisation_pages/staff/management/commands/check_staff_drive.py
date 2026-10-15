from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from googleapiclient.errors import HttpError

from ...google_drive import FOLDER_MIME_TYPE, assert_within_root, get_drive_service


class Command(BaseCommand):
    help = "Verify the staff portal's Google Shared Drive credentials and configured root folder."

    def handle(self, *args, **options):
        try:
            service = get_drive_service()
            drive = service.drives().get(
                driveId=settings.GOOGLE_DRIVE_SHARED_DRIVE_ID,
                fields="id,name",
            ).execute()
            root = assert_within_root(
                service,
                settings.GOOGLE_DRIVE_ROOT_FOLDER_ID,
                settings.GOOGLE_DRIVE_ROOT_FOLDER_ID,
            )
        except HttpError as exc:
            status = getattr(getattr(exc, "resp", None), "status", None)
            if status == 404:
                raise CommandError(
                    "Google Drive verification failed: the Shared Drive was not found. "
                    "Confirm GOOGLE_DRIVE_SHARED_DRIVE_ID and add the service-account email "
                    "as a member of that Shared Drive."
                ) from exc
            if status in {401, 403}:
                raise CommandError(
                    "Google Drive verification failed: Google denied access. Confirm the Drive API "
                    "is enabled and the service account is a Shared Drive member with Content manager access."
                ) from exc
            raise CommandError("Google Drive verification failed while contacting the Drive API.") from exc
        except Exception as exc:
            raise CommandError(f"Google Drive verification failed: {exc}") from exc
        if root.get("mimeType") != FOLDER_MIME_TYPE:
            raise CommandError("The configured Google Drive root ID is not a folder.")
        self.stdout.write(self.style.SUCCESS(
            f"Google Drive is ready: Shared Drive “{drive.get('name', 'Shared Drive')}”, "
            f"root folder “{root.get('name', 'Root')}”."
        ))
