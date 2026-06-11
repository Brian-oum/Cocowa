from django import forms
from django.contrib.auth.models import User
from django.utils import timezone

from .models import (
    IndividualMember,
    SaccoMember,
    PartnerMember,
    Vehicle,
    UserProfile,
    Complaint,
    NextOfKin,
    Dependant,
    Beneficiary,
)


# =====================================================
# SIMPLE REGISTRATION FORM
# =====================================================
class RegistrationForm(forms.Form):

    ROLE_CHOICES = [
        ("individual", "Individual"),
        ("sacco", "Sacco"),
        ("partner", "Partner/Donor"),
    ]

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "Enter Email"
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Enter Password"
        })
    )

    phone_number = forms.CharField(
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Phone Number"
        })
    )

    member_type = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={
            "class": "form-control"
        })
    )

    def clean_email(self):

        email = self.cleaned_data.get("email")

        if User.objects.filter(username=email).exists():

            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email


# =====================================================
# LOGIN FORM
# =====================================================
class LoginForm(forms.Form):

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "Email"
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Password"
        })
    )


# =====================================================
# INDIVIDUAL PROFILE COMPLETION FORM
# =====================================================
class IndividualMemberForm(forms.ModelForm):

    # --------------------------------------------------
    # COCOWA DATA CONSENT  — shown to ALL individual users
    # --------------------------------------------------
    cocowa_data_consent = forms.BooleanField(
        required=False,
        label="I consent to sharing my data with COCOWA",
        widget=forms.CheckboxInput(attrs={
            "class": "consent-checkbox",
            "id": "cocowa_data_consent",
        }),
    )

    class Meta:

        model = IndividualMember

        fields = [
            "first_name",
            "second_name",
            "id_number",
            "package",
        ]

        widgets = {

            "first_name": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "second_name": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "id_number": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "package": forms.Select(attrs={
                "class": "form-control"
            }),
        }

    def clean(self):

        cleaned_data = super().clean()

        required_fields = [
            "first_name",
            "second_name",
            "id_number",
            "package",
        ]

        for field in required_fields:

            if not cleaned_data.get(field):

                self.add_error(
                    field,
                    "This field is required"
                )

        return cleaned_data


# =====================================================
# SACCO PROFILE COMPLETION FORM
# =====================================================
class SaccoMemberForm(forms.ModelForm):

    # --------------------------------------------------
    # COCOWA DATA CONSENT  — shown to ALL users
    # --------------------------------------------------
    cocowa_data_consent = forms.BooleanField(
        required=False,
        label="I consent to sharing my data with COCOWA",
        widget=forms.CheckboxInput(attrs={
            "class": "consent-checkbox",
            "id": "cocowa_data_consent",
        }),
    )

    class Meta:

        model = SaccoMember

        fields = [
            "sacco_name",
        ]

        widgets = {

            "sacco_name": forms.TextInput(attrs={
                "class": "form-control"
            }),
        }

    def clean(self):

        cleaned_data = super().clean()

        required_fields = [
            "sacco_name",
        ]

        for field in required_fields:

            if not cleaned_data.get(field):

                self.add_error(
                    field,
                    "This field is required"
                )

        return cleaned_data


# =====================================================
# PARTNER PROFILE COMPLETION FORM
# =====================================================
class PartnerMemberForm(forms.ModelForm):

    # --------------------------------------------------
    # COCOWA DATA CONSENT  — shown to ALL users
    # --------------------------------------------------
    cocowa_data_consent = forms.BooleanField(
        required=False,
        label="I consent to sharing my data with COCOWA",
        widget=forms.CheckboxInput(attrs={
            "class": "consent-checkbox",
            "id": "cocowa_data_consent",
        }),
    )

    class Meta:

        model = PartnerMember

        fields = [
            "organization_name",
        ]

        widgets = {

            "organization_name": forms.TextInput(attrs={
                "class": "form-control"
            }),

        }

    def clean(self):

        cleaned_data = super().clean()

        if not cleaned_data.get("organization_name"):

            self.add_error(
                "organization_name",
                "Organization name is required"
            )

        return cleaned_data


# =====================================================
# NEXT OF KIN FORM  (Super Subscription only)
# =====================================================
class NextOfKinForm(forms.ModelForm):

    class Meta:

        model = NextOfKin

        fields = [
            "full_name",
            "relationship",
            "phone_number",
            "email",
            "id_number",
        ]

        widgets = {
            "full_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Full legal name",
            }),
            "relationship": forms.Select(attrs={
                "class": "form-control",
            }),
            "phone_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. +254 7XX XXX XXX",
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "Email address (optional)",
            }),
            "id_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "National ID / Passport (optional)",
            }),
        }

    def clean(self):
        cleaned_data = super().clean()

        for field in ("full_name", "relationship", "phone_number"):
            if not cleaned_data.get(field):
                self.add_error(field, "This field is required.")

        return cleaned_data


