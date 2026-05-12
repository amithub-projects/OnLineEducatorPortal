from rest_framework import generics, serializers, permissions
from apps.courses.models import Course, Enrollment
from apps.authentication.models import User, EducatorProfile


class CourseSerializer(serializers.ModelSerializer):
    educator_name = serializers.CharField(source='educator.full_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    enrolled_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'title', 'slug', 'description', 'educator_name', 'category_name',
                  'price', 'level', 'duration_hours', 'is_free', 'enrolled_count', 'created_at']

    def get_enrolled_count(self, obj):
        return obj.enrollments.filter(payment_status='paid').count()


class EducatorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducatorProfile
        fields = ['bio', 'subjects', 'experience_years', 'qualification', 'rating', 'hourly_rate']


class EducatorSerializer(serializers.ModelSerializer):
    educator_profile = EducatorProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'educator_profile']


class EnrollmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    student_name = serializers.CharField(source='student.full_name', read_only=True)

    class Meta:
        model = Enrollment
        fields = ['id', 'student_name', 'course_title', 'enrolled_at', 'payment_status', 'progress_percent']


class CourseListAPIView(generics.ListAPIView):
    queryset = Course.objects.filter(is_published=True).select_related('educator', 'category')
    serializer_class = CourseSerializer
    permission_classes = [permissions.AllowAny]


class EducatorListAPIView(generics.ListAPIView):
    queryset = User.objects.filter(role='educator', is_approved=True, is_active=True).select_related('educator_profile')
    serializer_class = EducatorSerializer
    permission_classes = [permissions.AllowAny]


class EnrollmentAPIView(generics.ListCreateAPIView):
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'educator':
            return Enrollment.objects.filter(course__educator=user)
        return Enrollment.objects.filter(student=user)
