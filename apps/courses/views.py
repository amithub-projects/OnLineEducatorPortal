from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.text import slugify
from django.db.models import Count, Q
import uuid
import re

from .models import Course, Module, Lesson, Enrollment, Category
from apps.authentication.models import User, Follower
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


def get_educator_courses(user):
    return Course.objects.filter(
        Q(educator=user) | 
        Q(assigned_educator=user) | 
        Q(educator__educator_profile__parent_institute=user) |
        Q(modules__assigned_sub_educators=user)
    ).distinct()

@educator_required
def educator_dashboard(request):
    educator = request.user
    courses = get_educator_courses(educator).annotate(student_count=Count('enrollments'))
    total_students = Enrollment.objects.filter(course__in=get_educator_courses(educator), payment_status='paid').values('student').distinct().count()
    total_courses = courses.count()
    upcoming_classes = ClassSchedule.objects.filter(
        Q(educator=educator) | Q(assigned_sub_educator=educator),
        is_cancelled=False
    ).select_related('assigned_sub_educator', 'course', 'live_session').order_by('start_time')[:5]
    recent_payments = Payment.objects.filter(course__in=get_educator_courses(educator), status='captured').order_by('-created_at')[:5]
    total_revenue = sum(p.amount for p in Payment.objects.filter(course__in=get_educator_courses(educator), status='captured'))
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
    courses = get_educator_courses(request.user).annotate(student_count=Count('enrollments'))
    return render(request, 'educator/course_list.html', {'courses': courses})


@educator_required
def course_create(request):
    if hasattr(request.user, 'educator_profile') and request.user.educator_profile.parent_institute:
        messages.error(request, 'Sub-educators do not have permission to create courses. Only the institute can create courses.')
        return redirect('course_list')
        
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
    course = get_object_or_404(get_educator_courses(request.user), pk=pk)
    modules = Module.objects.filter(course=course).prefetch_related('lessons', 'assigned_sub_educators')
    if hasattr(request.user, 'educator_profile') and request.user.educator_profile.parent_institute:
        modules = modules.filter(assigned_sub_educators=request.user)
    enrolled_students = Enrollment.objects.filter(course=course, payment_status='paid').select_related('student')
    files = CourseFile.objects.filter(course=course)
    sub_educators = User.objects.filter(educator_profile__parent_institute=course.educator).select_related('educator_profile')
    return render(request, 'educator/course_detail.html', {
        'course': course,
        'modules': modules,
        'enrolled_students': enrolled_students,
        'files': files,
        'sub_educators': sub_educators,
    })


@educator_required
def course_edit(request, pk):
    if hasattr(request.user, 'educator_profile') and request.user.educator_profile.parent_institute:
        messages.error(request, 'Sub-educators do not have permission to edit courses.')
        return redirect('course_detail_educator', pk=pk)
        
    course = get_object_or_404(get_educator_courses(request.user), pk=pk)
    categories = Category.objects.all()
    sub_educators = None
    if hasattr(request.user, 'educator_profile') and request.user.educator_profile.institute_name:
        sub_educators = User.objects.filter(educator_profile__parent_institute=request.user)

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
        
        assigned_educator_id = request.POST.get('assigned_educator')
        if assigned_educator_id:
            course.assigned_educator_id = assigned_educator_id
        else:
            course.assigned_educator = None

        if request.FILES.get('thumbnail'):
            course.thumbnail = request.FILES['thumbnail']
        course.save()
        messages.success(request, 'Course updated successfully!')
        return redirect('course_detail_educator', pk=pk)
    return render(request, 'educator/course_edit.html', {'course': course, 'categories': categories, 'sub_educators': sub_educators})


@educator_required
def course_delete(request, pk):
    if hasattr(request.user, 'educator_profile') and request.user.educator_profile.parent_institute:
        messages.error(request, 'Sub-educators do not have permission to delete courses.')
        return redirect('course_list')
        
    course = get_object_or_404(get_educator_courses(request.user), pk=pk)
    if request.method == 'POST':
        course.delete()
        messages.success(request, 'Course deleted.')
        return redirect('course_list')
    return render(request, 'educator/course_confirm_delete.html', {'course': course})


