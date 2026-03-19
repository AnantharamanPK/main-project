from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from notices.models import Notice, Notification
from datetime import timedelta

class Command(BaseCommand):
    help = 'Checks for notices expiring in the next 24 hours and notifies students'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        tomorrow = now + timedelta(days=1)

        # 1. Find APPROVED notices expiring between Now and Tomorrow
        expiring_notices = Notice.objects.filter(
            is_approved=True,
            expires_at__range=(now, tomorrow)
        )

        if not expiring_notices.exists():
            self.stdout.write("No deadlines approaching in the next 24 hours.")
            return

        count = 0
        
        # 2. Loop through expiring notices
        for notice in expiring_notices:
            # Only notify students (is_staff=False)
            students = User.objects.filter(is_staff=False)
            
            for student in students:
                # Define the warning message
                alert_msg = f"⚠️ DEADLINE TOMORROW: {notice.title}"

                # 3. Prevent Duplicates: Check if we already sent this specific warning
                already_notified = Notification.objects.filter(
                    recipient=student, 
                    message=alert_msg
                ).exists()

                if not already_notified:
                    Notification.objects.create(
                        recipient=student,
                        message=alert_msg,
                        related_notice=notice
                    )
                    count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully sent {count} deadline alerts.'))