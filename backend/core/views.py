# =======================
# DJANGO / DRF
# =======================
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Avg
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework import viewsets, permissions
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser

# =======================
# LOCAL
# =======================
from .models import (
    User,
    KnowledgeBase,
    Feedback,
    Notification,
    TicketNote,
    Poll,
    PollOption,
    MinistryInfo,
    Program,
    Workflow,
    YouthProfile,
    DocumentUpload,
)

from .serializers import (
    UserSerializer,
    KnowledgeBaseSerializer,
    FeedbackSerializer,
    NotificationSerializer,
    TicketNoteSerializer,
    PollSerializer,
    MinistryInfoSerializer,
    ProgramSerializer,
    WorkflowSerializer,
    YouthProfileSerializer,
    DocumentUploadSerializer,
)

# =======================
# BASIC VIEW
# =======================
def home(request):
    return JsonResponse({"message": "Welcome to Benue Youth HelpDesk"})

# =======================
# VIEWSETS
# =======================
class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return User.objects.all() if self.request.user.role == "admin" else User.objects.filter(id=self.request.user.id)

class KnowledgeBaseViewSet(viewsets.ModelViewSet):
    queryset = KnowledgeBase.objects.all()
    serializer_class = KnowledgeBaseSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @method_decorator(cache_page(60 * 5))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

class FeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(youth=self.request.user)

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

class TicketNoteViewSet(viewsets.ModelViewSet):
    queryset = TicketNote.objects.all()
    serializer_class = TicketNoteSerializer
    permission_classes = [permissions.IsAuthenticated]

class MinistryInfoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MinistryInfo.objects.all()
    serializer_class = MinistryInfoSerializer
    permission_classes = [permissions.AllowAny]

class ProgramViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Program.objects.all()
    serializer_class = ProgramSerializer
    permission_classes = [permissions.AllowAny]

class WorkflowViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Workflow.objects.all()
    serializer_class = WorkflowSerializer
    permission_classes = [permissions.AllowAny]

class YouthProfileViewSet(viewsets.ModelViewSet):
    serializer_class = YouthProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return YouthProfile.objects.filter(user=self.request.user)

    @action(
        detail=False,
        methods=["get", "patch", "put"],
        permission_classes=[permissions.IsAuthenticated],
        url_path="me",
    )
    def me(self, request):
        profile, created = YouthProfile.objects.get_or_create(
            user=request.user,
            defaults={
                "full_name": request.user.get_full_name() or request.user.username,
                "email": request.user.email,
                "phone": request.user.phone if hasattr(request.user, "phone") else "",
            },
        )

        if request.method == "GET":
            serializer = self.get_serializer(profile)
            return Response(serializer.data)

        serializer = self.get_serializer(
            profile, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class DocumentUploadViewSet(viewsets.ModelViewSet):
    queryset = DocumentUpload.objects.all()
    serializer_class = DocumentUploadSerializer
    parser_classes = [MultiPartParser]
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        profile = get_object_or_404(YouthProfile, user=self.request.user)
        serializer.save(profile=profile)

class PollViewSet(viewsets.ModelViewSet):
    queryset = Poll.objects.all()
    serializer_class = PollSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=["post"])
    def vote(self, request, pk=None):
        poll = self.get_object()
        option = poll.options.get(id=request.data.get("option_id"))
        option.votes += 1
        option.save()
        return Response({"message": "Vote recorded"})
