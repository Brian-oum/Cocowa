from allauth.account.adapter import DefaultAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect
from django.core.mail import send_mail
from django.conf import settings
from .models import EmailOTP

class OTPRedirectAdapter(DefaultAccountAdapter):
    def pre_login(self, request, user, identity, next_redirect, signup):
        """
        Intercepts Allauth right before authentication finishes.
        If it's a first-time registration (signup), lock it down and request OTP.
        """
        if signup:
            # 1. Deactivate account until code matches
            user.is_active = False
            user.save()

            # 2. Spin up security code entries
            otp_record, created = EmailOTP.objects.get_or_create(user=user)
            otp_record.generate_otp()

            # 3. Deliver via mail server
            subject = "Verify Your Account Registration Code"
            message = f"Your luxury authorization security code is: {otp_record.otp_code}. Valid for 10 minutes."
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

            # 4. Cache identifier transiently inside server session memory
            request.session['unverified_user_id'] = user.id

            # 5. Halt default registration login loop, redirect to our verification view
            raise ImmediateHttpResponse(redirect('verify_email_otp'))