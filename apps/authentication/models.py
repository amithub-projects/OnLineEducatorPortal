from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_approved', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('educator', 'Educator'),
        ('student', 'Student'),
    ]

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=15, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)  # Educators need admin approval
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    objects = UserManager()

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.full_name} ({self.role})"

    @property
    def is_educator(self):
        return self.role == 'educator'

    @property
    def is_student(self):
        return self.role == 'student'

    @property
    def is_admin_user(self):
        return self.role == 'admin'


class EducatorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='educator_profile')
    bio = models.TextField(blank=True)
    subjects = models.CharField(max_length=500, blank=True, help_text="Comma-separated subjects")
    experience_years = models.PositiveIntegerField(default=0)
    qualification = models.CharField(max_length=200, blank=True)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_reviews = models.PositiveIntegerField(default=0)
    unique_link = models.CharField(max_length=100, unique=True, blank=True)
    website = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    cover_image = models.ImageField(upload_to='educator_covers/', blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.unique_link:
            import uuid
            self.unique_link = str(uuid.uuid4())[:8]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Profile: {self.user.full_name}"

    def get_subjects_list(self):
        return [s.strip() for s in self.subjects.split(',') if s.strip()]


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        from datetime import timedelta
        return not self.is_used and timezone.now() < self.created_at + timedelta(hours=24)


class Follower(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    educator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['student', 'educator']

    def __str__(self):
        return f"{self.student.full_name} follows {self.educator.full_name}"
