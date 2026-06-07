from django.test import TestCase, Client, override_settings
from django.urls import reverse
from apps.authentication.models import User, Follower
from apps.courses.models import Course, Enrollment, Category


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class EnrollmentRedirectTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.educator = User.objects.create_user(
            email='educator@example.com',
            password='password123',
            full_name='Educator User',
            role='educator'
        )
        self.student = User.objects.create_user(
            email='student@example.com',
            password='password123',
            full_name='Student User',
            role='student'
        )
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        self.course = Course.objects.create(
            educator=self.educator,
            category=self.category,
            title='Paid Course',
            price=99.00,
            is_published=True
        )
        # Ensure student is following the educator so they can enroll/view details
        Follower.objects.create(student=self.student, educator=self.educator)

    def test_enroll_course_with_pending_enrollment_redirects_to_checkout(self):
        # Create a pending enrollment
        Enrollment.objects.create(
            student=self.student,
            course=self.course,
            payment_status='pending'
        )
        self.client.login(email='student@example.com', password='password123')
        
        # Accessing the enroll page again
        response = self.client.get(reverse('enroll_course', kwargs={'slug': self.course.slug}))
        
        # Should redirect to payment checkout page
        self.assertRedirects(response, reverse('payment_checkout', kwargs={'course_pk': self.course.pk}), fetch_redirect_response=False)

    def test_enroll_course_with_paid_enrollment_redirects_to_learn(self):
        # Create a paid enrollment
        enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            payment_status='paid'
        )
        self.client.login(email='student@example.com', password='password123')
        
        response = self.client.get(reverse('enroll_course', kwargs={'slug': self.course.slug}))
        
        # Should redirect to course learn page
        self.assertRedirects(response, reverse('course_learn', kwargs={'enrollment_pk': enrollment.pk}), fetch_redirect_response=False)

    def test_course_learn_with_pending_enrollment_redirects_to_checkout(self):
        # Create a pending enrollment
        enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            payment_status='pending'
        )
        self.client.login(email='student@example.com', password='password123')
        
        # Try to access learning dashboard
        response = self.client.get(reverse('course_learn', kwargs={'enrollment_pk': enrollment.pk}))
        
        # Should redirect to checkout rather than raising 404
        self.assertRedirects(response, reverse('payment_checkout', kwargs={'course_pk': self.course.pk}), fetch_redirect_response=False)

    def test_course_learn_with_paid_enrollment_renders_successfully(self):
        # Create a paid enrollment
        enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            payment_status='paid'
        )
        self.client.login(email='student@example.com', password='password123')
        
        response = self.client.get(reverse('course_learn', kwargs={'enrollment_pk': enrollment.pk}))
        
        # Paid enrollment should be loaded successfully (200 OK)
        self.assertEqual(response.status_code, 200)


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class EducatorStudentDetailTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.educator = User.objects.create_user(
            email='educator@example.com',
            password='password123',
            full_name='Educator One',
            role='educator'
        )
        self.other_educator = User.objects.create_user(
            email='other_educator@example.com',
            password='password123',
            full_name='Educator Two',
            role='educator'
        )
        self.student = User.objects.create_user(
            email='student@example.com',
            password='password123',
            full_name='Student One',
            role='student'
        )
        self.other_student = User.objects.create_user(
            email='other_student@example.com',
            password='password123',
            full_name='Student Two',
            role='student'
        )
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        self.course1 = Course.objects.create(
            educator=self.educator,
            category=self.category,
            title='Educator One Course',
            price=99.00,
            is_published=True
        )
        self.course2 = Course.objects.create(
            educator=self.other_educator,
            category=self.category,
            title='Educator Two Course',
            price=149.00,
            is_published=True
        )
        
        # Enrolls:
        # student enrolled in course1 (educator) and course2 (other_educator)
        Enrollment.objects.create(
            student=self.student,
            course=self.course1,
            payment_status='paid'
        )
        Enrollment.objects.create(
            student=self.student,
            course=self.course2,
            payment_status='paid'
        )
        # other_student enrolled only in course2 (other_educator)
        Enrollment.objects.create(
            student=self.other_student,
            course=self.course2,
            payment_status='paid'
        )

    def test_educator_can_view_enrolled_student_detail(self):
        self.client.login(email='educator@example.com', password='password123')
        response = self.client.get(reverse('student_detail_educator', kwargs={'pk': self.student.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Student One')
        self.assertContains(response, 'Educator One Course')
        # Check that course2 (from other educator) is not visible in the course table to prevent privacy leak
        self.assertNotContains(response, 'Educator Two Course')

    def test_educator_cannot_view_non_enrolled_student_detail(self):
        # other_student is not enrolled in educator's course
        self.client.login(email='educator@example.com', password='password123')
        response = self.client.get(reverse('student_detail_educator', kwargs={'pk': self.other_student.pk}))
        self.assertRedirects(response, reverse('student_management'), fetch_redirect_response=False)

    def test_non_educator_cannot_access_student_detail(self):
        # student (non-educator) trying to access the endpoint
        self.client.login(email='student@example.com', password='password123')
        response = self.client.get(reverse('student_detail_educator', kwargs={'pk': self.student.pk}))
        # educator_required decorator should redirect
        self.assertEqual(response.status_code, 302)

