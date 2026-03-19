from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from notices.models import Notice

# 1. Registration Form (Kept exactly as you requested)
class SignUpForm(UserCreationForm):
    email = forms.CharField(max_length=254, required=True, widget=forms.EmailInput())
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

# 2. Notice Form (Added this to fix the FieldError you received)
class NewNoticeForm(forms.ModelForm):
    class Meta:
        model = Notice
        fields = ('title', 'message', 'attachment', 'tags', 'expires_at')
        widgets = {
            'expires_at': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control'}),
            'tags': forms.TextInput(attrs={'class': 'form-control'}),
        }