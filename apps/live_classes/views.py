from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

from .models import LiveSession, SessionParticipant
from apps.courses.models import Course, Enrollment
from apps.courses.views import educator_required
from apps.chat.models import ChatRoom


@educator_required
def live_sessions_list(request):
    sessions = LiveSession.objects.filter(educator=request.user).order_by('-created_at')
    return render(request, 'educator/live_sessions.html', {'sessions': sessions})


@educator_required
def create_live_session(request):
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
    session = get_object_or_404(LiveSession, pk=session_pk, educator=request.user)
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
    session = get_object_or_404(LiveSession, pk=session_pk, educator=request.user)
    session.is_active = False
    session.ended_at = timezone.now()
    session.save()
    messages.info(request, 'Live session ended.')
    return redirect('live_sessions_list')


def live_session_room(request, room_code):
    if not request.user.is_authenticated:
        return redirect('login')
    session = get_object_or_404(LiveSession, room_code=room_code)
    is_educator = request.user == session.educator
    participant_count = SessionParticipant.objects.filter(session=session, left_at__isnull=True).count()
    return render(request, 'educator/live_room.html', {
        'session': session,
        'is_educator': is_educator,
        'room_code': room_code,
        'participant_count': participant_count,
    })


def join_live_session(request):
    if request.method == 'POST':
        room_code = request.POST.get('room_code', '').strip().upper()
        if room_code:
            try:
                session = LiveSession.objects.get(room_code=room_code)
                return redirect('live_session_room', room_code=room_code)
            except LiveSession.DoesNotExist:
                messages.error(request, 'Invalid room code. Please check and try again.')
    return render(request, 'public/join_live.html')
