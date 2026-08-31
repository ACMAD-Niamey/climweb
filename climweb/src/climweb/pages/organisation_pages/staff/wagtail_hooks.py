from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from . import views


@hooks.register("register_admin_urls")
def staff_admin_urls():
    return [
        path("staff-profiles/", views.dashboard, name="staff_profile_dashboard"),
        path("staff-profiles/add/", views.create_member, name="staff_profile_create"),
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
