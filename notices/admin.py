# notices/admin.py
import csv
from django.http import HttpResponse
from django.contrib import admin
from django.utils import timezone
from django.contrib.auth import get_user_model 
from django.utils.html import mark_safe # Using mark_safe instead of format_html
from django.shortcuts import redirect # Added for the Analytics redirect
from .models import Notice, NoticeReadStatus, DirectMessage, Profile, Notification, Poll, PollResponse, AnalyticsLink, Community # Added Community
from django.contrib.auth.admin import UserAdmin

# ==========================================
# 0. Community Admin (NEW)
# ==========================================
@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ('name', 'department')
    list_filter = ('department',)
    search_fields = ('name',)

# ==========================================
# 1. Profile Admin (To manage departments & communities)
# ==========================================
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'department', 'community') # Added community
    list_filter = ('department', 'community') # Added community
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
    # Added target_community to list_display
    list_display = ('title', 'target_department', 'target_community', 'created_by', 'status', 'is_approved', 'get_read_count', 'deadline_status', 'created_at') 
    list_filter = (PendingApprovalFilter, 'target_department', 'target_community', 'status', 'is_approved', 'expires_at', 'created_at')
    search_fields = ('title', 'message')
    
    # Added target_community to fields
    fields = ('title', 'message', 'target_department', 'target_community', 'created_by', 'tags', 'status', 'is_approved', 'rejection_reason', 'expires_at', 'who_has_read', 'who_has_not_read')
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
        
        # 1. Filter target students based on Notice Department or Community
        if obj.target_community:
            target_students = User.objects.filter(profile__community=obj.target_community, is_staff=False, is_superuser=False)
        elif obj.target_department == 'All':
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
# 5. Poll & Attendance Admin (UPGRADED)
# ==========================================

# --- NEW: EXCEL/CSV EXPORT ACTION ---
@admin.action(description="📥 Download Poll Summary Report (Excel/CSV)")
def export_poll_summary_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="Poll_Summary_Report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Poll Question', 'Target Audience', 'Student Username', 'Email', 'Department', 'Community', 'Response Status'])
    
    User = get_user_model()
    
    for poll in queryset:
        # Determine target audience
        if poll.target_community:
            target_students = User.objects.filter(profile__community=poll.target_community, is_staff=False, is_superuser=False)
            target_label = poll.target_community.name
        elif poll.target_department != 'All':
            target_students = User.objects.filter(profile__department=poll.target_department, is_staff=False, is_superuser=False)
            target_label = poll.target_department
        else:
            target_students = User.objects.filter(is_staff=False, is_superuser=False)
            target_label = "All Departments"

        # Get votes
        yes_responses = poll.responses.filter(choice='Yes').select_related('user', 'user__profile', 'user__profile__community')
        no_responses = poll.responses.filter(choice='No').select_related('user', 'user__profile', 'user__profile__community')
        
        # Calculate unreacted
        responded_ids = list(yes_responses.values_list('user_id', flat=True)) + list(no_responses.values_list('user_id', flat=True))
        unreacted_users = target_students.exclude(id__in=responded_ids).select_related('profile', 'profile__community')

        # Write Data - EMOJIS REMOVED FOR CLEAN EXCEL EXPORT
        for r in yes_responses:
            comm = r.user.profile.community.name if getattr(r.user.profile, 'community', None) else "N/A"
            writer.writerow([poll.question, target_label, r.user.username, r.user.email, r.user.profile.department, comm, 'YES'])
            
        for r in no_responses:
            comm = r.user.profile.community.name if getattr(r.user.profile, 'community', None) else "N/A"
            writer.writerow([poll.question, target_label, r.user.username, r.user.email, r.user.profile.department, comm, 'NO'])
            
        for u in unreacted_users:
            comm = u.profile.community.name if hasattr(u, 'profile') and getattr(u.profile, 'community', None) else "N/A"
            dept = u.profile.department if hasattr(u, 'profile') else "N/A"
            writer.writerow([poll.question, target_label, u.username, u.email, dept, comm, 'UNREACTED'])
            
    return response

