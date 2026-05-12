from django.db import models
from apps.authentication.models import User
from apps.courses.models import Course


class Payment(models.Model):
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('captured', 'Captured/Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=5, default='INR')
    razorpay_order_id = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.full_name} → {self.course.title} ₹{self.amount} [{self.status}]"
