from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from .models import UserProfile, IndividualMember

@receiver(user_signed_up)
def google_user_created(request, user, **kwargs):

    # Create base profile
    UserProfile.objects.get_or_create(
        user=user,
        defaults={
            "role": None,  # IMPORTANT: force selection later
            "profile_completed": False
        }
    )

    # Optional default member (you can delay this too)
    IndividualMember.objects.get_or_create(
        user=user,
        defaults={
            "email": user.email
        }
    )

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Complaint
from .notifications import send_sms_notification


@receiver(post_save, sender=Complaint)
def complaint_status_sms(sender, instance, created, **kwargs):

    if not created:

        send_sms_notification(
            instance.user,
            f"COCOWA: Complaint {instance.ticket_number} status changed to {instance.status}."
        )
@receiver(post_save, sender=IndividualMember)
def membership_payment_sms(sender, instance, **kwargs):

    if instance.payment_status == "paid":

        send_sms_notification(
            instance.user,
            f"Congratulations! Your COCOWA membership has been approved. Membership No: {instance.membership_number}"
        )