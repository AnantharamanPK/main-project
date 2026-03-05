from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.contrib import messages
from django.db import transaction
import urllib.parse 

# Added Poll and PollResponse to the imports
from .models import Notice, User, NoticeReadStatus, DirectMessage, Notification, Poll, PollResponse 
from .forms import NewNoticeForm

# 1. MAIN LIST VIEW (Board filtered by Department)
class NoticeListView(LoginRequiredMixin, ListView): 
    model = Notice
    context_object_name = 'notices'
    template_name = 'notices/home.html'
    paginate_by = 10

    def get_queryset(self):
        now = timezone.now()
        user = self.request.user
        
        # Base filter: Approved and not expired
        queryset = Notice.objects.filter(is_approved=True).filter(
            Q(expires_at__gt=now) | Q(expires_at__isnull=True)
        )

        # DEPARTMENT FILTERING: Students only see their dept or "All"
        if user.is_authenticated and not user.is_staff:
            try:
                user_dept = user.profile.department
                queryset = queryset.filter(
                    Q(target_department=user_dept) | Q(target_department='All')
                )
            except:
                # Fallback if profile is missing
                queryset = queryset.filter(target_department='All')
        
        # Search Query logic
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(message__icontains=query)
            ).distinct()
        
        # Tag Filter logic
        tag_filter = self.request.GET.get('tag')
        if tag_filter:
            queryset = queryset.filter(tags__icontains=tag_filter)
            
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_authenticated:
            context['read_notice_ids'] = NoticeReadStatus.objects.filter(
                user=user
            ).values_list('notice_id', flat=True)
            context['direct_messages'] = DirectMessage.objects.filter(
                student=user, 
                is_read=False
            )

            # ==========================================
            # NEW: POLL LOGIC
            # ==========================================
            try:
                user_dept = user.profile.department
            except:
                user_dept = 'All'
            
            # 1. Get active polls for this user's department (and 'All')
            active_polls = Poll.objects.filter(
                is_active=True, 
                target_department__in=['All', user_dept]
            )
            context['active_polls'] = active_polls

            # 2. Map out which polls this user has already answered
            user_responses = PollResponse.objects.filter(
                user=user, 
                poll__in=active_polls
            )
            # Create a dictionary {poll_id: 'Yes'/'No'} for the template
            context['user_poll_responses'] = {r.poll.id: r.choice for r in user_responses}
            # ==========================================
        
        tag_queryset = Notice.objects.filter(tags__isnull=False).values_list('tags', flat=True)
        unique_tags = set()
        for t_str in tag_queryset:
            if t_str:
                unique_tags.update([t.strip() for t in t_str.split(',') if t.strip()])
        
        unique_tags.add("General")
        unique_tags.add("Important")
        context['all_tags'] = sorted(list(unique_tags))
        return context

# 2. ARCHIVE VIEW (Department Aware)
class ArchivedNoticeListView(LoginRequiredMixin, ListView):
    model = Notice
    context_object_name = 'archived_notices'
    template_name = 'notices/archive.html'
    paginate_by = 12

    def get_queryset(self):
        now = timezone.now()
        user = self.request.user
        queryset = Notice.objects.filter(is_approved=True, expires_at__lt=now)

        if user.is_authenticated and not user.is_staff:
            try:
                queryset = queryset.filter(
                    Q(target_department=user.profile.department) | Q(target_department='All')
                )
            except:
                queryset = queryset.filter(target_department='All')

        return queryset.order_by('-expires_at')

# 3. GOOGLE CALENDAR REDIRECT
@login_required
def open_google_calendar(request, notice_id):
    notice = get_object_or_404(Notice, id=notice_id)
    if not notice.expires_at:
        messages.error(request, "This notice does not have a deadline.")
        return redirect('notices:notice_page', notice_id=notice.id)

    fmt = "%Y%m%dT%H%M%SZ"
    start_time = notice.expires_at.strftime(fmt)
    end_time = (notice.expires_at + timezone.timedelta(hours=1)).strftime(fmt)

    params = {
        'action': 'TEMPLATE',
        'text': notice.title,
        'dates': f"{start_time}/{end_time}",
        'details': f"Noticeboard Alert [{notice.target_department}]: {notice.message[:500]}",
        'location': 'Campus Noticeboard',
        'sf': 'true',
        'output': 'xml'
    }
    google_url = f"https://www.google.com/calendar/render?{urllib.parse.urlencode(params)}"
    return redirect(google_url)

