from django.test import TestCase, Client, override_settings
from django.urls import reverse
from apps.authentication.models import User


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class AdminStudentDetailTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='password123',
            full_name='Admin User',
            role='admin',
            is_staff=True,
            is_superuser=True
        )
        self.student_user = User.objects.create_user(
            email='student@example.com',
            password='password123',
            full_name='Student User',
            role='student'
        )

    def test_anonymous_user_redirects_to_login(self):
        response = self.client.get(reverse('student_detail_admin', kwargs={'pk': self.student_user.pk}))
        self.assertRedirects(response, reverse('login'), fetch_redirect_response=False)

    def test_non_admin_user_redirects_to_home(self):
        self.client.login(email='student@example.com', password='password123')
        response = self.client.get(reverse('student_detail_admin', kwargs={'pk': self.student_user.pk}))
        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)

    def test_admin_user_can_view_student_details(self):
        self.client.login(email='admin@example.com', password='password123')
        response = self.client.get(reverse('student_detail_admin', kwargs={'pk': self.student_user.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin_panel/student_detail.html')
        self.assertEqual(response.context['student'], self.student_user)
