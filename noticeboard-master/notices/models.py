from django.db import models
from django.contrib.auth.models import User
from django.utils.html import mark_safe
from markdown import markdown
from django.utils import timezone
from datetime import timedelta
import os

class Notice(models.Model):
    title = models.CharField(max_length=200)
    message = models.TextField()
    xpires_at = models.DateTimeField(null=True, blank=True) # ADD THIS LINE
    
    # 1. File Upload Field (Photos/PDFs)
    attachment = models.FileField(upload_to='notices/attachments/', null=True, blank=True)
    
    # 2. Existing Tags Field (Stored as a comma-separated string)
    tags = models.CharField(max_length=100, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    # 3. Relationship to User (CASCADE means if user is deleted, notices are too)
    created_by = models.ForeignKey(User, related_name='notices', on_delete=models.CASCADE)

    def __str__(self):
        return self.title

    # Helper for rendering Markdown content
    def get_message_as_markdown(self):
        return mark_safe(markdown(self.message, safe_mode='escape'))       

    # Helper to convert "Important, General" string into a list for the frontend
    def get_tags_as_list(self):
        if self.tags:
            # Splits by comma and removes empty strings
            return [tag.strip() for tag in self.tags.split(",") if tag.strip()]
        return []

    # Helper to detect if the attachment is an image for the template
    def is_image(self):
        if self.attachment:
            extension = os.path.splitext(self.attachment.name)[1].lower()
            return extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        return False
    
    # ... your existing fields (title, message, etc.) ...
    expires_at = models.DateTimeField(null=True, blank=True) # ADD THIS LINE
    
    @property
    def is_active(self):
        if self.expires_at:
            return timezone.now() < self.expires_at
        return True