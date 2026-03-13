from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone
from datetime import timedelta
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

def check_deadlines():
    """This function runs silently in the background every hour."""
    from notices.models import Notice, User, Notification
    
    now = timezone.now()
    target_48h = now + timedelta(days=2)
    target_24h = now + timedelta(days=1)
    
    # --- 1. CHECK FOR 48-HOUR WARNINGS ---
    notices_48h = Notice.objects.filter(is_approved=True, expires_at__date=target_48h.date(), alert_48h_sent=False)
    for notice in notices_48h:
        send_alert(notice, User, Notification, hours=48)
        notice.alert_48h_sent = True
        notice.save()

    # --- 2. CHECK FOR 24-HOUR WARNINGS ---
    notices_24h = Notice.objects.filter(is_approved=True, expires_at__date=target_24h.date(), alert_24h_sent=False)
    for notice in notices_24h:
        send_alert(notice, User, Notification, hours=24)
        notice.alert_24h_sent = True
        notice.save()


def send_alert(notice, User, Notification, hours):
    """Helper function that actually builds and sends the email/notification"""
    if notice.target_department == 'All':
        students = User.objects.filter(is_staff=False, is_superuser=False)
    else:
        students = User.objects.filter(profile__department=notice.target_department, is_staff=False, is_superuser=False)
    
    # Skip students who already read it!
    read_ids = notice.read_statuses.values_list('user_id', flat=True)
    unread_students = students.exclude(id__in=read_ids)

    if unread_students.exists():
        # Change the message based on how much time is left
        if hours == 48:
            in_app_msg = f"⏰ 48-HOUR WARNING: '{notice.title}' is expiring soon!"
            email_sub = f"48-HOUR WARNING: Deadline for '{notice.title}'"
        else:
            in_app_msg = f"🚨 FINAL WARNING: '{notice.title}' expires in 24 hours!"
            email_sub = f"URGENT FINAL WARNING: 24 hours left for '{notice.title}'"

        # 1. In-App Notifications
        notifications = [
            Notification(recipient=student, message=in_app_msg, related_notice=notice) 
            for student in unread_students
        ]
        Notification.objects.bulk_create(notifications)

        # 2. Email Blast
        student_emails = [student.email for student in unread_students if student.email]
        if student_emails:
            # ---------------------------------------------------------
            # THE LINK: Change this path if your notice URL is different!
            # When you launch the real website, change 127.0.0.1 to your real domain.
            # ---------------------------------------------------------
            site_url = "http://127.0.0.1:8000"
            notice_link = f"{site_url}/notices/view/{notice.id}/"
            # The plain text version (for older email apps that block HTML)
            text_body = f"Hello,\nThe notice '{notice.title}' expires in {hours} hours. View it here: {notice_link}"
            
            # The beautiful HTML version with the button!
            html_body = f"""
            <html>
              <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
                <h2 style="color: #dc3545;">🚨 Action Required: Deadline Approaching</h2>
                <p>Hello,</p>
                <p>This is an automated system alert. The notice <strong>"{notice.title}"</strong> will expire in exactly <strong>{hours} hours</strong>.</p>
                <p>Our records show you have not yet acknowledged this notice. Please log in immediately to view the details.</p>
                <br>
                <a href="{notice_link}" style="display: inline-block; padding: 12px 24px; font-size: 16px; color: #ffffff; background-color: #0d6efd; text-decoration: none; border-radius: 6px; font-weight: bold;">
                  View Notice on Portal
                </a>
                <br><br>
                <p style="font-size: 12px; color: #777; margin-top: 20px;">
                  If the button doesn't work, copy and paste this link into your browser:<br>
                  <a href="{notice_link}" style="color: #0d6efd;">{notice_link}</a>
                </p>
              </body>
            </html>
            """
            
            try:
                # Build the email with the text version first
                email = EmailMultiAlternatives(
                    subject=email_sub, 
                    body=text_body, 
                    from_email=settings.EMAIL_HOST_USER, 
                    bcc=student_emails
                )
                # Attach the HTML version
                email.attach_alternative(html_body, "text/html")
                email.send(fail_silently=True)
            except Exception as e:
                print(f"Email failed: {e}")

        print(f"[SYSTEM] Automatically sent {hours}-hour alerts for: {notice.title}")

def start_scheduler():
    """Turns the clock on"""
    scheduler = BackgroundScheduler()
    # Check the database every 1 hour (Change to minutes=1 to test it quickly!)
    scheduler.add_job(check_deadlines, 'interval', minutes=1)
    scheduler.start()