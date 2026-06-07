from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse

from .models import ClassSchedule, Attendance
from apps.courses.models import Course, Enrollment, Module
from apps.courses.views import educator_required, get_educator_courses
from apps.authentication.models import User


@educator_required
def schedule_list(request):
    educator = request.user
    profile = getattr(educator, 'educator_profile', None)

    # Build query: own schedules + institute schedules if sub-educator
    schedule_filter = Q(educator=educator) | Q(assigned_sub_educator=educator)
    if profile and profile.parent_institute:
        # Sub-educator: also show institute's schedules assigned to them
        schedule_filter = Q(assigned_sub_educator=educator) | Q(educator=educator)

    schedules = ClassSchedule.objects.filter(schedule_filter).select_related(
        'educator', 'course', 'assigned_sub_educator',
    ).order_by('start_time')
    upcoming = schedules.filter(start_time__gte=timezone.now())
    past = schedules.filter(start_time__lt=timezone.now())

    is_institute = profile and profile.institute_name and not profile.parent_institute
    is_sub_educator = profile and profile.parent_institute is not None

    return render(request, 'educator/schedule_list.html', {
        'schedules': schedules,
        'upcoming': upcoming,
        'past': past,
        'is_institute': is_institute,
        'is_sub_educator': is_sub_educator,
    })


@educator_required
def schedule_create(request):
    educator = request.user
    profile = getattr(educator, 'educator_profile', None)
    is_institute = profile and profile.institute_name and not profile.parent_institute
    is_sub_educator = profile and profile.parent_institute is not None

    # Sub-educators cannot create schedules — only institutes can
    if is_sub_educator:
        messages.error(request, 'Only the institute can schedule classes. Please contact your institute.')
        return redirect('schedule_list')

    courses = Course.objects.filter(educator=educator)
    if not courses.exists():
        messages.error(request, 'You must create a course before you can schedule a live class.')
        return redirect('course_create')

    # Get sub-educators for the dropdown (institutes only)
    sub_educators = []
    if is_institute:
        sub_educators = User.objects.filter(
            educator_profile__parent_institute=educator
        ).select_related('educator_profile')

    # Build a hierarchy map: course_id -> { "subjects": { subject_id -> { "title": ..., "sub_educators": [ { "id": ..., "full_name": ... } ] } } }
    hierarchy_map = {}
    for c in courses:
        hierarchy_map[str(c.id)] = {
            'id': c.id,
            'title': c.title,
            'subjects': {}
        }
        for m in c.modules.all():
            hierarchy_map[str(c.id)]['subjects'][str(m.id)] = {
                'id': m.id,
                'title': m.title,
                'sub_educators': [
                    {'id': sub.id, 'full_name': sub.full_name}
                    for sub in m.assigned_sub_educators.all()
                ]
            }

    if request.method == 'POST':
        course_id = request.POST.get('course')
        subject_id = request.POST.get('subject')
        description = request.POST.get('description', '')
        topics_covered = request.POST.get('topics_covered', '')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        meeting_link = request.POST.get('meeting_link', '')
        send_notification = request.POST.get('send_notification') == 'on'
        sub_educator_id = request.POST.get('assigned_sub_educator')

        title = "Live Class"
        if subject_id:
            subject_obj = Module.objects.filter(id=subject_id).first()
            if subject_obj:
                title = subject_obj.title

        if start_time and end_time:
            schedule = ClassSchedule.objects.create(
                educator=educator,
                course_id=course_id if course_id else None,
                subject_id=subject_id if subject_id else None,
                assigned_sub_educator_id=sub_educator_id if sub_educator_id else None,
                title=title,
                description=description,
                topics_covered=topics_covered,
                start_time=start_time,
                end_time=end_time,
                meeting_link=meeting_link,
            )

            # Send assignment notification to the assigned sub-educator
            if schedule.assigned_sub_educator:
                send_mail(
                    f'New Class Assignment: {title}',
                    f'Hi {schedule.assigned_sub_educator.full_name},\n\nYou have been assigned to conduct a live class by your institute:\n\nTitle: {title}\nTime: {start_time}\nCourse: {schedule.course.title if schedule.course else "General"}\nTopics to be Covered:\n{topics_covered or "General topics"}\n\nPlease prepare to log in and start the session at the scheduled time!',
                    settings.DEFAULT_FROM_EMAIL,
                    [schedule.assigned_sub_educator.email],
                    fail_silently=True,
                )

            # Send notifications to enrolled students
            if send_notification and course_id:
                enrolled_students = Enrollment.objects.filter(
                    course_id=course_id, payment_status='paid'
                ).select_related('student')
                student_emails = [e.student.email for e in enrolled_students]

                # Get sub-educator name for the email
                sub_name = ''
                if sub_educator_id:
                    try:
                        sub = User.objects.get(pk=sub_educator_id)
                        sub_name = f'\nInstructor: {sub.full_name}'
                    except User.DoesNotExist:
                        pass

                if student_emails:
                    send_mail(
                        f'New Class Scheduled: {title}',
                        f'A new class has been scheduled.\n\nTitle: {title}{sub_name}\nTime: {start_time}\nTopics to be Covered:\n{topics_covered or "General topics"}\nLink: {meeting_link or "Will be shared before class"}\n\nDescription: {description}',
                        settings.DEFAULT_FROM_EMAIL,
                        student_emails,
                        fail_silently=True,
                    )
            messages.success(request, f'Class "{title}" scheduled successfully!')
            return redirect('schedule_list')
        else:
            messages.error(request, 'Please fill in all required fields.')

    import json
    return render(request, 'educator/schedule_create.html', {
        'courses': courses,
        'sub_educators': sub_educators,
        'is_institute': is_institute,
        'hierarchy_map_json': json.dumps(hierarchy_map),
    })


