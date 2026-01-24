from .models import User, Ticket, KnowledgeBase, Feedback, Notification, TicketNote, Poll, PollOption, AuditLog, MinistryInfo, Program, Workflow, EscalationMatrix, YouthProfile, DocumentUpload, TicketMessage
from datetime import datetime
from .serializers import UserSerializer, TicketSerializer, KnowledgeBaseSerializer, FeedbackSerializer, NotificationSerializer, TicketNoteSerializer, PollSerializer, MinistryInfoSerializer, ProgramSerializer, WorkflowSerializer, YouthProfileSerializer, DocumentUploadSerializer, TicketMessageSerializer

from rest_framework import viewsets, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import status as drf_status

from django.contrib.auth import get_user_model
User = get_user_model()

from .permissions import IsOfficer

from django.contrib.auth.hashers import make_password
from django.db import IntegrityError, models
from django.contrib.auth import get_user_model, authenticate

from django.db.models.functions import TruncMonth
from django.http import JsonResponse, HttpResponse 
from django.db.models import Avg, Count, Q
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
import csv
from reportlab.pdfgen import canvas
from django.utils import timezone
from .models import Ticket
from backend.core.permissions import IsAdmin, IsOfficer, IsYouth
# from backend.core.task import send_notification, log_audit 
# from notifications.utils import send_sms, send_whatsapp
from backend.core.notifications.utils import send_whatsapp_doubletick, send_sms_africastalking

def auto_assign_officer():
        return (
            User.objects
            .filter(role="officer", is_active=True)
            .annotate(
                workload=Count(
                    "assigned_tickets",
                    filter=Q(
                        assigned_tickets__status__in=["open", "in_progress"]
                    )
                )
            )
            .order_by("workload")
            .first()
        )


def escalate_ticket(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    ticket.escalation_level += 1
    ticket.save()

    message = f"Your ticket '{ticket.title}' has been escalated to Level {ticket.escalation_level}."
    
    if ticket.youth.phone:
        send_whatsapp_doubletick(ticket.youth.phone, message)
        send_sms_africastalking(ticket.youth.phone, message)

    return JsonResponse({"message": f"Ticket {ticket.id} escalated"})



def home(request):
    return JsonResponse({"message": "Welcome to Benue Youth HelpDesk"})

class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return User.objects.all()
        else:
            return User.objects.filter(id=user.id)  # non-admins only see themselves

class KnowledgeBaseViewSet(viewsets.ModelViewSet):
    queryset = KnowledgeBase.objects.all()
    serializer_class = KnowledgeBaseSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @method_decorator(cache_page(60*5))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        # Youth can see all resources, officers/admins can manage them
        return KnowledgeBase.objects.all()

    def perform_create(self, serializer):
        if self.request.user.role == 'admin':
            serializer.save()
        else:
            raise PermissionDenied("Only admins can add resources.")


class FeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Youth can only submit feedback for their own tickets
        serializer.save(youth=self.request.user)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def stats(self, request):
        avg_rating = Feedback.objects.aggregate(Avg('rating'))['rating__avg']
        total_feedback = Feedback.objects.count()

        return Response({
            "average_rating": avg_rating,
            "total_feedback": total_feedback
        })

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Each user only sees their own notifications
        return Notification.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class TicketNoteViewSet(viewsets.ModelViewSet):
    queryset = TicketNote.objects.all()
    serializer_class = TicketNoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return TicketNote.objects.all()
        elif user.role == 'officer':
            return TicketNote.objects.filter(author=user)
        else:
            return TicketNote.objects.none()  # Youth can't view internal notes

class MinistryInfoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MinistryInfo.objects.all().order_by("-created_at")
    serializer_class = MinistryInfoSerializer
    permission_classes = [permissions.AllowAny]


class ProgramViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Program.objects.all().order_by("-created_at")
    serializer_class = ProgramSerializer
    permission_classes = [permissions.AllowAny]


class WorkflowViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Workflow.objects.all().order_by("name")
    serializer_class = WorkflowSerializer
    permission_classes = [permissions.AllowAny]


class YouthProfileViewSet(viewsets.ModelViewSet):
    queryset = YouthProfile.objects.all()
    serializer_class = YouthProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["get", "put", "patch"], permission_classes=[permissions.IsAuthenticated], url_path="me")
    def me(self, request):
        profile = get_object_or_404(YouthProfile, user=request.user)
        if request.method == "GET":
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        elif request.method in ["PUT", "PATCH"]:
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        

class DocumentUploadViewSet(viewsets.ModelViewSet):
    queryset = DocumentUpload.objects.all()
    serializer_class = DocumentUploadSerializer
    parser_classes = [MultiPartParser]
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Ensure uploaded docs bind to the requester’s profile
        profile = get_object_or_404(YouthProfile, user=self.request.user)
        serializer.save(profile=profile)

