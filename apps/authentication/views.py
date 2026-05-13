from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import uuid

from .models import User, EducatorProfile, PasswordResetToken, Follower
from .forms import (StudentRegistrationForm, EducatorRegistrationForm,
                    LoginForm, EducatorProfileForm, UserAvatarForm,
                    ForgotPasswordForm, ResetPasswordForm)
from apps.courses.models import Category


def sync_session_category(request, user):
    if user.role == 'student' and 'selected_category_id' in request.session:
        try:
            category_id = request.session['selected_category_id']
            category = Category.objects.get(id=category_id)
            user.selected_category = category
            user.save()
            # We don't delete yet, in case user logs out and logs in again without choosing, 
            # but actually it's better to clear it once synced.
            del request.session['selected_category_id']
        except Category.DoesNotExist:
            pass


def register_student(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = StudentRegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        sync_session_category(request, user)
        messages.success(request, f'Welcome, {user.full_name}! Your account has been created.')
        return redirect('student_dashboard')
    return render(request, 'public/register_student.html', {'form': form})


def register_educator(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = EducatorRegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        messages.success(request, 'Educator account created! Awaiting admin approval.')
        return redirect('login')
    return render(request, 'public/register_educator.html', {'form': form})


def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        password = form.cleaned_data['password']
        user = authenticate(request, email=email, password=password)
        if user:
            if not user.is_approved:
                messages.warning(request, 'Your account is pending admin approval.')
                return redirect('login')
            login(request, user)
            sync_session_category(request, user)
            messages.success(request, f'Welcome back, {user.full_name}!')
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid email or password.')
    return render(request, 'public/login.html', {'form': form})


def user_logout(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')


@login_required
def dashboard(request):
    user = request.user
    if user.role == 'admin':
        return redirect('admin_dashboard')
    elif user.role == 'educator':
        return redirect('educator_dashboard')
    else:
        return redirect('student_dashboard')


def forgot_password(request):
    form = ForgotPasswordForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        try:
            user = User.objects.get(email=email)
            token = str(uuid.uuid4())
            PasswordResetToken.objects.create(user=user, token=token)
            reset_url = request.build_absolute_uri(f'/auth/reset-password/{token}/')
            send_mail(
                'Password Reset - Online Educator Portal',
                f'Click the link to reset your password: {reset_url}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=True,
            )
        except User.DoesNotExist:
            pass
        messages.success(request, 'If that email exists, a reset link has been sent.')
        return redirect('login')
    return render(request, 'public/forgot_password.html', {'form': form})


def reset_password(request, token):
    reset_token = get_object_or_404(PasswordResetToken, token=token)
    if not reset_token.is_valid():
        messages.error(request, 'This reset link has expired or already been used.')
        return redirect('forgot_password')
    form = ResetPasswordForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        reset_token.user.set_password(form.cleaned_data['password'])
        reset_token.user.save()
        reset_token.is_used = True
        reset_token.save()
        messages.success(request, 'Password reset successfully. Please log in.')
        return redirect('login')
    return render(request, 'public/reset_password.html', {'form': form, 'token': token})


@login_required
def edit_profile(request):
    user = request.user
    avatar_form = UserAvatarForm(request.POST or None, request.FILES or None, instance=user)
    profile_form = None

    if user.is_educator:
        profile, _ = EducatorProfile.objects.get_or_create(user=user)
        profile_form = EducatorProfileForm(request.POST or None, request.FILES or None, instance=profile)

    if request.method == 'POST':
        if avatar_form.is_valid():
            avatar_form.save()
        if profile_form and profile_form.is_valid():
            profile_form.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('edit_profile')

    return render(request, 'educator/profile_edit.html', {
        'avatar_form': avatar_form,
        'profile_form': profile_form,
    })


@login_required
def toggle_follow(request, educator_pk):
    educator = get_object_or_404(User, pk=educator_pk, role='educator')
    if educator == request.user:
        messages.error(request, "You cannot follow yourself.")
        return redirect('educator_profile', unique_link=educator.educator_profile.unique_link)
    
    follower, created = Follower.objects.get_or_create(student=request.user, educator=educator)
    if not created:
        follower.delete()
        messages.info(request, f"You stopped following {educator.full_name}.")
    else:
        messages.success(request, f"You are now following {educator.full_name}!")
        
    return redirect('educator_profile', unique_link=educator.educator_profile.unique_link)
