from django.contrib import admin

from .models import StaffDriveAudit, StaffDriveFolder, StaffProfileEmailLog


@admin.register(StaffDriveFolder)
class StaffDriveFolderAdmin(admin.ModelAdmin):
    list_display = ("member", "folder_id", "updated_at")
    search_fields = ("member__name", "folder_id")
    readonly_fields = ("created_at", "updated_at")


@admin.register(StaffDriveAudit)
class StaffDriveAuditAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "member", "action", "file_name")
    list_filter = ("action", "created_at")
    search_fields = ("actor__username", "member__name", "file_name", "file_id")
    readonly_fields = ("actor", "member", "action", "file_id", "file_name", "details", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StaffProfileEmailLog)
class StaffProfileEmailLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "member", "recipient", "event", "status")
    list_filter = ("event", "status", "created_at")
    search_fields = ("actor__username", "actor__email", "member__name", "recipient")
    readonly_fields = ("actor", "member", "recipient", "event", "status", "error", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
