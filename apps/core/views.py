from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.db.models import Q

from apps.authentication.models import User, EducatorProfile, Follower
from apps.courses.models import Course, Enrollment, Category, Lesson
from apps.courses.views import get_educator_courses
from .models import SiteSettings, Announcement, ContactMessage


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    site = SiteSettings.get_settings()
    announcements = Announcement.objects.filter(is_active=True).order_by('-created_at')[:3]
    featured_educators = User.objects.filter(
        role='educator', is_approved=True, is_active=True,
        educator_profile__is_featured=True
    ).select_related('educator_profile')
    
    popular_courses = Course.objects.filter(is_published=True, is_featured=True)
    
    # If the user is linked to an educator via promo code, they only see that educator
    if request.user.is_authenticated and request.user.role == 'student' and request.user.linked_educator:
        linked_edu = request.user.linked_educator
        featured_educators = featured_educators.filter(id=linked_edu.id)
        popular_courses = popular_courses.filter(id__in=get_educator_courses(linked_edu))
    
    featured_educators = featured_educators[:6]
    popular_courses = popular_courses.order_by('-created_at')[:8]
    
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


def select_course(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    if request.user.is_authenticated:
        if request.user.role == 'student':
            request.user.selected_category = category
            request.user.save()
            messages.success(request, f'Selected course: {category.name}')
            return redirect('student_dashboard')
        else:
            messages.info(request, 'Selection saved. Only students see filtered content.')
            return redirect('home')
    else:
        # Store in session for later
        request.session['selected_category_id'] = category.id
        messages.info(request, f'Selected course: {category.name}. Please login or register to continue.')
        return redirect('register_student')


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
    if category_filter:
        educators = educators.filter(educator_profile__primary_category__slug=category_filter)
    
    # Enforce student's selected category if logged in
    if request.user.is_authenticated and request.user.role == 'student':
        if request.user.linked_educator:
            # If linked via promo code, they ONLY see this educator
            educators = educators.filter(id=request.user.linked_educator.id)
        else:
            student_cat = request.user.selected_category
            if student_cat:
                educators = educators.filter(
                    Q(educator_profile__primary_category=student_cat) |
                    Q(courses__category=student_cat)
                ).distinct()

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
        if not is_following and profile.parent_institute:
            is_following = Follower.objects.filter(student=request.user, educator=profile.parent_institute).exists()

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
    selected_cat = student.selected_category

    enrollments = Enrollment.objects.filter(student=student, payment_status='paid').select_related('course', 'course__educator')
    followed_educators = Follower.objects.filter(student=student).select_related('educator', 'educator__educator_profile')
    
    # Filtered Educators based on Category
    recommended_educators = User.objects.filter(
        role='educator', is_approved=True, is_active=True
    ).select_related('educator_profile')
    
    # Course Announcements
    course_announcements = Announcement.objects.filter(is_active=True).order_by('-created_at')
    
    if student.linked_educator:
        # Strictly lock everything to linked educator
        recommended_educators = recommended_educators.filter(id=student.linked_educator.id)
        allowed_course_ids = get_educator_courses(student.linked_educator).values_list('id', flat=True)
        # Assuming announcements might not be directly linked to educators, but to categories.
        # Ideally announcements have an educator or course link. Currently they might be global or category-based.
        # If we just filter by category for now:
        if selected_cat:
            course_announcements = course_announcements.filter(Q(category=selected_cat) | Q(category__isnull=True))
        else:
            course_announcements = course_announcements.filter(category__isnull=True)
            
    else:
        if selected_cat:
            # Strict filtering: Only educators in this category or with courses in this category
            recommended_educators = recommended_educators.filter(
                Q(educator_profile__primary_category=selected_cat) |
                Q(courses__category=selected_cat)
            ).distinct()
            course_announcements = course_announcements.filter(Q(category=selected_cat) | Q(category__isnull=True))
        else:
            recommended_educators = recommended_educators[:6]
            course_announcements = course_announcements.filter(category__isnull=True)

    followed_educator_ids = list(followed_educators.values_list('educator_id', flat=True))
    if student.linked_educator and student.linked_educator.id not in followed_educator_ids:
        followed_educator_ids.append(student.linked_educator.id)
        
    free_lessons = Lesson.objects.filter(
        module__course__educator_id__in=followed_educator_ids,
        is_preview=True,
        module__course__is_published=True
    ).select_related('module', 'module__course', 'module__course__educator').order_by('-created_at')[:6]

    # Fetch scheduled classes for the student
    from django.utils import timezone
    from apps.scheduling.models import ClassSchedule
    
    upcoming_schedules = ClassSchedule.objects.none()
    
    # Get courses the student is enrolled in
    enrolled_course_ids = list(enrollments.filter(payment_status='paid').values_list('course_id', flat=True))
    
    if student.linked_educator:
        # Determine the institute or individual educator
        profile = getattr(student.linked_educator, 'educator_profile', None)
        if profile:
            if profile.parent_institute:
                # Registered under a sub-educator of an institute
                institute = profile.parent_institute
                upcoming_schedules = ClassSchedule.objects.filter(
                    Q(course_id__in=enrolled_course_ids) |
                    (Q(course__isnull=True) & (Q(educator=institute) | Q(educator__educator_profile__parent_institute=institute))),
                    start_time__gte=timezone.now(),
                    is_cancelled=False
                ).select_related('educator', 'assigned_sub_educator', 'course', 'live_session').order_by('start_time')
            elif profile.educator_type == 'institute':
                # Registered directly under an institute
                institute = student.linked_educator
                upcoming_schedules = ClassSchedule.objects.filter(
                    Q(course_id__in=enrolled_course_ids) |
                    (Q(course__isnull=True) & (Q(educator=institute) | Q(educator__educator_profile__parent_institute=institute))),
                    start_time__gte=timezone.now(),
                    is_cancelled=False
                ).select_related('educator', 'assigned_sub_educator', 'course', 'live_session').order_by('start_time')
            else:
                # Registered under an individual educator
                upcoming_schedules = ClassSchedule.objects.filter(
                    Q(course_id__in=enrolled_course_ids) |
                    (Q(course__isnull=True) & Q(educator=student.linked_educator)),
                    start_time__gte=timezone.now(),
                    is_cancelled=False
                ).select_related('educator', 'assigned_sub_educator', 'course', 'live_session').order_by('start_time')
    else:
        # Fallback to followed educators and enrolled courses
        upcoming_schedules = ClassSchedule.objects.filter(
            Q(course_id__in=enrolled_course_ids) |
            (Q(course__isnull=True) & Q(educator_id__in=followed_educator_ids)),
            start_time__gte=timezone.now(),
            is_cancelled=False
        ).select_related('educator', 'assigned_sub_educator', 'course', 'live_session').order_by('start_time')

    return render(request, 'student/dashboard.html', {
        'enrollments': enrollments,
        'student': student,
        'followed_educators': followed_educators,
        'free_lessons': free_lessons,
        'recommended_educators': recommended_educators[:6],
        'course_announcements': course_announcements[:5],
        'selected_cat': selected_cat,
        'upcoming_schedules': upcoming_schedules,
    })
