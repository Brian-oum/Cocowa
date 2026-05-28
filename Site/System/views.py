from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from django.contrib.auth import logout
import json
import os

from .models import *


# ==========================================
# REGISTER
# ==========================================
def join_membership(request):

    if request.method == "POST":

        email = request.POST.get("email")
        password = request.POST.get("password")
        role = request.POST.get("member_type")
        phone = request.POST.get("phone_number")

        if User.objects.filter(username=email).exists():
            messages.error(request, "Account already exists")
            return redirect("join_membership")

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password
        )

        UserProfile.objects.create(
            user=user,
            role=role,
            phone_number=phone,
            profile_completed=False
        )

        # create empty member shell
        if role == "individual":
            IndividualMember.objects.create(user=user, phone_number=phone, email=email)

        elif role == "sacco":
            SaccoMember.objects.create(user=user, phone_number=phone, email=email)

        elif role == "partner":
            PartnerMember.objects.create(user=user, phone_number=phone, email=email)

        messages.success(request, "Account created. Please login.")

        return redirect("login")

    return render(request, "System/join.html")


# ==========================================
# LOGIN
# ==========================================
def custom_login(request):

    if request.method == "POST":

        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, username=email, password=password)

        if user:
            login(request, user)
            return redirect("dashboard_redirect")

        messages.error(request, "Invalid login credentials")

    return render(request, "System/login.html")


# ==========================================
# DASHBOARD REDIRECT (ROLE BASED)
# ==========================================
@login_required
def dashboard_redirect(request):

    profile = UserProfile.objects.get(user=request.user)

    if profile.role == "individual":
        return redirect("individual_dashboard")

    elif profile.role == "sacco":
        return redirect("sacco_dashboard")

    elif profile.role == "partner":
        return redirect("partner_dashboard")

    return redirect("home")


# ==========================================
# INDIVIDUAL DASHBOARD
# ==========================================
from datetime import timedelta
from django.utils import timezone


def calculate_health_score(member, profile):
    score = 0

    # profile completeness
    if member.first_name: score += 20
    if member.second_name: score += 20
    if member.id_number: score += 20
    if member.package: score += 10

    # payment status
    if member.payment_status == "paid":
        score += 30

    return score

def calculate_profile_progress(member):

    fields = [
        member.first_name,
        member.second_name,
        member.id_number,
        member.package,
        member.membership_number
    ]

    filled = len([f for f in fields if f])
    total = len(fields)

    return int((filled / total) * 100) if total > 0 else 0

@login_required
def individual_dashboard(request):

    profile = UserProfile.objects.get(user=request.user)
    member = IndividualMember.objects.filter(user=request.user).first()

    if not profile.profile_completed:
        return redirect("complete_individual_profile")

    # =========================
    # CORE STATS
    # =========================
    progress = calculate_profile_progress(member)
    health_score = calculate_health_score(member, profile)
    remaining = 100 - progress

    # =========================
    # MEMBERSHIP DURATION
    # =========================
    joined_date = member.created_at
    membership_days = (timezone.now().date() - member.created_at.date()).days

    membership_years = membership_days // 365

    # =========================
    # RENEWAL DATE (1 YEAR CYCLE)
    # =========================
    renewal_date = joined_date + timedelta(days=365) if joined_date else None
    days_to_renewal = (renewal_date.date() - timezone.now().date()).days if renewal_date else 0

    # =========================
    # FINANCIAL LOGIC
    # =========================
    amount_due = member.amount
    amount_paid = member.amount if member.payment_status == "paid" else 0
    balance = amount_due - amount_paid

    # =========================
    # PACKAGE INTELLIGENCE
    # =========================
    package_benefits = {
        "Standard": "Basic access, registration, membership card",
        "Super Subscription": "Priority support, premium benefits, full access"
    }

    package_info = package_benefits.get(member.package, "No package selected")

    # =========================
    # SMART ALERTS
    # =========================
    alerts = []

    if member.payment_status != "paid":
        alerts.append("⚠ Payment pending — complete payment to activate account.")

    if progress < 60:
        alerts.append("⚠ Complete your profile to unlock full benefits.")

    if days_to_renewal <= 30:
        alerts.append("⏳ Renewal approaching soon.")

    if not member.membership_number:
        alerts.append("ℹ Membership number will be generated after approval.")

    return render(request, "System/individual.html", {

        "member": member,
        "progress": progress,
        "remaining": remaining,
        "health_score": health_score,

        "membership_days": membership_days,
        "membership_years": membership_years,
        "renewal_date": renewal_date,
        "days_to_renewal": days_to_renewal,

        "amount_due": amount_due,
        "amount_paid": amount_paid,
        "balance": balance,

        "package_info": package_info,
        "alerts": alerts
    })
