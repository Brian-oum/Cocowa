from .models import Membership
import random

def generate_unique_membership_number():
    while True:
        number = f"COCOWA-{random.randint(100000, 999999)}"
        if not Membership.objects.filter(membership_number=number).exists():
            return number