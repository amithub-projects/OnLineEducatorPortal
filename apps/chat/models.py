from django.db import models
from apps.authentication.models import User
from apps.courses.models import Course


class ChatRoom(models.Model):
    ROOM_TYPE_CHOICES = [('course', 'Course Room'), ('private', 'Private'), ('live', 'Live Class')]
    name = models.CharField(max_length=200)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPE_CHOICES, default='course')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True, related_name='chat_rooms')
    participants = models.ManyToManyField(User, related_name='chat_rooms', blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_rooms')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    message_type = models.CharField(max_length=10, default='text', choices=[('text', 'Text'), ('file', 'File'), ('system', 'System')])
    file = models.FileField(upload_to='chat_files/', blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender.full_name}: {self.content[:50]}"


class PrivateMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='private_sent')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='private_received')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender.full_name} → {self.receiver.full_name}"
