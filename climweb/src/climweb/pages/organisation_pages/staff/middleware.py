from django.conf import settings
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse


class StaffPortalRestrictionMiddleware:
    """Do not expose other authenticated applications to profile-only accounts."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and hasattr(request.user, "staff_profile_access") and request.user.staff_profile_access.profile_only:
            path = request.path_info
            admin_path = getattr(settings, "ADMIN_URL_PATH", "") or ""
            admin_root = "/" + admin_path.strip("/") + "/" if admin_path else None
            if path == admin_root and request.method == "GET":
                return redirect(reverse("staff_portal:profile"))
            prefixes = ["/api/", "/auth/"]
            if admin_root:
                prefixes.append(admin_root)
            django_admin = getattr(settings, "DJANGO_ADMIN_URL_PATH", "")
            if django_admin:
                prefixes.append("/" + django_admin.strip("/") + "/")
            if any(path.rstrip("/") == prefix.rstrip("/") or path.startswith(prefix) for prefix in prefixes):
                return HttpResponseForbidden("This account can access My Profile only. Use /staff/profile/.")
        return self.get_response(request)
