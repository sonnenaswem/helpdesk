# =======================
# DJANGO / DRF
# =======================
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Avg
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework import viewsets, permissions, generics
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet


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
    Application,
    ProgramApplication,
    YouthHubCategory,
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
    ApplicationSerializer,
    ProgramApplicationSerializer,
    YouthHubCategorySerializer,
)


def home(request):
    return JsonResponse({"message": "Welcome to Benue Youth HelpDesk"})


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

class YouthHubListView(generics.ListAPIView):
    queryset = YouthHubCategory.objects.filter(is_active=True)
    serializer_class = YouthHubCategorySerializer
    

class ApplicationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAdminUser])
    def download_cv(self, request, pk=None):
        application = self.get_object()
        if not application.cv:
            return Response({"error": "No CV uploaded"}, status=404)

        return Response({"cv_url": application.cv.url})



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


class ProgramApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = ProgramApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.role in ["officer", "admin", "superadmin"]:
            return ProgramApplication.objects.all()

        return ProgramApplication.objects.filter(user=user)

    def create(self, request, *args, **kwargs):
        user = request.user

        
        if not hasattr(user, "youth_profile"):
            return Response(
                {"detail": "Complete your profile before applying."},
                status=400,
            )

        profile = user.youth_profile

        
        if not profile.is_age_eligible():
            return Response(
                {"detail": "Only youths between 15 and 40 years can apply."},
                status=403,
            )

        program_id = request.data.get("program_id")

        if not program_id:
            return Response(
                {"detail": "Program ID is required."},
                status=400,
            )

        application, created = ProgramApplication.objects.get_or_create(
            user=user,
            program_id=program_id,
        )

        if not created:
            return Response(
                {"detail": "You have already applied for this program."},
                status=400,
            )

        return Response(
            {"detail": "Application submitted successfully."},
            status=201,
        )

    def get_permissions(self):
        if self.action in ["update", "partial_update"]:
            return [IsOfficer()]
        return [IsAuthenticated()]


    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        if request.user.role not in ["officer", "admin", "superadmin"]:
            return Response({"detail": "Forbidden"}, status=403)

        application = self.get_object()
        application.status = "approved"
        application.save()

        return Response({"status": "approved"})

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        if request.user.role not in ["officer", "admin", "superadmin"]:
            return Response({"detail": "Forbidden"}, status=403)

        application = self.get_object()
        application.status = "rejected"
        application.save()

        return Response({"status": "rejected"})


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
