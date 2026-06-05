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
from django.contrib.auth import logout
import json
import os
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
import calendar
from .models import *
from .forms import *
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
# ==========================================
# REGISTER
# ==========================================
def join_membership(request):

    if request.method == "POST":

        email = request.POST.get("email")
        password = request.POST.get("password")
        role = request.POST.get("member_type")
        phone = request.POST.get("phone_number")

        # =========================
        # ALLOWED PUBLIC ROLES
        # =========================
        allowed_roles = [
            "individual",
            "sacco",
            "partner",
        ]

        if role not in allowed_roles:
            messages.error(
                request,
                "Invalid membership type selected."
            )
            return redirect("join")

        # =========================
        # CHECK EXISTING USER
        # =========================
        existing_user = User.objects.filter(
            username=email
        ).first()

        if existing_user:

            profile_exists = UserProfile.objects.filter(
                user=existing_user
            ).exists()

            # Existing valid account
            if profile_exists:
                messages.error(
                    request,
                    "Account already exists."
                )
                return redirect("join")

            # Orphaned account
            existing_user.delete()

        # =========================
        # CREATE USER ACCOUNT
        # =========================
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password
        )

        # =========================
        # CREATE USER PROFILE
        # =========================
        UserProfile.objects.create(
            user=user,
            role=role,
            phone_number=phone,
            profile_completed=False
        )

        # =========================
        # CREATE MEMBER RECORD
        # =========================
        if role == "individual":

            IndividualMember.objects.create(
                user=user,
                phone_number=phone,
                email=email
            )

        elif role == "sacco":

            SaccoMember.objects.create(
                user=user,
                phone_number=phone,
                email=email
            )

        elif role == "partner":

            PartnerMember.objects.create(
                user=user,
                phone_number=phone,
                email=email
            )

        messages.success(
            request,
            "Account created successfully. Please login."
        )

        return redirect("login")

    return render(
        request,
        "System/join.html"
    )


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
    elif profile.role == "manager":
        return redirect("manager_dashboard")

    return redirect("home")

