from django.db import models
from django.contrib.auth import get_user_model
import re
from django.utils import timezone
import random 
import datetime
from django.db.models.signals import post_save
from django.dispatch import receiver
User = get_user_model()

class EmailOTP(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="email_otp")
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def generate_otp(self):
        """Generates a random 6-digit number and timestamps it."""
        self.otp_code = f"{random.randint(100000, 999999)}"
        self.created_at = timezone.now()
        self.is_verified = False
        self.save()

    def is_valid(self):
        """Returns True if OTP is verified within a 10-minute validity window."""
        expiration_time = self.created_at + datetime.timedelta(minutes=10)
        return timezone.now() < expiration_time
# ==========================================
# GENERATE MEMBERSHIP NUMBER
# ==========================================
def generate_unique_membership_number():
    from .models import IndividualMember, SaccoMember

    all_numbers = []

    # ONLY models that actually contain membership_number
    models_list = [
        IndividualMember,
        SaccoMember,
    ]

    for model in models_list:

        last = model.objects.exclude(
            membership_number__isnull=True
        ).exclude(
            membership_number__exact=""
        ).order_by('-id').first()

        if last and last.membership_number:

            numbers = re.findall(r'\d+', last.membership_number)

            if numbers:
                all_numbers.append(int(numbers[0]))

    last_number = max(all_numbers) if all_numbers else 0

    return f"CMN{str(last_number + 1).zfill(4)}"


# ==========================================
# USER PROFILE
# ==========================================
class UserProfile(models.Model):

    ROLE_CHOICES = [
        ('individual', 'Individual Member'),
        ('sacco', 'Sacco Member'),
        ('partner', 'Partner/Donor'),
        ('manager', 'Manager'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        null=True,
        blank=True
    )

    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )

    profile_completed = models.BooleanField(default=False)

    email_verified = models.BooleanField(default=False)

    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True
    )

    # ==========================================
    # DATA SHARING CONSENT (COCOWA)
    # ==========================================
    cocowa_data_consent = models.BooleanField(
        default=False,
        help_text="User has consented to sharing their data with COCOWA"
    )

    cocowa_consent_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when consent was last given or revoked"
    )

    def __str__(self):
        return self.user.email

class UserSettings(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # =========================
    # NOTIFICATIONS
    # =========================
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    complaint_updates = models.BooleanField(default=True)
    payment_reminders = models.BooleanField(default=True)

    # =========================
    # EMAIL & LOGIN
    # =========================
    two_factor_enabled = models.BooleanField(default=False)
    login_alerts = models.BooleanField(default=True)

    # =========================
    # PRIVACY
    # =========================
    profile_visibility = models.BooleanField(default=True)
    show_email = models.BooleanField(default=False)
    show_phone = models.BooleanField(default=False)

    # =========================
    # SYSTEM PREFERENCES
    # =========================
    dark_mode = models.BooleanField(default=False)
    language = models.CharField(max_length=20, default="en")

    created_at = models.DateTimeField(auto_now_add=True)

    @receiver(post_save, sender=User)
    def create_user_settings(sender, instance, created, **kwargs):
        if created:
            UserSettings.objects.create(user=instance)
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

    first_name = models.CharField(max_length=100, blank=True, null=True)
    second_name = models.CharField(max_length=100, blank=True, null=True)

    id_number = models.CharField(max_length=20, unique=True, blank=True, null=True)

    package = models.CharField(
        max_length=20,
        choices=PACKAGE_CHOICES,
        blank=True,
        null=True
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    membership_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True
    )

    def save(self, *args, **kwargs):

        # auto set amount
        if self.package == "Standard":
            self.amount = 550
        elif self.package == "Super Subscription":
            self.amount = 3050

        # generate membership number ONLY if missing
        if self.payment_status == "paid" and not self.membership_number:
            self.membership_number = generate_unique_membership_number()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name or ''} {self.second_name or ''}"


