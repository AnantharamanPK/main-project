# notices/admin.py
from django.contrib import admin
from django.utils import timezone
from django.contrib.auth import get_user_model 
from django.utils.html import format_html # Added for formatting Poll results
from django.shortcuts import redirect # Added for the Analytics redirect
from .models import Notice, NoticeReadStatus, DirectMessage, Profile, Notification, Poll, PollResponse, AnalyticsLink # Added AnalyticsLink

# ==========================================
# 1. Profile Admin (To manage departments)
# ==========================================
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'department')
    list_filter = ('department',)
    search_fields = ('user__username',)

# ==========================================
# 2. Filters and Inlines
# ==========================================
class PendingApprovalFilter(admin.SimpleListFilter):
    title = 'Approval Status'
    parameter_name = 'is_approved'

    def lookups(self, request, model_admin):
        return (
            ('pending', '⏳ Needs Review'),
            ('approved', '✅ Published'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'pending':
            return queryset.filter(is_approved=False)
        if self.value() == 'approved':
            return queryset.filter(is_approved=True)

class NoticeReadInline(admin.TabularInline):
    model = NoticeReadStatus
    extra = 0
    can_delete = False
    readonly_fields = ('user', 'read_at')
    verbose_name = "Read Receipt"
    verbose_name_plural = "Student Read Receipts"

# ==========================================
# 3. Main Notice Admin
# ==========================================
@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ('title', 'target_department', 'created_by', 'status', 'is_approved', 'get_read_count', 'deadline_status', 'created_at') 
    list_filter = (PendingApprovalFilter, 'target_department', 'status', 'is_approved', 'expires_at', 'created_at')
    search_fields = ('title', 'message')
    
    fields = ('title', 'message', 'target_department', 'created_by', 'tags', 'status', 'is_approved', 'rejection_reason', 'expires_at', 'who_has_read', 'who_has_not_read')
    readonly_fields = ('who_has_read', 'who_has_not_read')

    inlines = [NoticeReadInline]

    def get_read_count(self, obj):
        return obj.read_statuses.count()
    get_read_count.short_description = 'Read By'

    def who_has_read(self, obj):
        # Filter read statuses to show only non-staff usernames
        students = obj.read_statuses.filter(user__is_staff=False).select_related('user').all()
        if not students:
            return "No students have read this yet."
        return ", ".join([s.user.username for s in students])
    who_has_read.short_description = 'Acknowledged Students'

    def who_has_not_read(self, obj):
        User = get_user_model()
        
        # 1. Filter target students based on Notice Department
        # EXPLICITLY EXCLUDE Staff (Admin) and Superusers
        if obj.target_department == 'All':
            target_students = User.objects.filter(is_staff=False, is_superuser=False)
        else:
            target_students = User.objects.filter(
                profile__department=obj.target_department,
                is_staff=False,
                is_superuser=False
            )

        # 2. Exclude those who have already read it
        read_ids = obj.read_statuses.values_list('user_id', flat=True)
        unread_students = target_students.exclude(id__in=read_ids)

        if not unread_students.exists():
            return "✅ All targeted students have seen this notice."
        
        return ", ".join([u.username for u in unread_students])
    who_has_not_read.short_description = 'Students Who Did Not See The Notice'

    def deadline_status(self, obj):
        if obj.expires_at:
            if obj.expires_at < timezone.now():
                return "⚠️ Date Passed"
            return "✅ Active"
        return "Permanent"
    deadline_status.short_description = 'Status'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('read_statuses')

# ==========================================
# 4. Direct Messages & Notifications
# ==========================================
@admin.register(DirectMessage)
class DirectMessageAdmin(admin.ModelAdmin):
    list_display = ('student', 'admin', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at')
    search_fields = ('student__username', 'message')
    exclude = ('admin',)

    def render_change_form(self, request, context, *args, **kwargs):
        # Ensure student dropdown only shows non-staff users
        context['adminform'].form.fields['student'].queryset = get_user_model().objects.filter(is_staff=False)
        return super().render_change_form(request, context, *args, **kwargs)

    def save_model(self, request, obj, form, change):
        if not obj.pk: 
            obj.admin = request.user
        super().save_model(request, obj, form, change)

admin.site.register(Notification)

# ==========================================
# 5. Poll & Attendance Admin
# ==========================================
# ==========================================
# 5. Poll & Attendance Admin
# ==========================================
@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ('question', 'target_department', 'get_yes_count', 'get_no_count', 'is_active', 'created_at')
    list_filter = ('target_department', 'is_active', 'created_at')
    search_fields = ('question', 'description')
    
    # NEW: Added 'created_by' so it displays as plain text, not a dropdown
    readonly_fields = ('created_by', 'get_detailed_results')

    # NEW: Automatically set the logged-in admin as the creator
    def save_model(self, request, obj, form, change):
        if not obj.pk: # If this is a brand new poll being created
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_yes_count(self, obj):
        return obj.responses.filter(choice='Yes').count()
    get_yes_count.short_description = '✅ Yes'

    def get_no_count(self, obj):
        return obj.responses.filter(choice='No').count()
    get_no_count.short_description = '❌ No'

    def get_detailed_results(self, obj):
        responses = obj.responses.select_related('user').all()
        if not responses: 
            return "No responses yet."
        
        html = "<table style='width:100%; max-width: 400px; border:1px solid #ccc; text-align: left;'>"
        html += "<tr><th style='padding: 8px; border-bottom: 1px solid #ccc;'>Student</th><th style='padding: 8px; border-bottom: 1px solid #ccc;'>Response</th></tr>"
        
        for r in responses:
            color = "green" if r.choice == 'Yes' else "red"
            html += f"<tr><td style='padding: 8px; border-bottom: 1px solid #eee;'>{r.user.username}</td><td style='color:{color}; font-weight:bold; padding: 8px; border-bottom: 1px solid #eee;'>{r.choice}</td></tr>"
        
        html += "</table>"
        return format_html(html)
    get_detailed_results.short_description = "Attendance Breakdown"

admin.site.register(PollResponse)

# ==========================================
# 6. Analytics Dashboard Link (Dummy Model)
# ==========================================
@admin.register(AnalyticsLink)
class AnalyticsLinkAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        # When you click the link in the admin, instantly redirect to the analytics page
        return redirect('notices:analytics')
        
    def has_add_permission(self, request):
        # This removes the "+ Add" button so it just looks like a standard link
        return False