@educator_required
def module_create(request, course_pk):
    course = get_object_or_404(get_educator_courses(request.user), pk=course_pk)
    if hasattr(request.user, 'educator_profile') and request.user.educator_profile.parent_institute:
        messages.error(request, 'Sub-educators do not have permission to add subjects.')
        return redirect('course_detail_educator', pk=course_pk)
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
    module = get_object_or_404(Module, pk=module_pk, course__in=get_educator_courses(request.user))
    if hasattr(request.user, 'educator_profile') and request.user.educator_profile.parent_institute:
        messages.error(request, 'Sub-educators do not have permission to modify subjects or add lessons.')
        return redirect('course_detail_educator', pk=module.course.pk)
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

    # Enforce following constraint before enrolling
    is_following = Follower.objects.filter(student=request.user, educator=course.educator).exists()
    if not is_following and hasattr(course.educator, 'educator_profile') and course.educator.educator_profile.parent_institute:
        is_following = Follower.objects.filter(student=request.user, educator=course.educator.educator_profile.parent_institute).exists()

    if not is_following and request.user != course.educator:
        messages.warning(request, f'Please follow {course.educator.full_name} to enroll in their courses.')
        return redirect('educator_profile', unique_link=course.educator.educator_profile.unique_link)

    existing = Enrollment.objects.filter(student=request.user, course=course).first()
    if existing:
        if existing.payment_status == 'paid':
            messages.info(request, 'You are already enrolled in this course.')
            return redirect('course_learn', enrollment_pk=existing.pk)
        else:
            return redirect('payment_checkout', course_pk=course.pk)

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
    enrollment = get_object_or_404(Enrollment, pk=enrollment_pk, student=request.user)
    if enrollment.payment_status != 'paid':
        return redirect('payment_checkout', course_pk=enrollment.course.pk)
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
    
    # Enforce following constraint
    if request.user.role == 'student':
        is_following = Follower.objects.filter(student=request.user, educator=course.educator).exists()
        if not is_following and hasattr(course.educator, 'educator_profile') and course.educator.educator_profile.parent_institute:
            is_following = Follower.objects.filter(student=request.user, educator=course.educator.educator_profile.parent_institute).exists()
        
        if not is_following and request.user != course.educator:
            messages.warning(request, f'Please follow {course.educator.full_name} to view their courses.')
            return redirect('educator_profile', unique_link=course.educator.educator_profile.unique_link)

    # Content isolation
    if request.user.role == 'student' and request.user.linked_educator:
        if course not in get_educator_courses(request.user.linked_educator):
            messages.error(request, 'You do not have permission to view this course.')
            return redirect('student_dashboard')

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
    courses = get_educator_courses(request.user)
    enrollments = Enrollment.objects.filter(
        course__in=get_educator_courses(request.user),
        payment_status='paid'
    ).select_related('student', 'course').order_by('-enrolled_at')
    return render(request, 'educator/student_management.html', {
        'enrollments': enrollments,
        'courses': courses,
    })


@educator_required
def student_detail_educator(request, pk):
    student = get_object_or_404(User, pk=pk, role='student')
    educator_courses = get_educator_courses(request.user)
    
    # Check if student is enrolled in any of this educator's courses
    if not Enrollment.objects.filter(student=student, course__in=educator_courses, payment_status='paid').exists():
        messages.error(request, "Access denied. Student is not enrolled in your courses.")
        return redirect('student_management')
        
    enrollments = Enrollment.objects.filter(student=student, course__in=educator_courses).select_related('course', 'course__educator')
    payments = Payment.objects.filter(student=student, course__in=educator_courses).select_related('course')
    
    return render(request, 'educator/student_detail.html', {
        'student': student,
        'enrollments': enrollments,
        'payments': payments,
    })



