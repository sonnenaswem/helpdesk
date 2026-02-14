from rest_framework import serializers
from .models import User, Ticket, KnowledgeBase, Feedback, Notification, TicketNote, Poll, PollOption, MinistryInfo, OfficerRole, Program, Workflow, EscalationMatrix, YouthProfile, DocumentUpload, TicketMessage, Application, ProgramApplication, YouthHubCategory
from django.contrib.auth import get_user_model


User = get_user_model()

class OfficerRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfficerRole
        fields = ["id", "role", "responsibility"]


class MinistryInfoSerializer(serializers.ModelSerializer):
    officers = OfficerRoleSerializer(many=True, read_only=True)

    class Meta:
        model = MinistryInfo
        fields = [
            "id", "name", "department_unit", "office_address", "contacts",
            "working_hours", "officers", "created_at"
        ]


class ProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = Program
        fields = [
            "id", "title", "description", "target_beneficiaries",
            "eligibility_criteria", "workflows", "timelines", "created_at"
        ]


class EscalationMatrixSerializer(serializers.ModelSerializer):
    class Meta:
        model = EscalationMatrix
        fields = ["id", "level", "target_role", "condition_note"]


class WorkflowSerializer(serializers.ModelSerializer):
    escalations = EscalationMatrixSerializer(many=True, read_only=True)

    class Meta:
        model = Workflow
        fields = ["id", "name", "description", "sla_hours", "owner_role", "escalations"]

class KnowledgeBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeBase
        fields = ['id', 'title', 'content', 'category', 'attachment', 'created_at']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'first_name', 'middle_name', 'surname']

class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['id', 'youth', 'ticket', 'rating', 'comment', 'created_at']
        read_only_fields = ['youth', 'created_at']

class YouthHubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = YouthHubCategory
        fields = "__all__"



class TicketMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.username", read_only=True)

    class Meta:
        model = TicketMessage
        fields = [
            "id",
            "sender_name",
            "message",
            "created_at",
        ]
        read_only_fields = ["id", "sender", "created_at"]

class TicketNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(
        source="author.username", read_only=True
    )

    class Meta:
        model = TicketNote
        fields = [
            "id",
            "author",
            "author_name",
            "note",
            "created_at",
        ]
        read_only_fields = ['author', 'created_at']


class TicketSerializer(serializers.ModelSerializer):
    youth_name = serializers.CharField(source="youth.username", read_only=True)
    officer_name = serializers.CharField(source="officer.username", read_only=True)

    messages = TicketMessageSerializer(many=True, read_only=True)
    internal_notes = TicketNoteSerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = [
            'id',
            'title',
            'description',
            'category',
            'status',
            'escalation_level',
            'sla_deadline',
            'created_at',
            'updated_at',
            'youth',
            'youth_name',
            'officer',
            'officer_name',
            "messages",
            "internal_notes",
        ]
        read_only_fields = [
            'id',
            'escalation_level',
            'sla_deadline',
            'created_at',
            'updated_at',
            'youth',
        ]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'user', 'message', 'created_at', 'is_read']
        read_only_fields = ['user', 'created_at']

class PollOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PollOption
        fields = ['id', 'text', 'votes']

class PollSerializer(serializers.ModelSerializer):
    options = PollOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Poll
        fields = ['id', 'question', 'created_by', 'created_at', 'options']
        read_only_fields = ['created_by', 'created_at']


class DocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentUpload
        fields = ['id', 'profile', 'kind', 'file', 'uploaded_at']

    def validate_kind(self, value):
        allowed = ["nin_card", "cv", "certificate", "voter_card"]
        if value not in allowed:
            raise serializers.ValidationError("Invalid document kind.")
        return value

class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = "__all__"





class ProgramApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgramApplication
        fields = [
            "id",
            "program_id",
            "user",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "user", "status", "created_at"]


class YouthProfileSerializer(serializers.ModelSerializer):
    # Pull fields from related User model
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    middle_name = serializers.CharField(source="user.middle_name", read_only=True)
    surname = serializers.CharField(source="user.surname", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    nin = serializers.CharField(source="user.nin", read_only=True)
    lga = serializers.CharField(source="user.lga", read_only=True)

    documents = DocumentUploadSerializer(many=True, read_only=True)

    
    class Meta:
        model = YouthProfile
        fields = [
            'id',

            # user-derived fields
            'first_name',
            'middle_name',
            'surname',
            'email',
            'phone',
            'nin',
            'lga',

            # profile fields
            'age',
            'address',
            'academic_qualifications',
            'area_of_interest',

            'verified_nin',
            'verified_voter_id',

            'documents',
            'created_at',
            'updated_at',
        ]

    def validate_age(self, value):
        validate_age(value)
        return value


