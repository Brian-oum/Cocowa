from .sms import send_sms
from System.models import UserSettings


def send_sms_notification(user, message):

    try:
        settings = UserSettings.objects.get(user=user)

        if not settings.sms_notifications:
            return

        profile = user.userprofile

        if profile.phone_number:
            send_sms(profile.phone_number, message)

    except Exception as e:
        print("SMS Notification Error:", e)