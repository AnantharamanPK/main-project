from django.contrib import admin
from django.urls import path, include
from accounts import views as account_views
from django.conf import settings # Import settings
from django.conf.urls.static import static # Import static helper

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # This makes the "Login Choice" page the initial page (localhost:8000/)
    path('', account_views.login_choice, name='initial_page'),
    
    # Use namespace='accounts' to fix the 'my_account' reverse error
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('notices/', include('notices.urls')),
]

# ADD THIS TO SERVE PDF/MEDIA FILES DURING DEVELOPMENT
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)