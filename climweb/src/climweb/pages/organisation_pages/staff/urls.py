from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = "staff_portal"

urlpatterns = [
    path("login/", views.StaffLoginView.as_view(), name="login"),
    path("logout/", views.staff_logout, name="logout"),
    path("", views.staff_dashboard, name="dashboard"),
    path("hr/", views.staff_hr_dashboard, name="hr_dashboard"),
    path("hr/training/assign/", views.staff_hr_assign_training, name="hr_assign_training"),
    path("hr/training-report/<int:report_id>/", views.staff_hr_review_training_report, name="hr_review_training_report"),
    path("profile/", views.profile, name="profile"),
    path("training/<int:assignment_id>/report/", views.training_report, name="training_report"),
    path("training-report/document/<int:document_id>/download/", views.training_report_download, name="training_report_download"),
    path("password/", views.password_change, name="password_change"),
    path("invite/<int:access_id>/<str:token>/", views.accept_invitation, name="accept"),
    path("photo/<int:update_id>/", views.photo_preview, name="photo"),
    path("password-reset/", views.StaffPasswordResetView.as_view(), name="password_reset"),
    path("password-reset/sent/", auth_views.PasswordResetDoneView.as_view(template_name="staff/portal/password_reset_done.html"), name="password_reset_done"),
    path("password-reset/<uidb64>/<token>/", views.StaffPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
]