# ==========================================
# MANAGER DASHBOARD 
# ==========================================
@login_required
def manager_dashboard(request):

    profile = UserProfile.objects.get(user=request.user)

    if profile.role != "manager":
        return redirect("home")

    # =========================
    # MEMBER COUNTS
    # =========================
    individual_count = IndividualMember.objects.count()
    sacco_count = SaccoMember.objects.count()
    partner_count = PartnerMember.objects.count()

    total_members = individual_count + sacco_count + partner_count

    # =========================
    # ACTIVE MEMBERS
    # =========================
    individual_active = IndividualMember.objects.filter(payment_status="paid").count()
    sacco_active = SaccoMember.objects.filter(payment_status="paid").count()
    partner_active = PartnerMember.objects.filter(payment_status="paid").count()

    active_members = individual_active + sacco_active + partner_active

    # =========================
    # REVENUE
    # =========================
    individual_revenue = IndividualMember.objects.filter(payment_status="paid").aggregate(
        total=Sum("amount")
    )["total"] or 0

    sacco_revenue = Vehicle.objects.filter(payment_status="paid").aggregate(
        total=Sum("amount")
    )["total"] or 0

    partner_revenue = PartnerDonation.objects.filter(status="paid").aggregate(
        total=Sum("amount")
    )["total"] or 0

    total_revenue = individual_revenue + sacco_revenue + partner_revenue

    # =========================
    # COMPLAINTS (TICKETS)
    # =========================
    complaint_open = Complaint.objects.filter(status="open").count()
    complaint_in_progress = Complaint.objects.filter(status="in_progress").count()
    complaint_resolved = Complaint.objects.filter(status="resolved").count()
    complaint_closed = Complaint.objects.filter(status="closed").count()

    complaint_count = (
        complaint_open +
        complaint_in_progress +
        complaint_resolved +
        complaint_closed
    )

    recent_complaints = Complaint.objects.order_by("-created_at")[:3]

    # =========================
    # REPORTED CASES (TOTAL)
    # =========================
    reported_cases = ReportCases.objects.order_by("-created_at")[:3]

    # =========================
    # INSIGHTS
    # =========================
    payment_rate = (active_members / total_members * 100) if total_members else 0

    max_revenue = max(individual_revenue, sacco_revenue, partner_revenue)

    dominant_sector = (
        "Individual" if max_revenue == individual_revenue else
        "Sacco" if max_revenue == sacco_revenue else
        "Partner"
    )

    alerts = []

    if payment_rate < 50:
        alerts.append("⚠ Low payment compliance across system")

    if sacco_count == 0:
        alerts.append("⚠ No SACCO registered")


    # =========================
    # CONTEXT
    # =========================
    context = {
        # members
        "individual_members": individual_count,
        "sacco_members": sacco_count,
        "partner_members": partner_count,
        "total_members": total_members,

        # activity
        "active_members": active_members,

        # revenue
        "individual_revenue": individual_revenue,
        "sacco_revenue": sacco_revenue,
        "partner_revenue": partner_revenue,
        "total_revenue": total_revenue,

        # complaints
        "complaint_count": complaint_count,
        "complaint_open": complaint_open,
        "complaint_in_progress": complaint_in_progress,
        "complaint_resolved": complaint_resolved,
        "complaint_closed": complaint_closed,

        "recent_complaints": recent_complaints,

        # cases
        "reported_cases": reported_cases,

        # insights
        "payment_rate": round(payment_rate, 1),
        "dominant_sector": dominant_sector,

        # alerts
        "alerts": alerts,
    }

    return render(request, "System/manager_dashboard.html", context)
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
    member = get_object_or_404(SaccoMember, user=request.user)

    if not profile.profile_completed:
        return redirect("complete_sacco_profile")

    vehicles = Vehicle.objects.filter(sacco=member).order_by("-created_at")

    # =========================
    # TOTAL VEHICLES
    # =========================
    total_vehicles = vehicles.count()

    # =========================
    # MEMBERSHIP DURATION
    # =========================
    membership_days = (timezone.now().date() - member.created_at.date()).days

    # =========================
    # RENEWAL LOGIC (1 YEAR CYCLE)
    # =========================
    renewal_date = member.created_at.date() + timedelta(days=365)
    days_to_renewal = (renewal_date - timezone.now().date()).days

    # =========================
    # SACCO STATUS
    # =========================
    sacco_status = "ACTIVE" if member.payment_status == "paid" else "PENDING"
    # =========================
    # PROFILE PROGRESS
    # =========================
    fields = [
        member.sacco_name,
        member.phone_number,
        member.email
    ]

    progress = int((sum(1 for f in fields if f) / len(fields)) * 100)
    remaining = 100 - progress

    # =========================
    # FINANCIAL SUMMARY (VEHICLE BASED)
    # =========================
    total_revenue = vehicles.aggregate(total=Sum("amount"))["total"] or 0

    monthly_labels = []
    monthly_data = []

    current_year = timezone.now().year

    for m in range(1, 13):
        month_total = vehicles.filter(
            created_at__year=current_year,
            created_at__month=m
        ).aggregate(total=Sum("amount"))["total"] or 0

        monthly_labels.append(calendar.month_name[m])
        monthly_data.append(float(month_total))

    # =========================
    # RECENT VEHICLES
    # =========================
    recent_vehicles = vehicles[:5]

    # =========================
    # ALERTS
    # =========================
    alerts = []

    if not member.membership_number:
        alerts.append("Membership number pending approval")

    if days_to_renewal <= 30:
        alerts.append("Renewal is approaching soon")

    if total_vehicles == 0:
        alerts.append("No vehicles registered yet")

    return render(request, "System/sacco.html", {

        "member": member,
        "vehicles": vehicles,

        "total_vehicles": total_vehicles,
        "membership_days": membership_days,
        "days_to_renewal": days_to_renewal,

        "progress": progress,
        "remaining": remaining,

        "sacco_status": sacco_status,

        "total_revenue": total_revenue,

        "monthly_labels": json.dumps(monthly_labels),
        "monthly_data": json.dumps(monthly_data),

        "recent_vehicles": recent_vehicles,
        "alerts": alerts
    })

