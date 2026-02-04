from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
import debug_toolbar

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

# =========================
# API MODULE IMPORTS
# =========================
from backend.core.api import auth_views, dashboard_views, export_views
from backend.core.api.ticket_views import TicketViewSet

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
    path("api/current-user/", auth_views.current_user),
    path("verify-email/<uidb64>/<token>/", auth_views.verify_email),

    # ---------- JWT ----------
    path("api/token/", TokenObtainPairView.as_view()),
    path("api/token/refresh/", TokenRefreshView.as_view()),

    # ---------- DASHBOARD ----------
    path("api/dashboard/", dashboard_views.dashboard_report),

    # ---------- EXPORTS ----------
    path("api/tickets/export/csv/", export_views.export_tickets_csv),
    path("api/tickets/export/pdf/", export_views.export_tickets_pdf),

    # ---------- ROUTER ----------
    path("api/", include(router.urls)),

    # ---------- DEBUG ----------
    path("__debug__/", include(debug_toolbar.urls)),
    path("", include("django_prometheus.urls")),
]
