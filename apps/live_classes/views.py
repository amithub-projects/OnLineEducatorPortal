from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q

from .models import LiveSession, SessionParticipant
from apps.courses.models import Course, Enrollment
from apps.courses.views import educator_required
from apps.chat.models import ChatRoom


@educator_required
def live_sessions_list(request):
    profile = getattr(request.user, 'educator_profile', None)
    if profile and profile.parent_institute:
        # Sub-educator: can see sessions they created OR are assigned to via schedule
        sessions = LiveSession.objects.filter(
            Q(educator=request.user) | Q(schedule__assigned_sub_educator=request.user)
        ).select_related('course', 'schedule', 'schedule__assigned_sub_educator').order_by('-created_at')
    else:
        # Institute / Individual Educator: can see sessions they created OR where they scheduled it
        sessions = LiveSession.objects.filter(
            Q(educator=request.user) | Q(schedule__educator=request.user)
        ).select_related('course', 'schedule', 'schedule__assigned_sub_educator').order_by('-created_at')
    return render(request, 'educator/live_sessions.html', {'sessions': sessions})


@educator_required
def create_live_session(request):
    profile = getattr(request.user, 'educator_profile', None)
    if profile and profile.parent_institute:
        courses = Course.objects.filter(assigned_educator=request.user, is_published=True)
    else:
        courses = Course.objects.filter(educator=request.user, is_published=True)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '')
        course_id = request.POST.get('course')
        if title:
            session = LiveSession.objects.create(
                educator=request.user,
                title=title,
                description=description,
                course_id=course_id if course_id else None,
            )
            messages.success(request, f'Live session "{title}" created! Room code: {session.room_code}')
            return redirect('live_session_room', room_code=session.room_code)
        else:
            messages.error(request, 'Please enter a session title.')
    return render(request, 'educator/live_create.html', {'courses': courses})


@educator_required
def start_live_session(request, session_pk):
    session = get_object_or_404(LiveSession, pk=session_pk)
    is_authorized = (
        session.educator == request.user or
        (session.schedule and session.schedule.assigned_sub_educator == request.user)
    )
    if not is_authorized:
        messages.error(request, 'Access denied.')
        return redirect('live_sessions_list')

    session.is_active = True
    session.started_at = timezone.now()
    session.save()
    
    # Create live chat room
    room, _ = ChatRoom.objects.get_or_create(
        name=f"Live: {session.title}",
        room_type='live',
        created_by=request.user,
    )
    messages.success(request, f'Session started! Share room code: {session.room_code}')
    return redirect('live_session_room', room_code=session.room_code)


@educator_required
def end_live_session(request, session_pk):
    session = get_object_or_404(LiveSession, pk=session_pk)
    is_authorized = (
        session.educator == request.user or
        (session.schedule and (
            session.schedule.assigned_sub_educator == request.user or
            session.schedule.educator == request.user
        )) or
        (session.course and session.course.educator == request.user)
    )
    if not is_authorized:
        messages.error(request, 'Access denied.')
        return redirect('live_sessions_list')

    session.is_active = False
    session.ended_at = timezone.now()
    session.save()
    messages.info(request, 'Live session ended.')
    return redirect('live_sessions_list')


@educator_required
def start_scheduled_live_session(request, schedule_pk):
    from apps.scheduling.models import ClassSchedule
    schedule = get_object_or_404(ClassSchedule, pk=schedule_pk)
    
    # Verify permission: must be either the scheduling educator (institute) or the assigned sub-educator
    is_authorized = (
        schedule.educator == request.user or
        schedule.assigned_sub_educator == request.user
    )
    if not is_authorized:
        messages.error(request, 'You are not authorized to start a live session for this scheduled class.')
        return redirect('schedule_list')
    
    # Check if LiveSession already exists for this schedule
    session = getattr(schedule, 'live_session', None)
    if not session:
        # Create new live session
        session = LiveSession.objects.create(
            educator=request.user,
            course=schedule.course,
            schedule=schedule,
            title=schedule.title,
            description=schedule.description,
        )
    
    # Start the session
    session.is_active = True
    if not session.started_at:
        session.started_at = timezone.now()
    session.save()
    
    # Create live chat room
    room, _ = ChatRoom.objects.get_or_create(
        name=f"Live: {session.title}",
        room_type='live',
        created_by=request.user,
    )
    
    messages.success(request, f'Live session started! Room code: {session.room_code}')
    return redirect('live_session_room', room_code=session.room_code)


def live_session_room(request, room_code):
    if not request.user.is_authenticated:
        return redirect('login')
    session = get_object_or_404(LiveSession, room_code=room_code)
    
    is_educator = (
        session.educator == request.user or
        (session.schedule and (
            session.schedule.assigned_sub_educator == request.user or
            session.schedule.educator == request.user
        )) or
        (session.course and (
            session.course.educator == request.user or
            session.course.assigned_educator == request.user
        )) or
        request.user.role == 'educator'
    )
    
    # For student: check enrollment status
    if not is_educator and request.user.role == 'student':
        if session.course:
            is_enrolled = Enrollment.objects.filter(
                student=request.user,
                course=session.course,
                payment_status='paid'
            ).exists()
            if not is_enrolled:
                messages.error(request, 'You are not enrolled in the subject/course for this live session.')
                return redirect('student_dashboard')
    
    participant_count = SessionParticipant.objects.filter(session=session, left_at__isnull=True).count()
    
    # Automatically record attendance if student joins
    if request.user.role == 'student' and session.schedule:
        from apps.scheduling.models import Attendance
        Attendance.objects.get_or_create(
            schedule=session.schedule,
            student=request.user,
            defaults={'is_present': True}
        )
        
    return render(request, 'educator/live_room.html', {
        'session': session,
        'is_educator': is_educator,
        'room_code': room_code,
        'participant_count': participant_count,
    })


def join_live_session(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method == 'POST':
        room_code = request.POST.get('room_code', '').strip().upper()
        if room_code:
            try:
                session = LiveSession.objects.get(room_code=room_code)
                # If student, verify enrollment
                if request.user.role == 'student' and session.course:
                    is_enrolled = Enrollment.objects.filter(
                        student=request.user,
                        course=session.course,
                        payment_status='paid'
                    ).exists()
                    if not is_enrolled:
                        messages.error(request, 'You are not enrolled in the subject/course for this live session.')
                        return redirect('join_live_session')
                
                return redirect('live_session_room', room_code=room_code)
            except LiveSession.DoesNotExist:
                messages.error(request, 'Invalid room code. Please check and try again.')
      
    return render(request, 'public/join_live.html')