# 4. LIVE SEARCH
def live_search(request):
    query = request.GET.get('q', '')
    if len(query) > 0:
        results = Notice.objects.filter(is_approved=True, title__icontains=query)[:5]
        data = [{'id': n.id, 'title': n.title} for n in results]
    else:
        data = []
    return JsonResponse({'results': data})

# 5. STAFF VIEW: NOTICES BY CURRENT USER
class UserNoticeListView(LoginRequiredMixin, ListView):
    model = Notice
    context_object_name = 'notices'
    template_name = 'notices/notices_by_user.html'
    paginate_by = 10

    def get_queryset(self):
        return Notice.objects.filter(created_by=self.request.user).order_by('-created_at')

# 6. FILTER BY TAGS
class TagView(LoginRequiredMixin, ListView):
    model = Notice
    context_object_name = 'notices'
    template_name = 'notices/tag.html'
    paginate_by = 10

    def get_queryset(self):
        tag = self.kwargs['tag']
        return Notice.objects.filter(is_approved=True, tags__icontains=tag).order_by('-created_at')

# 7. SINGLE NOTICE DETAIL & DYNAMIC ATTENDANCE REPORT
@login_required
def NoticeView(request, notice_id):
    notice = get_object_or_404(Notice, id=notice_id)
    
    # Logic to identify the target audience for the attendance report
    # We exclude Staff (AnantharamanPK) and Superusers from the count
    if notice.target_department == 'All':
        target_students = User.objects.filter(is_staff=False, is_superuser=False)
    else:
        # Filter by department but ensure staff members are excluded
        target_students = User.objects.filter(
            profile__department=notice.target_department,
            is_staff=False,
            is_superuser=False
        )

    # Calculate Read Status based on the target student group only
    read_ids = NoticeReadStatus.objects.filter(notice=notice).values_list('user_id', flat=True)
    
    # Generate querysets for the template display
    acknowledged_students = target_students.filter(id__in=read_ids)
    unseen_students = target_students.exclude(id__in=read_ids)

    return render(request, 'notices/notice_page.html', {
        'notice': notice,
        'acknowledged_students': acknowledged_students,
        'unseen_students': unseen_students,
    })

# 8. POSTING A NEW NOTICE
@staff_member_required
def NewNoticePage(request):
    if request.method == 'POST':
        form = NewNoticeForm(request.POST, request.FILES) 
        if form.is_valid():
            notice = form.save(commit=False)
            notice.created_by = request.user
            notice.is_approved = False 
            notice.status = 'pending'
            notice.save()
            messages.info(request, "Notice submitted for Admin approval.")
            return redirect('notices:home') 
    else:
        form = NewNoticeForm()
    return render(request, 'notices/notice_form.html', {'form': form})

# 9. EDIT NOTICE
@login_required
def edit_notice(request, notice_id):
    notice = get_object_or_404(Notice, id=notice_id)
    if notice.created_by != request.user:
        messages.error(request, "You do not have permission to edit this notice.")
        return redirect('notices:home')

    if request.method == 'POST':
        form = NewNoticeForm(request.POST, request.FILES, instance=notice)
        if form.is_valid():
            updated_notice = form.save(commit=False)
            updated_notice.status = 'pending'
            updated_notice.is_approved = False 
            updated_notice.rejection_reason = "" 
            updated_notice.save()
            messages.success(request, "Notice resubmitted for approval!")
            return redirect('notices:home')
    else:
        form = NewNoticeForm(instance=notice)
    return render(request, 'notices/notice_form.html', {'form': form, 'edit_mode': True, 'notice': notice})

# 10. MARK AS READ
@login_required
def mark_as_read(request, notice_id):
    if request.method == 'POST':
        notice = get_object_or_404(Notice, id=notice_id)
        NoticeReadStatus.objects.get_or_create(user=request.user, notice=notice)
    return redirect('notices:home')

# 11. MARK ALL AS READ (Filtered by Department)
@login_required
def mark_all_as_read(request):
    if request.method == 'POST':
        user = request.user
        try:
            user_dept = user.profile.department
        except:
            user_dept = 'All'
        
        # Mark only eligible student-facing notices
        all_eligible_notices = Notice.objects.filter(
            is_approved=True,
            target_department__in=[user_dept, 'All']
        )
        
        read_notice_ids = NoticeReadStatus.objects.filter(
            user=user
        ).values_list('notice_id', flat=True)
        
        unread_notices = all_eligible_notices.exclude(id__in=read_notice_ids)
        
        with transaction.atomic():
            for notice in unread_notices:
                NoticeReadStatus.objects.get_or_create(user=user, notice=notice)
                
    return redirect('notices:home')

