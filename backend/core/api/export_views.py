from django.http import HttpResponse
from datetime import datetime
import csv

from reportlab.pdfgen import canvas

from backend.core.models import Ticket

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


# Helper to filter tickets based on query parameters
def get_filtered_tickets(request):
    qs = Ticket.objects.all()

    # Query params
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    status = request.GET.get("status")
    category = request.GET.get("category")

    # Date validation
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

    # Status validation
    valid_statuses = ["open", "in_progress", "resolved"]
    if status in valid_statuses:
        qs = qs.filter(status=status)

    # Category validation
    valid_categories = ["grants", "training", "startup", "incident"]
    if category in valid_categories:
        qs = qs.filter(category=category)

    return qs