def lesson_preview(request, lesson_pk):
    if not request.user.is_authenticated:
        messages.info(request, 'Please login to watch lessons.')
        return redirect('login')
        
    lesson = get_object_or_404(Lesson, pk=lesson_pk)
    course = lesson.module.course
    
    if request.user.role == 'student' and request.user.linked_educator:
        if course not in get_educator_courses(request.user.linked_educator):
            messages.error(request, 'You do not have permission to view this content.')
            return redirect('student_dashboard')

    is_enrolled = Enrollment.objects.filter(
        student=request.user, 
        course=course, 
        payment_status='paid'
    ).exists()

    is_following = Follower.objects.filter(student=request.user, educator=course.educator).exists()
    if not is_following and hasattr(course.educator, 'educator_profile') and course.educator.educator_profile.parent_institute:
        is_following = Follower.objects.filter(student=request.user, educator=course.educator.educator_profile.parent_institute).exists()

    # Determine access permission based on lesson type
    if lesson.is_preview:
        # Free video: must follow the educator/institute to watch!
        has_access = (is_following or is_enrolled or request.user == course.educator)
        if not has_access:
            messages.warning(request, f'Please follow {course.educator.full_name} to unlock this free video!')
            return redirect('educator_profile', unique_link=course.educator.educator_profile.unique_link)
    else:
        # Premium video: must be enrolled to watch!
        has_access = (is_enrolled or request.user == course.educator)
        if not has_access:
            messages.error(request, 'This is a premium lesson. Please enroll to watch.')
            return redirect('course_public_detail', slug=course.slug)

    youtube_id = get_youtube_id(lesson.video_url)

    return render(request, 'public/lesson_preview.html', {
        'lesson': lesson,
        'course': course,
        'youtube_id': youtube_id,
    })

from apps.authentication.forms import SubEducatorCreationForm
from apps.authentication.models import EducatorProfile, PromoCode

@educator_required
def manage_sub_educators(request):
    if not hasattr(request.user, 'educator_profile') or not request.user.educator_profile.institute_name:
        messages.error(request, 'Only institutes can manage sub-educators.')
        return redirect('educator_dashboard')
    
    courses = Course.objects.filter(educator=request.user)
    selected_course_id = request.GET.get('course')
    
    sub_educators = User.objects.filter(educator_profile__parent_institute=request.user).prefetch_related('assigned_subjects__course')
    if selected_course_id:
        sub_educators = sub_educators.filter(assigned_subjects__course_id=selected_course_id).distinct()
        
    return render(request, 'educator/manage_sub_educators.html', {
        'sub_educators': sub_educators,
        'courses': courses,
        'selected_course_id': selected_course_id,
    })

@educator_required
def add_sub_educator(request):
    if not hasattr(request.user, 'educator_profile') or not request.user.educator_profile.institute_name:
        messages.error(request, 'Only institutes can add sub-educators.')
        return redirect('educator_dashboard')
        
    form = SubEducatorCreationForm(request.POST or None)
    courses = Course.objects.filter(educator=request.user).prefetch_related('modules')
    # Build a flat list of subjects with course info for the template
    subjects_by_course = [
        {'course': course, 'subjects': list(course.modules.all())}
        for course in courses
        if course.modules.exists()
    ]
    
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        EducatorProfile.objects.create(
            user=user,
            parent_institute=request.user
        )
        
        # Assign selected subjects (Modules) to this sub-educator via M2M
        subject_ids = request.POST.getlist('assigned_subjects')
        for sid in subject_ids:
            module = Module.objects.filter(id=sid, course__educator=request.user).first()
            if module:
                module.assigned_sub_educators.add(user)
                
        messages.success(request, f'Sub-educator {user.full_name} created successfully!')
        return redirect('manage_sub_educators')
        
    return render(request, 'educator/add_sub_educator.html', {
        'form': form,
        'subjects_by_course': subjects_by_course,
    })

@educator_required
def assign_courses_to_sub_educator(request, sub_id):
    if not hasattr(request.user, 'educator_profile') or not request.user.educator_profile.institute_name:
        messages.error(request, 'Only institutes can assign subjects to sub-educators.')
        return redirect('educator_dashboard')

    sub_educator = get_object_or_404(User, pk=sub_id, educator_profile__parent_institute=request.user)
    institute_courses = Course.objects.filter(educator=request.user).prefetch_related('modules')
    # All subjects belonging to this institute's courses
    all_subjects = Module.objects.filter(course__educator=request.user)
    # Subjects currently assigned to this sub-educator
    assigned_subject_ids = list(
        all_subjects.filter(assigned_sub_educators=sub_educator).values_list('id', flat=True)
    )
    subjects_by_course = [
        {'course': course, 'subjects': list(course.modules.all())}
        for course in institute_courses
        if course.modules.exists()
    ]

    if request.method == 'POST':
        selected_subject_ids = request.POST.getlist('assigned_subjects')
        selected_subject_ids = [int(i) for i in selected_subject_ids if i.isdigit()]

        # Remove sub_educator from subjects not in the selected list
        for module in all_subjects.filter(assigned_sub_educators=sub_educator).exclude(id__in=selected_subject_ids):
            module.assigned_sub_educators.remove(sub_educator)

        # Add sub_educator to selected subjects
        for module in all_subjects.filter(id__in=selected_subject_ids):
            module.assigned_sub_educators.add(sub_educator)

        messages.success(request, f'Subjects successfully assigned to {sub_educator.full_name}.')
        return redirect('manage_sub_educators')

    return render(request, 'educator/assign_courses.html', {
        'sub_educator': sub_educator,
        'subjects_by_course': subjects_by_course,
        'assigned_subject_ids': assigned_subject_ids,
    })

