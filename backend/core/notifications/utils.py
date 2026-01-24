# notifications/utils.py
import os
import requests
import africastalking
from django.conf import settings
from django.core.mail import send_mail


# WhatsApp via DoubleTick
def send_whatsapp_doubletick(phone_number, message):
    try:
        url = "https://api.doubletick.io/v1/messages"
        headers = {
            "Authorization": f"Bearer {settings.DOUBLETICK_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "to": phone_number,
            "from": settings.DOUBLETICK_SENDER_ID,
            "text": message,
        }
        response = requests.post(url, json=payload, headers=headers)
        return response.json()
    except Exception as e:
        return {"error": str(e)}


# SMS via Africa’s Talking
def send_sms_africastalking(phone_number, message):
    try:
        africastalking.initialize(
            settings.AFRICASTALKING_USERNAME,
            settings.AFRICASTALKING_API_KEY
        )
        sms = africastalking.SMS
        response = sms.send(message, [phone_number])
        return response
    except Exception as e:
        return {"error": str(e)}

def send_email(recipient, subject, message):
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,  # safer than None
            [recipient],
            fail_silently=False,
        )
        return {"status": "sent", "to": recipient}
    except Exception as e:
        return {"error": str(e)}