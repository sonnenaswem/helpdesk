from django.core.mail import send_mail
from django.conf import settings


def send_email_verification(email, code):
    subject = "Verify your Benue Youth HelpDesk account"
    message = (
        "Welcome to Benue Youth HelpDesk.\n\n"
        f"Your verification code is: {code}\n\n"
        "If you did not create this account, please ignore this email."
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )