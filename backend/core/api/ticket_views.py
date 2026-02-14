from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from backend.core.models import (
    Ticket,
    TicketMessage,
    Notification,
    User,

)

from backend.core.serializers import (
    TicketSerializer,
    TicketMessageSerializer,
    TicketNoteSerializer,
)
from backend.core.permissions import IsAdmin, IsOfficer 
from backend.core.notifications.utils import send_whatsapp_doubletick
from backend.core.permissions import IsYouth

def auto_assign_officer():
        """
        Assign officer with the least active workload.
        Active = open or in_progress tickets.
        """

        officers = (
            User.objects
            .filter(role="officer", is_active=True)
            .annotate(
                active_tickets=Count(
                    "assigned_tickets",
                    filter=Q(
                        assigned_tickets__status__in=["open", "in_progress"]
                    )
                )
            )
            .order_by("active_tickets", "date_joined")
        )

        return officers.first()  


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
            # SEND MESSAGE VIA WEBSOCKET
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"ticket_{ticket.id}",
                {
                    "type": "chat_message",
                    "data": {
                        "id": message.id,
                        "sender_name": message.sender.username,
                        "message": message.message,
                        "created_at": message.created_at.isoformat(),
                    },
                }
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

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated, IsYouth],
        url_path="my-tickets",
    )
    def my_tickets(self, request):
        tickets = Ticket.objects.filter(youth=request.user)
        serializer = self.get_serializer(tickets, many=True)
        return Response(serializer.data)


    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated],
        url_path="escalate",
    )
    def escalate(self, request, pk=None):
        ticket = self.get_object()
        user = request.user

        # Officers can only escalate their own tickets
        if user.role == "officer" and ticket.officer != user:
            return Response(
                {"detail": "You cannot escalate this ticket"},
                status=403,
            )
        ticket.escalation_level += 1
        ticket.status = "in_progress"
        ticket.save()

        # 🔑 LOG ESCALATION INTO THE SAME CONVERSATION
        TicketMessage.objects.create(
            ticket=ticket,
            sender=user,
            message=f"⚠️ Ticket escalated to Level {ticket.escalation_level}"
        )
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"ticket_{ticket.id}",
            {
                "type": "chat_message",
                "data": {
                    "sender_name": user.username,
                    "message": f"⚠️ Ticket escalated to Level {ticket.escalation_level}",
                    "created_at": ticket.updated_at.isoformat(),
                },
            }
        )

        # Optional notifications (fine where they are)
        if ticket.youth.phone:
            send_whatsapp_doubletick(
                ticket.youth.phone,
                f"Your ticket '{ticket.title}' has been escalated."
            )
        return Response({
            "message": "Ticket escalated",
            "escalation_level": ticket.escalation_level
        })

    
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

