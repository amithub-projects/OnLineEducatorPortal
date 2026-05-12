from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.db.models import Q

from apps.authentication.models import User, EducatorProfile, Follower
from apps.courses.models import Course, Enrollment, Category, Lesson
from .models import SiteSettings, Announcement, ContactMessage


def home(request):
    site = SiteSettings.get_settings()
    announcements = Announcement.objects.filter(is_active=True).order_by('-created_at')[:3]
    featured_educators = User.objects.filter(
        role='educator', is_approved=True, is_active=True,
        educator_profile__is_featured=True
    ).select_related('educator_profile')[:6]
    popular_courses = Course.objects.filter(is_published=True).order_by('-created_at')[:8]
    categories = Category.objects.all()
    total_educators = User.objects.filter(role='educator', is_approved=True).count()
    total_students = User.objects.filter(role='student').count()
    total_courses = Course.objects.filter(is_published=True).count()
    return render(request, 'public/home.html', {
        'site': site,
        'announcements': announcements,
        'featured_educators': featured_educators,
        'popular_courses': popular_courses,
        'categories': categories,
        'total_educators': total_educators,
        'total_students': total_students,
        'total_courses': total_courses,
    })


def about(request):
    site = SiteSettings.get_settings()
    return render(request, 'public/about.html', {'site': site})


def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()
        if name and email and subject and message:
            ContactMessage.objects.create(name=name, email=email, subject=subject, message=message)
            send_mail(
                f'Contact: {subject}',
                f'From: {name} ({email})\n\n{message}',
                settings.DEFAULT_FROM_EMAIL,
                [settings.DEFAULT_FROM_EMAIL],
                fail_silently=True,
            )
            messages.success(request, 'Your message has been sent successfully!')
            return redirect('contact')
        else:
            messages.error(request, 'Please fill in all fields.')
    return render(request, 'public/contact.html')


def educator_listing(request):
    educators = User.objects.filter(
        role='educator', is_approved=True, is_active=True
    ).select_related('educator_profile')

    subject_filter = request.GET.get('subject', '')
    experience_filter = request.GET.get('experience', '')
    category_filter = request.GET.get('category', '')
    search_q = request.GET.get('q', '')

    if search_q:
        educators = educators.filter(
            Q(full_name__icontains=search_q) |
            Q(educator_profile__subjects__icontains=search_q) |
            Q(educator_profile__bio__icontains=search_q)
        )
    if subject_filter:
        educators = educators.filter(educator_profile__subjects__icontains=subject_filter)
    if experience_filter:
        try:
            educators = educators.filter(educator_profile__experience_years__gte=int(experience_filter))
        except (ValueError, TypeError):
            pass

    categories = Category.objects.all()
    return render(request, 'public/educator_listing.html', {
        'educators': educators,
        'categories': categories,
        'subject_filter': subject_filter,
        'experience_filter': experience_filter,
        'search_q': search_q,
    })


def educator_public_profile(request, unique_link):
    profile = get_object_or_404(EducatorProfile, unique_link=unique_link)
    educator = profile.user
    courses = Course.objects.filter(educator=educator, is_published=True)
    
    is_following = False
    if request.user.is_authenticated:
        is_following = Follower.objects.filter(student=request.user, educator=educator).exists()

    return render(request, 'public/educator_profile.html', {
        'educator': educator,
        'profile': profile,
        'courses': courses,
        'is_following': is_following,
    })


def student_dashboard(request):
    if not request.user.is_authenticated or request.user.role != 'student':
        return redirect('login')
    student = request.user
    enrollments = Enrollment.objects.filter(student=student).select_related('course', 'course__educator')
    followed_educators = Follower.objects.filter(student=student).select_related('educator', 'educator__educator_profile')
    
    followed_educator_ids = followed_educators.values_list('educator_id', flat=True)
    free_lessons = Lesson.objects.filter(
        module__course__educator_id__in=followed_educator_ids,
        is_preview=True,
        module__course__is_published=True
    ).select_related('module', 'module__course', 'module__course__educator').order_by('-created_at')[:6]

    return render(request, 'student/dashboard.html', {
        'enrollments': enrollments,
        'student': student,
        'followed_educators': followed_educators,
        'free_lessons': free_lessons,
    })