@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    # Added target_community
    list_display = ('question', 'target_department', 'target_community', 'get_yes_count', 'get_no_count', 'is_active', 'created_at')
    list_filter = ('target_department', 'target_community', 'is_active', 'created_at')
    search_fields = ('question', 'description')
    
    # Registered the new Action for downloading Excel/CSV reports
    actions = [export_poll_summary_csv]
    
    readonly_fields = ('created_by', 'get_detailed_results')

    def save_model(self, request, obj, form, change):
        if not obj.pk: 
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_yes_count(self, obj):
        return obj.responses.filter(choice='Yes').count()
    get_yes_count.short_description = '✅ Yes'

    def get_no_count(self, obj):
        return obj.responses.filter(choice='No').count()
    get_no_count.short_description = '❌ No'

    # Upgraded get_detailed_results to use the 3-column Yes/No/Unreacted Dashboard
    def get_detailed_results(self, obj):
        User = get_user_model()

        # 1. Determine the target audience
        if obj.target_community:
            target_students = User.objects.filter(profile__community=obj.target_community, is_staff=False, is_superuser=False)
        elif obj.target_department != 'All':
            target_students = User.objects.filter(profile__department=obj.target_department, is_staff=False, is_superuser=False)
        else:
            target_students = User.objects.filter(is_staff=False, is_superuser=False)

        # 2. Get the voters
        yes_users = [r.user.username for r in obj.responses.filter(choice='Yes').select_related('user')]
        no_users = [r.user.username for r in obj.responses.filter(choice='No').select_related('user')]
        
        # 3. Calculate who ignored it
        responded_ids = obj.responses.values_list('user_id', flat=True)
        unreacted_users = [u.username for u in target_students.exclude(id__in=responded_ids)]

        # 4. Build the 3-Column Dashboard HTML
        html = f"""
        <div style='display: flex; gap: 15px; font-family: Arial, sans-serif; width: 100%; max-width: 900px;'>
            <div style='border: 1px solid #28a745; border-radius: 8px; width: 33%; background: #f8fff9; overflow: hidden;'>
                <div style='background: #28a745; color: white; padding: 10px; font-weight: bold; text-align: center;'>✅ Voted YES ({len(yes_users)})</div>
                <div style='padding: 10px; max-height: 200px; overflow-y: auto;'>
                    {'<br>'.join(yes_users) if yes_users else '<i>None</i>'}
                </div>
            </div>
            
            <div style='border: 1px solid #dc3545; border-radius: 8px; width: 33%; background: #fffafb; overflow: hidden;'>
                <div style='background: #dc3545; color: white; padding: 10px; font-weight: bold; text-align: center;'>❌ Voted NO ({len(no_users)})</div>
                <div style='padding: 10px; max-height: 200px; overflow-y: auto;'>
                    {'<br>'.join(no_users) if no_users else '<i>None</i>'}
                </div>
            </div>
            
            <div style='border: 1px solid #6c757d; border-radius: 8px; width: 33%; background: #f8f9fa; overflow: hidden;'>
                <div style='background: #6c757d; color: white; padding: 10px; font-weight: bold; text-align: center;'>💤 Unreacted ({len(unreacted_users)})</div>
                <div style='padding: 10px; max-height: 200px; overflow-y: auto;'>
                    {'<br>'.join(unreacted_users) if unreacted_users else '<i>All students reacted!</i>'}
                </div>
            </div>
        </div>
        """
        return mark_safe(html)
    get_detailed_results.short_description = "Detailed Poll Summary"

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
    
# ==========================================
# 7. Add Department Dropdown to User Admin
# ==========================================
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Student Department & Community' # Updated label

# Get the standard User model
User = get_user_model()

# Unregister Django's default User admin
admin.site.unregister(User)

# Re-register the User admin, but attach our new ProfileInline to it
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline, )