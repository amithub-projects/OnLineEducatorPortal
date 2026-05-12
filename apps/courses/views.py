from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.text import slugify
from django.db.models import Count
import uuid
import re

from .models import Course, Module, Lesson, Enrollment, Category
from apps.authentication.models import User
from apps.scheduling.models import ClassSchedule
from apps.content.models import CourseFile
from apps.payments.models import Payment


def educator_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.role != 'educator':
            messages.error(request, 'Access denied. Educator account required.')
            return redirect('home')
        if not request.user.is_approved:
            messages.warning(request, 'Your account is pending admin approval.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


@educator_required
def educator_dashboard(request):
    educator = request.user
    courses = Course.objects.filter(educator=educator).annotate(student_count=Count('enrollments'))
    total_students = Enrollment.objects.filter(course__educator=educator, payment_status='paid').values('student').distinct().count()
    total_courses = courses.count()
    upcoming_classes = ClassSchedule.objects.filter(educator=educator, is_cancelled=False).order_by('start_time')[:5]
    recent_payments = Payment.objects.filter(course__educator=educator, status='captured').order_by('-created_at')[:5]
    total_revenue = sum(p.amount for p in Payment.objects.filter(course__educator=educator, status='captured'))
    return render(request, 'educator/dashboard.html', {
        'courses': courses,
        'total_students': total_students,
        'total_courses': total_courses,
        'upcoming_classes': upcoming_classes,
        'recent_payments': recent_payments,
        'total_revenue': total_revenue,
    })


@educator_required
def course_list(request):
    courses = Course.objects.filter(educator=request.user).annotate(student_count=Count('enrollments'))
    return render(request, 'educator/course_list.html', {'courses': courses})


@educator_required
def course_create(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        price = request.POST.get('price')
        if not price: price = 0
        duration_hours = request.POST.get('duration_hours')
        if not duration_hours: duration_hours = 0
        is_free = request.POST.get('is_free') == 'on'
        thumbnail = request.FILES.get('thumbnail')

        if title and description:
            course = Course.objects.create(
                educator=request.user,
                title=title,
                description=description,
                price=float(price) if not is_free else 0,
                duration_hours=int(duration_hours),
                is_free=is_free,
                thumbnail=thumbnail,
            )
            messages.success(request, f'Course "{title}" created successfully!')
            return redirect('course_detail_educator', pk=course.pk)
        else:
            messages.error(request, 'Please fill in all required fields.')

    return render(request, 'educator/course_create.html', {'categories': categories})


@educator_required
def course_detail_educator(request, pk):
    course = get_object_or_404(Course, pk=pk, educator=request.user)
    modules = Module.objects.filter(course=course).prefetch_related('lessons')
    enrolled_students = Enrollment.objects.filter(course=course, payment_status='paid').select_related('student')
    files = CourseFile.objects.filter(course=course)
    return render(request, 'educator/course_detail.html', {
        'course': course,
        'modules': modules,
        'enrolled_students': enrolled_students,
        'files': files,
    })


@educator_required
def course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk, educator=request.user)
    categories = Category.objects.all()
    if request.method == 'POST':
        course.title = request.POST.get('title', course.title)
        course.description = request.POST.get('description', course.description)
        category_id = request.POST.get('category')
        course.category_id = category_id if category_id else None
        course.price = float(request.POST.get('price') or 0)
        course.level = request.POST.get('level', course.level)
        course.duration_hours = int(request.POST.get('duration_hours') or 0)
        course.is_free = request.POST.get('is_free') == 'on'
        course.is_published = request.POST.get('is_published') == 'on'
        if request.FILES.get('thumbnail'):
            course.thumbnail = request.FILES['thumbnail']
        course.save()
        messages.success(request, 'Course updated successfully!')
        return redirect('course_detail_educator', pk=pk)
    return render(request, 'educator/course_edit.html', {'course': course, 'categories': categories})


@educator_required
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk, educator=request.user)
    if request.method == 'POST':
        course.delete()
        messages.success(request, 'Course deleted.')
        return redirect('course_list')
    return render(request, 'educator/course_confirm_delete.html', {'course': course})


@educator_required
def module_create(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk, educator=request.user)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if title:
            order = Module.objects.filter(course=course).count() + 1
            Module.objects.create(course=course, title=title, order=order)
            messages.success(request, 'Module added.')
        return redirect('course_detail_educator', pk=course_pk)
    return redirect('course_detail_educator', pk=course_pk)


