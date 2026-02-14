from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
import debug_toolbar

from django.conf import settings
from django.conf.urls.static import static

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

# =========================
# API MODULE IMPORTS
# =========================
from backend.core.api import auth_views, dashboard_views, export_views
from backend.core.api.ticket_views import TicketViewSet
from backend.core.api.profile_views import update_profile
from backend.core.api.profile_views import my_youth_profile
# =========================
# VIEWSETS (NON-TICKET)
# =========================
from backend.core.views import (
    home,
    UserViewSet,
    KnowledgeBaseViewSet,
    FeedbackViewSet,
    NotificationViewSet,
    TicketNoteViewSet,
    PollViewSet,
    ProgramViewSet,
    WorkflowViewSet,
    MinistryInfoViewSet,
    YouthProfileViewSet,
    DocumentUploadViewSet,
    ApplicationViewSet,
    ProgramApplicationViewSet,
    YouthHubListView,
)

# =========================
# ROUTER
# =========================
router = DefaultRouter()
router.register("users", UserViewSet, basename="users")
router.register("tickets", TicketViewSet, basename="tickets")
router.register("knowledgebase", KnowledgeBaseViewSet, basename="knowledgebase")
router.register("feedback", FeedbackViewSet, basename="feedback")
router.register("notifications", NotificationViewSet, basename="notifications")
router.register("ticketnotes", TicketNoteViewSet, basename="ticketnotes")
router.register("polls", PollViewSet, basename="polls")
router.register("programs", ProgramViewSet, basename="programs")
router.register("workflows", WorkflowViewSet, basename="workflows")
router.register("ministry", MinistryInfoViewSet, basename="ministry")
router.register("youth-profile", YouthProfileViewSet, basename="youth-profile")
router.register("documents", DocumentUploadViewSet, basename="documents")
router.register(r'applications', ApplicationViewSet, basename='application')
router.register("program-applications", ProgramApplicationViewSet, basename="program-application")
# =========================
# URLS
# =========================
urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),

    # ---------- AUTH ----------
    path("api/login/", auth_views.login_view),
    path("api/register/", auth_views.register_user),
    path("api/onboard/", auth_views.onboard_youth),
    path("api/verify-account/", auth_views.verify_account),
    path("api/resend-verification/", auth_views.resend_verification),
    path("api/complete-profile/", auth_views.complete_profile),
    path("api/current-user/", auth_views.current_user),
    



    # ---------- JWT ----------
    path("api/token/", TokenObtainPairView.as_view()),
    path("api/token/refresh/", TokenRefreshView.as_view()),
    path("youth-hub/", YouthHubListView.as_view()),

    # ---------- DASHBOARD ----------
    path("api/dashboard/", dashboard_views.dashboard_report),
    path("youth-profile/me/", my_youth_profile),
    # ---------- EXPORTS ----------
    path("api/tickets/export/csv/", export_views.export_tickets_csv),
    path("api/tickets/export/pdf/", export_views.export_tickets_pdf),
    path("profile/update/", update_profile),
    # ---------- ROUTER ----------
    path("api/", include(router.urls)),

    # ---------- DEBUG ----------
    path("__debug__/", include(debug_toolbar.urls)),
    path("", include("django_prometheus.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
