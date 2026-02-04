from django.urls import path
from .consumers import NotificationConsumer, TicketChatConsumer

websocket_urlpatterns = [
    path("ws/notifications/", NotificationConsumer.as_asgi()),
    path("ws/tickets/<int:ticket_id>/", TicketChatConsumer.as_asgi()),
]
