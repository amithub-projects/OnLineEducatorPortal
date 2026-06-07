from django.db import models
from apps.authentication.models import User
from apps.courses.models import Course, Enrollment, Module


class ClassSchedule(models.Model):
    educator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='schedules')
    assigned_sub_educator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_schedules', help_text='Sub-educator assigned to conduct this class')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='schedules', null=True, blank=True)
    subject = models.ForeignKey(Module, on_delete=models.SET_NULL, null=True, blank=True, related_name='schedules')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    topics_covered = models.TextField(blank=True, help_text='Topics or course content to be covered in this live class')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    meeting_link = models.URLField(blank=True)
    is_live_class = models.BooleanField(default=True)
    is_cancelled = models.BooleanField(default=False)
    reminder_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"{self.title} - {self.start_time.strftime('%d %b %Y %H:%M')}"

    @property
    def duration_minutes(self):
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() / 60)

    @property
    def has_started(self):
        from django.utils import timezone
        return self.start_time <= timezone.now()


class Attendance(models.Model):
    schedule = models.ForeignKey(ClassSchedule, on_delete=models.CASCADE, related_name='attendances')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendances')
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    is_present = models.BooleanField(default=True)

    class Meta:
        unique_together = ['schedule', 'student']

    def __str__(self):
        return f"{self.student.full_name} - {self.schedule.title}"
