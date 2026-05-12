from django.db import models
from apps.authentication.models import User
from apps.courses.models import Course


class CourseFile(models.Model):
    FILE_TYPE_CHOICES = [
        ('pdf', 'PDF'),
        ('doc', 'Document'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('assignment', 'Assignment'),
        ('notes', 'Notes'),
        ('other', 'Other'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='files')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='course_files/')
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, default='other')
    is_public = models.BooleanField(default=False, help_text='Visible to enrolled students only if False')
    download_count = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    def get_file_icon(self):
        icons = {
            'pdf': 'bi-file-pdf',
            'doc': 'bi-file-word',
            'image': 'bi-file-image',
            'video': 'bi-camera-video',
            'assignment': 'bi-clipboard-check',
            'notes': 'bi-journal-text',
            'other': 'bi-file-earmark',
        }
        return icons.get(self.file_type, 'bi-file-earmark')

    @property
    def file_size_display(self):
        try:
            size = self.file.size
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size/1024:.1f} KB"
            else:
                return f"{size/1024/1024:.1f} MB"
        except Exception:
            return "Unknown"
