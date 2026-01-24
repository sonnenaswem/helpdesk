from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from rest_framework.routers import DefaultRouter
import debug_toolbar
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from backend.core import views

from backend.core.views import (
    current_user,
    onboard_youth,
    register_user,
    UserViewSet,
    TicketViewSet,
    KnowledgeBaseViewSet,
    FeedbackViewSet,
    NotificationViewSet,
    TicketNoteViewSet,
    PollViewSet,
    MinistryInfoViewSet,
    ProgramViewSet,
    WorkflowViewSet,
    dashboard_report,
    home,
    export_tickets_csv,
    export_tickets_pdf,
    escalate_ticket,
    YouthProfileViewSet,
    DocumentUploadViewSet,
    list_programs,
    
    OfficerTicketViewSet,
    OfficerInboxView,   
   
)


# DRF router for ViewSets
router = routers.DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'tickets', TicketViewSet, basename='ticket')
router.register(r'knowledgebase', KnowledgeBaseViewSet, basename='knowledgebase')
router.register(r'feedback', FeedbackViewSet, basename='feedback')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'ticketnotes', TicketNoteViewSet, basename='ticketnote')
router.register(r'polls', PollViewSet, basename='poll')
router.register(r'ministry', MinistryInfoViewSet, basename='ministry')
router.register(r'programs', ProgramViewSet, basename='programs')
router.register(r'workflows', WorkflowViewSet, basename='workflows')
router.register(r'documents', DocumentUploadViewSet, basename='documents')
router.register(r"youth-profile", YouthProfileViewSet, basename="youth-profile") 

router.register(r"officer-tickets", OfficerTicketViewSet, basename="officer-tickets")


urlpatterns = [
    # Home and admin
    path('', home, name="home"),
    path('admin/', admin.site.urls),
    
    # Explicit user endpoints
    path("api/current_user/", views.current_user, name="current-user"),
    path("api/onboard/", onboard_youth, name="onboard_youth"),
    path("api/register/", register_user, name='register_user'),
    path("api/youth-profile/me/", YouthProfileViewSet.as_view({"get": "me", "patch": "me"})),
    path("api/documents/", DocumentUploadViewSet.as_view({"post": "create"})),
    # path("api/tickets/<int:ticket_id>/messages/", views.add_ticket_message, name="add_ticket_message"),


    path('api/', include(router.urls)),
    path('api/dashboard/', dashboard_report, name="dashboard_report"),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/programs/', list_programs, name='list_programs'),

    path("officer-inbox/", OfficerInboxView.as_view()),

    # Ticket escalation
    
    path('tickets/<int:pk>/escalate/', escalate_ticket, name="escalate_ticket"),
    path("api/my-tickets/", views.my_tickets),
    path("api/officer-tickets/", views.officer_tickets),
    path("api/admin-tickets/", views.admin_tickets),

    # Export endpoints
    path('tickets/export/csv/', export_tickets_csv, name="export_tickets_csv"),
    path('tickets/export/pdf/', export_tickets_pdf, name="export_tickets_pdf"),

    # Debug and monitoring
    path('__debug__/', include(debug_toolbar.urls)),
    path('', include('django_prometheus.urls')),
]

