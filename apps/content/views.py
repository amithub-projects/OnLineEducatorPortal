from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404
import os

from .models import CourseFile
from apps.courses.models import Course, Enrollment
from apps.courses.views import educator_required


@educator_required
def upload_file(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk, educator=request.user)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        file_type = request.POST.get('file_type', 'other')
        description = request.POST.get('description', '')
        is_public = request.POST.get('is_public') == 'on'
        uploaded_file = request.FILES.get('file')
        if title and uploaded_file:
            CourseFile.objects.create(
                course=course,
                uploaded_by=request.user,
                title=title,
                file_type=file_type,
                description=description,
                is_public=is_public,
                file=uploaded_file,
            )
            messages.success(request, f'File "{title}" uploaded successfully!')
        else:
            messages.error(request, 'Please provide a title and select a file.')
        return redirect('course_detail_educator', pk=course_pk)
    return redirect('course_detail_educator', pk=course_pk)


@educator_required
def delete_file(request, pk):
    file_obj = get_object_or_404(CourseFile, pk=pk, uploaded_by=request.user)
    course_pk = file_obj.course.pk
    if request.method == 'POST':
        try:
            if file_obj.file and os.path.exists(file_obj.file.path):
                os.remove(file_obj.file.path)
        except Exception:
            pass
        file_obj.delete()
        messages.success(request, 'File deleted.')
    return redirect('course_detail_educator', pk=course_pk)


@login_required
def download_file(request, pk):
    file_obj = get_object_or_404(CourseFile, pk=pk)
    course = file_obj.course

    # Permission check
    if not file_obj.is_public:
        if request.user.role == 'educator' and course.educator != request.user:
            raise Http404
        elif request.user.role == 'student':
            enrolled = Enrollment.objects.filter(
                student=request.user, course=course, payment_status='paid'
            ).exists()
            if not enrolled:
                messages.error(request, 'You must be enrolled to download this file.')
                return redirect('course_public_detail', slug=course.slug)

    file_obj.download_count += 1
    file_obj.save(update_fields=['download_count'])
    response = FileResponse(file_obj.file.open('rb'), as_attachment=True)
    return response
