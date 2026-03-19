from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import UpdateView
from django.http import JsonResponse
from django.contrib.auth.forms import AuthenticationForm 

# Import your Notice model here so it's available for the search view
from notices.models import Notice 
from .forms import SignUpForm

def login_choice(request):
    """
    Renders the Student vs Staff selection page.
    If the user is already logged in, redirect them to the home board.
    """
    if request.user.is_authenticated:
        return redirect('notices:home')
    return render(request, 'accounts/login_choice.html')

# UPDATED: Separate Login View for Students (Blocks Staff)
def student_login(request):
    if request.user.is_authenticated:
        return redirect('notices:home')
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            # BLOCK STAFF FROM STUDENT PORTAL
            if not user.is_staff:
                login(request, user)
                return redirect('notices:home')
            else:
                form.add_error(None, "Staff members must use the Admin Login portal.")
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form, 'user_type': 'Student'})

# UPDATED: Separate Login View for Staff (Blocks Students)
def staff_login(request):
    if request.user.is_authenticated:
        return redirect('notices:home')
    
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            # CHECK IF THE USER HAS STAFF PERMISSIONS
            if user.is_staff:
                login(request, user)
                return redirect('notices:home')
            else:
                # Add a custom error if a student tries to use this portal
                form.add_error(None, "Access Denied: This portal is for authorized Staff only.")
    else:
        form = AuthenticationForm()
        
    return render(request, 'accounts/login.html', {
        'form': form, 
        'user_type': 'Staff'
    })

def signup(request):
    if request.user.is_authenticated:
        return redirect('notices:home')
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('notices:home')
    else:
        form = SignUpForm()
    return render(request, 'accounts/signup.html', {'form': form})

@method_decorator(login_required, name='dispatch')
class UserUpdateView(UpdateView):
    model = User
    fields = ('first_name', 'last_name', 'email', )
    template_name = 'accounts/my_account.html'
    success_url = reverse_lazy('accounts:my_account')

    def get_object(self):
        return self.request.user
    
def live_search(request):
    """
    Handles the AJAX request from the navbar search bar.
    Returns a JSON list of notices matching the query.
    """
    query = request.GET.get('q', '')
    if len(query) > 1:  
        results = Notice.objects.filter(title__icontains=query)[:5]
        data = [{'id': n.id, 'title': n.title} for n in results]
    else:
        data = []
    return JsonResponse({'results': data})

