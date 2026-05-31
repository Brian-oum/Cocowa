
from django import forms
from django.contrib.auth.models import User

from .models import (
    IndividualMember,
    SaccoMember,
    PartnerMember,
    Vehicle,
    UserProfile,
    Complaint
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

    class Meta:

        model = SaccoMember

        fields = [
            "sacco_name",
            "sacco_registration_number",
        ]

        widgets = {

            "sacco_name": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "sacco_registration_number": forms.TextInput(attrs={
                "class": "form-control"
            }),
        }

    def clean(self):

        cleaned_data = super().clean()

        required_fields = [
            "sacco_name",
            "sacco_registration_number",
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

    class Meta:

        model = PartnerMember

        fields = [
            "organization_name",
            "donation_amount",
        ]

        widgets = {

            "organization_name": forms.TextInput(attrs={
                "class": "form-control"
            }),

            "donation_amount": forms.NumberInput(attrs={
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

class ComplaintForm(forms.ModelForm):

    class Meta:
        model = Complaint
        fields = ["title", "description", "priority"]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter complaint title"
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Describe your issue"
            }),
            "priority": forms.Select(attrs={
                "class": "form-control"
            }),
        }