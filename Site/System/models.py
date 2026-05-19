from django.db import models
import random
import re 
def generate_unique_membership_number():
    from .models import Membership

    last_member = Membership.objects.exclude(
        membership_number__isnull=True
    ).order_by('-id').first()

    if last_member and last_member.membership_number:

        # Extract only digits
        numbers = re.findall(r'\d+', last_member.membership_number)

        if numbers:
            last_number = int(numbers[0])
            new_number = last_number + 1
        else:
            new_number = 1

    else:
        new_number = 1

    return f"CMN{str(new_number).zfill(3)}"

class Membership(models.Model):
    PACKAGE_CHOICES = [
        ('Standard', 'Standard'),
        ('Premium', 'Premium'),
    ]

    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
    ]

    first_name = models.CharField(max_length=100)
    second_name = models.CharField(max_length=100)
    id_number = models.CharField(max_length=20, unique=True)
    phone_number = models.CharField(max_length=15)
    membership_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    email = models.EmailField()
    package = models.CharField(max_length=10, choices=PACKAGE_CHOICES)

    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS,default='pending')

    transaction_code = models.CharField(max_length=50, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def get_amount(self):
        return 550 if self.package == 'standard' else 3050

    def __str__(self):
        return f"{self.first_name} {self.second_name}"
    
    def save(self, *args, **kwargs):
        # Only generate when payment is confirmed
        if self.payment_status == "paid" and not self.membership_number:
            self.membership_number = generate_unique_membership_number()

        super().save(*args, **kwargs)