# ==========================================
# PARTNER DASHBOARD
# ==========================================
@login_required
def partner_dashboard(request):

    partner = get_object_or_404(
        PartnerMember,
        user=request.user
    )

    # =========================
    # TOTAL DONATIONS
    # =========================
    total_donation = partner.total_donations

    # =========================
    # LATEST PENDING DONATION
    # =========================
    latest_pending = partner.donations.filter(
        status="pending"
    ).order_by('-created_at').first()

    balance = latest_pending.amount if latest_pending else 0

    # =========================
    # MEMBERSHIP STATS
    # =========================
    membership_days = (
        timezone.now().date() - partner.created_at.date()
    ).days

    membership_years = membership_days // 365

    # =========================
    # IMPACT SCORE
    # =========================
    impact_score = min(100, int(total_donation / 1000))

    # =========================
    # PROFILE COMPLETION
    # =========================
    fields = [
        partner.organization_name,
        partner.phone_number,
        partner.email,
    ]

    progress = int(
        (sum(1 for f in fields if f) / len(fields)) * 100
    )

    # =========================
    # RENEWAL
    # =========================
    renewal_date = (
        partner.created_at.date() + timedelta(days=365)
    )

    days_to_renewal = (
        renewal_date - timezone.now().date()
    ).days

    # =========================
    # ALERTS
    # =========================
    alerts = []

    if partner.payment_status != "paid":
        alerts.append(
            "⚠ Your account is awaiting donation approval."
        )

    if progress < 100:
        alerts.append(
            "⚠ Complete your profile information."
        )

    if days_to_renewal <= 30:
        alerts.append(
            "⏳ Membership renewal approaching."
        )

    return render(request, "System/partner.html", {

        "partner": partner,
        "balance": balance,
        "total_donation": total_donation,

        "membership_years": membership_years,
        "membership_days": membership_days,

        "impact_score": impact_score,

        "progress": progress,
        "remaining": 100 - progress,

        "renewal_date": renewal_date,
        "days_to_renewal": days_to_renewal,

        "alerts": alerts,
    })
# ==========================================
# PARTNER DONATION PAGE
# ==========================================
@login_required
def partner_donation(request):

    partner = get_object_or_404(PartnerMember, user=request.user)

    if request.method == "POST":

        amount = request.POST.get("amount")

        if not amount:
            messages.error(request, "Please enter a valid amount.")
            return redirect("partner_donation")

        # CREATE NEW DONATION RECORD
        PartnerDonation.objects.create(
            partner=partner,
            amount=amount,
            status="pending"
        )

        messages.success(
            request,
            "Donation submitted successfully. Proceed to payment."
        )

        # redirect to payment page using partner id
        return redirect("payment", partner.id)

    return render(request, "System/partner_donation.html", {
        "partner": partner
    })
# ==========================================
# PARTNER REOORT PAGE
# ==========================================
from django.db.models import Sum, Count, Avg
from django.utils import timezone
import calendar


