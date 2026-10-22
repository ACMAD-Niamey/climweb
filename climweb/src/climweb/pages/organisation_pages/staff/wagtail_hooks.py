from django.contrib.auth.models import Permission
from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from . import views


@hooks.register("register_permissions")
def staff_profile_permissions():
    """Expose the HR reviewer permission on Wagtail's group edit screen."""
    return Permission.objects.filter(
        content_type__app_label="staff",
        codename="review_staff_profiles",
    )


@hooks.register("register_admin_urls")
def staff_admin_urls():
    return [
        path("staff-profiles/", views.dashboard, name="staff_profile_dashboard"),
        path("staff-profiles/bulk-invite/", views.bulk_invite_profile_updates, name="staff_profile_bulk_invite"),
        path("staff-profiles/add/", views.create_member, name="staff_profile_create"),
        path("staff-profiles/training/assign/", views.assign_training, name="staff_training_assign"),
        path("staff-profiles/training-report/<int:report_id>/", views.review_training_report, name="staff_training_report_review"),
        path("staff-profiles/member/<int:member_id>/link-user/", views.link_user, name="staff_profile_link_user"),
        path("staff-profiles/member/<int:member_id>/edit/", views.edit_member, name="staff_profile_edit"),
        path("staff-profiles/member/<int:member_id>/offboard/", views.employment_change, {"action": "offboard"}, name="staff_profile_offboard"),
        path("staff-profiles/member/<int:member_id>/reactivate/", views.employment_change, {"action": "reactivate"}, name="staff_profile_reactivate"),
        path("staff-profiles/<int:update_id>/", views.review, name="staff_profile_review"),
    ]


class StaffProfilesMenuItem(MenuItem):
    def is_shown(self, request):
        return request.user.has_perm("staff.review_staff_profiles")


@hooks.register("register_admin_menu_item")
def staff_profiles_menu():
    return StaffProfilesMenuItem("Staff Profiles", reverse("staff_profile_dashboard"), icon_name="user", order=292)


class MyStaffProfileMenuItem(MenuItem):
    def is_shown(self, request):
        access = getattr(request.user, "staff_profile_access", None)
        return bool(access and not access.profile_only and access.member.is_current_staff)


@hooks.register("register_admin_menu_item")
def my_staff_profile_menu():
    return MyStaffProfileMenuItem("My Staff Profile", reverse("staff_portal:profile"), icon_name="user", order=293)
