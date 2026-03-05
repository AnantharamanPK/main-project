from django.urls import path
from . import views

app_name = 'notices'

urlpatterns = [
    # Main Home Page
    path('', views.NoticeListView.as_view(), name='home'),
    
    # AJAX Live Search
    path('live-search/', views.live_search, name='live_search'),
    
    # Notice Detail - Changed to match modern path nesting
    path('view/<int:notice_id>/', views.NoticeView, name='notice_page'),
    
    # Create Notice - This matches your base.html link perfectly
    path('new/', views.NewNoticePage, name='new_notice'),
    
    # Filtering and Explorer
    path('tags/', views.TagView.as_view(), name='tags'),
    path('tags/<str:tag>/', views.TagView.as_view(), name='tag'),
    path('user/<str:user>/', views.UserNoticeListView.as_view(), name='user_notices'),
    path('edit/<int:notice_id>/', views.edit_notice, name='edit_notice'),
    path('mark-as-read/<int:notice_id>/', views.mark_as_read, name='mark_as_read'),
    path('mark-all-as-read/', views.mark_all_as_read, name='mark_all_as_read'),
    # notices/urls.py
    path('message/dismiss/<int:message_id>/', views.dismiss_direct_message, name='dismiss_message'),
    path('notifications/clear/', views.clear_notifications, name='clear_notifications'),
    path('archive/', views.ArchivedNoticeListView.as_view(), name='archive'),
    # notices/urls.py
path('notice/<int:notice_id>/google-calendar/', views.open_google_calendar, name='open_google_calendar'),
path('poll/<int:poll_id>/submit/', views.submit_poll, name='submit_poll'),
path('analytics/', views.analytics_dashboard, name='analytics'),
path('calendar/', views.calendar_view, name='calendar'),
path('api/calendar-events/', views.get_calendar_events, name='calendar_events'),
]