# 12. CLEAR NOTIFICATIONS
@login_required
def clear_notifications(request):
    Notification.objects.filter(recipient=request.user).delete()
    return redirect(request.META.get('HTTP_REFERER', 'notices:home'))

# 13. DISMISS MESSAGES
@login_required
def dismiss_direct_message(request, message_id):
    if request.method == 'POST':
        msg = get_object_or_404(DirectMessage, id=message_id, student=request.user)
        msg.is_read = True
        msg.save()
    return redirect('notices:home')


# ==========================================
# 14. NEW: SUBMIT POLL RESPONSE
# ==========================================
@login_required
def submit_poll(request, poll_id):
    if request.method == 'POST':
        poll = get_object_or_404(Poll, id=poll_id, is_active=True)
        choice = request.POST.get('choice')
        
        if choice in ['Yes', 'No']:
            # Create or update the student's poll response
            PollResponse.objects.update_or_create(
                poll=poll, 
                user=request.user, 
                defaults={'choice': choice}
            )
            messages.success(request, f"Your response '{choice}' has been recorded.")
        else:
            messages.error(request, "Invalid choice.")
            
    return redirect('notices:home')


# ==========================================
# 15. ADMIN ANALYTICS DASHBOARD
# ==========================================
from django.db.models import Count

@staff_member_required
def analytics_dashboard(request):
    # 1. General Stats
    total_students = User.objects.filter(is_staff=False, is_superuser=False).count()
    total_notices = Notice.objects.count()
    
    # 2. Poll Engagement
    total_polls = Poll.objects.count()
    total_votes = PollResponse.objects.count()
    
    # 3. Department Read Engagement
    departments = ['MCA', 'BTech', 'MBA']
    dept_stats = []
    
    for dept in departments:
        # How many students in this dept?
        student_count = User.objects.filter(profile__department=dept, is_staff=False).count()
        # How many total read receipts belong to students in this dept?
        read_count = NoticeReadStatus.objects.filter(user__profile__department=dept).count()
        
        dept_stats.append({
            'department': dept,
            'students': student_count,
            'reads': read_count,
        })

    context = {
        'total_students': total_students,
        'total_notices': total_notices,
        'total_polls': total_polls,
        'total_votes': total_votes,
        'dept_stats': dept_stats,
    }
    
    return render(request, 'notices/analytics.html', context)


# ==========================================
# 16. INTERNAL CALENDAR DASHBOARD
# ==========================================
from django.urls import reverse

@login_required
def calendar_view(request):
    """Renders the empty calendar page."""
    return render(request, 'notices/calendar.html')

@login_required
def get_calendar_events(request):
    """Returns a JSON list of notices and polls for FullCalendar.js"""
    user = request.user
    
    # Determine department
    if user.is_staff or user.is_superuser:
        user_dept = 'All' # Staff sees everything
    else:
        try:
            user_dept = user.profile.department
        except:
            user_dept = 'All'

    events = []

    # 1. Fetch Notices with Deadlines
    if user.is_staff or user.is_superuser:
        notices = Notice.objects.filter(expires_at__isnull=False)
    else:
        notices = Notice.objects.filter(
            is_approved=True, 
            expires_at__isnull=False,
            target_department__in=['All', user_dept]
        )

    for notice in notices:
        # Note: adjust 'notices:NoticeView' below if your actual URL name is different
        events.append({
            'title': f"📝 {notice.title}",
            'start': notice.expires_at.isoformat(),
            'url': reverse('notices:notice_page', args=[notice.id]), 
            'backgroundColor': 'rgba(255, 193, 7, 0.9)', # Warning/Yellow
            'borderColor': '#ffc107',
            'textColor': '#000'
        })

    # 2. Fetch Active Polls (Displaying on the day they were created)
    if user.is_staff or user.is_superuser:
        polls = Poll.objects.filter(is_active=True)
    else:
        polls = Poll.objects.filter(
            is_active=True,
            target_department__in=['All', user_dept]
        )

    for poll in polls:
        events.append({
            'title': f"📊 Poll: {poll.question}",
            'start': poll.created_at.isoformat(),
            'allDay': True,
            'url': reverse('notices:home'), # Redirects home where polls live
            'backgroundColor': 'rgba(40, 167, 69, 0.9)', # Success/Green
            'borderColor': '#28a745',
        })

    return JsonResponse(events, safe=False)