@login_required
def partner_report(request):

    partner = get_object_or_404(PartnerMember, user=request.user)

    donations = partner.donations.all().order_by("-created_at")

    # =========================
    # CORE TOTALS
    # =========================
    total_donations = donations.filter(status="paid").aggregate(
        total=Sum("amount")
    )["total"] or 0

    pending_donations = donations.filter(status="pending").aggregate(
        total=Sum("amount")
    )["total"] or 0

    rejected_donations = donations.filter(status="rejected").aggregate(
        total=Sum("amount")
    )["total"] or 0

    donation_count = donations.filter(status="paid").count()

    avg_donation = donations.filter(status="paid").aggregate(
        avg=Avg("amount")
    )["avg"] or 0

    # =========================
    # MONTHLY ANALYTICS
    # =========================
    current_year = timezone.now().year

    monthly_labels = []
    monthly_data = []
    monthly_counts = []

    best_month = {"name": "", "value": 0}

    for month in range(1, 13):

        month_qs = donations.filter(
            status="paid",
            created_at__year=current_year,
            created_at__month=month
        )

        month_total = month_qs.aggregate(total=Sum("amount"))["total"] or 0
        month_count = month_qs.count()

        monthly_labels.append(calendar.month_name[month])
        monthly_data.append(float(month_total))
        monthly_counts.append(month_count)

        if month_total > best_month["value"]:
            best_month = {
                "name": calendar.month_name[month],
                "value": float(month_total)
            }

    # =========================
    # DONUT DATA (STATUS BREAKDOWN)
    # =========================
    donut_data = [
        float(total_donations),
        float(pending_donations),
        float(rejected_donations),
    ]

    # =========================
    # BAR DATA (MONTHLY COUNT)
    # =========================
    bar_data = monthly_counts

    # =========================
    # RECENT TRANSACTIONS
    # =========================
    recent_donations = donations[:10]

    # =========================
    # INSIGHTS (IMPORTANT UPGRADE)
    # =========================
    insights = [
        f"Total confirmed donations: KES {total_donations:,.0f}",
        f"Average donation size: KES {avg_donation:,.0f}",
        f"Best performing month: {best_month['name']} (KES {best_month['value']:,.0f})",
        f"Total completed transactions: {donation_count}",
    ]

    return render(request, "System/partner_report.html", {
        "partner": partner,

        # totals
        "total_donations": total_donations,
        "pending_donations": pending_donations,
        "rejected_donations": rejected_donations,
        "avg_donation": avg_donation,
        "donation_count": donation_count,

        # charts
        "monthly_labels": json.dumps(monthly_labels),
        "monthly_data": json.dumps(monthly_data),
        "bar_data": bar_data,
        "donut_data": donut_data,

        # tables
        "recent_donations": recent_donations,

        # insights
        "insights": insights,
    })
@login_required
def partner_report_pdf(request):
    partner = PartnerMember.objects.get(user=request.user)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="partner_report.pdf"'

    p = canvas.Canvas(response)

    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, 800, "Partner Donation Report")

    p.setFont("Helvetica", 12)
    p.drawString(50, 770, f"Organization: {partner.organization_name}")
    p.drawString(50, 750, f"Email: {partner.email}")
    p.drawString(50, 730, f"Phone: {partner.phone_number}")

    p.drawString(50, 700, f"Donation Amount: {partner.total_donations}")

    p.showPage()
    p.save()

    return response
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

    member, _ = SaccoMember.objects.get_or_create(
        user=request.user
    )

    profile, _ = UserProfile.objects.get_or_create(
        user=request.user
    )

    edit_mode = request.GET.get("edit") == "1"

    existing_vehicles = Vehicle.objects.filter(
        sacco=member
    )

    if request.method == "POST":

        member.sacco_name = request.POST.get(
            "sacco_name"
        )

        member.phone_number = request.POST.get(
            "phone_number"
        )

        member.email = request.POST.get(
            "email"
        )

        member.save()

        # Remove old vehicles
        member.vehicles.all().delete()

        # Save vehicles
        vehicles_json = request.POST.get(
            "vehicles_data"
        )

        if vehicles_json:

            try:

                vehicles = json.loads(
                    vehicles_json
                )

                for v in vehicles:

                    vehicle_type = v.get(
                        "vehicle_type"
                    )

                    # Legacy support
                    if vehicle_type == "nairobi":
                        vehicle_type = "town_service"

                    allowed_types = [
                        choice[0]
                        for choice in Vehicle.VEHICLE_TYPES
                    ]

                    if vehicle_type not in allowed_types:

                        print(
                            f"INVALID VEHICLE TYPE: {vehicle_type}"
                        )

                        continue

                    Vehicle.objects.create(
                        sacco=member,
                        vehicle_type=vehicle_type,
                        number_plate=v.get(
                            "number_plate"
                        ),
                        route=v.get(
                            "route"
                        ),
                    )

            except json.JSONDecodeError:

                messages.error(
                    request,
                    "Invalid vehicle data submitted."
                )

                return redirect(
                    "complete_sacco_profile"
                )

        if not profile.profile_completed:

            profile.profile_completed = True
            profile.save()

            messages.success(
                request,
                "SACCO profile completed successfully!"
            )

            return redirect(
                "payment_page"
            )

        messages.success(
            request,
            "SACCO profile updated successfully!"
        )

        return redirect(
            "sacco_dashboard"
        )

    context = {
        "vehicle_choices": Vehicle.VEHICLE_TYPES,
        "member": member,
        "profile": profile,
        "vehicles": existing_vehicles,
        "is_complete": profile.profile_completed,
        "edit_mode": edit_mode,
    }

    return render(
        request,
        "System/sacco_profile.html",
        context
    )
# ==========================================
# COMPLETE PARTNER PROFILE
# ==========================================
@login_required
def complete_partner_profile(request):

    member, _ = PartnerMember.objects.get_or_create(
        user=request.user
    )

    profile, _ = UserProfile.objects.get_or_create(
        user=request.user
    )

    edit_mode = request.GET.get("edit") == "1"

    if request.method == "POST":

        member.organization_name = request.POST.get(
            "organization_name"
        )

        member.phone_number = request.POST.get(
            "phone_number"
        )

        member.email = request.POST.get(
            "email"
        )

        member.save()

        # FIRST COMPLETION
        if not profile.profile_completed:

            profile.profile_completed = True
            profile.save()

            messages.success(
                request,
                "Partner profile completed successfully!"
            )

            return redirect("partner_dashboard")

        # UPDATE MODE
        messages.success(
            request,
            "Partner profile updated successfully!"
        )

        return redirect("partner_dashboard")

    context = {
        "member": member,
        "profile": profile,
        "is_complete": profile.profile_completed,
        "edit_mode": edit_mode
    }

    return render(
        request,
        "System/partner_profile.html",
        context
    )


@login_required
def payment_page(request, member_type, member_id):

    member = None
    amount = 0

    # =========================
    # INDIVIDUAL
    # =========================
    if member_type == "individual":
        member = IndividualMember.objects.filter(id=member_id).first()

        if not member:
            raise Http404("Individual not found")

        amount = member.amount if member.payment_status != "paid" else 0

    # =========================
    # SACCO
    # =========================
    elif member_type == "sacco":
        member = SaccoMember.objects.filter(id=member_id).first()

        if not member:
            raise Http404("Sacco not found")

        total_vehicle_amount = sum(
            v.amount or 0 for v in member.vehicles.all()
        )

        amount = total_vehicle_amount if member.payment_status != "paid" else 0

    # =========================
    # PARTNER
    # =========================
    elif member_type == "partner":
        member = PartnerMember.objects.filter(id=member_id).first()

        if not member:
            raise Http404("Partner not found")

        pending = PartnerDonation.objects.filter(
            partner=member,
            status="pending"
        ).order_by("-created_at").first()

        amount = pending.amount if pending else 0

    else:
        raise Http404("Invalid member type")

    # POST handling unchanged
    if request.method == "POST":
        transaction_code = request.POST.get("transaction_code")

        if member.payment_status != "paid":
            member.transaction_code = transaction_code
            member.payment_status = "pending"
            member.save()

        return redirect("payment_status", member.id)

    return render(request, "System/payment.html", {
        "member": member,
        "member_type": member_type,
        "amount": amount
    })
