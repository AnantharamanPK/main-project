from django.apps import AppConfig
import os

class NoticesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notices'

    def ready(self):
        # We use this check so the scheduler doesn't accidentally start twice 
        # when Django reloads itself during development
        if os.environ.get('RUN_MAIN') == 'true':
            from . import scheduler
            scheduler.start_scheduler()
            print("⏰ Background Scheduler Started: Checking for deadlines...")