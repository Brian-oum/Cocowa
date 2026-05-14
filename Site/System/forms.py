from django import forms
from .models import Membership

class MembershipForm(forms.ModelForm):
    class Meta:
        model = Membership
        fields = [
            'first_name',
            'second_name',
            'email',
            'id_number',
            'phone_number',
            'package'
        ]