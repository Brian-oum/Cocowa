from django.db import models
from django.contrib.auth import get_user_model
import re

User = get_user_model()


# ==========================================
# GENERATE MEMBERSHIP NUMBER
# ==========================================
def generate_unique_membership_number():

    from .models import (
        IndividualMember,
        SaccoMember,
        PartnerMember,
        Vehicle
    )

    all_members = []

    for model in [
        IndividualMember,
        SaccoMember,
        PartnerMember,
        Vehicle
    ]:

        last = model.objects.exclude(
            membership_number__isnull=True
        ).order_by('-id').first()

        if last and last.membership_number:

            numbers = re.findall(r'\d+', last.membership_number)

            if numbers:
                all_members.append(int(numbers[0]))

    last_number = max(all_members) if all_members else 0

    return f"CMN{str(last_number + 1).zfill(4)}"


# ==========================================
# USER PROFILE
# ==========================================
class UserProfile(models.Model):

    ROLE_CHOICES = [
        ('individual', 'Individual'),
        ('sacco', 'Sacco'),
        ('partner', 'Partner/Donor'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES
    )

    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )

    profile_completed = models.BooleanField(default=False)

    def __str__(self):
        return self.user.email


# ==========================================
# BASE MEMBER
# ==========================================
class BaseMember(models.Model):

    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )

    email = models.EmailField(
        blank=True,
        null=True
    )

    payment_status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS,
        default='pending'
    )

    transaction_code = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


# ==========================================
# INDIVIDUAL MEMBER
# ==========================================
class IndividualMember(BaseMember):

    PACKAGE_CHOICES = [
        ('Standard', 'Standard'),
        ('Super Subscription', 'Super Subscription'),
    ]

    first_name = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    second_name = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    id_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True
    )

    package = models.CharField(
        max_length=20,
        choices=PACKAGE_CHOICES,
        blank=True,
        null=True
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    membership_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True
    )

    def save(self, *args, **kwargs):

        if self.package == "Standard":
            self.amount = 550

        elif self.package == "Super Subscription":
            self.amount = 3050

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name or ''} {self.second_name or ''}"


# ==========================================
# SACCO MEMBER
# ==========================================
class SaccoMember(BaseMember):

    sacco_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    sacco_registration_number = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True
    )

    membership_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True
    )

    def __str__(self):
        return self.sacco_name or "Sacco"


# ==========================================
# PARTNER MEMBER
# ==========================================
class PartnerMember(BaseMember):

    organization_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    donation_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    membership_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True
    )

    def __str__(self):
        return self.organization_name or "Partner"


# ==========================================
# VEHICLE
# ==========================================
class Vehicle(models.Model):

    VEHICLE_TYPES = [
        ('nairobi', 'Nairobi Vehicle'),
        ('long_distance', 'Long Distance Vehicle'),
    ]

    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
    ]

    sacco = models.ForeignKey(
        SaccoMember,
        on_delete=models.CASCADE,
        related_name="vehicles"
    )

    vehicle_type = models.CharField(
        max_length=20,
        choices=VEHICLE_TYPES
    )

    number_plate = models.CharField(
        max_length=20,
        unique=True
    )

    route = models.CharField(max_length=255)

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    payment_status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS,
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):

        self.amount = (
            1000
            if self.vehicle_type == "nairobi"
            else 5000
        )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.number_plate

