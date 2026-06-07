from django.db import models
from apps.authentication.models import User
from apps.courses.models import Course
import uuid


class LiveSession(models.Model):
    educator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='live_sessions')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True, related_name='live_sessions')
    schedule = models.OneToOneField('scheduling.ClassSchedule', on_delete=models.SET_NULL, null=True, blank=True, related_name='live_session')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    room_code = models.CharField(max_length=20, unique=True, blank=True)
    is_active = models.BooleanField(default=False)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.room_code:
            self.room_code = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({'Live' if self.is_active else 'Ended'})"


class SessionParticipant(models.Model):
    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['session', 'user']

    def __str__(self):
        return f"{self.user.full_name} in {self.session.title}"
