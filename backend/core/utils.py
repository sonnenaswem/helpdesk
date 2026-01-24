from .models import AuditLog

def log_action(user, action, ticket=None):
    AuditLog.objects.create(
        user=user,
        action=action,
        ticket=ticket
    )
