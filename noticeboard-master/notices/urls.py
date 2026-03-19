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
    path('tags/', views.TagListView, name='tags'),
    path('tags/<str:tag>/', views.TagView.as_view(), name='tag'),
    path('user/<str:user>/', views.UserNoticeListView.as_view(), name='user_notices'),
]
