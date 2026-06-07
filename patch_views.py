import re

with open('apps/courses/views.py', 'r') as f:
    content = f.read()

content = content.replace("from django.db.models import Count", "from django.db.models import Count, Q")

helper_func = """
def get_educator_courses(user):
    return Course.objects.filter(
        Q(educator=user) | 
        Q(assigned_educator=user) | 
        Q(educator__educator_profile__parent_institute=user)
    ).distinct()

"""

# Insert after educator_required
content = content.replace("def educator_dashboard(request):", helper_func + "@educator_required\ndef educator_dashboard(request):")

# Replace Course queries
content = content.replace("Course.objects.filter(educator=educator)", "get_educator_courses(educator)")
content = content.replace("Course.objects.filter(educator=request.user)", "get_educator_courses(request.user)")
content = content.replace("get_object_or_404(Course, pk=pk, educator=request.user)", "get_object_or_404(get_educator_courses(request.user), pk=pk)")
content = content.replace("get_object_or_404(Course, pk=course_pk, educator=request.user)", "get_object_or_404(get_educator_courses(request.user), pk=course_pk)")
# For lesson_create module:
content = content.replace("module = get_object_or_404(Module, pk=module_pk, course__educator=request.user)", "module = get_object_or_404(Module, pk=module_pk, course__in=get_educator_courses(request.user))")

# For student_management
content = content.replace("course__educator=request.user", "course__in=get_educator_courses(request.user)")
content = content.replace("course__educator=educator", "course__in=get_educator_courses(educator)")

course_edit_orig = """@educator_required
def course_edit(request, pk):
    course = get_object_or_404(get_educator_courses(request.user), pk=pk)
    categories = Category.objects.all()
    if request.method == 'POST':
        course.title = request.POST.get('title', course.title)
        course.description = request.POST.get('description', course.description)
        category_id = request.POST.get('category')
        course.category_id = category_id if category_id else None
        course.price = float(request.POST.get('price') or 0)
        course.level = request.POST.get('level', course.level)
        course.duration_hours = int(request.POST.get('duration_hours') or 0)
        course.is_free = request.POST.get('is_free') == 'on'
        course.is_published = request.POST.get('is_published') == 'on'
        if request.FILES.get('thumbnail'):
            course.thumbnail = request.FILES['thumbnail']
        course.save()
        messages.success(request, 'Course updated successfully!')
        return redirect('course_detail_educator', pk=pk)
    return render(request, 'educator/course_edit.html', {'course': course, 'categories': categories})"""

course_edit_new = """@educator_required
def course_edit(request, pk):
    course = get_object_or_404(get_educator_courses(request.user), pk=pk)
    categories = Category.objects.all()
    sub_educators = None
    if hasattr(request.user, 'educator_profile') and request.user.educator_profile.institute_name:
        sub_educators = User.objects.filter(educator_profile__parent_institute=request.user)

    if request.method == 'POST':
        course.title = request.POST.get('title', course.title)
        course.description = request.POST.get('description', course.description)
        category_id = request.POST.get('category')
        course.category_id = category_id if category_id else None
        course.price = float(request.POST.get('price') or 0)
        course.level = request.POST.get('level', course.level)
        course.duration_hours = int(request.POST.get('duration_hours') or 0)
        course.is_free = request.POST.get('is_free') == 'on'
        course.is_published = request.POST.get('is_published') == 'on'
        
        assigned_educator_id = request.POST.get('assigned_educator')
        if assigned_educator_id:
            course.assigned_educator_id = assigned_educator_id
        else:
            course.assigned_educator = None

        if request.FILES.get('thumbnail'):
            course.thumbnail = request.FILES['thumbnail']
        course.save()
        messages.success(request, 'Course updated successfully!')
        return redirect('course_detail_educator', pk=pk)
    return render(request, 'educator/course_edit.html', {'course': course, 'categories': categories, 'sub_educators': sub_educators})"""

content = content.replace(course_edit_orig, course_edit_new)

# Append sub educator views
sub_educator_views = """
from apps.authentication.forms import SubEducatorCreationForm
from apps.authentication.models import EducatorProfile

@educator_required
def manage_sub_educators(request):
    if not hasattr(request.user, 'educator_profile') or not request.user.educator_profile.institute_name:
        messages.error(request, 'Only institutes can manage sub-educators.')
        return redirect('educator_dashboard')
    
    sub_educators = User.objects.filter(educator_profile__parent_institute=request.user)
    return render(request, 'educator/manage_sub_educators.html', {'sub_educators': sub_educators})

@educator_required
def add_sub_educator(request):
    if not hasattr(request.user, 'educator_profile') or not request.user.educator_profile.institute_name:
        messages.error(request, 'Only institutes can add sub-educators.')
        return redirect('educator_dashboard')
        
    form = SubEducatorCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        EducatorProfile.objects.create(
            user=user,
            parent_institute=request.user
        )
        messages.success(request, f'Sub-educator {user.full_name} created successfully!')
        return redirect('manage_sub_educators')
        
    return render(request, 'educator/add_sub_educator.html', {'form': form})
"""

content += sub_educator_views

with open('apps/courses/views.py', 'w') as f:
    f.write(content)