@educator_required
def schedule_edit(request, pk):
    educator = request.user
    profile = getattr(educator, 'educator_profile', None)
    is_institute = profile and profile.institute_name and not profile.parent_institute

    schedule = get_object_or_404(ClassSchedule, pk=pk, educator=educator)
    if schedule.has_started:
        messages.error(request, 'Cannot edit a scheduled class that has already started.')
        return redirect('schedule_list')
    courses = Course.objects.filter(educator=educator)

    sub_educators = []
    if is_institute:
        sub_educators = User.objects.filter(
            educator_profile__parent_institute=educator
        ).select_related('educator_profile')

    # Build a hierarchy map: course_id -> { "subjects": { subject_id -> { "title": ..., "sub_educators": [ { "id": ..., "full_name": ... } ] } } }
    hierarchy_map = {}
    for c in courses:
        hierarchy_map[str(c.id)] = {
            'id': c.id,
            'title': c.title,
            'subjects': {}
        }
        for m in c.modules.all():
            hierarchy_map[str(c.id)]['subjects'][str(m.id)] = {
                'id': m.id,
                'title': m.title,
                'sub_educators': [
                    {'id': sub.id, 'full_name': sub.full_name}
                    for sub in m.assigned_sub_educators.all()
                ]
            }

    if request.method == 'POST':
        schedule.description = request.POST.get('description', schedule.description)
        schedule.topics_covered = request.POST.get('topics_covered', schedule.topics_covered)
        schedule.start_time = request.POST.get('start_time', schedule.start_time)
        schedule.end_time = request.POST.get('end_time', schedule.end_time)
        schedule.meeting_link = request.POST.get('meeting_link', schedule.meeting_link)
        schedule.is_cancelled = request.POST.get('is_cancelled') == 'on'

        sub_educator_id = request.POST.get('assigned_sub_educator')
        if sub_educator_id:
            schedule.assigned_sub_educator_id = sub_educator_id
        else:
            schedule.assigned_sub_educator = None

        course_id = request.POST.get('course')
        if course_id:
            schedule.course_id = course_id
        else:
            schedule.course = None

        subject_id = request.POST.get('subject')
        if subject_id:
            schedule.subject_id = subject_id
            subject_obj = Module.objects.filter(id=subject_id).first()
            if subject_obj:
                schedule.title = subject_obj.title
        else:
            schedule.subject = None

        schedule.save()
        messages.success(request, 'Schedule updated.')
        return redirect('schedule_list')

    import json
    return render(request, 'educator/schedule_edit.html', {
        'schedule': schedule,
        'courses': courses,
        'sub_educators': sub_educators,
        'is_institute': is_institute,
        'hierarchy_map_json': json.dumps(hierarchy_map),
    })


@educator_required
def schedule_cancel(request, pk):
    educator = request.user
    schedule = get_object_or_404(ClassSchedule, pk=pk, educator=educator)
    if schedule.has_started:
        messages.error(request, 'Cannot cancel a class that has already started.')
        return redirect('schedule_list')
    schedule.is_cancelled = True
    schedule.save()
    messages.success(request, 'Scheduled class has been cancelled.')
    return redirect('schedule_list')


@educator_required
def schedule_delete(request, pk):
    educator = request.user
    schedule = get_object_or_404(ClassSchedule, pk=pk, educator=educator)
    if not schedule.is_cancelled:
        messages.error(request, 'Only cancelled class schedules can be deleted.')
        return redirect('schedule_list')
    schedule.delete()
    messages.success(request, 'Scheduled class has been deleted.')
    return redirect('schedule_list')


@educator_required
def attendance_view(request, schedule_pk):
    schedule = get_object_or_404(ClassSchedule, pk=schedule_pk)
    # Allow institute or the assigned sub-educator to view attendance
    educator = request.user
    profile = getattr(educator, 'educator_profile', None)
    if schedule.educator != educator and schedule.assigned_sub_educator != educator:
        if not (profile and profile.parent_institute and schedule.educator == profile.parent_institute):
            messages.error(request, 'Access denied.')
            return redirect('schedule_list')

    attendances = Attendance.objects.filter(schedule=schedule).select_related('student')
    attendances_dict = {a.student_id: a for a in attendances}
    
    enrolled_students = []
    if schedule.course:
        enrolled_students = Enrollment.objects.filter(
            course=schedule.course, payment_status='paid'
        ).select_related('student')
        
        for enrollment in enrolled_students:
            att = attendances_dict.get(enrollment.student.pk)
            if att:
                enrollment.is_present = att.is_present
                enrollment.joined_at = att.joined_at
            else:
                enrollment.is_present = False
                enrollment.joined_at = None

    return render(request, 'educator/attendance.html', {
        'schedule': schedule,
        'attendances': attendances,
        'enrolled_students': enrolled_students,
    })



@educator_required
def mark_attendance(request, schedule_pk):
    schedule = get_object_or_404(ClassSchedule, pk=schedule_pk)
    educator = request.user
    if schedule.educator != educator and schedule.assigned_sub_educator != educator:
        messages.error(request, 'Access denied.')
        return redirect('schedule_list')

    if request.method == 'POST':
        present_ids = request.POST.getlist('present_students')
        if schedule.course:
            enrolled = Enrollment.objects.filter(course=schedule.course, payment_status='paid')
            for enrollment in enrolled:
                student = enrollment.student
                is_present = str(student.pk) in present_ids
                Attendance.objects.update_or_create(
                    schedule=schedule,
                    student=student,
                    defaults={'is_present': is_present}
                )
        messages.success(request, 'Attendance saved.')
    return redirect('attendance_view', schedule_pk=schedule_pk)
