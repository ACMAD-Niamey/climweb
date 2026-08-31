from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = "staff_portal"

urlpatterns = [
    path("login/", views.StaffLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page=reverse_lazy("staff_portal:login")), name="logout"),
    path("profile/", views.profile, name="profile"),
    path("password/", views.password_change, name="password_change"),
    path("invite/<int:access_id>/<str:token>/", views.accept_invitation, name="accept"),
    path("photo/<int:update_id>/", views.photo_preview, name="photo"),
    path("password-reset/", views.StaffPasswordResetView.as_view(), name="password_reset"),
    path("password-reset/sent/", auth_views.PasswordResetDoneView.as_view(template_name="staff/portal/password_reset_done.html"), name="password_reset_done"),
    path("password-reset/<uidb64>/<token>/", views.StaffPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
]
