from django.contrib import admin
from .models import Membership


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'second_name', 'package', 'payment_status', 'transaction_code')
    list_filter = ('payment_status', 'package')
    search_fields = ('first_name', 'second_name', 'transaction_code')