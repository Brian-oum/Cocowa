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