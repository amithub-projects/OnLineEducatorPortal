from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
import razorpay
import hmac
import hashlib
import json

from .models import Payment
from apps.courses.models import Course, Enrollment


@login_required
def payment_checkout(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk, is_published=True)
    if request.user.role != 'student':
        messages.error(request, 'Only students can make payments.')
        return redirect('course_public_detail', slug=course.slug)

    existing = Enrollment.objects.filter(student=request.user, course=course, payment_status='paid').first()
    if existing:
        return redirect('course_learn', enrollment_pk=existing.pk)

    amount_paise = int(course.price * 100)
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    try:
        order = client.order.create({
            'amount': amount_paise,
            'currency': 'INR',
            'payment_capture': 1,
        })
        payment = Payment.objects.create(
            student=request.user,
            course=course,
            amount=course.price,
            razorpay_order_id=order['id'],
        )
        enrollment, _ = Enrollment.objects.get_or_create(student=request.user, course=course)
        return render(request, 'public/payment_checkout.html', {
            'course': course,
            'payment': payment,
            'order': order,
            'razorpay_key': settings.RAZORPAY_KEY_ID,
        })
    except Exception as e:
        messages.error(request, f'Payment gateway error: {str(e)}')
        return redirect('course_public_detail', slug=course.slug)


@csrf_exempt
def payment_callback(request):
    if request.method == 'POST':
        data = request.POST
        razorpay_order_id = data.get('razorpay_order_id', '')
        razorpay_payment_id = data.get('razorpay_payment_id', '')
        razorpay_signature = data.get('razorpay_signature', '')

        # Verify signature
        key_secret = settings.RAZORPAY_KEY_SECRET.encode('utf-8')
        msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode('utf-8')
        generated_sig = hmac.new(key_secret, msg, hashlib.sha256).hexdigest()

        try:
            payment = Payment.objects.get(razorpay_order_id=razorpay_order_id)
            if generated_sig == razorpay_signature:
                payment.razorpay_payment_id = razorpay_payment_id
                payment.razorpay_signature = razorpay_signature
                payment.status = 'captured'
                payment.save()
                # Activate enrollment
                Enrollment.objects.filter(
                    student=payment.student, course=payment.course
                ).update(payment_status='paid')
                messages.success(request, f'Payment successful! You are now enrolled in "{payment.course.title}".')
                enrollment = Enrollment.objects.get(student=payment.student, course=payment.course)
                return redirect('course_learn', enrollment_pk=enrollment.pk)
            else:
                payment.status = 'failed'
                payment.save()
                messages.error(request, 'Payment verification failed. Please contact support.')
        except Payment.DoesNotExist:
            messages.error(request, 'Payment record not found.')

    return redirect('home')


@login_required
def payment_history(request):
    if request.user.role == 'student':
        payments = Payment.objects.filter(student=request.user)
    elif request.user.role == 'educator':
        payments = Payment.objects.filter(course__educator=request.user, status='captured')
    else:
        payments = Payment.objects.all()
    total = sum(p.amount for p in payments.filter(status='captured'))
    return render(request, 'public/payment_history.html', {
        'payments': payments,
        'total': total,
    })