# =====================================================
# DEPENDANT FORM  (Super Subscription only)
# =====================================================
class DependantForm(forms.ModelForm):

    class Meta:

        model = Dependant

        fields = [
            "full_name",
            "relationship",
            "date_of_birth",
            "id_number",
        ]

        widgets = {
            "full_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Full name",
            }),
            "relationship": forms.Select(attrs={
                "class": "form-control",
            }),
            "date_of_birth": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "id_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "National ID / Passport (optional)",
            }),
        }

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get("date_of_birth")

        if dob:
            if dob >= timezone.now().date():
                raise forms.ValidationError(
                    "Date of birth must be in the past."
                )

            # Block adding someone already 18+
            import datetime
            age = (
                timezone.now().date().year - dob.year
                - (
                    (timezone.now().date().month, timezone.now().date().day)
                    < (dob.month, dob.day)
                )
            )

            if age >= 18:
                raise forms.ValidationError(
                    "Dependants must be under 18 years of age. "
                    "Persons aged 18 or over cannot be added as dependants."
                )

        return dob

    def clean(self):
        cleaned_data = super().clean()

        for field in ("full_name", "relationship", "date_of_birth"):
            if not cleaned_data.get(field):
                self.add_error(field, "This field is required.")

        return cleaned_data


# =====================================================
# BENEFICIARY FORM  (Super Subscription only)
# =====================================================
class BeneficiaryForm(forms.ModelForm):

    class Meta:

        model = Beneficiary

        fields = [
            "full_name",
            "relationship",
            "phone_number",
            "id_number",
            "allocation_percentage",
        ]

        widgets = {
            "full_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Full legal name",
            }),
            "relationship": forms.Select(attrs={
                "class": "form-control",
            }),
            "phone_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. +254 7XX XXX XXX",
            }),
            "id_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "National ID / Passport (optional)",
            }),
            "allocation_percentage": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "1",
                "max": "100",
                "step": "0.01",
                "placeholder": "e.g. 50",
            }),
        }

    def clean_allocation_percentage(self):
        value = self.cleaned_data.get("allocation_percentage")

        if value is not None:
            if value <= 0 or value > 100:
                raise forms.ValidationError(
                    "Allocation must be between 1% and 100%."
                )

        return value

    def clean(self):
        cleaned_data = super().clean()

        for field in ("full_name", "relationship", "phone_number"):
            if not cleaned_data.get(field):
                self.add_error(field, "This field is required.")

        return cleaned_data


# =====================================================
# VEHICLE FORM
# =====================================================
class VehicleForm(forms.ModelForm):

    class Meta:

        model = Vehicle

        fields = [
            "vehicle_type",
            "number_plate",
            "route",
        ]

        widgets = {

            "vehicle_type": forms.Select(attrs={
                "class": "form-control"
            }),

            "number_plate": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "route": forms.TextInput(attrs={
                "class": "form-control"
            }),
        }

# ==========================================
# COMPLAINT FORM (GENERAL SUPPORT TICKET)
# ==========================================
class ComplaintForm(forms.ModelForm):

    class Meta:
        model = Complaint
        fields = ["category", "description", "subject"]

        widgets = {
            "subject": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter the ticket subject"
            }),
            "category": forms.Select(attrs={
                "class": "form-control",
                "placeholder": "Select a ticket category"
            }),

            "description": forms.Textarea(attrs={
                "class": "form-control",
                "placeholder": "Describe your issue in detail...",
                "rows": 3
            }),
        }

    def save(self, commit=True, user=None):
        complaint = super().save(commit=False)

        # attach logged-in user
        if user:
            complaint.user = user

        if commit:
            complaint.save()

        return complaint


# ==========================================
# VEHICLE INCIDENT REPORT FORM
# ==========================================
class VehicleIncidentForm(forms.Form):

    number_plate = forms.CharField(max_length=20)

    sacco = forms.ModelChoiceField(
        queryset=SaccoMember.objects.all(),
        required=False,
        empty_label="Select SACCO (optional)",
        widget=forms.Select()
    )

    sacco_name = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={
            "placeholder": "Or type SACCO name manually"
        })
    )

    vehicle_type = forms.ChoiceField(choices=[
        ("town_service", "Town Service"),
        ("long_distance", "Long Distance"),
    ])

    route = forms.CharField(max_length=255)

    incident_type = forms.ChoiceField(choices=[
        ("overloading", "Overloading"),
        ("reckless_driving", "Reckless Driving"),
        ("misconduct", "Crew Misconduct"),
        ("fare_overcharge", "Fare Overcharge"),
        ("harassment", "Harassment"),
        ("unsafe_vehicle", "Unsafe Vehicle"),
        ("other", "Other"),
    ])

    journey_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    description = forms.CharField(widget=forms.Textarea)