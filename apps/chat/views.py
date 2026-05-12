from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import ChatRoom, Message, PrivateMessage
from apps.courses.models import Course, Enrollment
from apps.courses.views import educator_required
from apps.authentication.models import User


@educator_required
def chat_room_list(request):
    rooms = ChatRoom.objects.filter(created_by=request.user)
    return render(request, 'educator/chat_rooms.html', {'rooms': rooms})


@educator_required
def create_chat_room(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk, educator=request.user)
    room, created = ChatRoom.objects.get_or_create(
        course=course,
        room_type='course',
        defaults={'name': f"{course.title} - Chat", 'created_by': request.user}
    )
    if created:
        # Add enrolled students
        enrolled = Enrollment.objects.filter(course=course, payment_status='paid').select_related('student')
        for e in enrolled:
            room.participants.add(e.student)
        room.participants.add(request.user)
    return redirect('chat_room', room_id=room.pk)


@login_required
def chat_room(request, room_id):
    room = get_object_or_404(ChatRoom, pk=room_id)
    # Permission check
    if request.user not in room.participants.all() and room.created_by != request.user:
        messages.error(request, 'You do not have access to this chat room.')
        return redirect('home')
    recent_messages = Message.objects.filter(room=room).select_related('sender').order_by('-timestamp')[:50]
    recent_messages = list(reversed(recent_messages))
    return render(request, 'educator/chat_room.html', {
        'room': room,
        'messages': recent_messages,
    })


@login_required
def private_messages(request, user_id):
    other_user = get_object_or_404(User, pk=user_id)
    
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            PrivateMessage.objects.create(sender=request.user, receiver=other_user, content=content)
            return redirect('private_messages', user_id=other_user.pk)

    msgs = PrivateMessage.objects.filter(
        sender__in=[request.user, other_user],
        receiver__in=[request.user, other_user]
    ).order_by('timestamp')
    # Mark as read
    PrivateMessage.objects.filter(sender=other_user, receiver=request.user, is_read=False).update(is_read=True)
    return render(request, 'educator/private_chat.html', {
        'other_user': other_user,
        'messages': msgs,
    })