# ==========================================
# SACCO DASHBOARD
# ==========================================
@login_required
def sacco_dashboard(request):

    profile = UserProfile.objects.get(user=request.user)
    member = SaccoMember.objects.filter(user=request.user).first()

    if not profile.profile_completed:
        return redirect("complete_sacco_profile")

    vehicles = Vehicle.objects.filter(sacco=member) if member else []

    return render(request, "System/sacco.html", {
        "member": member,
        "vehicles": vehicles
    })


# ==========================================
# PARTNER DASHBOARD
# ==========================================
@login_required
def partner_dashboard(request):

    profile = UserProfile.objects.get(user=request.user)
    member = PartnerMember.objects.filter(user=request.user).first()

    if not profile.profile_completed:
        return redirect("complete_partner_profile")

    return render(request, "System/partner.html", {
        "member": member
    })


# ==========================================
# COMPLETE INDIVIDUAL PROFILE
# ==========================================
@login_required
def complete_individual_profile(request):

    member, _ = IndividualMember.objects.get_or_create(user=request.user)
    profile = UserProfile.objects.get(user=request.user)

    # check if user clicked edit
    edit_mode = request.GET.get("edit") == "1"

    if request.method == "POST":

        member.first_name = request.POST.get("first_name")
        member.second_name = request.POST.get("second_name")
        member.phone_number = request.POST.get("phone_number")
        member.email = request.POST.get("email")
        member.id_number = request.POST.get("id_number")
        member.package = request.POST.get("package")

        member.save()

        # mark complete only once
        if not profile.profile_completed:
            profile.profile_completed = True
            profile.save()

            messages.success(request, "Profile completed successfully!")
            return redirect("payment", member.id)

        messages.success(request, "Profile updated successfully!")
        return redirect("individual_profile")

    context = {
        "member": member,
        "profile": profile,
        "is_complete": profile.profile_completed,
        "edit_mode": edit_mode
    }

    return render(request, "System/individual_profile.html", context)
# ==========================================
# COMPLETE SACCO PROFILE
# ==========================================
@login_required
def complete_sacco_profile(request):

    member = SaccoMember.objects.get(user=request.user)
    profile = UserProfile.objects.get(user=request.user)

    if request.method == "POST":

        member.sacco_name = request.POST.get("sacco_name")
        member.sacco_registration_number = request.POST.get("sacco_registration_number")
        member.save()

        vehicles_json = request.POST.get("vehicles_data")

        if vehicles_json:
            vehicles = json.loads(vehicles_json)

            for v in vehicles:
                Vehicle.objects.create(
                    sacco=member,
                    vehicle_type=v.get("vehicle_type"),
                    number_plate=v.get("number_plate"),
                    route=v.get("route"),
                )

        profile.profile_completed = True
        profile.save()

        return redirect("sacco_dashboard")

    return render(request, "profiles/complete_sacco.html", {
        "member": member
    })


# ==========================================
# COMPLETE PARTNER PROFILE
# ==========================================
@login_required
def complete_partner_profile(request):

    member = PartnerMember.objects.get(user=request.user)
    profile = UserProfile.objects.get(user=request.user)

    if request.method == "POST":

        member.organization_name = request.POST.get("organization_name")
        member.donation_amount = request.POST.get("donation_amount") or 0
        member.save()

        profile.profile_completed = True
        profile.save()

        return redirect("partner_dashboard")

    return render(request, "profiles/complete_partner.html", {
        "member": member
    })


# ==========================================
# PAYMENT PAGE (MANUAL FROM DASHBOARD)
# ==========================================
def payment_page(request, member_id):

    member = None
    member_type = None
    amount = 0

    try:
        member = IndividualMember.objects.get(id=member_id)
        member_type = "individual"
        amount = member.amount
    except:
        pass

    if not member:
        try:
            member = SaccoMember.objects.get(id=member_id)
            member_type = "sacco"
            amount = sum(v.amount for v in member.vehicles.all())
        except:
            pass

    if not member:
        try:
            member = PartnerMember.objects.get(id=member_id)
            member_type = "partner"
            amount = member.donation_amount or 0
        except:
            pass

    if not member:
        raise Http404("Member not found")

    if request.method == "POST":
        member.transaction_code = request.POST.get("transaction_code")
        member.payment_status = "pending"
        member.save()

        return redirect("payment_status", member_id=member.id)

    return render(request, "System/payment.html", {
        "member": member,
        "member_type": member_type,
        "amount": amount
    })


# ==========================================
# PAYMENT STATUS
# ==========================================
def payment_status(request, member_id):

    member = get_object_or_404(IndividualMember, id=member_id)

    return render(request, "System/payment_status.html", {
        "member": member
    })


# ==========================================
# HOME PAGES
# ==========================================
def home(request): return render(request, "System/home.html")
def about(request): return render(request, "System/about.html")
def contact(request): return render(request, "System/contact.html")
def services(request): return render(request, "System/services.html")

def check_membership(request):

    member = None
    error = None

    if request.method == "POST":

        membership_number = request.POST.get("membership_number")

        # =========================
        # SEARCH ACROSS ALL MODELS
        # =========================
        try:
            member = IndividualMember.objects.get(
                membership_number=membership_number
            )
        except IndividualMember.DoesNotExist:
            member = None

        if not member:
            try:
                member = SaccoMember.objects.get(
                    membership_number=membership_number
                )
            except SaccoMember.DoesNotExist:
                member = None

        if not member:
            try:
                member = PartnerMember.objects.get(
                    membership_number=membership_number
                )
            except PartnerMember.DoesNotExist:
                member = None

        # =========================
        # VEHICLE SEARCH (optional fallback)
        # =========================
        if not member:
            try:
                member = Vehicle.objects.get(
                    membership_number=membership_number
                )
            except Vehicle.DoesNotExist:
                member = None

        # =========================
        # ERROR HANDLING
        # =========================
        if not member:
            error = "No member found with that membership number."

    return render(
        request,
        "System/membership.html",
        {
            "member": member,
            "error": error
        }
    )

def custom_logout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("login")


# =========================================================
# DISPLAY MEMBERSHIP CARD PAGE
# =========================================================
@login_required
def membership_card(request):

    role = request.user.userprofile.role

    member = None

    if role == "individual":
        member = get_object_or_404(
            IndividualMember,
            user=request.user
        )

    elif role == "sacco":
        member = get_object_or_404(
            SaccoMember,
            user=request.user
        )

    elif role == "partner":
        member = get_object_or_404(
            PartnerMember,
            user=request.user
        )

    context = {
        "member": member,
        "role": role,
    }

    return render(
        request,
        "System/membership_card.html",
        context
    )


# =========================================================
# DOWNLOAD MEMBERSHIP CARD PDF
# =========================================================
@login_required
def download_membership_card(request):

    role = request.user.userprofile.role

    member = None

    # =========================
    # GET MEMBER BASED ON ROLE
    # =========================
    if role == "individual":

        member = get_object_or_404(
            IndividualMember,
            user=request.user
        )

    elif role == "sacco":

        member = get_object_or_404(
            SaccoMember,
            user=request.user
        )

    elif role == "partner":

        member = get_object_or_404(
            PartnerMember,
            user=request.user
        )

    # =========================
    # PDF RESPONSE
    # =========================
    response = HttpResponse(
        content_type='application/pdf'
    )

    response['Content-Disposition'] = (
        f'attachment; filename="COCOWA_Card_{member.id}.pdf"'
    )

    p = canvas.Canvas(response, pagesize=A4)

    width, height = A4

    # =========================
    # COLORS
    # =========================
    navy = colors.HexColor("#001C3D")
    cream = colors.HexColor("#FDF2E2")
    accent_green = colors.HexColor("#28A745")

    # =========================
    # CARD BACKGROUND
    # =========================
    p.setFillColor(cream)

    p.roundRect(
        50,
        height - 350,
        width - 100,
        300,
        15,
        fill=1,
        stroke=0
    )

    # =========================
    # BORDER
    # =========================
    p.setStrokeColor(navy)

    p.setLineWidth(2)

    p.roundRect(
        50,
        height - 350,
        width - 100,
        300,
        15
    )

    # =========================
    # HEADER
    # =========================
    header_y = height - 100

    logo_path = finders.find(
        'images/cocowalogo.png'
    )

    if logo_path and os.path.exists(logo_path):

        p.drawImage(
            logo_path,
            70,
            header_y - 25,
            width=60,
            height=60,
            mask='auto'
        )

    p.setFillColor(navy)

    p.setFont(
        "Helvetica-Bold",
        22
    )

    p.drawRightString(
        width - 70,
        header_y,
        "MEMBERSHIP CARD"
    )

    p.setLineWidth(1)

    p.line(
        70,
        header_y - 30,
        width - 70,
        header_y - 30
    )

    # =========================
    # MEMBER DETAILS
    # =========================
    y_pos = header_y - 70

    details = []

    if role == "individual":

        details = [
            ("NAME:", f"{member.first_name} {member.second_name}"),
            ("MEMBER NO:", member.membership_number),
            ("PACKAGE:", member.package),
            ("PHONE:", member.phone_number),
            ("EMAIL:", member.email),
        ]

    elif role == "sacco":

        details = [
            ("SACCO:", member.sacco_name),
            ("MEMBER NO:", member.membership_number),
            ("REG NO:", member.sacco_registration_number),
            ("PHONE:", member.phone_number),
            ("EMAIL:", member.email),
        ]

    elif role == "partner":

        details = [
            ("ORGANIZATION:", member.organization_name),
            ("MEMBER NO:", member.membership_number),
            ("DONATION:", f"KES {member.donation_amount}"),
            ("PHONE:", member.phone_number),
            ("EMAIL:", member.email),
        ]

    for label, value in details:

        p.setFillColor(navy)

        p.setFont(
            "Helvetica-Bold",
            10
        )

        p.drawString(
            70,
            y_pos,
            label
        )

        p.setFillColor(colors.black)

        p.setFont(
            "Helvetica",
            12
        )

        p.drawString(
            180,
            y_pos,
            str(value)
        )

        y_pos -= 28

    # =========================
    # STATUS BADGE
    # =========================
    status_text = (
        "ACTIVE"
        if member.payment_status == "paid"
        else "PENDING"
    )

    status_color = (
        accent_green
        if member.payment_status == "paid"
        else colors.red
    )

    p.setFillColor(status_color)

    p.roundRect(
        width - 180,
        height - 320,
        100,
        35,
        8,
        fill=1,
        stroke=0
    )

    p.setFillColor(colors.white)

    p.setFont(
        "Helvetica-Bold",
        11
    )

    p.drawCentredString(
        width - 130,
        height - 307,
        status_text
    )

    # =========================
    # FOOTER
    # =========================
    p.setFillColor(colors.grey)

    p.setFont(
        "Helvetica-Oblique",
        8
    )

    p.drawString(
        70,
        height - 340,
        f"Generated on: {member.created_at.strftime('%Y-%m-%d')}"
    )

    p.drawRightString(
        width - 70,
        height - 340,
        "COCOWA Membership Verification"
    )

    # =========================
    # SAVE PDF
    # =========================
    p.showPage()

    p.save()

    return response