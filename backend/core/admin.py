from django.contrib import admin 
from .models import User, Ticket, KnowledgeBase, Feedback, TicketNote, MinistryInfo, OfficerRole, Program, Workflow, EscalationMatrix, YouthProfile


admin.site.register(User)
admin.site.register(Ticket)
admin.site.register(KnowledgeBase)
admin.site.register(Feedback)
admin.site.register(TicketNote)
admin.site.register(YouthProfile)


@admin.register(MinistryInfo)
class MinistryInfoAdmin(admin.ModelAdmin):
    list_display = ("name", "office_address", "contacts", "working_hours", "created_at")
    search_fields = ("name", "office_address", "contacts")


@admin.register(OfficerRole)
class OfficerRoleAdmin(admin.ModelAdmin):
    list_display = ("role", "ministry", "responsibility")
    list_filter = ("ministry",)
    search_fields = ("role", "responsibility")


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("title", "target_beneficiaries", "eligibility_criteria", "workflows", "timelines", "created_at")
    search_fields = ("title", "description", "eligibility_criteria", "target_beneficiaries")


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ("name", "sla_hours", "owner_role")
    search_fields = ("name", "owner_role")


@admin.register(EscalationMatrix)
class EscalationMatrixAdmin(admin.ModelAdmin):
    list_display = ("workflow", "level", "target_role", "condition_note")
    list_filter = ("workflow", "level")
    search_fields = ("target_role", "condition_note")

