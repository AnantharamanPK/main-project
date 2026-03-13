import os

# 1. Base Directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 2. Security & Debug
SECRET_KEY = '3)bigi@1+z#6zlx!w)+f1qif3#)^9dm9wfcjqw@(d*-hpl5=89'
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']

# 3. Application Definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'widget_tweaks', 
    'markdown',  
    'accounts',
    'notices'
]

# 4. Middleware (Fixed E408, E409, E410)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'noticeboard.urls'

# 5. Templates (Fixed E403)
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
            ],
        },
    },
]

WSGI_APPLICATION = 'noticeboard.wsgi.application'

# 6. Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        # ADD THIS OPTIONS BLOCK:
        'OPTIONS': {
            # Tells Django to wait up to 20 seconds for the lock to release
            'timeout': 20,
    }
}
}

# 7. Static and Media (For Photos/Files)
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 8. Auth & Localization
# settings.py

# 1. Where to go if a user is not logged in
LOGIN_URL = 'accounts:login_choice' 

# 2. Where to go after a successful login
LOGIN_REDIRECT_URL = 'notices:home' 

# 3. Where to go after logout
LOGOUT_REDIRECT_URL = 'accounts:login_choice'
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_L10N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
# ==========================================
# EMAIL CONFIGURATION (SMTP)
# ==========================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

# Replace these with your actual email details
EMAIL_HOST_USER = 'anantharamann003@gmail.com' 
EMAIL_HOST_PASSWORD = 'qlrxpolphwvpsozv'