class PollViewSet(viewsets.ModelViewSet):
    queryset = Poll.objects.all()
    serializer_class = PollSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        if self.request.user.role == 'admin':
            serializer.save(created_by=self.request.user)
        else:
            raise PermissionDenied("Only admins can create polls.")

    @action(detail=True, methods=['post'])
    def vote(self, request, pk=None):
        poll = self.get_object()
        option_id = request.data.get('option_id')
        try:
            option = poll.options.get(id=option_id)
            option.votes += 1
            option.save()
            return Response({'message': 'Vote recorded'})
        except PollOption.DoesNotExist:
            return Response({'error': 'Invalid option'}, status=400)

class OfficerInboxView(APIView):
    permission_classes = [IsOfficer]

    def get(self, request):
        messages = TicketMessage.objects.filter(
            ticket__officer=request.user
        ).order_by("-created_at")

        serializer = TicketMessageSerializer(messages, many=True)
        return Response(serializer.data)



class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    queryset = Ticket.objects.select_related(
        "youth", "officer"
    ).order_by("-created_at")

    # =========================
    # ROLE-BASED VISIBILITY
    # =========================
    def get_queryset(self):
        user = self.request.user

        if user.role == "admin":
            return self.queryset

        # Officer sees ONLY assigned tickets (no more confusion)
        if user.role == "officer":
            return self.queryset.filter(officer=user)

        # Youth sees own tickets
        return self.queryset.filter(youth=user)

    # =========================
    # CREATE TICKET (YOUTH)
    # =========================
    def perform_create(self, serializer):
        officer = auto_assign_officer()

        ticket = serializer.save(
            youth=self.request.user,
            status="open",
            escalation_level=1,
            officer=officer,
        )

        if officer:
            Notification.objects.create(
                user=officer,
                message=f"New ticket assigned: {ticket.title}"
            )
    
    # =========================
    # ADMIN: VIEW UNASSIGNED
    # =========================
    @action(detail=False, methods=["get"], url_path="unassigned")
    def unassigned_tickets(self, request):
        if request.user.role != "admin":
            return Response(
                {"detail": "Not allowed"},
                status=status.HTTP_403_FORBIDDEN,
            )

        tickets = self.queryset.filter(officer__isnull=True)
        serializer = self.get_serializer(tickets, many=True)
        return Response(serializer.data)

   
            
    @action(detail=True, methods=["get", "post"], permission_classes=[IsAuthenticated])
    def messages(self, request, pk=None):
        ticket = self.get_object()
        if request.method == "POST":
            if request.user.role == "officer" and ticket.officer != request.user:
                return Response(
                    {"detail": "You cannot message this ticket"},
                    status=status.HTTP_403_FORBIDDEN
                )

            serializer = TicketMessageSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            message = TicketMessage.objects.create(
                ticket=ticket,
                sender=request.user,
                message=serializer.validated_data["message"],
            )

            return Response(
                TicketMessageSerializer(message).data,
                status=status.HTTP_201_CREATED
            )

        # GET messages
        messages = ticket.messages.select_related("sender").order_by("created_at")
        serializer = TicketMessageSerializer(messages, many=True)
        return Response(serializer.data)


    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def add_note(self, request, pk=None):
        ticket = self.get_object()

        if request.user.role not in ["admin", "officer"]:
            return Response(
                {"detail": "Not allowed"},
                status=status.HTTP_403_FORBIDDEN,
            )
            
        serializer = TicketNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save(
            ticket=ticket,
            author=request.user
        )

        return Response(serializer.data, status=201)


    
    # =========================
    # ADMIN: REASSIGN OFFICER
    # =========================
    @action(detail=True, methods=["post"], url_path="reassign")
    def reassign_officer(self, request, pk=None):
        if request.user.role != "admin":
            return Response(
                {"detail": "Admin only"},
                status=status.HTTP_403_FORBIDDEN,
            )

        ticket = self.get_object()
        identifier = request.data.get("officer")

        if not identifier:
            return Response(
                {"detail": "Officer username or ID is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if str(identifier).isdigit():
                officer = User.objects.get(
                    id=int(identifier), role="officer"
                )
            else:
                officer = User.objects.get(
                    username=identifier, role="officer"
                )
        except User.DoesNotExist:
            return Response(
                {"detail": "Officer not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        ticket.officer = officer
        ticket.status = "in_progress"
        ticket.save()

        # send_notification.delay(
        #     ticket.youth.id,
        #     f"Your ticket '{ticket.title}' has been reassigned."
        # )

        # log_audit.delay(
        #     request.user.id,
        #     f"Reassigned ticket {ticket.id} to {officer.username}"
        # )

        return Response(
            TicketSerializer(ticket).data,
            status=status.HTTP_200_OK,
        )

    # =========================
    # UPDATE STATUS (ADMIN / OFFICER)
    # =========================
    @action(
        detail=True,
        methods=["patch"],
        url_path="update-status",
        permission_classes=[IsAuthenticated],
    )
    def update_status(self, request, pk=None):
        ticket = self.get_object()
        user = request.user

        # Officers can only update their own tickets
        if user.role == "officer" and ticket.officer != user:
            return Response(
                {"detail": "You cannot update this ticket"},
                status=status.HTTP_403_FORBIDDEN,
            )

        new_status = request.data.get("status")

        if new_status not in ["open", "in_progress", "resolved"]:
            return Response(
                {"detail": "Invalid status"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ticket.status = new_status
        ticket.save()

    
        # send_notification.delay(
        #     ticket.youth.id,
        #     f"Your ticket '{ticket.title}' status changed to {new_status}"
        # )

        # log_audit.delay(
        #     request.user.id,
        #     f"Updated ticket {ticket.id} status to {new_status}"
        # )

        return Response(
            {"message": f"Ticket status updated to {new_status}"},
            status=status.HTTP_200_OK,
        )

    # =========================
    # ADMIN DASHBOARD STATS
    # =========================
    @action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAdminUser],
    )
    def stats(self, request):
        return Response({
            "total_tickets": Ticket.objects.count(),
            "open_tickets": Ticket.objects.filter(status="open").count(),
            "in_progress_tickets": Ticket.objects.filter(status="in_progress").count(),
            "resolved_tickets": Ticket.objects.filter(status="resolved").count(),
        })


class OfficerTicketViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Ticket.objects.filter(officer=user).order_by("-created_at")


@api_view(['GET'])
def list_programs(request):
    programs = Program.objects.all()
    serializer = ProgramSerializer(programs, many=True)
    return Response({"results": serializer.data})

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmin])
def dashboard_report(request):
    
    # Ticket stats
    total_tickets = Ticket.objects.count()
    open_tickets = Ticket.objects.filter(status='open').count()
    in_progress_tickets = Ticket.objects.filter(status='in_progress').count()
    resolved_tickets = Ticket.objects.filter(status='resolved').count()

    # SLA breaches 
    sla_breaches = Ticket.objects.filter(
        status__in=["open", "in_progress"],
        sla_deadline__lt=now()
    ).update(escalation_level=2)

    # Escalation levels
    escalation_stats = {
        "L1": Ticket.objects.filter(escalation_level=1).count(),
        "L2": Ticket.objects.filter(escalation_level=2).count(),
        "L3": Ticket.objects.filter(escalation_level=3).count(),
    }

    # Regional breakdown (tickets by LGA)
    lga_distribution = (
        Ticket.objects.values('youth__lga')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # Officer performance (tickets per officer)
    officer_performance = (
        Ticket.objects.values('officer__username')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # Tickets per Month
    monthly_counts = (
        Ticket.objects.annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    # Feedback stats
    avg_rating = Feedback.objects.aggregate(Avg('rating'))['rating__avg']
    total_feedback = Feedback.objects.count()

    return Response({
        "tickets": {
            "total": total_tickets,
            "open": open_tickets,
            "in_progress": in_progress_tickets,
            "resolved": resolved_tickets,
            "sla_breaches": sla_breaches,
            "escalation": escalation_stats,
            "lga_distribution": list(lga_distribution),
            "officer_performance": list(officer_performance),  
            "tickets_per_month": list(monthly_counts),         
        },
        "feedback": {
            "average_rating": avg_rating,
            "total_feedback": total_feedback,
        }
    })

# Existing dashboard_report stays above this

# Helper to filter tickets based on query parameters
def get_filtered_tickets(request):
    qs = Ticket.objects.all()

    # Query params
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    status = request.GET.get("status")
    category = request.GET.get("category")

    # ✅ Date validation
    def parse_date(date_str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    start_date_obj = parse_date(start_date)
    end_date_obj = parse_date(end_date)

    if start_date_obj:
        qs = qs.filter(created_at__date__gte=start_date_obj)
    if end_date_obj:
        qs = qs.filter(created_at__date__lte=end_date_obj)

    # ✅ Status validation
    valid_statuses = ["open", "in_progress", "resolved"]
    if status in valid_statuses:
        qs = qs.filter(status=status)

    # ✅ Category validation
    valid_categories = ["grants", "training", "startup", "incident"]
    if category in valid_categories:
        qs = qs.filter(category=category)

    return qs


# CSV Export with filters
def export_tickets_csv(request):
    tickets = get_filtered_tickets(request)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="tickets_report.csv"'

    writer = csv.writer(response)
    writer.writerow(["ID", "Title", "Category", "Status", "Youth", "Officer", "Escalation", "Deadline"])

    for t in tickets:
        writer.writerow([
            t.id,
            t.title,
            t.category,
            t.status,
            t.youth.username if t.youth else "",
            t.officer.username if t.officer else "",
            t.escalation_level,
            t.deadline,
        ])

    return response

# PDF Export with filters
def export_tickets_pdf(request):
    tickets = get_filtered_tickets(request)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="tickets_report.pdf"'

    p = canvas.Canvas(response)
    p.setFont("Helvetica", 12)
    p.drawString(100, 800, "Tickets Report")

    y = 780
    for t in tickets:
        line = f"{t.id} | {t.title} | {t.category} | {t.status} | {t.deadline}"
        p.drawString(100, y, line)
        y -= 20

        # Prevent writing off the page
        if y < 50:
            p.showPage()
            p.setFont("Helvetica", 12)
            y = 800

    p.showPage()
    p.save()
    return response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    user = request.user
    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": getattr(user, "role", "youth")  # fallback if no role field
    })



# Admin-only: Register officers/admins

@api_view(["POST"])
@permission_classes([IsAdminUser])  # ✅ Only admins can access
def register_user(request):
    data = request.data
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")
    role = data.get("role")

    # Validate required fields
    if not username or not password or not role:
        return Response({"error": "Username, password, and role are required."}, status=400)

    if role not in ["officer", "admin"]:
        return Response({"error": "Invalid role. Must be 'officer' or 'admin'."}, status=400)

    if User.objects.filter(username=username).exists():
        return Response({"error": "Username already exists."}, status=400)

    try:
        user = User.objects.create_user(username=username, password=password, email=email)
        if hasattr(user, "role"):
            user.role = role
            user.save()
        return Response({"message": "User created successfully."}, status=status.HTTP_201_CREATED)
    except IntegrityError:
        return Response({"error": "Username already exists."}, status=400)



# Youth-only: Onboarding to create profile

@api_view(["POST"])
@permission_classes([permissions.AllowAny])  # youths are new, not logged in yet
def onboard_youth(request):
    data = request.data

    # Required fields for account creation
    required_fields = ["username", "password", "email", "first_name", "surname", "age", "lga", "address", "phone_number"]
    for field in required_fields:
        if field not in data or not data[field]:
            return Response({field: "This field is required."}, status=status.HTTP_400_BAD_REQUEST)

    # Prevent duplicate usernames
    if User.objects.filter(username=data["username"]).exists():
        return Response({"error": "Username already exists."}, status=400)

    # Create the User
    user = User.objects.create_user(
        username=data["username"],
        password=data["password"],
        email=data["email"],
        role="youth"
    )

    # Create the linked YouthProfile
    profile = YouthProfile.objects.create(
        user=user,
        first_name=data["first_name"],
        middle_name=data.get("middle_name", ""),
        surname=data["surname"],
        age=data["age"],
        lga=data["lga"],
        address=data["address"],
        email=data["email"],
        phone_number=data["phone_number"],
        nin=data.get("nin", ""),
        academic_qualifications=data.get("academic_qualifications", ""),
        area_of_interest=data.get("area_of_interest", "")
    )

    # Generate verification link
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    verify_url = f"{request.scheme}://{request.get_host()}/verify-email/{uid}/{token}/"

    # Send email
    send_mail(
        subject="Verify your email - Benue Youth HelpDesk",
        message=f"Welcome! Please click the link to verify your email: {verify_url}",
        from_email="noreply@benuehelpdesk.ng",
        recipient_list=[user.email],
    )

    serializer = YouthProfileSerializer(profile)
    return Response(
        {"detail": "Account created. Please check your email to verify.", "profile": serializer.data},
        status=status.HTTP_201_CREATED
    )

@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def verify_email(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_verified = True
        user.save()
        return Response({"detail": "Email verified successfully. You can now log in."})
    else:
        return Response({"detail": "Invalid or expired verification link."}, status=400)


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get("username")
    password = request.data.get("password")

    user = authenticate(username=username, password=password)

    if user is None:
        return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

    if not user.is_verified:
        return Response({"detail": "Please verify your email before logging in."}, status=status.HTTP_403_FORBIDDEN)

    # ✅ Issue JWT tokens only if verified
    refresh = RefreshToken.for_user(user)
    return Response({
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsYouth])
def my_tickets(request):
    tickets = Ticket.objects.filter(youth=request.user)
    serializer = TicketSerializer(tickets, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsOfficer])
def officer_tickets(request):
    tickets = Ticket.objects.filter(officer=request.user)
    serializer = TicketSerializer(tickets, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def admin_tickets(request):
    tickets = Ticket.objects.all()
    serializer = TicketSerializer(tickets, many=True)
    return Response(serializer.data)

