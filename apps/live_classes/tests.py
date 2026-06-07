from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from apps.authentication.models import User, Follower, EducatorProfile
from apps.courses.models import Course, Enrollment, Category
from apps.live_classes.models import LiveSession
from apps.scheduling.models import ClassSchedule


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class LiveClassAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.educator = User.objects.create_user(
            email='educator@example.com',
            password='password123',
            full_name='Educator User',
            role='educator'
        )
        self.educator_profile = EducatorProfile.objects.create(
            user=self.educator,
            unique_link='educator-user',
            subjects='Test Subjects'
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
        self.free_course = Course.objects.create(
            educator=self.educator,
            category=self.category,
            title='Free Course',
            price=0,
            is_free=True,
            is_published=True
        )
        self.paid_course = Course.objects.create(
            educator=self.educator,
            category=self.category,
            title='Paid Course',
            price=100.00,
            is_free=False,
            is_published=True
        )
        
        # Create live sessions
        self.free_session = LiveSession.objects.create(
            educator=self.educator,
            course=self.free_course,
            title='Free Course Live Class',
            is_active=True
        )
        self.paid_session = LiveSession.objects.create(
            educator=self.educator,
            course=self.paid_course,
            title='Paid Course Live Class',
            is_active=True
        )
        
        # Student follows educator
        Follower.objects.create(student=self.student, educator=self.educator)

    def test_student_cannot_join_paid_course_live_session_without_enrollment(self):
        self.client.login(email='student@example.com', password='password123')
        response = self.client.get(reverse('live_session_room', kwargs={'room_code': self.paid_session.room_code}))
        self.assertRedirects(response, reverse('student_dashboard'), fetch_redirect_response=False)

    def test_student_can_join_paid_course_live_session_with_enrollment(self):
        Enrollment.objects.create(student=self.student, course=self.paid_course, payment_status='paid')
        self.client.login(email='student@example.com', password='password123')
        response = self.client.get(reverse('live_session_room', kwargs={'room_code': self.paid_session.room_code}))
        self.assertEqual(response.status_code, 200)

    def test_student_cannot_join_free_course_live_session_without_enrollment(self):
        self.client.login(email='student@example.com', password='password123')
        response = self.client.get(reverse('live_session_room', kwargs={'room_code': self.free_session.room_code}))
        self.assertRedirects(response, reverse('student_dashboard'), fetch_redirect_response=False)

    def test_student_can_join_free_course_live_session_with_enrollment(self):
        Enrollment.objects.create(student=self.student, course=self.free_course, payment_status='paid')
        self.client.login(email='student@example.com', password='password123')
        response = self.client.get(reverse('live_session_room', kwargs={'room_code': self.free_session.room_code}))
        self.assertEqual(response.status_code, 200)

    def test_student_dashboard_does_not_show_unenrolled_free_course_schedule(self):
        # Schedule a class for the free course
        schedule = ClassSchedule.objects.create(
            educator=self.educator,
            course=self.free_course,
            title='Free Course Live Class',
            start_time=timezone.now() + timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=2)
        )
        self.client.login(email='student@example.com', password='password123')
        response = self.client.get(reverse('student_dashboard'))
        
        # The schedule should not be in the dashboard's upcoming schedules
        schedules_in_context = response.context['upcoming_schedules']
        self.assertNotIn(schedule, schedules_in_context)

    def test_student_dashboard_does_not_show_unenrolled_paid_course_schedule(self):
        # Schedule a class for the paid course
        schedule = ClassSchedule.objects.create(
            educator=self.educator,
            course=self.paid_course,
            title='Paid Course Live Class',
            start_time=timezone.now() + timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=2)
        )
        self.client.login(email='student@example.com', password='password123')
        response = self.client.get(reverse('student_dashboard'))
        
        schedules_in_context = response.context['upcoming_schedules']
        self.assertNotIn(schedule, schedules_in_context)

    def test_student_dashboard_shows_enrolled_course_schedule(self):
        # Enroll student in the free course
        Enrollment.objects.create(student=self.student, course=self.free_course, payment_status='paid')
        
        # Schedule a class for the free course
        schedule = ClassSchedule.objects.create(
            educator=self.educator,
            course=self.free_course,
            title='Free Course Live Class',
            start_time=timezone.now() + timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=2)
        )
        self.client.login(email='student@example.com', password='password123')
        response = self.client.get(reverse('student_dashboard'))
        
        schedules_in_context = response.context['upcoming_schedules']
        self.assertIn(schedule, schedules_in_context)

    def test_student_dashboard_shows_general_schedule_for_followed_educator(self):
        # Schedule a general class with no course associated
        schedule = ClassSchedule.objects.create(
            educator=self.educator,
            course=None,
            title='General Session',
            start_time=timezone.now() + timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=2)
        )
        self.client.login(email='student@example.com', password='password123')
        response = self.client.get(reverse('student_dashboard'))
        
        schedules_in_context = response.context['upcoming_schedules']
        self.assertIn(schedule, schedules_in_context)


class LiveClassEndingTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Lead Educator (Institute)
        self.educator = User.objects.create_user(
            email='educator@example.com',
            password='password123',
            full_name='Lead Educator',
            role='educator'
        )
        
        # Sub Educator
        self.sub_educator = User.objects.create_user(
            email='sub_educator@example.com',
            password='password123',
            full_name='Sub Educator',
            role='educator'
        )
        EducatorProfile.objects.create(
            user=self.sub_educator,
            educator_type='individual',
            parent_institute=self.educator
        )
        
        # Category & Course
        self.category = Category.objects.create(name='Test Category', slug='test-category')
        self.course = Course.objects.create(
            educator=self.educator,
            category=self.category,
            title='Course 1',
            price=0.0,
            is_published=True
        )
        
        # Class Schedule
        self.schedule = ClassSchedule.objects.create(
            educator=self.educator,
            assigned_sub_educator=self.sub_educator,
            course=self.course,
            title='Class 1',
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=1)
        )
        
        # Live Session (started by Sub Educator)
        self.session = LiveSession.objects.create(
            educator=self.sub_educator,
            course=self.course,
            schedule=self.schedule,
            title='Live Class 1 Room',
            is_active=True
        )

    def test_lead_educator_can_end_sub_educator_started_session(self):
        # Login as Lead Educator (Institute owner)
        self.client.login(email='educator@example.com', password='password123')
        
        # Post to end session
        response = self.client.post(reverse('end_live_session', kwargs={'session_pk': self.session.pk}))
        self.assertRedirects(response, reverse('live_sessions_list'), fetch_redirect_response=False)
        
        # Verify session is ended
        self.session.refresh_from_db()
        self.assertFalse(self.session.is_active)

