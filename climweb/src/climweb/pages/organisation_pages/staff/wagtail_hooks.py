from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from . import views


@hooks.register("register_admin_urls")
def staff_admin_urls():
    return [
        path("staff-profiles/", views.dashboard, name="staff_profile_dashboard"),
        path("staff-profiles/<int:update_id>/", views.review, name="staff_profile_review"),
    ]


class StaffProfilesMenuItem(MenuItem):
    def is_shown(self, request):
        return request.user.has_perm("staff.review_staff_profiles")


@hooks.register("register_admin_menu_item")
def staff_profiles_menu():
    return StaffProfilesMenuItem("Staff Profiles", reverse("staff_profile_dashboard"), icon_name="user", order=292)
