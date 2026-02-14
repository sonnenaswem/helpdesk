from django.contrib.auth.models import AbstractUser 
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta, date
from django.contrib.auth import get_user_model

User = settings.AUTH_USER_MODEL


class MinistryInfo(models.Model):
    name = models.CharField(max_length=255)
    department_unit = models.CharField(max_length=255, blank=True)
    office_address = models.CharField(max_length=255, blank=True)
    contacts = models.CharField(max_length=255, blank=True)
    working_hours = models.CharField(max_length=255, blank=True)
    # Single-record control: optional
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or "Ministry Info"


class OfficerRole(models.Model):
    ministry = models.ForeignKey(MinistryInfo, on_delete=models.CASCADE, related_name="officers")
    role = models.CharField(max_length=255)
    responsibility = models.TextField(blank=True)

    def __str__(self):
        return f"{self.role}"


class Program(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    target_beneficiaries = models.CharField(max_length=255, blank=True)
    eligibility_criteria = models.CharField(max_length=255, blank=True)
    workflows = models.CharField(max_length=255, blank=True)  # e.g., "24hours"
    timelines = models.CharField(max_length=255, blank=True)  # e.g., "24hours"
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Workflow(models.Model):
    WORKFLOW_TYPE_CHOICES = [
        ("inquiry", "Inquiry Handling"),
        ("complaint", "Complaints Resolution"),
        ("application", "Applications Processing"),
    ]
    name = models.CharField(max_length=255, choices=WORKFLOW_TYPE_CHOICES, unique=True)
    description = models.TextField(blank=True)
    sla_hours = models.PositiveIntegerField(default=24)  # 24hr rule
    owner_role = models.CharField(max_length=255, blank=True)  # e.g., "State Coordinator" for inquiries

    def __str__(self):
        return self.get_name_display()


class EscalationMatrix(models.Model):
    LEVEL_CHOICES = [
        (1, "L1"),
        (2, "L2"),
        (3, "L3"),
    ]
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="escalations")
    level = models.PositiveSmallIntegerField(choices=LEVEL_CHOICES)
    target_role = models.CharField(max_length=255)  # e.g., "Case Officer", "State Coordinator"

    # escalation condition logic can be expanded later (time-based, status-based)
    condition_note = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("workflow", "level")
        ordering = ["level"]

    def __str__(self):
        return f"{self.workflow} - L{self.level} -> {self.target_role}"
    

class User(AbstractUser):
    ROLE_CHOICES = [
        ('youth', 'Youth'),
        ('officer', 'Officer'),
        ('admin', 'Admin'),
        ('superadmin', 'Super Admin'),
    ]
    first_name = models.CharField(max_length=100, blank=True, null=True)
    
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    surname = models.CharField(max_length=100, blank=True, null=True)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='youth')
    phone = models.CharField(max_length=50, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    nin = models.CharField(max_length=50, blank=True, null=True)
    lga = models.CharField(max_length=80, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    profile_complete = models.BooleanField(default=False)

    verification_code = models.CharField(max_length=6, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"

class YouthHubCategory(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    details = models.TextField()
    is_active =models.BooleanField(default=True)

    def __str__(self):
        return self.title

    
class KnowledgeBase(models.Model):
    CATEGORY_CHOICES = [
        ('faq', 'FAQ'),
        ('guide', 'Guide'),
        ('training', 'Training Material'),
        ('resource', 'Resource'),
    ]
    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='faq')
    attachment = models.FileField(upload_to='knowledgebase/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.category})"

def default_deadline():
    """Return SLA deadline 24 hours from now."""
    return timezone.now() + timedelta(hours=24)

class Ticket(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ]

    ESCALATION_LEVELS = [
        (1, "L1"),
        (2, "L2"),
        (3, "L3"),
    ]

    youth = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tickets",
        db_index=True
    )

    officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tickets",
        db_index=True
    )

    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=80)

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="open",
        db_index=True
    )

    escalation_level = models.PositiveSmallIntegerField(
        choices=ESCALATION_LEVELS,
        default=1
    )

    sla_deadline = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.sla_deadline:
            self.sla_deadline = timezone.now() + timedelta(hours=72)
        super().save(*args, **kwargs)

    def escalate(self):
        if self.escalation_level < 3:
            self.escalation_level += 1
            self.save()

    def __str__(self):
        return f"{self.title} ({self.status})"  


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    action = models.CharField(max_length=255)
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    timestamp = models.DateTimeField(auto_now_add=True)


class TicketMessage(models.Model):
    ticket = models.ForeignKey(
        "Ticket",
        on_delete=models.CASCADE,
        related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message on Ticket #{self.ticket.id}"

    
class Feedback(models.Model):
    RATING_CHOICES = [
        (1, 'Very Poor'),
        (2, 'Poor'),
        (3, 'Average'),
        (4, 'Good'),
        (5, 'Excellent'),
    ]

    youth = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedbacks')
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='feedbacks')
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback by {self.youth.username} on Ticket {self.ticket.id}"

class TicketNote(models.Model):
    ticket = models.ForeignKey(
        "Ticket",
        on_delete=models.CASCADE,
        related_name="internal_notes"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Note on Ticket #{self.ticket.id}"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message}" 

class Poll(models.Model):
    question = models.CharField(max_length=255)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question

class PollOption(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=255)
    votes = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.text} ({self.votes} votes)"
    

User = get_user_model()

from datetime import date

class YouthProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="youth_profile"
    )

    # Identity
    date_of_birth = models.DateField(null=True, blank=True)
    nin_verified = models.BooleanField(default=False)

    # Location
    state = models.CharField(max_length=100, blank=True, null=True)
    lga = models.CharField(max_length=100, blank=True, null=True)

    # Background
    academic_qualifications = models.TextField(blank=True)
    area_of_interest = models.CharField(max_length=255, blank=True)

    # Other verifications
    voter_id_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def age(self):
        """Calculate age from date_of_birth."""
        if not self.date_of_birth:
            return None

        today = date.today()
        return (
            today.year
            - self.date_of_birth.year
            - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        )

    def is_age_eligible(self):
        """Check if user falls within youth age range."""
        age = self.age()
        if age is None:
            return False
        return 15 <= age <= 40

    def __str__(self):
        return f"YouthProfile for {self.user.username}"


class Application(models.Model):
    program_id = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    cv = models.FileField(upload_to='applications/cvs/', blank=True, null=True)  # store filename or URL
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.program_id}"

class ProgramApplication(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    program_id = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "program_id")


class DocumentUpload(models.Model):
    profile = models.ForeignKey(YouthProfile, on_delete=models.CASCADE, related_name='documents')
    kind = models.CharField(max_length=50, choices=[
        ('nin_card', 'National Identification Card'),
        ('cv', 'CV'),
        ('certificate', 'Academic Qualification Certificate'),
        ('voter_card', 'Voter Card'),
    ])
    file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)