import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from backend.core.models import Ticket

class Command(BaseCommand):
    help = "Seed the database with officers, youths, and tickets for testing"

    def handle(self, *args, **kwargs):
        User = get_user_model()

        # Create officers
        officers = []
        for i in range(3):
            officer, _ = User.objects.get_or_create(
                username=f"officer{i+1}",
                defaults={"role": "officer", "password": "dummy123"}
            )
            officers.append(officer)

        # Create youths
        lgas = ["Makurdi", "Gboko", "Otukpo", "Vandeikya"]
        youths = []
        for i in range(5):
            youth, _ = User.objects.get_or_create(
                username=f"youth{i+1}",
                defaults={"role": "youth", "lga": random.choice(lgas), "password": "dummy123"}
            )
            youths.append(youth)

        # Create tickets across months
        statuses = ["open", "in_progress", "resolved"]
        for month_offset in range(6):  # last 6 months
            for _ in range(random.randint(3, 8)):  # 3–8 tickets per month
                Ticket.objects.create(
                    title=f"Test Ticket {random.randint(100,999)}",
                    description="Auto-generated test ticket",
                    category="General",
                    status=random.choice(statuses),
                    officer=random.choice(officers),
                    youth=random.choice(youths),
                    created_at=timezone.now() - timezone.timedelta(days=30*month_offset)
                )

        self.stdout.write(self.style.SUCCESS("✅ Seeded officers, youths, and tickets successfully!"))
        