# ==========================================
# NEXT OF KIN  (Super Subscription only)
# ==========================================
class NextOfKin(models.Model):

    RELATIONSHIP_CHOICES = [
        ('spouse', 'Spouse'),
        ('parent', 'Parent'),
        ('sibling', 'Sibling'),
        ('child', 'Child'),
        ('guardian', 'Guardian'),
        ('other', 'Other'),
    ]

    member = models.OneToOneField(
        IndividualMember,
        on_delete=models.CASCADE,
        related_name='next_of_kin'
    )

    full_name = models.CharField(max_length=255)

    relationship = models.CharField(
        max_length=20,
        choices=RELATIONSHIP_CHOICES
    )

    phone_number = models.CharField(max_length=15)

    email = models.EmailField(blank=True, null=True)

    id_number = models.CharField(max_length=20, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name} ({self.get_relationship_display()}) — NOK of {self.member}"


# ==========================================
# DEPENDANT  (Super Subscription only)
# Age-based auto-removal at exactly 18 years
# ==========================================
class Dependant(models.Model):

    RELATIONSHIP_CHOICES = [
        ('child', 'Child'),
        ('spouse', 'Spouse'),
        ('sibling', 'Sibling'),
        ('parent', 'Parent'),
        ('other', 'Other'),
    ]

    member = models.ForeignKey(
        IndividualMember,
        on_delete=models.CASCADE,
        related_name='dependants'
    )

    full_name = models.CharField(max_length=255)

    relationship = models.CharField(
        max_length=20,
        choices=RELATIONSHIP_CHOICES
    )

    date_of_birth = models.DateField()

    id_number = models.CharField(max_length=20, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Soft-flag so the record is retained for audit purposes
    # but effectively treated as removed from the active list.
    aged_out = models.BooleanField(
        default=False,
        help_text="Set to True automatically when the dependant turns 18"
    )

    aged_out_date = models.DateField(
        null=True,
        blank=True,
        help_text="The date on which the dependant was auto-removed"
    )

    @property
    def age(self):
        """Returns the dependant's current age in completed years."""
        today = datetime.date.today()
        dob = self.date_of_birth
        return today.year - dob.year - (
            (today.month, today.day) < (dob.month, dob.day)
        )

    @property
    def turns_18_on(self):
        """Returns the exact date the dependant turns 18."""
        dob = self.date_of_birth
        try:
            return dob.replace(year=dob.year + 18)
        except ValueError:
            # Feb 29 edge-case — use Mar 1
            return dob.replace(year=dob.year + 18, day=28) + datetime.timedelta(days=1)

    def check_and_age_out(self):
        """
        Call this method (e.g. from a management command or Celery beat task)
        to soft-delete dependants who have reached their 18th birthday.
        Returns True if the record was newly aged out.
        """
        if not self.aged_out and self.age >= 18:
            self.aged_out = True
            self.aged_out_date = datetime.date.today()
            self.save(update_fields=['aged_out', 'aged_out_date'])
            return True
        return False

    def __str__(self):
        return f"{self.full_name} (age {self.age}) — dependant of {self.member}"


# ==========================================
# BENEFICIARY  (Super Subscription only)
# ==========================================
class Beneficiary(models.Model):

    RELATIONSHIP_CHOICES = [
        ('spouse', 'Spouse'),
        ('child', 'Child'),
        ('parent', 'Parent'),
        ('sibling', 'Sibling'),
        ('other', 'Other'),
    ]

    member = models.ForeignKey(
        IndividualMember,
        on_delete=models.CASCADE,
        related_name='beneficiaries'
    )

    full_name = models.CharField(max_length=255)

    relationship = models.CharField(
        max_length=20,
        choices=RELATIONSHIP_CHOICES
    )

    phone_number = models.CharField(max_length=15)

    id_number = models.CharField(max_length=20, blank=True, null=True)

    # Allocation percentage (all beneficiaries for one member must sum to 100)
    allocation_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100.00,
        help_text="Percentage of benefits allocated to this beneficiary"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name} ({self.allocation_percentage}%) — beneficiary of {self.member}"


# ==========================================
# SACCO MEMBER
# ==========================================
class SaccoMember(BaseMember):

    sacco_name = models.CharField(max_length=255, blank=True, null=True)

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

    def save(self, *args, **kwargs):

    # ONLY generate AFTER payment approval
        if self.payment_status == "paid" and not self.membership_number:
            self.membership_number = generate_unique_membership_number()

        super().save(*args, **kwargs)
    def __str__(self):
        return self.sacco_name or "Sacco"
    
