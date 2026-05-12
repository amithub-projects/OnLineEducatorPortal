from django.contrib import admin
from .models import User, EducatorProfile, PasswordResetToken

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'full_name', 'role', 'is_approved', 'is_active', 'date_joined']
    list_filter = ['role', 'is_approved', 'is_active']
    search_fields = ['email', 'full_name']
    list_editable = ['is_approved', 'is_active']

@admin.register(EducatorProfile)
class EducatorProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'subjects', 'experience_years', 'rating']
    search_fields = ['user__full_name', 'subjects']

admin.site.register(PasswordResetToken)
