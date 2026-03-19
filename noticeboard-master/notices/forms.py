from django import forms
from .models import Notice

class NewNoticeForm(forms.ModelForm):
    # Title with modern styling
    title = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg custom-input',
            'placeholder': 'Notice Title'
        })
    )

    # Message with custom rows
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 5, 
            'placeholder': 'Detailed description...',
            'class': 'form-control custom-input'
        }),
        max_length=2000,
        help_text='Maximum 2000 characters.'
    )

    # Simplified tags for the user
    tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control custom-input',
            'placeholder': 'e.g. Exam, Holiday'
        }),
        help_text='Separate tags with commas.'
    )

    # File upload field
    attachment = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control-file'
        })
    )

    class Meta:
        model = Notice
        fields = ['title', 'message', 'tags', 'attachment']

    def clean_tags(self):
        """Automatically formats tags: 'Exam, Holiday' becomes 'Exam,Holiday,'"""
        data = self.cleaned_data.get('tags', '').strip()
        if data:
            # Clean spaces and ensure trailing comma for your database logic
            tag_list = [t.strip() for t in data.split(',') if t.strip()]
            return ",".join(tag_list) + ","
        return ""