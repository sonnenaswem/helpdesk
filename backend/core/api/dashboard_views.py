from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.db.models import Count, Avg
from django.db.models.functions import TruncMonth
from django.utils.timezone import now

from backend.core.models import Ticket, Feedback
from backend.core.permissions import IsAdmin

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

