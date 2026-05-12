from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from apps.authentication.models import User, EducatorProfile
from apps.courses.models import Course, Enrollment, Category
from apps.payments.models import Payment
from apps.core.models import SiteSettings, Announcement, ContactMessage
from apps.live_classes.models import LiveSession
from apps.scheduling.models import ClassSchedule


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.role != 'admin':
            messages.error(request, 'Admin access required.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


@admin_required
def admin_dashboard(request):
    total_educators = User.objects.filter(role='educator').count()
    total_students = User.objects.filter(role='student').count()
    total_courses = Course.objects.count()
    active_live = LiveSession.objects.filter(is_active=True).count()
    total_revenue = Payment.objects.filter(status='captured').aggregate(Sum('amount'))['amount__sum'] or 0
    pending_educators = User.objects.filter(role='educator', is_approved=False).count()
    recent_payments = Payment.objects.filter(status='captured').order_by('-created_at')[:10]
    recent_users = User.objects.order_by('-date_joined')[:10]
    unread_messages = ContactMessage.objects.filter(is_read=False).count()
    return render(request, 'admin_panel/dashboard.html', {
        'total_educators': total_educators,
        'total_students': total_students,
        'total_courses': total_courses,
        'active_live': active_live,
        'total_revenue': total_revenue,
        'pending_educators': pending_educators,
        'recent_payments': recent_payments,
        'recent_users': recent_users,
        'unread_messages': unread_messages,
    })


@admin_required
def manage_educators(request):
    educators = User.objects.filter(role='educator').select_related('educator_profile').order_by('-date_joined')
    return render(request, 'admin_panel/educators.html', {'educators': educators})


@admin_required
def approve_educator(request, pk):
    educator = get_object_or_404(User, pk=pk, role='educator')
    educator.is_approved = True
    educator.save()
    send_mail(
        'Your Educator Account has been Approved!',
        f'Congratulations {educator.full_name}! Your educator account on Online Educator Portal has been approved. You can now log in and start creating courses.',
        settings.DEFAULT_FROM_EMAIL,
        [educator.email],
        fail_silently=True,
    )
    messages.success(request, f'Educator {educator.full_name} approved and notified.')
    return redirect('manage_educators')


@admin_required
def suspend_educator(request, pk):
    educator = get_object_or_404(User, pk=pk, role='educator')
    educator.is_approved = False
    educator.is_active = False
    educator.save()
    messages.warning(request, f'Educator {educator.full_name} has been suspended.')
    return redirect('manage_educators')


@admin_required
def create_educator_admin(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '').strip()
        subjects = request.POST.get('subjects', '')
        if full_name and email and password:
            if User.objects.filter(email=email).exists():
                messages.error(request, 'An account with this email already exists.')
            else:
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    full_name=full_name,
                    phone=phone,
                    role='educator',
                    is_approved=True,
                )
                EducatorProfile.objects.create(user=user, subjects=subjects)
                send_mail(
                    'Your Educator Account Credentials',
                    f'Hello {full_name},\n\nYour educator account has been created.\n\nEmail: {email}\nPassword: {password}\n\nPlease log in and change your password immediately.\n\nPortal: http://localhost:8000',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=True,
                )
                messages.success(request, f'Educator account created for {full_name}. Credentials sent via email.')
                return redirect('manage_educators')
        else:
            messages.error(request, 'Please fill in all required fields.')
    return render(request, 'admin_panel/create_educator.html')


