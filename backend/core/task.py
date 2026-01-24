# from celery import shared_task
from django.utils import timezone
from backend.core.models import Ticket, Notification, AuditLog, User
from backend.core.notifications.utils import (
    send_whatsapp_doubletick,
    send_sms_africastalking,
    send_email,
)


def send_deadline_reminders():
    """Check tickets nearing deadline and notify youth."""
    now = timezone.now()
    upcoming_tickets = Ticket.objects.filter(
        deadline__lte=now + timezone.timedelta(hours=24),
        status__in=["open", "in_progress"]
    )

    for ticket in upcoming_tickets:
        message = f"Reminder: Your ticket '{ticket.title}' is due by {ticket.deadline}."
        
        # WhatsApp + SMS
        if ticket.youth.phone:
            send_whatsapp_doubletick(ticket.youth.phone, message)
            send_sms_africastalking(ticket.youth.phone, message)

        # Email
        if ticket.youth.email:
            send_email(ticket.youth.email, "Ticket Deadline Reminder", message)

        # Log audit
        AuditLog.objects.create(
            user=ticket.youth,
            action=f"Deadline reminder sent for ticket {ticket.id}"
        )


def send_notification(user_id, message):
    """Persist notification and deliver to user."""
    user = User.objects.get(id=user_id)
    Notification.objects.create(user=user, message=message)
    # Optionally extend: send_email / send_sms here too
    return f"Notification created for {user.username}"


def log_audit(user_id, action):
    """Write audit log entry."""
    user = User.objects.get(id=user_id)
    AuditLog.objects.create(user=user, action=action)
    return f"Audit logged: {action} by {user.username}"

# Test task (safe to keep for debugging)

def hello_world():
    return "Hello from Celery!"