@educator_required
def toggle_sub_educator_status(request, sub_id):
    if not hasattr(request.user, 'educator_profile') or not request.user.educator_profile.institute_name:
        messages.error(request, 'Only institutes can manage sub-educators.')
        return redirect('educator_dashboard')
        
    sub_educator = get_object_or_404(User, pk=sub_id, educator_profile__parent_institute=request.user)
    
    if request.method == 'POST':
        sub_educator.is_active = not sub_educator.is_active
        sub_educator.save()
        status = "activated" if sub_educator.is_active else "suspended"
        messages.success(request, f'Sub-educator {sub_educator.full_name} has been {status} successfully.')
        
    return redirect('manage_sub_educators')

@educator_required
def delete_sub_educator(request, sub_id):
    if not hasattr(request.user, 'educator_profile') or not request.user.educator_profile.institute_name:
        messages.error(request, 'Only institutes can manage sub-educators.')
        return redirect('educator_dashboard')
        
    sub_educator = get_object_or_404(User, pk=sub_id, educator_profile__parent_institute=request.user)
    
    if request.method == 'POST':
        name = sub_educator.full_name
        sub_educator.delete()
        messages.success(request, f'Sub-educator {name} has been removed successfully.')
        
    return redirect('manage_sub_educators')

import string
import random

@educator_required
def manage_promo_codes(request):
    # Get all educators under this institute (if the user is an institute)
    if hasattr(request.user, 'educator_profile') and request.user.educator_profile.institute_name and not request.user.educator_profile.parent_institute:
        sub_educators = list(User.objects.filter(educator_profile__parent_institute=request.user))
    else:
        sub_educators = []
        
    all_educators = [request.user] + sub_educators

    if request.method == 'POST':
        action = request.POST.get('action')
        educator_id = request.POST.get('educator_id')
        
        if action == 'generate' and educator_id:
            target_educator = get_object_or_404(User, pk=educator_id)
            if target_educator in all_educators:
                if not hasattr(target_educator, 'promo_code_obj'):
                    # Generate random 6-character alphanumeric code
                    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    while PromoCode.objects.filter(code=code).exists():
                        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    
                    PromoCode.objects.create(
                        code=code,
                        educator=target_educator,
                        created_by=request.user
                    )
                    messages.success(request, f'Promo code generated for {target_educator.full_name}.')
        
        elif action == 'toggle' and educator_id:
            target_educator = get_object_or_404(User, pk=educator_id)
            if target_educator in all_educators and hasattr(target_educator, 'promo_code_obj'):
                promo = target_educator.promo_code_obj
                promo.is_active = not promo.is_active
                promo.save()
                status = "activated" if promo.is_active else "deactivated"
                messages.success(request, f'Promo code {status} for {target_educator.full_name}.')

        return redirect('manage_promo_codes')

    return render(request, 'educator/manage_promo_codes.html', {
        'educators': all_educators,
    })


@educator_required
def assign_subject_sub_educators(request, module_pk):
    module = get_object_or_404(Module, pk=module_pk)
    # Check permission: only the course creator can assign sub-educators
    if module.course.educator != request.user:
        messages.error(request, 'You do not have permission to assign sub-educators for this course.')
        return redirect('course_detail_educator', pk=module.course.pk)
        
    if request.method == 'POST':
        sub_educator_ids = request.POST.getlist('sub_educators')
        # Filter to only allow sub-educators of this institute
        valid_sub_educators = User.objects.filter(
            pk__in=sub_educator_ids,
            educator_profile__parent_institute=request.user
        )
        module.assigned_sub_educators.set(valid_sub_educators)
        messages.success(request, f'Sub-educators assigned to subject "{module.title}" successfully.')
    return redirect('course_detail_educator', pk=module.course.pk)

