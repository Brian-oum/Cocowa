from django.core.mail import send_mail
from django.conf import settings
from .models import EmailOTP


def send_otp_email(user):

    otp_obj, created = EmailOTP.objects.get_or_create(
        user=user
    )

    otp_obj.generate_otp()

    send_mail(
        subject="Email Verification OTP",
        message=f"""
Hello,

Your OTP code is:

{otp_obj.otp_code}

This code expires in 10 minutes.

Thank you.
""",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )