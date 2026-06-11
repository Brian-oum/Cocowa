from django.contrib import admin
from .models import (
    IndividualMember,
    SaccoMember,
    PartnerMember,
    Vehicle,
    PartnerDonation, UserProfile
)
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):

    list_display = ("user", "role", "phone_number", "profile_completed")

    list_filter = ("role", "profile_completed")

    search_fields = ("user__username", "user__email", "phone_number")

    def get_readonly_fields(self, request, obj=None):
        # Prevent normal admins from changing roles of existing users
        if not request.user.is_superuser:
            return ("role",)
        return ()
    def save_model(self, request, obj, form, change):

    # Only superuser can assign manager role
        if obj.role == "manager" and not request.user.is_superuser:
            raise PermissionError("Only superuser can assign manager role")

        super().save_model(request, obj, form, change)
@admin.register(IndividualMember)
class IndividualMemberAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "first_name",
        "second_name",
        "id_number",
        "package",
        "amount",
        "payment_status",
        "membership_number",
        "created_at",
    )

    list_filter = (
        "package",
        "payment_status",
        "created_at",
    )

    search_fields = (
        "first_name",
        "second_name",
        "id_number",
        "membership_number",
        "phone_number",
        "email",
    )

    readonly_fields = ("amount", "membership_number", "created_at")
    ordering = ("-created_at",)

class VehicleInline(admin.TabularInline):
    model = Vehicle
    extra = 1
    fields = ("vehicle_type", "number_plate", "route", "amount", "payment_status")
    readonly_fields = ("amount",)


@admin.register(SaccoMember)
class SaccoMemberAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "sacco_name",
        "payment_status",
        "membership_number",
        "created_at",
    )

    search_fields = (
        "sacco_name",
        "phone_number",
        "email",
    )

    list_filter = ("payment_status", "created_at")

    inlines = [VehicleInline]

    readonly_fields = ("membership_number", "created_at")
    ordering = ("-created_at",)

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "sacco",
        "vehicle_type",
        "number_plate",
        "route",
        "amount",
        "payment_status",
        "created_at",
    )

    list_filter = (
        "vehicle_type",
        "payment_status",
        "created_at",
    )

    search_fields = (
        "number_plate",
        "route",
        "sacco__sacco_name",
    )


    ordering = ("-created_at",)

@admin.register(PartnerMember)
class PartnerMemberAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "organization_name",
        "user",
        "payment_status",
        "total_donations_display",
        "created_at",
    )

    list_display_links = ("id", "organization_name")

    search_fields = (
        "id",
        "organization_name",
        "user__email",
    )

    list_filter = (
        "payment_status",
        "created_at",
    )

    ordering = ("-id",)

    readonly_fields = ("id","created_at")

    def total_donations_display(self, obj):
        return obj.total_donations

    total_donations_display.short_description = "Total Donations"

@admin.register(PartnerDonation)
class PartnerDonationAdmin(admin.ModelAdmin):

    list_display = (
        "partner",
        "amount",
        "status",
        "transaction_code",
        "created_at",
    )

    list_filter = ("status",)

    search_fields = (
        "partner__organization_name",
        "transaction_code",
    )

    actions = ["mark_as_paid"]

    def mark_as_paid(self, request, queryset):
        queryset.update(status="paid")
        self.message_user(request, "Selected donations marked as PAID.")

    mark_as_paid.short_description = "Mark selected donations as PAID"