# ==========================================
# PARTNER MEMBER (UPDATED)
# ==========================================
class PartnerMember(BaseMember):

    organization_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    @property
    def total_donations(self):
        total = self.donations.filter(
            status="paid"
        ).aggregate(total=models.Sum("amount"))["total"]

        return total or 0

    def __str__(self):
        return self.organization_name or "Partner"

    # =========================
    # TOTAL DONATIONS (AUTO)
    # =========================
    @property
    def total_donations(self):

        total = self.donations.filter(
            status="paid"
        ).aggregate(
            total=models.Sum("amount")
        )["total"]

        return total or 0

    def __str__(self):
        return self.organization_name or "Partner"


# ==========================================
# PARTNER DONATIONS (NEW CORE TABLE)
# ==========================================
class PartnerDonation(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),   # admin approved
        ('rejected', 'Rejected'),
    ]

    partner = models.ForeignKey(
        PartnerMember,
        on_delete=models.CASCADE,
        related_name="donations"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    transaction_code = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )
    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)

        # 🔥 THIS IS THE KEY LOGIC
        if self.status == "paid":

            partner = self.partner

            # activate partner
            partner.payment_status = "paid"

            # generate membership number ONLY ON FIRST APPROVAL
            if not partner.membership_number:
                partner.membership_number = generate_unique_membership_number()

            partner.save()
    def __str__(self):
        return f"{self.partner.organization_name} - {self.amount}"
# ==========================================
# VEHICLE
# ==========================================
class Vehicle(models.Model):

    VEHICLE_TYPES = [
        ('bodaboda', 'Boda Boda'),
        ('uber', 'Uber'),
        ('long_distance', 'Long Distance'),
        ('tuktuk', 'Tuk Tuk'),
        ('minibus_matatu', 'Minibus / Matatu'),
    ]

    VEHICLE_PRICES = {
        'bodaboda': 3050,
        'uber': 2500,
        'long_distance': 10000,
        'tuktuk': 2000,
        'minibus_matatu': 4000,
    }

    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
    ]

    sacco = models.ForeignKey(
        'SaccoMember',
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
        blank=True,
        null=True
    )

    payment_status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS,
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.amount = self.VEHICLE_PRICES.get(self.vehicle_type, 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.number_plate

class Complaint(models.Model):

    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    ]

    CATEGORY_CHOICES = [
        ("membership", "Membership"),
        ("payment", "Payment"),
        ("event", "Event"),
        ("account", "Account"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="complaints"
    )

    ticket_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES, default="Membership"
    )
    subject = models.CharField(max_length=255)

    description = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="open"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):

        if not self.ticket_number:
            last = Complaint.objects.order_by("-id").first()

            next_id = 1 if not last else last.id + 1

            self.ticket_number = f"CMP{str(next_id).zfill(5)}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.ticket_number

class Event(models.Model):

    title = models.CharField(max_length=255)

    description = models.TextField()

    event_date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)

class EventParticipant(models.Model):

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    registered_at = models.DateTimeField(auto_now_add=True)

class ReportCases(models.Model):

    STATUS_CHOICES = [
        ("open", "Open"),
        ("investigating", "Investigating"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    ]

    INCIDENT_TYPES = [
        ("overloading", "Overloading"),
        ("reckless_driving", "Reckless Driving"),
        ("misconduct", "Crew Misconduct"),
        ("fare_overcharge", "Fare Overcharge"),
        ("harassment", "Harassment"),
        ("unsafe_vehicle", "Unsafe Vehicle"),
        ("other", "Other"),
    ]

    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="vehicle_incidents"
    )

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incident_reports"
    )

    # Registered SACCO
    sacco = models.ForeignKey(
        SaccoMember,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    # Unregistered SACCO
    external_sacco_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    incident_type = models.CharField(
        max_length=50,
        choices=INCIDENT_TYPES
    )

    description = models.TextField()

    journey_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="open"
    )

    number_plate = models.CharField(
        max_length=20,
        blank=True,
        default=""
    )

    vehicle_type = models.CharField(
        max_length=20,
        choices=Vehicle.VEHICLE_TYPES,
        blank=True,
        default=""
    )

    route = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.number_plate} - {self.incident_type}"