@educator_required
def lesson_create(request, module_pk):
    module = get_object_or_404(Module, pk=module_pk, course__educator=request.user)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '')
        video_url = request.POST.get('video_url', '')
        video_file = request.FILES.get('video_file')
        duration = request.POST.get('duration_minutes')
        if not duration: duration = 0
        is_preview = request.POST.get('is_preview') == 'on'
        if title:
            order = Lesson.objects.filter(module=module).count() + 1
            Lesson.objects.create(
                module=module,
                title=title,
                description=description,
                video_url=video_url,
                video_file=video_file,
                duration_minutes=int(duration),
                is_preview=is_preview,
                order=order,
            )
            messages.success(request, 'Lesson added.')
        return redirect('course_detail_educator', pk=module.course.pk)
    return redirect('course_detail_educator', pk=module.course.pk)


@login_required
def enroll_course(request, slug):
    course = get_object_or_404(Course, slug=slug, is_published=True)
    if request.user.role != 'student':
        messages.error(request, 'Only students can enroll in courses.')
        return redirect('course_public_detail', slug=slug)

    existing = Enrollment.objects.filter(student=request.user, course=course).first()
    if existing:
        if existing.payment_status == 'paid':
            messages.info(request, 'You are already enrolled in this course.')
        return redirect('course_learn', enrollment_pk=existing.pk)

    if course.is_free or course.price == 0:
        enrollment = Enrollment.objects.create(student=request.user, course=course, payment_status='paid')
        messages.success(request, f'Enrolled in "{course.title}" for free!')
        return redirect('course_learn', enrollment_pk=enrollment.pk)
    else:
        enrollment, _ = Enrollment.objects.get_or_create(student=request.user, course=course)
        return redirect('payment_checkout', course_pk=course.pk)


def get_youtube_id(url):
    if not url: return None
    import re
    pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None


@login_required
def course_learn(request, enrollment_pk):
    enrollment = get_object_or_404(Enrollment, pk=enrollment_pk, student=request.user, payment_status='paid')
    course = enrollment.course
    modules = Module.objects.filter(course=course).prefetch_related('lessons')
    current_lesson_id = request.GET.get('lesson')
    current_lesson = None
    if current_lesson_id:
        try:
            current_lesson = Lesson.objects.get(pk=current_lesson_id, module__course=course)
        except Lesson.DoesNotExist:
            pass
    if not current_lesson and modules.exists() and modules.first().lessons.exists():
        current_lesson = modules.first().lessons.first()
    
    youtube_id = get_youtube_id(current_lesson.video_url) if current_lesson else None

    return render(request, 'student/course_learn.html', {
        'enrollment': enrollment,
        'course': course,
        'modules': modules,
        'current_lesson': current_lesson,
        'youtube_id': youtube_id,
    })


@login_required
def course_public_detail(request, slug):
    course = get_object_or_404(Course, slug=slug, is_published=True)
    modules = Module.objects.filter(course=course).prefetch_related('lessons')
    is_enrolled = False
    enrollment = None
    if request.user.is_authenticated and request.user.role == 'student':
        enrollment = Enrollment.objects.filter(student=request.user, course=course, payment_status='paid').first()
        is_enrolled = enrollment is not None
    return render(request, 'public/course_detail.html', {
        'course': course,
        'modules': modules,
        'is_enrolled': is_enrolled,
        'enrollment': enrollment,
    })


@educator_required
def student_management(request):
    courses = Course.objects.filter(educator=request.user)
    enrollments = Enrollment.objects.filter(
        course__educator=request.user,
        payment_status='paid'
    ).select_related('student', 'course').order_by('-enrolled_at')
    return render(request, 'educator/student_management.html', {
        'enrollments': enrollments,
        'courses': courses,
    })


def lesson_preview(request, lesson_pk):
    lesson = get_object_or_404(Lesson, pk=lesson_pk)
    course = lesson.module.course
    
    # Check if user has access
    has_access = lesson.is_preview
    
    if not has_access and request.user.is_authenticated:
        # Check enrollment if not a preview
        has_access = Enrollment.objects.filter(
            student=request.user, 
            course=course, 
            payment_status='paid'
        ).exists() or request.user == course.educator

    if not has_access:
        messages.error(request, 'This is a paid lesson. Please enroll to watch.')
        return redirect('course_public_detail', slug=course.slug)

    youtube_id = get_youtube_id(lesson.video_url)

    return render(request, 'public/lesson_preview.html', {
        'lesson': lesson,
        'course': course,
        'youtube_id': youtube_id,
    })
