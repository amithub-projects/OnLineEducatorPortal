from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from apps.authentication.models import User
from apps.courses.models import Course, Enrollment, Category
from apps.scheduling.models import ClassSchedule, Attendance


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class ClassAttendanceTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create Educator
        self.educator = User.objects.create_user(
            email='educator@example.com',
            password='password123',
            full_name='Lead Educator',
            role='educator'
        )
        
        # Create Sub-Educator
        self.sub_educator = User.objects.create_user(
            email='sub_educator@example.com',
            password='password123',
            full_name='Sub Educator',
            role='educator'
        )
        # Create parent institute relation
        from apps.authentication.models import EducatorProfile
        EducatorProfile.objects.create(
            user=self.sub_educator,
            educator_type='individual',
            parent_institute=self.educator
        )
        
        # Create Unrelated Educator
        self.other_educator = User.objects.create_user(
            email='other_educator@example.com',
            password='password123',
            full_name='Other Educator',
            role='educator'
        )
        
        # Create Student
        self.student = User.objects.create_user(
            email='student@example.com',
            password='password123',
            full_name='Test Student',
            role='student'
        )
        
        # Create Category and Course
        self.category = Category.objects.create(name='Test Cat', slug='test-cat')
        self.course = Course.objects.create(
            educator=self.educator,
            category=self.category,
            title='Attendance Course',
            price=0.00,
            is_published=True
        )
        
        # Enroll student in course
        Enrollment.objects.create(
            student=self.student,
            course=self.course,
            payment_status='paid'
        )
        
        # Create Class Schedule
        self.schedule = ClassSchedule.objects.create(
            educator=self.educator,
            assigned_sub_educator=self.sub_educator,
            course=self.course,
            title='Live Class 1',
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1)
        )

    def test_attendance_view_accessible_by_owner_educator(self):
        self.client.login(email='educator@example.com', password='password123')
        response = self.client.get(reverse('attendance_view', kwargs={'schedule_pk': self.schedule.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Student')
        self.assertContains(response, 'Attendance Sheet')

    def test_attendance_view_accessible_by_assigned_sub_educator(self):
        self.client.login(email='sub_educator@example.com', password='password123')
        response = self.client.get(reverse('attendance_view', kwargs={'schedule_pk': self.schedule.pk}))
        self.assertEqual(response.status_code, 200)

    def test_attendance_view_denied_for_unrelated_educator(self):
        self.client.login(email='other_educator@example.com', password='password123')
        response = self.client.get(reverse('attendance_view', kwargs={'schedule_pk': self.schedule.pk}))
        self.assertRedirects(response, reverse('schedule_list'), fetch_redirect_response=False)

    def test_attendance_view_denied_for_student(self):
        self.client.login(email='student@example.com', password='password123')
        response = self.client.get(reverse('attendance_view', kwargs={'schedule_pk': self.schedule.pk}))
        self.assertEqual(response.status_code, 302)

    def test_mark_attendance_post_saves_records(self):
        self.client.login(email='educator@example.com', password='password123')
        
        response = self.client.post(
            reverse('mark_attendance', kwargs={'schedule_pk': self.schedule.pk}),
            {'present_students': [self.student.pk]}
        )
        self.assertRedirects(response, reverse('attendance_view', kwargs={'schedule_pk': self.schedule.pk}), fetch_redirect_response=False)
        
        att = Attendance.objects.get(schedule=self.schedule, student=self.student)
        self.assertTrue(att.is_present)
        
        response = self.client.post(
            reverse('mark_attendance', kwargs={'schedule_pk': self.schedule.pk}),
            {'present_students': []}
        )
        att.refresh_from_db()
        self.assertFalse(att.is_present)

    def test_edit_scheduled_class_before_start(self):
        self.client.login(email='educator@example.com', password='password123')
        # Future schedule
        self.schedule.start_time = timezone.now() + timezone.timedelta(days=1)
        self.schedule.end_time = timezone.now() + timezone.timedelta(days=1, hours=1)
        self.schedule.save()
        
        response = self.client.get(reverse('schedule_edit', kwargs={'pk': self.schedule.pk}))
        self.assertEqual(response.status_code, 200)
        
        response = self.client.post(
            reverse('schedule_edit', kwargs={'pk': self.schedule.pk}),
            {
                'description': 'Updated description',
                'start_time': (timezone.now() + timezone.timedelta(days=2)).strftime('%Y-%m-%dT%H:%M'),
                'end_time': (timezone.now() + timezone.timedelta(days=2, hours=1)).strftime('%Y-%m-%dT%H:%M'),
            }
        )
        self.assertRedirects(response, reverse('schedule_list'), fetch_redirect_response=False)
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.description, 'Updated description')

    def test_edit_scheduled_class_after_start_blocked(self):
        self.client.login(email='educator@example.com', password='password123')
        # Past schedule
        self.schedule.start_time = timezone.now() - timezone.timedelta(hours=1)
        self.schedule.end_time = timezone.now() + timezone.timedelta(hours=1)
        self.schedule.save()
        
        response = self.client.get(reverse('schedule_edit', kwargs={'pk': self.schedule.pk}))
        self.assertRedirects(response, reverse('schedule_list'), fetch_redirect_response=False)
        
        response = self.client.post(
            reverse('schedule_edit', kwargs={'pk': self.schedule.pk}),
            {'description': 'Updated description'}
        )
        self.assertRedirects(response, reverse('schedule_list'), fetch_redirect_response=False)

    def test_cancel_scheduled_class_before_start(self):
        self.client.login(email='educator@example.com', password='password123')
        self.schedule.start_time = timezone.now() + timezone.timedelta(days=1)
        self.schedule.end_time = timezone.now() + timezone.timedelta(days=1, hours=1)
        self.schedule.save()
        
        response = self.client.get(reverse('schedule_cancel', kwargs={'pk': self.schedule.pk}))
        self.assertRedirects(response, reverse('schedule_list'), fetch_redirect_response=False)
        self.schedule.refresh_from_db()
        self.assertTrue(self.schedule.is_cancelled)

    def test_cancel_scheduled_class_after_start_blocked(self):
        self.client.login(email='educator@example.com', password='password123')
        # Already started
        self.schedule.start_time = timezone.now() - timezone.timedelta(hours=1)
        self.schedule.end_time = timezone.now() + timezone.timedelta(hours=1)
        self.schedule.save()
        
        response = self.client.get(reverse('schedule_cancel', kwargs={'pk': self.schedule.pk}))
        self.assertRedirects(response, reverse('schedule_list'), fetch_redirect_response=False)
        self.schedule.refresh_from_db()
        self.assertFalse(self.schedule.is_cancelled)

    def test_delete_cancelled_class_schedule(self):
        self.client.login(email='educator@example.com', password='password123')
        self.schedule.is_cancelled = True
        self.schedule.save()
        
        response = self.client.get(reverse('schedule_delete', kwargs={'pk': self.schedule.pk}))
        self.assertRedirects(response, reverse('schedule_list'), fetch_redirect_response=False)
        self.assertFalse(ClassSchedule.objects.filter(pk=self.schedule.pk).exists())

    def test_delete_non_cancelled_class_schedule_blocked(self):
        self.client.login(email='educator@example.com', password='password123')
        self.schedule.is_cancelled = False
        self.schedule.save()
        
        response = self.client.get(reverse('schedule_delete', kwargs={'pk': self.schedule.pk}))
        self.assertRedirects(response, reverse('schedule_list'), fetch_redirect_response=False)
        self.assertTrue(ClassSchedule.objects.filter(pk=self.schedule.pk).exists())

    def test_delete_cancelled_class_schedule_unrelated_educator_blocked(self):
        self.client.login(email='other_educator@example.com', password='password123')
        self.schedule.is_cancelled = True
        self.schedule.save()
        
        response = self.client.get(reverse('schedule_delete', kwargs={'pk': self.schedule.pk}))
        # Returns 404 since educator doesn't match
        self.assertEqual(response.status_code, 404)
        self.assertTrue(ClassSchedule.objects.filter(pk=self.schedule.pk).exists())


