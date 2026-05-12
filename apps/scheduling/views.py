from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from .models import ClassSchedule, Attendance
from apps.courses.models import Course, Enrollment
from apps.courses.views import educator_required
from apps.authentication.models import User


@educator_required
def schedule_list(request):
    educator = request.user
    schedules = ClassSchedule.objects.filter(educator=educator).order_by('start_time')
    upcoming = schedules.filter(start_time__gte=timezone.now(), is_cancelled=False)
    past = schedules.filter(start_time__lt=timezone.now())
    return render(request, 'educator/schedule_list.html', {
        'schedules': schedules,
        'upcoming': upcoming,
        'past': past,
    })


@educator_required
def schedule_create(request):
    courses = Course.objects.filter(educator=request.user)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        course_id = request.POST.get('course')
        description = request.POST.get('description', '')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        meeting_link = request.POST.get('meeting_link', '')
        send_notification = request.POST.get('send_notification') == 'on'

        if title and start_time and end_time:
            schedule = ClassSchedule.objects.create(
                educator=request.user,
                course_id=course_id if course_id else None,
                title=title,
                description=description,
                start_time=start_time,
                end_time=end_time,
                meeting_link=meeting_link,
            )
            if send_notification and course_id:
                enrolled_students = Enrollment.objects.filter(
                    course_id=course_id, payment_status='paid'
                ).select_related('student')
                student_emails = [e.student.email for e in enrolled_students]
                if student_emails:
                    send_mail(
                        f'New Class Scheduled: {title}',
                        f'Your educator has scheduled a new class.\n\nTitle: {title}\nTime: {start_time}\nLink: {meeting_link or "Will be shared"}\n\nDescription: {description}',
                        settings.DEFAULT_FROM_EMAIL,
                        student_emails,
                        fail_silently=True,
                    )
            messages.success(request, f'Class "{title}" scheduled successfully!')
            return redirect('schedule_list')
        else:
            messages.error(request, 'Please fill in all required fields.')

    return render(request, 'educator/schedule_create.html', {'courses': courses})


@educator_required
def schedule_edit(request, pk):
    schedule = get_object_or_404(ClassSchedule, pk=pk, educator=request.user)
    courses = Course.objects.filter(educator=request.user)
    if request.method == 'POST':
        schedule.title = request.POST.get('title', schedule.title)
        schedule.description = request.POST.get('description', schedule.description)
        schedule.start_time = request.POST.get('start_time', schedule.start_time)
        schedule.end_time = request.POST.get('end_time', schedule.end_time)
        schedule.meeting_link = request.POST.get('meeting_link', schedule.meeting_link)
        schedule.is_cancelled = request.POST.get('is_cancelled') == 'on'
        schedule.save()
        messages.success(request, 'Schedule updated.')
        return redirect('schedule_list')
    return render(request, 'educator/schedule_edit.html', {'schedule': schedule, 'courses': courses})


@educator_required
def attendance_view(request, schedule_pk):
    schedule = get_object_or_404(ClassSchedule, pk=schedule_pk, educator=request.user)
    attendances = Attendance.objects.filter(schedule=schedule).select_related('student')
    enrolled_students = []
    if schedule.course:
        enrolled_students = Enrollment.objects.filter(
            course=schedule.course, payment_status='paid'
        ).select_related('student')
    return render(request, 'educator/attendance.html', {
        'schedule': schedule,
        'attendances': attendances,
        'enrolled_students': enrolled_students,
    })


@educator_required
def mark_attendance(request, schedule_pk):
    schedule = get_object_or_404(ClassSchedule, pk=schedule_pk, educator=request.user)
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
