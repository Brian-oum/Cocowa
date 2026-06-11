import requests
from django.conf import settings


def send_sms(phone, message):
    """
    Send SMS using Africa's Talking
    """

    url = "https://api.africastalking.com/version1/messaging"

    headers = {
        "apiKey": settings.AT_API_KEY,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    payload = {
        "username": settings.AT_USERNAME,
        "to": phone,
        "message": message,
        "from": settings.AT_SENDER_ID,
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            data=payload
        )

        return response.json()

    except Exception as e:
        print("SMS Error:", e)
        return None