from django.db import models
from django.contrib.auth.models import User
from django.utils.html import mark_safe
from markdown import markdown
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from datetime import timedelta
import os
from django.core.mail import EmailMultiAlternatives

# ==========================================
# 1. NEW: User Profile (To store Department)
# ==========================================
class Profile(models.Model):
    DEPARTMENT_CHOICES = [
        ('MCA', 'MCA'),
        ('BTech', 'BTech'),
        ('MBA', 'MBA'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    department = models.CharField(max_length=10, choices=DEPARTMENT_CHOICES, default='MCA')

    def __str__(self):
        return f"{self.user.username} ({self.department})"

# Signal to ensure every User has a Profile automatically
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

# ==========================================
# 2. The Notice Model
# ==========================================
class Notice(models.Model):
    title = models.CharField(max_length=200)
    message = models.TextField()
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Target specific departments
    DEPARTMENT_TARGETS = [
        ('All', 'All Departments'),
        ('MCA', 'MCA'),
        ('BTech', 'BTech'),
        ('MBA', 'MBA'),
    ]
    target_department = models.CharField(
        max_length=10, 
        choices=DEPARTMENT_TARGETS, 
        default='All'
    )

    attachment = models.FileField(upload_to='notices/attachments/', null=True, blank=True)
    tags = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, related_name='notices', on_delete=models.CASCADE)

    notifications_sent = models.BooleanField(default=False)
    
    # NEW: Tracks if the automated alerts have been sent
    alert_48h_sent = models.BooleanField(default=False)
    alert_24h_sent = models.BooleanField(default=False)

    status = models.CharField(
        max_length=10, 
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='pending'
    )
    is_approved = models.BooleanField(default=False) 
    rejection_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title

    def get_message_as_markdown(self):
        return mark_safe(markdown(self.message, safe_mode='escape'))       

    def get_tags_as_list(self):
        if self.tags:
            return [tag.strip() for tag in self.tags.split(",") if tag.strip()]
        return []

    def is_image(self):
        if self.attachment:
            extension = os.path.splitext(self.attachment.name)[1].lower()
            return extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        return False
    
    @property
    def is_active(self):
        if self.expires_at:
            return timezone.now() < self.expires_at
        return True

    @property
    def is_archived(self):
        if self.expires_at:
            return timezone.now() >= self.expires_at
        return False

    @property
    def is_urgent(self):
        if self.expires_at:
            now = timezone.now()
            return now < self.expires_at <= now + timedelta(hours=24)
        return False

# ==========================================
# 3. Acknowledgement & Messages
# ==========================================
class NoticeReadStatus(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    notice = models.ForeignKey(Notice, on_delete=models.CASCADE, related_name='read_statuses')
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'notice')

class DirectMessage(models.Model):
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    notice_reference = models.ForeignKey('Notice', on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

# ==========================================
# 4. The Notification System
# ==========================================
class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    related_notice = models.ForeignKey(Notice, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

# ==========================================
# 5. Multi-Step Notification Signal
# ==========================================
@receiver(post_save, sender=Notice)
def create_notice_notification(sender, instance, created, **kwargs):
    if created:
        # STAFF -> ADMIN (In-App Notification Only)
        admins = User.objects.filter(is_superuser=True)
        notifications = [
            Notification(
                recipient=admin,
                message=f"Approval Required: {instance.title} by @{instance.created_by.username}",
                related_notice=instance
            ) for admin in admins
        ]
        Notification.objects.bulk_create(notifications)

    elif instance.status == 'approved' and not instance.notifications_sent:
        # ADMIN -> STUDENTS (FILTERED BY DEPARTMENT)
        students = User.objects.filter(is_staff=False, is_superuser=False)
        
        # Only target students in the correct department
        if instance.target_department != 'All':
            students = students.filter(profile__department=instance.target_department)
        
        deadline_info = ""
        email_deadline = "No specific deadline."
        
        if instance.expires_at:
            deadline_info = f" | Deadline: {instance.expires_at.strftime('%d %b, %H:%M')}"
            email_deadline = instance.expires_at.strftime('%A, %d %B %Y at %I:%M %p') # Formats nicely for email
        
        # 1. CREATE IN-APP NOTIFICATIONS
        notifications = [
            Notification(
                recipient=student,
                message=f"[{instance.target_department}] New Notice: {instance.title}{deadline_info}",
                related_notice=instance
            ) for student in students
        ]
        Notification.objects.bulk_create(notifications)
        
        # 2. SEND THE AUTOMATED EMAIL
        # Gather all valid email addresses from the targeted students
        student_emails = [student.email for student in students if student.email]
        
        if student_emails:
            # --- MAKE SURE TO USE YOUR IPV4 ADDRESS HERE IF TESTING ON PHONE ---
            site_url = "http://127.0.0.1:8000" 
            notice_link = f"{site_url}/notices/view/{instance.id}/"
            
            subject = f"New Campus Notice [{instance.target_department}]: {instance.title}"
            
            # The plain text backup version
            text_body = f"Hello,\n\nA new notice has been posted for the {instance.target_department} department.\n\nTITLE: {instance.title}\nDEADLINE: {email_deadline}\n\nPlease view and acknowledge it here: {notice_link}"
            
            # The beautiful HTML version with the button!
            html_body = f"""
            <html>
              <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
                <h2 style="color: #0d6efd;">📢 New Campus Notice Posted</h2>
                <p>Hello,</p>
                <p>A new notice has been posted for the <strong>{instance.target_department}</strong> department.</p>
                <p>
                  <strong>Title:</strong> {instance.title}<br>
                  <strong>Deadline:</strong> {email_deadline}
                </p>
                <br>
                <a href="{notice_link}" style="display: inline-block; padding: 12px 24px; font-size: 16px; color: #ffffff; background-color: #0d6efd; text-decoration: none; border-radius: 6px; font-weight: bold;">
                  View Notice & Acknowledge
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
                    subject=subject,
                    body=text_body,
                    from_email=settings.EMAIL_HOST_USER,
                    bcc=student_emails
                )
                # Attach the HTML version so the button shows up
                email.attach_alternative(html_body, "text/html")
                email.send(fail_silently=True)
            except Exception as e:
                print(f"Email failed to send: {e}")
        
        # 3. MARK AS SENT
        # Use update to avoid re-triggering signals
        Notice.objects.filter(id=instance.id).update(notifications_sent=True)
# ==========================================
# 6. Poll & Attendance System
# ==========================================
class Poll(models.Model):
    question = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    # Target specific departments for the poll
    target_department = models.CharField(
        max_length=10, 
        choices=[
            ('All', 'All Departments'),
            ('MCA', 'MCA'),
            ('BTech', 'BTech'),
            ('MBA', 'MBA'),
        ], 
        default='All'
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"Poll: {self.question}"

    class Meta:
        ordering = ['-created_at']

class PollResponse(models.Model):
    CHOICES = [('Yes', 'Yes'), ('No', 'No')]
    poll = models.ForeignKey(Poll, related_name='responses', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    choice = models.CharField(max_length=5, choices=CHOICES)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('poll', 'user') # Prevents double voting

# ==========================================
# 7. Notification Signal for New Polls
# ==========================================
@receiver(post_save, sender=Poll)
def create_poll_notification(sender, instance, created, **kwargs):
    if created:
        students = User.objects.filter(is_staff=False, is_superuser=False)
        if instance.target_department != 'All':
            students = students.filter(profile__department=instance.target_department)
            
        notifications = [
            Notification(
                recipient=student,
                message=f"New Poll: {instance.question} (Please respond Yes/No)",
            ) for student in students
        ]
        Notification.objects.bulk_create(notifications)

# ==========================================
# 8. Admin Link Placeholder (Dummy Model)
# ==========================================
class AnalyticsLink(models.Model):
    class Meta:
        managed = False  # Tells Django NOT to create a database table
        verbose_name = "📊 View Analytics Dashboard"
        verbose_name_plural = "📊 View Analytics Dashboard"