@admin_required
def delete_user(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user.role == 'admin':
        messages.error(request, 'Cannot delete admin accounts.')
        return redirect('admin_dashboard')
    if request.method == 'POST':
        name = user.full_name
        user.delete()
        messages.success(request, f'User {name} deleted.')
        return redirect('manage_educators' if user.role == 'educator' else 'manage_students')
    return render(request, 'admin_panel/confirm_delete.html', {'user': user})


@admin_required
def manage_students(request):
    students = User.objects.filter(role='student').order_by('-date_joined')
    return render(request, 'admin_panel/students.html', {'students': students})


@admin_required
def student_detail_admin(request, pk):
    student = get_object_or_404(User, pk=pk, role='student')
    enrollments = Enrollment.objects.filter(student=student).select_related('course', 'course__educator')
    payments = Payment.objects.filter(student=student).select_related('course')
    return render(request, 'admin_panel/student_detail.html', {
        'student': student,
        'enrollments': enrollments,
        'payments': payments,
    })


@admin_required
def manage_courses(request):
    courses = Course.objects.all().select_related('educator', 'category').annotate(
        student_count=Count('enrollments')
    ).order_by('-created_at')
    return render(request, 'admin_panel/courses.html', {'courses': courses})


@admin_required
def manage_payments(request):
    payments = Payment.objects.all().select_related('student', 'course', 'course__educator').order_by('-created_at')
    total_revenue = payments.filter(status='captured').aggregate(Sum('amount'))['amount__sum'] or 0
    return render(request, 'admin_panel/payments.html', {
        'payments': payments,
        'total_revenue': total_revenue,
    })


@admin_required
def site_settings_admin(request):
    site = SiteSettings.get_settings()
    if request.method == 'POST':
        site.site_name = request.POST.get('site_name', site.site_name)
        site.tagline = request.POST.get('tagline', site.tagline)
        site.hero_title = request.POST.get('hero_title', site.hero_title)
        site.hero_subtitle = request.POST.get('hero_subtitle', site.hero_subtitle)
        site.about_content = request.POST.get('about_content', site.about_content)
        site.contact_email = request.POST.get('contact_email', site.contact_email)
        site.contact_phone = request.POST.get('contact_phone', site.contact_phone)
        site.contact_address = request.POST.get('contact_address', site.contact_address)
        site.facebook_url = request.POST.get('facebook_url', site.facebook_url)
        site.twitter_url = request.POST.get('twitter_url', site.twitter_url)
        site.linkedin_url = request.POST.get('linkedin_url', site.linkedin_url)
        if request.FILES.get('logo'):
            site.logo = request.FILES['logo']
        site.save()
        messages.success(request, 'Site settings updated!')
        return redirect('site_settings_admin')
    return render(request, 'admin_panel/site_settings.html', {'site': site})


@admin_required
def announcements_admin(request):
    announcements = Announcement.objects.all().order_by('-created_at')
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        if title and content:
            Announcement.objects.create(title=title, content=content, created_by=request.user)
            messages.success(request, 'Announcement created!')
        return redirect('announcements_admin')
    return render(request, 'admin_panel/announcements.html', {'announcements': announcements})


@admin_required
def toggle_announcement(request, pk):
    ann = get_object_or_404(Announcement, pk=pk)
    ann.is_active = not ann.is_active
    ann.save()
    return redirect('announcements_admin')


@admin_required
def monitor_live_sessions(request):
    sessions = LiveSession.objects.filter(is_active=True).select_related('educator', 'course')
    all_sessions = LiveSession.objects.all().select_related('educator', 'course').order_by('-created_at')
    return render(request, 'admin_panel/live_monitor.html', {
        'active_sessions': sessions,
        'all_sessions': all_sessions,
    })


@admin_required
def contact_messages(request):
    msgs = ContactMessage.objects.all().order_by('-created_at')
    ContactMessage.objects.filter(is_read=False).update(is_read=True)
    return render(request, 'admin_panel/contact_messages.html', {'messages_list': msgs})


@admin_required
def manage_categories(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        from django.utils.text import slugify
        if name:
            Category.objects.get_or_create(name=name, defaults={'slug': slugify(name)})
            messages.success(request, f'Category "{name}" added.')
        return redirect('manage_categories')
    return render(request, 'admin_panel/categories.html', {'categories': categories})


@admin_required
def admin_course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    modules = course.modules.all().prefetch_related('lessons')
    return render(request, 'admin_panel/course_detail.html', {'course': course, 'modules': modules})

@admin_required
def admin_delete_lesson(request, pk):
    from apps.courses.models import Lesson
    lesson = get_object_or_404(Lesson, pk=pk)
    course_id = lesson.module.course.id
    if request.method == 'POST':
        lesson.delete()
        messages.success(request, 'Lesson/Video deleted successfully.')
    return redirect('admin_course_detail', pk=course_id)