# ==========================================
# PAYMENT STATUS VIEW (UNCHANGED BUT SAFE)
# ==========================================
def payment_status(request, member_id):

    role = request.user.userprofile.role

    if role == "individual":
        member = get_object_or_404(IndividualMember, id=member_id)

    elif role == "sacco":
        member = get_object_or_404(SaccoMember, id=member_id)

    else:
        member = get_object_or_404(PartnerMember, id=member_id)

    return render(request, "System/payment_status.html", {
        "member": member,
        "role": role
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
            ("DONATION:", f"KES {member.total_donations}"),
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

# ==================================================
# 1. CREATE COMPLAINT (TICKET)
# ==================================================
@login_required
def raise_complaint(request):

    profile = get_object_or_404(UserProfile, user=request.user)

    if request.method == "POST":

        form = ComplaintForm(request.POST)

        if form.is_valid():
            form.save(user=request.user)
            messages.success(request, "Complaint submitted successfully.")
            return redirect("my_complaints")

    else:
        form = ComplaintForm()

    return render(request, "System/ticket.html", {
        "form": form
    })


# ==================================================
# 2. USER COMPLAINT LIST
# ==================================================
@login_required
def my_complaints(request):
    complaints = Complaint.objects.filter(
        user=request.user
    ).order_by("-created_at")

    return render(request, "System/my_ticket.html", {
        "complaints": complaints
    })


# ==================================================
# 3. CREATE VEHICLE INCIDENT REPORT
# ==================================================
@login_required
def report_cases(request):

    if request.method == "POST":

        number_plate = request.POST.get(
            "number_plate", ""
        ).strip().upper()

        sacco_value = request.POST.get("sacco")

        sacco_obj = None
        external_sacco_name = None

        if sacco_value:

            try:
                sacco_obj = SaccoMember.objects.get(
                    id=sacco_value
                )

            except (ValueError, SaccoMember.DoesNotExist):

                # User typed a SACCO that isn't registered
                external_sacco_name = sacco_value

        vehicle = Vehicle.objects.filter(
            number_plate__iexact=number_plate
        ).first()

        ReportCases.objects.create(
            reporter=request.user,
            vehicle=vehicle,
            sacco=sacco_obj,
            external_sacco_name=external_sacco_name,
            number_plate=number_plate,
            vehicle_type=request.POST.get("vehicle_type"),
            route=request.POST.get("route"),
            incident_type=request.POST.get("incident_type"),
            journey_date=request.POST.get("journey_date"),
            description=request.POST.get("description"),
        )

        messages.success(
            request,
            "Incident reported successfully."
        )

        return redirect("my_cases")

    sacco_list = SaccoMember.objects.all().order_by(
        "sacco_name"
    )

    return render(
        request,
        "System/report_case.html",
        {
            "sacco_list": sacco_list
        }
    )

# ==================================================
# 4. USER INCIDENT LIST
# ==================================================
@login_required
def my_cases(request):

    incidents = ReportCases.objects.filter(
        reporter=request.user
    ).select_related("vehicle", "sacco").order_by("-created_at")

    return render(request, "System/my_cases.html", {
        "incidents": incidents
    })

# ==================================================
# 5. MANAGER: ALL COMPLAINTS
# ==================================================
@login_required
def manager_complaints(request):

    profile = get_object_or_404(UserProfile, user=request.user)

    if profile.role != "manager":
        return redirect("home")

    # FILTERING
    status_filter = request.GET.get("status")

    complaints = Complaint.objects.all().order_by("-created_at")

    if status_filter:
        complaints = complaints.filter(status=status_filter)

    # STATS (for dashboard insight)
    total = Complaint.objects.count()
    open_count = Complaint.objects.filter(status="open").count()
    progress_count = Complaint.objects.filter(status="in_progress").count()
    resolved_count = Complaint.objects.filter(status="resolved").count()

    return render(request, "System/complaint.html", {
        "complaints": complaints,
        "total": total,
        "open_count": open_count,
        "progress_count": progress_count,
        "resolved_count": resolved_count,
        "status_filter": status_filter,
    })

# ================================
# UPDATE COMPLAINT STATUS
# ================================
@login_required
def update_complaint_status(request, pk):

    profile = get_object_or_404(UserProfile, user=request.user)

    if profile.role != "manager":
        return redirect("home")

    complaint = get_object_or_404(Complaint, pk=pk)

    if request.method == "POST":

        new_status = request.POST.get("status")

        if new_status in ["open", "in_progress", "resolved", "closed"]:
            complaint.status = new_status
            complaint.save()

            messages.success(request, "Ticket updated successfully.")

    return redirect("manager_complaints")
# ==================================================
# 6. MANAGER: ALL INCIDENT REPORTS
# ==================================================
@login_required
def manager_cases(request):

    cases = ReportCases.objects.select_related(
        "vehicle",
        "sacco",
        "reporter"
    ).order_by("-created_at")

    # OPTIONAL FILTER (status)
    status = request.GET.get("status")

    if status:
        cases = cases.filter(status=status)

    return render(request, "System/manager_cases.html", {
        "cases": cases,
        "status": status
    })

@login_required
@require_POST
def update_case_status(request):

    if not request.user.is_staff:
        return JsonResponse({"error": "Not allowed"}, status=403)

    case_id = request.POST.get("case_id")
    status = request.POST.get("status")

    valid_statuses = ["open", "investigating", "resolved", "closed"]

    if status not in valid_statuses:
        return JsonResponse({"error": "Invalid status"}, status=400)

    case = get_object_or_404(ReportCases, id=case_id)
    case.status = status
    case.save()

    return JsonResponse({
        "success": True,
        "status": status
    })

@login_required
def individuals_list(request):

    query = request.GET.get("q", "").strip()

    individuals = IndividualMember.objects.all()

    if query:
        individuals = individuals.filter(
            Q(membership_number__icontains=query) |
            Q(first_name__icontains=query) |
            Q(second_name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone_number__icontains=query)
        )

    individuals = individuals.order_by("-created_at")
    suggestions = IndividualMember.objects.all()[:100]
    return render(
        request,
        "System/individual_list.html",
        {
            "individuals": individuals,
            "query": query,
            "suggestions": suggestions,
        }
    )

@login_required
def member_autocomplete(request):

    term = request.GET.get("term", "")

    suggestions = []

    if term:

        members = IndividualMember.objects.filter(
            Q(membership_number__icontains=term) |
            Q(first_name__icontains=term) |
            Q(second_name__icontains=term)
        )[:10]

        for member in members:

            suggestions.append({
                "name": f"{member.first_name} {member.second_name}",
                "membership": member.membership_number,
            })

    return JsonResponse(suggestions, safe=False)

@login_required
def sacco_list(request):

    query = request.GET.get("q", "").strip()

    saccos = SaccoMember.objects.all()

    if query:
        saccos = saccos.filter(
            Q(membership_number__icontains=query) |
            Q(name__icontains=query) |
            Q(phone_number__icontains=query)
        )

    return render(request, "System/sacco_list.html", {
        "saccos": saccos,
        "query": query
    })

@login_required
def sacco_list(request):

    query = request.GET.get("q", "").strip()

    saccos = SaccoMember.objects.all()

    if query:
        saccos = saccos.filter(
            Q(membership_number__icontains=query) |
            Q(name__icontains=query) |
            Q(phone_number__icontains=query)
        )

    return render(request, "System/sacco_list.html", {
        "saccos": saccos,
        "query": query
    })

@login_required
def sacco_autocomplete(request):

    term = request.GET.get("term", "").strip()

    results = SaccoMember.objects.filter(
        Q(membership_number__icontains=term) |
        Q(name__icontains=term)
    )[:10]

    data = [
        {
            "name": s.name,
            "membership": s.membership_number
        }
        for s in results
    ]

    return JsonResponse(data, safe=False)

@login_required
def partners_list(request):

    query = request.GET.get("q", "").strip()

    partners = PartnerMember.objects.all()

    if query:
        partners = partners.filter(
            Q(membership_number__icontains=query) |
            Q(name__icontains=query) |
            Q(phone_number__icontains=query)
        )

    return render(request, "System/partner_list.html", {
        "partners": partners,
        "query": query
    })

@login_required
def partner_autocomplete(request):

    term = request.GET.get("term", "").strip()

    results = PartnerMember.objects.filter(
        Q(membership_number__icontains=term) |
        Q(name__icontains=term)
    )[:10]

    data = [
        {
            "name": p.name,
            "membership": p.membership_number
        }
        for p in results
    ]

    return JsonResponse(data, safe=False)

@login_required
def manager_report(request):

    profile = get_object_or_404(UserProfile, user=request.user)

    if profile.role != "manager":
        return redirect("home")

    current_year = timezone.now().year

    # =====================================================
    # MEMBERSHIP
    # =====================================================

    individual_count = IndividualMember.objects.count()
    sacco_count = SaccoMember.objects.count()
    partner_count = PartnerMember.objects.count()

    total_members = (
        individual_count +
        sacco_count +
        partner_count
    )

    active_individuals = IndividualMember.objects.filter(
        payment_status="paid"
    ).count()

    active_saccos = SaccoMember.objects.filter(
        payment_status="paid"
    ).count()

    active_partners = PartnerMember.objects.filter(
        payment_status="paid"
    ).count()

    active_members = (
        active_individuals +
        active_saccos +
        active_partners
    )

    payment_rate = round(
        (active_members / total_members) * 100, 1
    ) if total_members else 0

    # =====================================================
    # REVENUE
    # =====================================================

    individual_revenue = IndividualMember.objects.filter(
        payment_status="paid"
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0

    sacco_revenue = Vehicle.objects.filter(
        payment_status="paid"
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0

    partner_revenue = PartnerDonation.objects.filter(
        status="paid"
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0

    total_revenue = (
        individual_revenue +
        sacco_revenue +
        partner_revenue
    )

    # =====================================================
    # COMPLAINTS
    # =====================================================

    complaint_open = Complaint.objects.filter(
        status="open"
    ).count()

    complaint_progress = Complaint.objects.filter(
        status="in_progress"
    ).count()

    complaint_resolved = Complaint.objects.filter(
        status="resolved"
    ).count()

    complaint_closed = Complaint.objects.filter(
        status="closed"
    ).count()

    total_complaints = Complaint.objects.count()

    recent_complaints = Complaint.objects.order_by(
        "-created_at"
    )[:10]

    # =====================================================
    # INCIDENT CASES
    # =====================================================

    open_cases = ReportCases.objects.filter(
        status="open"
    ).count()

    investigating_cases = ReportCases.objects.filter(
        status="investigating"
    ).count()

    resolved_cases = ReportCases.objects.filter(
        status="resolved"
    ).count()

    closed_cases = ReportCases.objects.filter(
        status="closed"
    ).count()

    total_cases = ReportCases.objects.count()

    recent_cases = ReportCases.objects.order_by(
        "-created_at"
    )[:10]

    # =====================================================
    # VEHICLE ANALYTICS
    # =====================================================

    total_vehicles = Vehicle.objects.count()

    town_service = Vehicle.objects.filter(
        vehicle_type="town_service"
    ).count()

    long_distance = Vehicle.objects.filter(
        vehicle_type="long_distance"
    ).count()

    # =====================================================
    # MONTHLY REVENUE TREND
    # =====================================================

    months = []
    revenue_data = []

    for month in range(1, 13):

        individual = IndividualMember.objects.filter(
            payment_status="paid",
            created_at__year=current_year,
            created_at__month=month
        ).aggregate(
            total=Sum("amount")
        )["total"] or 0

        sacco = Vehicle.objects.filter(
            payment_status="paid",
            created_at__year=current_year,
            created_at__month=month
        ).aggregate(
            total=Sum("amount")
        )["total"] or 0

        partner = PartnerDonation.objects.filter(
            status="paid",
            created_at__year=current_year,
            created_at__month=month
        ).aggregate(
            total=Sum("amount")
        )["total"] or 0

        months.append(calendar.month_abbr[month])

        revenue_data.append(
            float(individual + sacco + partner)
        )

    # =====================================================
    # AI INSIGHTS
    # =====================================================

    insights = []

    if payment_rate < 50:
        insights.append(
            "Low payment compliance detected."
        )

    if complaint_open > complaint_resolved:
        insights.append(
            "Open complaints exceed resolved complaints."
        )

    if total_revenue > 500000:
        insights.append(
            "Revenue performance is strong."
        )

    if total_cases > 20:
        insights.append(
            "High number of reported transport incidents."
        )

    context = {

        "total_members": total_members,
        "active_members": active_members,
        "payment_rate": payment_rate,

        "individual_count": individual_count,
        "sacco_count": sacco_count,
        "partner_count": partner_count,

        "total_revenue": total_revenue,
        "individual_revenue": individual_revenue,
        "sacco_revenue": sacco_revenue,
        "partner_revenue": partner_revenue,

        "total_complaints": total_complaints,
        "complaint_open": complaint_open,
        "complaint_progress": complaint_progress,
        "complaint_resolved": complaint_resolved,
        "complaint_closed": complaint_closed,

        "total_cases": total_cases,
        "open_cases": open_cases,
        "investigating_cases": investigating_cases,
        "resolved_cases": resolved_cases,
        "closed_cases": closed_cases,

        "total_vehicles": total_vehicles,
        "town_service": town_service,
        "long_distance": long_distance,

        "months": json.dumps(months),
        "revenue_data": json.dumps(revenue_data),

        "recent_complaints": recent_complaints,
        "recent_cases": recent_cases,

        "insights": insights,
    }

    return render(
        request,
        "System/manager_report.html",
        context
    )