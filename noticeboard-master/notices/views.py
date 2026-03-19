from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.db.models import Q
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone

from .models import Notice, User
from .forms import NewNoticeForm

# 1. MAIN LIST VIEW
class NoticeListView(LoginRequiredMixin, ListView): 
    model = Notice
    context_object_name = 'notices'
    template_name = 'notices/home.html'
    paginate_by = 10

    def get_queryset(self):
        # Base queryset: Filter for future expiry OR no expiry set (Permanent)
        now = timezone.now()
        queryset = Notice.objects.filter(
            Q(expires_at__gt=now) | Q(expires_at__isnull=True)
        ).order_by('-created_at')
        
        # Search Filtering
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | 
                Q(message__icontains=query)
            ).distinct()
        
        # Tag Filtering
        tag_filter = self.request.GET.get('tag')
        if tag_filter:
            queryset = queryset.filter(tags__icontains=tag_filter)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Extract unique tags from the database
        tag_queryset = Notice.objects.filter(tags__isnull=False).values_list('tags', flat=True)
        unique_tags = set()
        for t_str in tag_queryset:
            if t_str:
                # Splits by comma and cleans up whitespace
                unique_tags.update([t.strip() for t in t_str.split(',') if t.strip()])
        
        # ENSURE GENERAL AND IMPORTANT ALWAYS EXIST
        # We add them to the set manually so they appear even if no post has them yet
        unique_tags.add("General")
        unique_tags.add("Important")
        
        # Sort them: This makes 'General' and 'Important' appear near the start
        context['all_tags'] = sorted(list(unique_tags))
        return context

# 2. LIVE SEARCH FUNCTION
def live_search(request):
    query = request.GET.get('q', '')
    if len(query) > 0:
        results = Notice.objects.filter(title__icontains=query)[:5]
        data = [{'id': n.id, 'title': n.title} for n in results]
    else:
        data = []
    return JsonResponse({'results': data})

# 3. NOTICES BY SPECIFIC USER
class UserNoticeListView(LoginRequiredMixin, ListView):
    model = Notice
    context_object_name = 'notices'
    template_name = 'notices/notices_by_user.html'
    paginate_by = 10

    def get_queryset(self):
        self.user = get_object_or_404(User, username=self.kwargs['user'])
        return Notice.objects.filter(created_by=self.user).order_by('-created_at')

# 4. FILTER BY TAGS (Dedicated Page)
class TagView(LoginRequiredMixin, ListView):
    model = Notice
    context_object_name = 'notices'
    template_name = 'notices/tag.html'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)       
        context_data['tag'] = self.kwargs['tag']
        return context_data

    def get_queryset(self):
        tag = self.kwargs['tag']
        return Notice.objects.filter(tags__icontains=tag).order_by('-created_at')

# 5. ALL TAGS LIST 
@login_required
def TagListView(request):
    queryset = Notice.objects.filter(tags__isnull=False).values_list('tags', flat=True)
    tags = set()
    for t_str in queryset:
        if t_str:
            tags.update([t.strip() for t in t_str.split(',') if t.strip()])
    return render(request, 'notices/tags.html', {'tags': sorted(list(tags))})

# 6. SINGLE NOTICE DETAIL PAGE
@login_required
def NoticeView(request, notice_id):
    notice = get_object_or_404(Notice, id=notice_id)
    return render(request, 'notices/notice_page.html', {'notice': notice})
@login_required
def NoticeView(request, notice_id):
    notice = get_object_or_404(Notice, id=notice_id)
    return render(request, 'notices/notice_page.html', {'notice': notice})

# 7. CREATE NEW NOTICE
@staff_member_required
def NewNoticePage(request):
    if request.method == 'POST':
        form = NewNoticeForm(request.POST, request.FILES) 
        if form.is_valid():
            notice = form.save(commit=False)
            notice.created_by = request.user
            notice.save()
            return redirect('notices:notice_page', notice_id=notice.pk) 
    else:
        form = NewNoticeForm()
    
    return render(request, 'notices/notice_form.html', {'form': form})


