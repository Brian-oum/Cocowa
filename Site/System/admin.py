from django.contrib import admin
from .models import (
    IndividualMember,
    SaccoMember,
    PartnerMember,
    Vehicle
)

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
        "sacco_registration_number",
        "payment_status",
        "membership_number",
        "created_at",
    )

    search_fields = (
        "sacco_name",
        "sacco_registration_number",
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

    readonly_fields = ("amount", "created_at")

    ordering = ("-created_at",)

@admin.register(PartnerMember)
class PartnerMemberAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "organization_name",
        "donation_amount",
        "payment_status",
        "membership_number",
        "created_at",
    )

    search_fields = (
        "organization_name",
        "phone_number",
        "email",
    )

    list_filter = ("payment_status", "created_at")

    readonly_fields = ("donation_amount", "membership_number", "created_at")

    ordering = ("-created_at",)

