from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, Http404, JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from django.views.decorators.http import require_POST
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
import json
from django.conf import settings
import os
import calendar
import logging
from datetime import datetime, timedelta
from .models import *
from .forms import *
from .utils import send_otp_email
from django.core.mail import send_mail
# ==========================================
# EMAIL UTILITIES
# ==========================================
# Central dispatcher — every outgoing email goes through here.
# A broken mail server never crashes a user request.

from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
import logging as _logging
_email_logger = _logging.getLogger("cocowa.email")


def _send_email(subject, to_email, html_body):
    """Send one HTML+text email. Silently logs failures."""
    if not to_email:
        return
    from django.conf import settings as _s
    from_email = getattr(_s, "DEFAULT_FROM_EMAIL", "noreply@cocowa.org")
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=strip_tags(html_body),
            from_email=from_email,
            to=[to_email],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
    except Exception as exc:
        _email_logger.error("Email failed → %s | %s: %s", to_email, subject, exc)


# ── helpers ──────────────────────────────────────────────────
def _base(title, body_html, colour="#1e3a8a"):
    """Wrap content in a consistent branded shell."""
    return f"""
<!DOCTYPE html><html><body style="margin:0;padding:0;background:#f8fafc;font-family:sans-serif;">
<div style="max-width:560px;margin:32px auto;background:#fff;border-radius:12px;
            border-top:4px solid {colour};box-shadow:0 2px 12px rgba(0,0,0,.06);overflow:hidden;">
  <div style="background:{colour};padding:20px 28px;">
    <span style="color:#fff;font-size:18px;font-weight:800;letter-spacing:-.3px;">COCOWA</span>
  </div>
  <div style="padding:28px 32px;">
    <h2 style="margin:0 0 12px;color:#0f172a;font-size:20px;">{title}</h2>
    {body_html}
  </div>
  <div style="background:#f1f5f9;padding:14px 32px;text-align:center;">
    <p style="margin:0;color:#94a3b8;font-size:11px;">
      © COCOWA · This is an automated message, please do not reply directly.
    </p>
  </div>
</div>
</body></html>"""


# ──────────────────────────────────────────────────────────────
# 1. WELCOME  (after account creation + OTP)
# ──────────────────────────────────────────────────────────────
def email_welcome(user, role):
    labels = {"individual": "Individual Member", "sacco": "SACCO Member", "partner": "Partner / Donor"}
    body = f"""
<p style="color:#334155;">Hi <strong>{user.username}</strong>,</p>
<p style="color:#334155;">
  Your account has been created as a <strong>{labels.get(role, role)}</strong>.
  An OTP has been sent to this address — enter it to activate your account.
</p>
<p style="color:#94a3b8;font-size:13px;">Didn't create this account? You can safely ignore this email.</p>"""
    _send_email(
        "Welcome to COCOWA — verify your email",
        user.email,
        _base("Welcome aboard 🎉", body),
    )


# ──────────────────────────────────────────────────────────────
# 2. PAYMENT SUBMITTED (member → system, awaiting review)
# ──────────────────────────────────────────────────────────────
def email_payment_submitted(user, amount, transaction_code):
    body = f"""
<p style="color:#334155;">Hi <strong>{user.get_full_name() or user.username}</strong>,</p>
<p style="color:#334155;">
  We have received your payment submission of <strong>KES {float(amount):,.2f}</strong>.
</p>
<table style="width:100%;border-collapse:collapse;font-size:13px;margin:16px 0;">
  <tr><td style="padding:8px 0;color:#64748b;width:45%">Transaction Code</td>
      <td style="padding:8px 0;font-weight:700;color:#0f172a;">{transaction_code or '—'}</td></tr>
  <tr><td style="padding:8px 0;color:#64748b;">Amount</td>
      <td style="padding:8px 0;font-weight:700;color:#0f172a;">KES {float(amount):,.2f}</td></tr>
  <tr><td style="padding:8px 0;color:#64748b;">Status</td>
      <td style="padding:8px 0;"><span style="background:#fffbeb;color:#f59e0b;padding:3px 10px;
          border-radius:20px;font-size:12px;font-weight:700;">Pending Review</span></td></tr>
</table>
<p style="color:#64748b;font-size:13px;">
  Our team will verify and approve your payment within 24 hours. You will receive
  a confirmation email once approved.
</p>"""
    _send_email(
        "Payment Submitted — Awaiting Approval",
        user.email,
        _base("Payment Received ✅", body, "#f59e0b"),
    )


# ──────────────────────────────────────────────────────────────
# 3. PAYMENT APPROVED
# ──────────────────────────────────────────────────────────────
def email_payment_approved(user, membership_number, amount):
    body = f"""
<p style="color:#334155;">Hi <strong>{user.get_full_name() or user.username}</strong>,</p>
<p style="color:#334155;">
  Great news — your payment of <strong>KES {float(amount):,.2f}</strong> has been
  <strong>approved</strong>. Your membership is now active.
</p>
<div style="background:#ecfdf5;border-radius:10px;padding:18px 24px;margin:16px 0;text-align:center;">
  <p style="margin:0 0 4px;color:#065f46;font-size:11px;font-weight:700;
             text-transform:uppercase;letter-spacing:.4px;">Your Membership Number</p>
  <p style="margin:0;font-size:26px;font-weight:900;color:#065f46;letter-spacing:3px;">
    {membership_number or "Pending Assignment"}
  </p>
</div>
<p style="color:#64748b;font-size:13px;">
  Log in to your dashboard to download your membership card and access all benefits.
</p>"""
    _send_email(
        "Payment Approved — Your Membership is Active 🎉",
        user.email,
        _base("Payment Approved ✅", body, "#10b981"),
    )


# ──────────────────────────────────────────────────────────────
# 4. PAYMENT REJECTED
# ──────────────────────────────────────────────────────────────
def email_payment_rejected(user, amount, reason=""):
    reason_row = f"""
  <tr><td style="padding:8px 0;color:#64748b;">Reason</td>
      <td style="padding:8px 0;color:#0f172a;">{reason}</td></tr>""" if reason else ""
    body = f"""
<p style="color:#334155;">Hi <strong>{user.get_full_name() or user.username}</strong>,</p>
<p style="color:#334155;">
  Unfortunately your payment of <strong>KES {float(amount):,.2f}</strong> could
  not be approved.
</p>
<table style="width:100%;border-collapse:collapse;font-size:13px;margin:16px 0;">
  <tr><td style="padding:8px 0;color:#64748b;width:45%">Amount</td>
      <td style="padding:8px 0;font-weight:700;color:#0f172a;">KES {float(amount):,.2f}</td></tr>
  <tr><td style="padding:8px 0;color:#64748b;">Status</td>
      <td style="padding:8px 0;"><span style="background:#fef2f2;color:#ef4444;padding:3px 10px;
          border-radius:20px;font-size:12px;font-weight:700;">Rejected</span></td></tr>
  {reason_row}
</table>
<p style="color:#334155;font-size:13px;">
  Please log in, check your transaction code, and resubmit. Contact support if you
  believe this is an error.
</p>"""
    _send_email(
        "Action Required — Payment Not Approved",
        user.email,
        _base("Payment Not Approved ❌", body, "#ef4444"),
    )


# ──────────────────────────────────────────────────────────────
# 5. COMPLAINT RAISED  (user confirmation)
# ──────────────────────────────────────────────────────────────
def email_complaint_raised(user, complaint):
    body = f"""
<p style="color:#334155;">Hi <strong>{user.get_full_name() or user.username}</strong>,</p>
<p style="color:#334155;">
  Your complaint has been logged. Our support team will respond within 2 business days.
</p>
<table style="width:100%;border-collapse:collapse;font-size:13px;margin:16px 0;">
  <tr><td style="padding:8px 0;color:#64748b;width:45%">Ticket Number</td>
      <td style="padding:8px 0;font-weight:700;color:#0f172a;">#{complaint.ticket_number}</td></tr>
  <tr><td style="padding:8px 0;color:#64748b;">Category</td>
      <td style="padding:8px 0;color:#0f172a;">{complaint.get_category_display()}</td></tr>
  <tr><td style="padding:8px 0;color:#64748b;">Subject</td>
      <td style="padding:8px 0;color:#0f172a;">{complaint.subject}</td></tr>
  <tr><td style="padding:8px 0;color:#64748b;">Status</td>
      <td style="padding:8px 0;"><span style="background:#fef2f2;color:#ef4444;padding:3px 10px;
          border-radius:20px;font-size:12px;font-weight:700;">Open</span></td></tr>
</table>
<p style="color:#64748b;font-size:13px;">
  Keep your ticket number handy. You can track progress from your dashboard.
</p>"""
    _send_email(
        f"Complaint Received — Ticket #{complaint.ticket_number}",
        user.email,
        _base("Complaint Received 📋", body),
    )


# ──────────────────────────────────────────────────────────────
# 6. COMPLAINT STATUS UPDATED
# ──────────────────────────────────────────────────────────────
def email_complaint_status_updated(user, complaint, new_status):
    labels = {"open": "Open", "in_progress": "In Progress", "resolved": "Resolved", "closed": "Closed"}
    colours = {"open": "#ef4444", "in_progress": "#f59e0b", "resolved": "#10b981", "closed": "#475569"}
    label  = labels.get(new_status, new_status)
    colour = colours.get(new_status, "#1e3a8a")
    body = f"""
<p style="color:#334155;">Hi <strong>{user.get_full_name() or user.username}</strong>,</p>
<p style="color:#334155;">
  Your complaint <strong>#{complaint.ticket_number}</strong> has been updated.
</p>
<div style="background:#f8fafc;border-radius:10px;padding:16px 20px;margin:16px 0;">
  <p style="margin:0 0 6px;color:#64748b;font-size:11px;font-weight:700;
             text-transform:uppercase;letter-spacing:.4px;">New Status</p>
  <span style="background:{colour}18;color:{colour};padding:4px 14px;
               border-radius:20px;font-size:13px;font-weight:800;">{label}</span>
</div>
<p style="color:#64748b;font-size:13px;">
  Log in to your dashboard to view the full ticket history.
</p>"""
    _send_email(
        f"Ticket #{complaint.ticket_number} Updated — {label}",
        user.email,
        _base("Complaint Status Update 🔄", body, colour),
    )

def email_case_response(user, case, response):

    send_mail(
        subject=f"Response to Case #{case.id}",
        message=f"""
Dear {user.username},

Your reported case has received a response.

Case Reference: {case.id}

Response:
{response}

Regards,
COCOWA Management
""",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
# ──────────────────────────────────────────────────────────────
# 7. INCIDENT REPORT SUBMITTED  (reporter confirmation)
# ──────────────────────────────────────────────────────────────
def email_incident_submitted(user, case):
    body = f"""
<p style="color:#334155;">Hi <strong>{user.get_full_name() or user.username}</strong>,</p>
<p style="color:#334155;">
  Thank you for reporting this incident. Our safety team has been notified and will
  investigate promptly.
</p>
<table style="width:100%;border-collapse:collapse;font-size:13px;margin:16px 0;">
  <tr><td style="padding:8px 0;color:#64748b;width:45%">Vehicle</td>
      <td style="padding:8px 0;font-weight:700;color:#0f172a;">{case.number_plate or '—'}</td></tr>
  <tr><td style="padding:8px 0;color:#64748b;">Incident Type</td>
      <td style="padding:8px 0;color:#0f172a;">{case.get_incident_type_display()}</td></tr>
  <tr><td style="padding:8px 0;color:#64748b;">Journey Date</td>
      <td style="padding:8px 0;color:#0f172a;">{case.journey_date}</td></tr>
  <tr><td style="padding:8px 0;color:#64748b;">Status</td>
      <td style="padding:8px 0;"><span style="background:#fef2f2;color:#ef4444;padding:3px 10px;
          border-radius:20px;font-size:12px;font-weight:700;">Open</span></td></tr>
</table>
<p style="color:#64748b;font-size:13px;">
  You will receive a follow-up notification when the investigation progresses.
</p>"""
    _send_email(
        "Incident Report Received — We're On It 🚨",
        user.email,
        _base("Incident Report Submitted", body, "#f59e0b"),
    )


# ──────────────────────────────────────────────────────────────
# 8. INCIDENT STATUS UPDATED  (reporter)
# ──────────────────────────────────────────────────────────────
def email_incident_status_updated(user, case, new_status):
    labels  = {"open": "Open", "investigating": "Investigating", "resolved": "Resolved", "closed": "Closed"}
    colours = {"open": "#ef4444", "investigating": "#f59e0b", "resolved": "#10b981", "closed": "#475569"}
    label  = labels.get(new_status, new_status)
    colour = colours.get(new_status, "#1e3a8a")
    body = f"""
<p style="color:#334155;">Hi <strong>{user.get_full_name() or user.username}</strong>,</p>
<p style="color:#334155;">
  The incident you reported for vehicle <strong>{case.number_plate or '—'}</strong> has been updated.
</p>
<div style="background:#f8fafc;border-radius:10px;padding:16px 20px;margin:16px 0;">
  <p style="margin:0 0 6px;color:#64748b;font-size:11px;font-weight:700;
             text-transform:uppercase;letter-spacing:.4px;">New Status</p>
  <span style="background:{colour}18;color:{colour};padding:4px 14px;
               border-radius:20px;font-size:13px;font-weight:800;">{label}</span>
</div>
<p style="color:#64748b;font-size:13px;">Log in to your dashboard for full details.</p>"""
    _send_email(
        f"Incident Update — {label} ({case.number_plate or 'Unknown'})",
        user.email,
        _base("Incident Status Update 🔄", body, colour),
    )


# ──────────────────────────────────────────────────────────────
# 9. DONATION SUBMITTED  (partner → system)
# ──────────────────────────────────────────────────────────────
def email_donation_submitted(user, donation):
    body = f"""
<p style="color:#334155;">Hi <strong>{user.get_full_name() or user.username}</strong>,</p>
<p style="color:#334155;">
  Your donation of <strong>KES {float(donation.amount):,.2f}</strong> has been received
  and is pending approval.
</p>
<table style="width:100%;border-collapse:collapse;font-size:13px;margin:16px 0;">
  <tr><td style="padding:8px 0;color:#64748b;width:45%">Amount</td>
      <td style="padding:8px 0;font-weight:700;color:#0f172a;">KES {float(donation.amount):,.2f}</td></tr>
  <tr><td style="padding:8px 0;color:#64748b;">Status</td>
      <td style="padding:8px 0;"><span style="background:#fffbeb;color:#f59e0b;padding:3px 10px;
          border-radius:20px;font-size:12px;font-weight:700;">Pending</span></td></tr>
</table>
<p style="color:#64748b;font-size:13px;">
  We will notify you once your donation is approved. Thank you for your support!
</p>"""
    _send_email(
        "Donation Received — Pending Approval",
        user.email,
        _base("Donation Submitted 🤝", body, "#8b5cf6"),
    )


# ──────────────────────────────────────────────────────────────
# 10. DONATION APPROVED  (partner)
# ──────────────────────────────────────────────────────────────
def email_donation_approved(user, donation, membership_number=None):
    membership_row = f"""
  <tr><td style="padding:8px 0;color:#64748b;">Membership No.</td>
      <td style="padding:8px 0;font-weight:700;color:#065f46;">{membership_number}</td></tr>""" if membership_number else ""
    body = f"""
<p style="color:#334155;">Hi <strong>{user.get_full_name() or user.username}</strong>,</p>
<p style="color:#334155;">
  Your donation of <strong>KES {float(donation.amount):,.2f}</strong> has been
  <strong>approved</strong>. Thank you for your generous contribution!
</p>
<table style="width:100%;border-collapse:collapse;font-size:13px;margin:16px 0;">
  <tr><td style="padding:8px 0;color:#64748b;width:45%">Amount</td>
      <td style="padding:8px 0;font-weight:700;color:#0f172a;">KES {float(donation.amount):,.2f}</td></tr>
  <tr><td style="padding:8px 0;color:#64748b;">Status</td>
      <td style="padding:8px 0;"><span style="background:#ecfdf5;color:#10b981;padding:3px 10px;
          border-radius:20px;font-size:12px;font-weight:700;">Approved</span></td></tr>
  {membership_row}
</table>
<p style="color:#64748b;font-size:13px;">
  Log in to your dashboard to view your full donation history and membership card.
</p>"""
    _send_email(
        "Donation Approved — Thank You! 🌟",
        user.email,
        _base("Donation Approved ✅", body, "#10b981"),
    )


# ──────────────────────────────────────────────────────────────
# 11. PROFILE COMPLETED
# ──────────────────────────────────────────────────────────────
def email_profile_completed(user, role):
    next_step = {
        "individual": "proceed to payment to activate your membership",
        "sacco":      "proceed to payment to register your SACCO and fleet",
        "partner":    "submit your first donation to activate your partner account",
    }.get(role, "log in to your dashboard")
    body = f"""
<p style="color:#334155;">Hi <strong>{user.get_full_name() or user.username}</strong>,</p>
<p style="color:#334155;">
  Your profile has been completed successfully. You can now {next_step}.
</p>
<p style="color:#64748b;font-size:13px;">
  If you need any help, raise a support ticket from your dashboard.
</p>"""
    _send_email(
        "Profile Completed — Next Steps",
        user.email,
        _base("Profile Complete 🎯", body, "#8b5cf6"),
    )


# ──────────────────────────────────────────────────────────────
# 12. PASSWORD CHANGED  (security alert)
# ──────────────────────────────────────────────────────────────
def email_password_changed(user):
    from django.utils import timezone as _tz
    body = f"""
<p style="color:#334155;">Hi <strong>{user.get_full_name() or user.username}</strong>,</p>
<p style="color:#334155;">
  Your COCOWA account password was changed on
  <strong>{_tz.now().strftime('%d %b %Y at %H:%M UTC')}</strong>.
</p>
<p style="color:#ef4444;font-size:13px;font-weight:600;">
  If you did not make this change, please contact support immediately and secure your account.
</p>"""
    _send_email(
        "Security Alert — Password Changed",
        user.email,
        _base("Password Changed 🔐", body, "#ef4444"),
    )


# ──────────────────────────────────────────────────────────────
# 13. MANAGER: WEEKLY DIGEST
# (call from a Celery beat task / management command every Monday)
# ──────────────────────────────────────────────────────────────
def email_manager_digest(manager_user, ctx):
    """
    ctx keys: total_members, active_members, total_revenue,
              payment_rate, complaint_open, open_cases
    """
    def stat(label, value, colour="#1e3a8a"):
        return f"""
    <div style="background:#fff;border-radius:10px;padding:16px 18px;border:1px solid #f1f5f9;">
      <p style="margin:0 0 4px;font-size:10px;color:#64748b;text-transform:uppercase;
                font-weight:700;letter-spacing:.4px;">{label}</p>
      <p style="margin:0;font-size:26px;font-weight:900;color:{colour};">{value}</p>
    </div>"""
    body = f"""
<p style="color:#334155;">Hi <strong>{manager_user.get_full_name() or manager_user.username}</strong>,</p>
<p style="color:#64748b;font-size:13px;margin-bottom:18px;">Here is your weekly system snapshot.</p>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
  {stat("Total Members",    ctx.get("total_members",  0))}
  {stat("Active Members",   ctx.get("active_members", 0), "#10b981")}
  {stat("Revenue (KES)",    f"{ctx.get('total_revenue', 0):,.0f}")}
  {stat("Compliance",       f"{ctx.get('payment_rate', 0)}%", "#f59e0b")}
  {stat("Open Complaints",  ctx.get("complaint_open", 0), "#ef4444")}
  {stat("Open Cases",       ctx.get("open_cases",     0), "#f59e0b")}
</div>
<p style="color:#94a3b8;font-size:12px;margin-top:20px;text-align:center;">
  Log in to your dashboard for the full analytics report.
</p>"""
    _send_email(
        "Weekly Manager Digest — System Summary",
        manager_user.email,
        _base("Weekly Digest 📊", body),
    )

# ==========================================
# REGISTER
# ==========================================
def join_membership(request):

    if request.method == "POST":

        email    = request.POST.get("email", "").strip()
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password")
        confirm  = request.POST.get("confirm_password")
        role     = request.POST.get("member_type")
        phone    = request.POST.get("phone_number")

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
        # BASIC VALIDATION
        # =========================
        if not username:
            messages.error(request, "Username is required.")
            return redirect("join")

        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return redirect("join")

        # =========================
        # CHECK USERNAME TAKEN
        # =========================
        if User.objects.filter(username=username).exists():
            messages.error(request, "That username is already taken.")
            return redirect("join")

        # =========================
        # CHECK EMAIL TAKEN
        # =========================
        existing_user = User.objects.filter(email=email).first()

        if existing_user:

            profile_exists = UserProfile.objects.filter(
                user=existing_user
            ).exists()

            # Existing valid account
            if profile_exists:
                messages.error(
                    request,
                    "An account with that email already exists."
                )
                return redirect("join")

            # Orphaned account
            existing_user.delete()

        # =========================
        # CREATE USER ACCOUNT
        # =========================
        user = User.objects.create_user(
            username=username,
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

        send_otp_email(user)
        email_welcome(user, role)

        request.session["pending_verification_user"] = user.id

        messages.success(
           request,
            "Account created successfully. Check your email for OTP."
        )

        return redirect("verify_email")
    return render(
        request,
        "System/join.html"
    )

def verify_email(request):

    user_id = request.session.get(
        "pending_verification_user"
    )

    if not user_id:
        return redirect("login")

    user = User.objects.get(id=user_id)

    try:
        otp_record = EmailOTP.objects.get(user=user)

    except EmailOTP.DoesNotExist:

        messages.error(
            request,
            "OTP not found."
        )

        return redirect("login")

    if request.method == "POST":

        entered_otp = request.POST.get("otp")

        if not otp_record.is_valid():

            messages.error(
                request,
                "OTP expired."
            )

            return redirect("resend_otp")

        if entered_otp == otp_record.otp_code:

            otp_record.is_verified = True
            otp_record.save()

            profile = UserProfile.objects.get(
                user=user
            )

            profile.email_verified = True
            profile.save()

            del request.session[
                "pending_verification_user"
            ]

            messages.success(
                request,
                "Email verified successfully."
            )

            # Google users have no role yet — log them in and
            # send them to role selection.
            is_google_user = user.socialaccount_set.filter(
                provider="google"
            ).exists()

            if is_google_user and not profile.role:
                login(
                    request,
                    user,
                    backend="django.contrib.auth.backends.ModelBackend"
                )
                return redirect("select_role")

            return redirect("login")

        messages.error(
            request,
            "Invalid OTP."
        )

    return render(
        request,
        "System/verify_email.html"
    )

def resend_otp(request):

    user_id = request.session.get(
        "pending_verification_user"
    )

    if not user_id:
        return redirect("login")

    user = User.objects.get(id=user_id)

    send_otp_email(user)

    messages.success(
        request,
        "New OTP sent successfully."
    )

    return redirect("verify_email")
# ==========================================
# LOGIN
# ==========================================
def custom_login(request):

    if request.method == "POST":

        login_input = request.POST.get("login_input", "").strip()
        password    = request.POST.get("password")

        # Support login by username OR email
        # Django's authenticate() matches on username, so if the
        # user typed an email we need to resolve it to a username first.
        if "@" in login_input:
            try:
                resolved_user = User.objects.get(email=login_input)
                login_username = resolved_user.username
            except User.DoesNotExist:
                login_username = login_input   # will fail auth cleanly
        else:
            login_username = login_input

        user = authenticate(request, username=login_username, password=password)

        if user:

            profile = UserProfile.objects.get(
                user=user
            )

            if not profile.email_verified:

                request.session[
                    "pending_verification_user"
                ] = user.id

                messages.error(
                request,
                    "Please verify your email first."
                )

                return redirect("verify_email")

            login(request, user)

            return redirect("dashboard_redirect")

        messages.error(request, "Invalid login credentials")

    return render(request, "System/login.html")


def google_redirect(request):

    # IMPORTANT: safety check
    if not request.user.is_authenticated:
        return redirect("account_login")

    user = request.user

    # GET OR CREATE PROFILE
    profile, _ = UserProfile.objects.get_or_create(user=user)

    # ======================================
    # 1. EMAIL VERIFICATION CHECK
    # ======================================
    if not profile.email_verified:

        # create OTP if not exists
        otp_obj, _ = EmailOTP.objects.get_or_create(user=user)

        send_otp_email(user)

        # Store user id in session BEFORE logout, and force-save it
        # so it survives the logout session flush.
        pending_user_id = user.id
        logout(request)  # clears the allauth session (user is no longer logged in)

        # Re-set the key on the now-fresh anonymous session
        request.session["pending_verification_user"] = pending_user_id
        request.session.modified = True

        messages.warning(
            request,
            "Please verify your email before continuing."
        )

        return redirect("verify_email")

    # ======================================
    # 2. ROLE SELECTION CHECK
    # ======================================
    if not profile.role:
        request.session["pending_verification_user"] = user.id
        return redirect("select_role")

    # ======================================
    # 3. PROFILE COMPLETION CHECK
    # ======================================
    if not profile.profile_completed:

        request.session["pending_verification_user"] = user.id

        if profile.role == "individual":
            return redirect("complete_individual_profile")

        elif profile.role == "sacco":
            return redirect("complete_sacco_profile")

        elif profile.role == "partner":
            return redirect("complete_partner_profile")

    # ======================================
    # 4. FINAL DASHBOARD
    # ======================================
    return redirect("dashboard_redirect")

@login_required
def select_role(request):

    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":

        role = request.POST.get("role")

        print("ROLE SELECTED:", role)  # DEBUG (check terminal)

        if role not in ["individual", "sacco", "partner"]:
            return render(request, "System/select_role.html", {
                "error": "Invalid role selected"
            })

        profile.role = role
        profile.save()

        print("ROLE SAVED SUCCESSFULLY")

        return redirect("google_redirect")

    return render(request, "System/select_role.html")
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

@login_required
def vehicle_list(request):

    member = get_object_or_404(SaccoMember, user=request.user)

    vehicles = Vehicle.objects.filter(sacco=member).order_by("-created_at")

    return render(request, "System/vehicle_list.html", {
        "vehicles": vehicles,
        "member": member
    })
@login_required
def sacco_report(request):
    """
    Comprehensive SACCO analytics dashboard with vehicle, revenue,
    incident, and complaint metrics.
    """
    profile = get_object_or_404(UserProfile, user=request.user)

    if profile.role != "sacco":
        return redirect("home")

    member = get_object_or_404(SaccoMember, user=request.user)
    current_year = timezone.now().year

    # ─────────────────────────────────────────────────────────
    # VEHICLES & FLEET
    # ─────────────────────────────────────────────────────────
    vehicles = Vehicle.objects.filter(sacco=member)
    total_vehicles = vehicles.count()
    approved_vehicles = vehicles.filter(payment_status='paid').count()
    pending_vehicles = vehicles.filter(payment_status='pending').count()
    rejected_vehicles = vehicles.filter(payment_status='rejected').count()

    
    # ─────────────────────────────────────────────────────────
    # REVENUE
    # ─────────────────────────────────────────────────────────
    total_revenue = vehicles.filter(payment_status="paid").aggregate(
        total=Sum("amount")
    )["total"] or 0

    pending_payments = vehicles.filter(payment_status="pending").aggregate(
        total=Sum("amount")
    )["total"] or 0

    # ─────────────────────────────────────────────────────────
    # INCIDENTS (REPORT CASES)
    # ─────────────────────────────────────────────────────────
    incidents = ReportCases.objects.filter(sacco=member)
    total_incidents = incidents.count()
    open_incidents = incidents.filter(status="open").count()
    investigating = incidents.filter(status="investigating").count()
    resolved_incidents = incidents.filter(status="resolved").count()
    closed_incidents = incidents.filter(status="closed").count()

    recent_incidents = incidents.order_by("-created_at")[:10]

    # ─────────────────────────────────────────────────────────
    # MEMBERSHIP & COMPLIANCE
    # ─────────────────────────────────────────────────────────
    membership_days = (timezone.now().date() - member.created_at.date()).days
    payment_status = member.payment_status

    # ─────────────────────────────────────────────────────────
    # MONTHLY REVENUE TREND (12 months)
    # ─────────────────────────────────────────────────────────
    months = []
    revenue_data = []

    for month in range(1, 13):
        month_total = vehicles.filter(
            payment_status="paid",
            created_at__year=current_year,
            created_at__month=month,
        ).aggregate(total=Sum("amount"))["total"] or 0

        months.append(calendar.month_abbr[month])
        revenue_data.append(float(month_total))

    # ─────────────────────────────────────────────────────────
    # INCIDENT DISTRIBUTION BY TYPE
    # ─────────────────────────────────────────────────────────
    incident_breakdown = list(
        incidents.values('incident_type')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    incident_types = [item['incident_type'] for item in incident_breakdown]
    incident_counts = [item['count'] for item in incident_breakdown]

    # ─────────────────────────────────────────────────────────
    # VEHICLE TYPE BREAKDOWN
    # ─────────────────────────────────────────────────────────
    vehicle_status_data = [
        approved_vehicles,
        pending_vehicles,
        rejected_vehicles,
    ]

    # ─────────────────────────────────────────────────────────
    # SMART INSIGHTS
    # ─────────────────────────────────────────────────────────
    insights = []

    if payment_status != "paid":
        insights.append("⚠ SACCO membership payment pending — activate account to ensure compliance.")

    if open_incidents > 5:
        insights.append(f"🚨 High incident volume ({open_incidents} open). Fleet safety review recommended.")

    if total_vehicles == 0:
        insights.append("ℹ No vehicles registered yet. Register your fleet to begin tracking.")

    if total_revenue > 100_000:
        insights.append(f"✅ Strong revenue performance — KES {total_revenue:,.0f} collected this year.")

    if investigating > 0:
        insights.append(f"⏳ {investigating} incidents under investigation — monitor progress.")

    if not insights:
        insights.append("✅ Operations running smoothly. No critical alerts at this time.")

    # ─────────────────────────────────────────────────────────
    # CONTEXT
    # ─────────────────────────────────────────────────────────
    context = {
        # SACCO Info
        "sacco": member,
        "membership_days": membership_days,
        "payment_status": payment_status,

        # Fleet
        "approved_vehicles": approved_vehicles,
        "pending_vehicles": pending_vehicles,
        "rejected_vehicles": rejected_vehicles,
        "vehicle_status_data": json.dumps(vehicle_status_data),
        # Revenue
        "total_revenue": total_revenue,
        "pending_payments": pending_payments,

        # Incidents
        "total_incidents": total_incidents,
        "open_incidents": open_incidents,
        "investigating": investigating,
        "resolved_incidents": resolved_incidents,
        "closed_incidents": closed_incidents,
        "recent_incidents": recent_incidents,

        # Charts
        "months": json.dumps(months),
        "revenue_data": json.dumps(revenue_data),
        "incident_types": json.dumps(incident_types),
        "incident_counts": json.dumps(incident_counts),

        # Insights
        "insights": insights,

        # Meta
        "current_year": current_year,
    }

    return render(request, "System/sacco_report.html", context)
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
        donation = PartnerDonation.objects.create(
            partner=partner,
            amount=amount,
            status="pending"
        )
        email_donation_submitted(request.user, donation)

        messages.success(
            request,
            "Donation submitted successfully. Proceed to payment."
        )

        # redirect to payment page using partner id
        return redirect("payment_page",'partner', partner.id)

    return render(request, "System/partner_donation.html", {
        "partner": partner
    })
# ==========================================
# PARTNER REOORT PAGE
# ==========================================

@login_required
def partner_report(request):
    """
    Comprehensive partner analytics dashboard with donation tracking,
    financial metrics, and impact analytics.
    """
    partner = get_object_or_404(PartnerMember, user=request.user)
    donations = partner.donations.all().order_by("-created_at")
    current_year = timezone.now().year

    # ─────────────────────────────────────────────────────────
    # CORE DONATION METRICS
    # ─────────────────────────────────────────────────────────
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

    # ─────────────────────────────────────────────────────────
    # STATUS BREAKDOWN
    # ─────────────────────────────────────────────────────────
    paid_count = donations.filter(status="paid").count()
    pending_count = donations.filter(status="pending").count()
    rejected_count = donations.filter(status="rejected").count()
    total_count = donations.count()

    # ─────────────────────────────────────────────────────────
    # MEMBERSHIP & COMPLIANCE
    # ─────────────────────────────────────────────────────────
    membership_days = (timezone.now().date() - partner.created_at.date()).days
    membership_years = membership_days // 365
    payment_status = partner.payment_status

    # ─────────────────────────────────────────────────────────
    # MONTHLY ANALYTICS (12 months)
    # ─────────────────────────────────────────────────────────
    months = []
    monthly_data = []
    monthly_counts = []
    best_month = {"name": "", "value": 0}

    for month in range(1, 13):
        month_qs = donations.filter(
            status="paid",
            created_at__year=current_year,
            created_at__month=month,
        )

        month_total = month_qs.aggregate(total=Sum("amount"))["total"] or 0
        month_count = month_qs.count()

        months.append(calendar.month_abbr[month])
        monthly_data.append(float(month_total))
        monthly_counts.append(month_count)

        if month_total > best_month["value"]:
            best_month = {
                "name": calendar.month_name[month],
                "value": float(month_total)
            }

    # ─────────────────────────────────────────────────────────
    # IMPACT SCORE
    # ─────────────────────────────────────────────────────────
    impact_score = min(100, int(total_donations / 1000)) if total_donations > 0 else 0

    # ─────────────────────────────────────────────────────────
    # DONATION STATUS PIE DATA
    # ─────────────────────────────────────────────────────────
    status_data = [paid_count, pending_count, rejected_count]

    # ─────────────────────────────────────────────────────────
    # SMART INSIGHTS
    # ─────────────────────────────────────────────────────────
    insights = []

    if payment_status != "paid":
        insights.append("⚠ Partner account pending activation — complete verification to unlock full features.")

    if total_donations > 500_000:
        insights.append(f"🌟 Exceptional impact — KES {total_donations:,.0f} contributed. You're making a real difference!")

    if pending_count > 0:
        insights.append(f"⏳ {pending_count} donations awaiting approval. They'll be confirmed soon.")

    if rejected_count > 0:
        insights.append(f"⚠ {rejected_count} donations were declined. Check rejection details for next steps.")

    if donation_count == 0:
        insights.append("ℹ No confirmed donations yet. Start contributing to create impact.")

    if avg_donation > 50000:
        insights.append(f"💰 Strong average contribution — KES {avg_donation:,.0f} per donation.")

    if not insights:
        insights.append("✅ All systems operational. Your contributions are being processed smoothly.")

    # ─────────────────────────────────────────────────────────
    # RECENT TRANSACTIONS
    # ─────────────────────────────────────────────────────────
    recent_donations = donations[:10]

    # ─────────────────────────────────────────────────────────
    # CONTEXT
    # ─────────────────────────────────────────────────────────
    context = {
        # Partner Info
        "partner": partner,
        "membership_days": membership_days,
        "membership_years": membership_years,
        "payment_status": payment_status,

        # Donation Totals
        "total_donations": total_donations,
        "pending_donations": pending_donations,
        "rejected_donations": rejected_donations,
        "donation_count": donation_count,
        "avg_donation": avg_donation,
        "total_count": total_count,

        # Status Breakdown
        "paid_count": paid_count,
        "pending_count": pending_count,
        "rejected_count": rejected_count,

        # Impact
        "impact_score": impact_score,

        # Charts
        "months": json.dumps(months),
        "monthly_data": json.dumps(monthly_data),
        "monthly_counts": json.dumps(monthly_counts),
        "status_data": json.dumps(status_data),

        # Best Month
        "best_month": best_month,

        # Transactions
        "recent_donations": recent_donations,

        # Insights
        "insights": insights,

        # Meta
        "current_year": current_year,
    }

    return render(request, "System/partner_report.html", context)
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
# ============================================================
# VIEWS PATCH — paste these functions into views.py
#
# 1. Replace  complete_individual_profile()  with the version below.
# 2. Add the four new AJAX / management views below it.
# 3. Register the new URL patterns shown at the bottom of this file.
# ============================================================

# ── imports to add at the top of views.py (if not already present) ──
# from django.utils import timezone
# from .models import NextOfKin, Dependant, Beneficiary
# from .forms  import NextOfKinForm, DependantForm, BeneficiaryForm
# ─────────────────────────────────────────────────────────────────────


# ==========================================
# COMPLETE INDIVIDUAL PROFILE  (REPLACED)
# ==========================================
@login_required
def complete_individual_profile(request):

    member, _ = IndividualMember.objects.get_or_create(user=request.user)
    profile   = UserProfile.objects.get(user=request.user)

    edit_mode = request.GET.get("edit") == "1"

    if request.method == "POST":

        member.first_name  = request.POST.get("first_name")
        member.second_name = request.POST.get("second_name")
        member.phone_number = request.POST.get("phone_number")
        member.email       = request.POST.get("email")
        member.id_number   = request.POST.get("id_number")
        member.package     = request.POST.get("package")
        member.save()

        # ── COCOWA DATA CONSENT ────────────────────────────────
        consent_value = request.POST.get("cocowa_data_consent") == "on"
        if profile.cocowa_data_consent != consent_value:
            profile.cocowa_data_consent = consent_value
            profile.cocowa_consent_date = timezone.now()

        # ── MARK PROFILE COMPLETE (first time only) ────────────
        if not profile.profile_completed:
            profile.profile_completed = True
            profile.save()
            email_profile_completed(request.user, "individual")
            messages.success(request, "Profile completed successfully!")
            return redirect("payment_page", 'individual', member.id)

        profile.save()
        messages.success(request, "Profile updated successfully!")
        return redirect("complete_individual_profile")

    # ── Fetch existing Super Subscription data for view context ──
    next_of_kin   = NextOfKin.objects.filter(member=member).first()
    dependants    = Dependant.objects.filter(member=member, aged_out=False)
    beneficiaries = Beneficiary.objects.filter(member=member)

    from django.db.models import Sum as _Sum
    total_allocation = (
        beneficiaries.aggregate(total=_Sum("allocation_percentage"))["total"] or 0
    )

    context = {
        "member":             member,
        "profile":            profile,
        "is_complete":        profile.profile_completed,
        "edit_mode":          edit_mode,
        "next_of_kin":        next_of_kin,
        "dependants":         dependants,
        "beneficiaries":      beneficiaries,
        "total_allocation":   total_allocation,
        # Choice tuples for modal selects
        "next_of_kin_choices":  NextOfKin.RELATIONSHIP_CHOICES,
        "dependant_choices":    Dependant.RELATIONSHIP_CHOICES,
        "beneficiary_choices":  Beneficiary.RELATIONSHIP_CHOICES,
    }

    return render(request, "System/individual_profile.html", context)


# ==========================================
# SAVE NEXT OF KIN  (AJAX / modal POST)
# ==========================================
@login_required
@require_POST
def save_next_of_kin(request):
    """
    Creates or fully replaces the Next-of-Kin record for the logged-in
    IndividualMember.  Only accessible to Super Subscription members.
    Returns JSON so the modal can update the UI without a page reload.
    """
    member = get_object_or_404(IndividualMember, user=request.user)

    if member.package != "Super Subscription":
        return JsonResponse(
            {"status": "error", "message": "Next of Kin is only available on the Super Subscription plan."},
            status=403
        )

    form = NextOfKinForm(request.POST)

    if form.is_valid():
        # Replace existing record (OneToOne)
        NextOfKin.objects.filter(member=member).delete()
        nok = form.save(commit=False)
        nok.member = member
        nok.save()

        return JsonResponse({
            "status": "ok",
            "message": "Next of Kin saved successfully.",
            "data": {
                "full_name":    nok.full_name,
                "relationship": nok.get_relationship_display(),
                "phone_number": nok.phone_number,
                "email":        nok.email or "",
                "id_number":    nok.id_number or "",
            }
        })

    return JsonResponse(
        {"status": "error", "errors": form.errors},
        status=400
    )


# ==========================================
# ADD DEPENDANT  (AJAX / modal POST)
# ==========================================
@login_required
@require_POST
def add_dependant(request):
    """
    Adds a new Dependant for the logged-in IndividualMember.
    Only accessible to Super Subscription members.
    """
    member = get_object_or_404(IndividualMember, user=request.user)

    if member.package != "Super Subscription":
        return JsonResponse(
            {"status": "error", "message": "Dependants are only available on the Super Subscription plan."},
            status=403
        )

    MAX_DEPENDANTS = 7
    current_count = Dependant.objects.filter(member=member, aged_out=False).count()
    if current_count >= MAX_DEPENDANTS:
        return JsonResponse(
            {"status": "error", "message": f"You have reached the maximum of {MAX_DEPENDANTS} dependants."},
            status=400
        )

    form = DependantForm(request.POST)

    if form.is_valid():
        dep = form.save(commit=False)
        dep.member = member
        dep.save()

        remaining = MAX_DEPENDANTS - (current_count + 1)
        return JsonResponse({
            "status": "ok",
            "message": "Dependant added successfully.",
            "remaining": remaining,
            "at_limit": remaining == 0,
            "data": {
                "id":           dep.id,
                "full_name":    dep.full_name,
                "relationship": dep.get_relationship_display(),
                "dob":          dep.date_of_birth.strftime("%d %b %Y"),
                "age":          dep.age,
                "turns_18_on":  dep.turns_18_on.strftime("%d %b %Y"),
            }
        })

    return JsonResponse(
        {"status": "error", "errors": form.errors},
        status=400
    )


# ==========================================
# REMOVE DEPENDANT  (AJAX DELETE)
# ==========================================
@login_required
@require_POST
def remove_dependant(request, dependant_id):
    """
    Hard-deletes a Dependant record that belongs to the logged-in member.
    This is for manual removal; automatic removal at age 18 uses
    Dependant.check_and_age_out() called from a management command.
    """
    member    = get_object_or_404(IndividualMember, user=request.user)
    dependant = get_object_or_404(Dependant, id=dependant_id, member=member)
    dependant.delete()

    return JsonResponse({"status": "ok", "message": "Dependant removed."})


# ==========================================
# UPDATE DEPENDANT  (AJAX / modal POST)
# ==========================================
@login_required
@require_POST
def update_dependant(request, dependant_id):
    """
    Updates an existing Dependant record for the logged-in IndividualMember.
    Only accessible to Super Subscription members.
    """
    member    = get_object_or_404(IndividualMember, user=request.user)
    dependant = get_object_or_404(Dependant, id=dependant_id, member=member)

    if member.package != "Super Subscription":
        return JsonResponse(
            {"status": "error", "message": "Dependants are only available on the Super Subscription plan."},
            status=403
        )

    form = DependantForm(request.POST, instance=dependant)

    if form.is_valid():
        dep = form.save()
        return JsonResponse({
            "status": "ok",
            "message": "Dependant updated successfully.",
            "data": {
                "id":           dep.id,
                "full_name":    dep.full_name,
                "relationship": dep.get_relationship_display(),
                "dob":          dep.date_of_birth.strftime("%d %b %Y"),
                "age":          dep.age,
                "turns_18_on":  dep.turns_18_on.strftime("%d %b %Y"),
            }
        })

    return JsonResponse(
        {"status": "error", "errors": form.errors},
        status=400
    )


# ==========================================
# ADD BENEFICIARY  (AJAX / modal POST)
# ==========================================
@login_required
@require_POST
def add_beneficiary(request):
    """
    Adds a Beneficiary for the logged-in IndividualMember.
    Validates that total allocation across all beneficiaries stays ≤ 100%.
    """
    member = get_object_or_404(IndividualMember, user=request.user)

    if member.package != "Super Subscription":
        return JsonResponse(
            {"status": "error", "message": "Beneficiaries are only available on the Super Subscription plan."},
            status=403
        )

    MAX_BENEFICIARIES = 2
    current_count = Beneficiary.objects.filter(member=member).count()
    if current_count >= MAX_BENEFICIARIES:
        return JsonResponse(
            {"status": "error", "message": f"You can only add up to {MAX_BENEFICIARIES} beneficiaries."},
            status=400
        )

    form = BeneficiaryForm(request.POST)

    if form.is_valid():
        new_pct = form.cleaned_data["allocation_percentage"]

        # Validate total allocation won't exceed 100 %
        from django.db.models import Sum as _Sum
        existing_total = (
            Beneficiary.objects.filter(member=member)
            .aggregate(total=_Sum("allocation_percentage"))["total"]
            or 0
        )

        if existing_total + new_pct > 100:
            remaining = 100 - existing_total
            return JsonResponse(
                {
                    "status": "error",
                    "errors": {
                        "allocation_percentage": [
                            f"Total allocation would exceed 100%. "
                            f"You have {remaining:.2f}% remaining to allocate."
                        ]
                    }
                },
                status=400
            )

        ben = form.save(commit=False)
        ben.member = member
        ben.save()

        remaining = MAX_BENEFICIARIES - (current_count + 1)
        return JsonResponse({
            "status": "ok",
            "message": "Beneficiary added successfully.",
            "remaining": remaining,
            "at_limit": remaining == 0,
            "data": {
                "id":                    ben.id,
                "full_name":             ben.full_name,
                "relationship":          ben.get_relationship_display(),
                "phone_number":          ben.phone_number,
                "allocation_percentage": str(ben.allocation_percentage),
            }
        })

    return JsonResponse(
        {"status": "error", "errors": form.errors},
        status=400
    )


# ==========================================
# REMOVE BENEFICIARY  (AJAX DELETE)
# ==========================================
@login_required
@require_POST
def remove_beneficiary(request, beneficiary_id):
    """Hard-deletes a Beneficiary that belongs to the logged-in member."""
    member      = get_object_or_404(IndividualMember, user=request.user)
    beneficiary = get_object_or_404(Beneficiary, id=beneficiary_id, member=member)
    beneficiary.delete()

    return JsonResponse({"status": "ok", "message": "Beneficiary removed."})


# ==========================================
# UPDATE BENEFICIARY  (AJAX / modal POST)
# ==========================================
@login_required
@require_POST
def update_beneficiary(request, beneficiary_id):
    """
    Updates an existing Beneficiary record for the logged-in IndividualMember.
    Re-validates that total allocation across all beneficiaries stays ≤ 100%.
    """
    member      = get_object_or_404(IndividualMember, user=request.user)
    beneficiary = get_object_or_404(Beneficiary, id=beneficiary_id, member=member)

    if member.package != "Super Subscription":
        return JsonResponse(
            {"status": "error", "message": "Beneficiaries are only available on the Super Subscription plan."},
            status=403
        )

    form = BeneficiaryForm(request.POST, instance=beneficiary)

    if form.is_valid():
        new_pct = form.cleaned_data["allocation_percentage"]

        from django.db.models import Sum as _Sum
        existing_total = (
            Beneficiary.objects.filter(member=member)
            .exclude(id=beneficiary_id)
            .aggregate(total=_Sum("allocation_percentage"))["total"]
            or 0
        )

        if existing_total + new_pct > 100:
            remaining = 100 - existing_total
            return JsonResponse(
                {
                    "status": "error",
                    "errors": {
                        "allocation_percentage": [
                            f"Total allocation would exceed 100%. "
                            f"You have {remaining:.2f}% remaining to allocate."
                        ]
                    }
                },
                status=400
            )

        ben = form.save()
        return JsonResponse({
            "status": "ok",
            "message": "Beneficiary updated successfully.",
            "data": {
                "id":                    ben.id,
                "full_name":             ben.full_name,
                "relationship":          ben.get_relationship_display(),
                "phone_number":          ben.phone_number,
                "allocation_percentage": str(ben.allocation_percentage),
            }
        })

    return JsonResponse(
        {"status": "error", "errors": form.errors},
        status=400
    )


# ==========================================
# UPDATE DATA CONSENT  (AJAX toggle)
# ==========================================
@login_required
@require_POST
def update_data_consent(request):
    """
    Lightweight endpoint to toggle COCOWA data-sharing consent
    without requiring a full form submission.
    POST body (JSON or form-encoded):
        consent — "true" / "false"
    """
    try:
        if request.content_type == "application/json":
            body    = json.loads(request.body)
            consent = body.get("consent", "false")
        else:
            consent = request.POST.get("consent", "false")

        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        new_value  = consent in ("true", "True", True, "1", "on")

        profile.cocowa_data_consent = new_value
        profile.cocowa_consent_date = timezone.now()
        profile.save(update_fields=["cocowa_data_consent", "cocowa_consent_date"])

        return JsonResponse({
            "status":  "ok",
            "consent": new_value,
            "message": "Consent updated successfully."
        })

    except Exception as exc:
        return JsonResponse({"status": "error", "message": str(exc)}, status=500)


# ============================================================
# URL PATTERNS  — add these to your urls.py
# ============================================================
#
# from django.urls import path
# from . import views
#
# urlpatterns = [
#     ...
#     # Individual profile (existing, now replaced above)
#     path('profile/individual/', views.complete_individual_profile, name='complete_individual_profile'),
#
#     # Next of Kin
#     path('profile/nok/save/',                      views.save_next_of_kin,    name='save_next_of_kin'),
#
#     # Dependants
#     path('profile/dependants/add/',                views.add_dependant,       name='add_dependant'),
#     path('profile/dependants/<int:dependant_id>/remove/', views.remove_dependant, name='remove_dependant'),
#     path('profile/dependants/<int:dependant_id>/update/', views.update_dependant, name='update_dependant'),
#
#     # Beneficiaries
#     path('profile/beneficiaries/add/',             views.add_beneficiary,     name='add_beneficiary'),
#     path('profile/beneficiaries/<int:beneficiary_id>/remove/', views.remove_beneficiary, name='remove_beneficiary'),
#     path('profile/beneficiaries/<int:beneficiary_id>/update/', views.update_beneficiary, name='update_beneficiary'),
#
#     # Data consent
#     path('profile/consent/update/',                views.update_data_consent, name='update_data_consent'),
# ]
#     path('profile/next-of-kin/save/', views.save_next_of_kin, name='save_next_of_kin'),
#
#     # Dependants
#     path('profile/dependants/add/',               views.add_dependant,    name='add_dependant'),
#     path('profile/dependants/<int:dependant_id>/remove/', views.remove_dependant, name='remove_dependant'),
#
#     # Beneficiaries
#     path('profile/beneficiaries/add/',                     views.add_beneficiary,    name='add_beneficiary'),
#     path('profile/beneficiaries/<int:beneficiary_id>/remove/', views.remove_beneficiary, name='remove_beneficiary'),
#
#     # Data consent toggle
#     path('profile/consent/update/', views.update_data_consent, name='update_data_consent'),
#     ...
# ]
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
            email_profile_completed(request.user, "sacco")
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
            email_profile_completed(request.user, "partner")
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

    # POST: save transaction code and notify member
    if request.method == "POST":
        transaction_code = request.POST.get("transaction_code")

        if member.payment_status != "paid":
            member.transaction_code = transaction_code
            member.payment_status = "pending"
            member.save()
            email_payment_submitted(request.user, amount, transaction_code)

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
            complaint = form.save(user=request.user)
            email_complaint_raised(request.user, complaint)
            messages.success(request, "Complaint submitted successfully.")
            return redirect("my_complaints")

    else:
        form = ComplaintForm()

    return render(request, "System/ticket.html", {
        "form": form
    })

@login_required
@require_POST
def respond_to_complaint(request, pk):
    """
    Manager-only AJAX endpoint.
    - Validates the manager role
    - Optionally updates the complaint status
    - Sends the manager's response to the user's email
    - Returns JSON so the modal can update without a page reload
    """
    profile = get_object_or_404(UserProfile, user=request.user)
 
    if profile.role != "manager":
        return JsonResponse({"error": "Not authorised."}, status=403)
 
    complaint = get_object_or_404(Complaint, pk=pk)
 
    response_text = request.POST.get("response_message", "").strip()
    new_status    = request.POST.get("status", "").strip()
 
    if not response_text:
        return JsonResponse({"error": "Response message cannot be empty."}, status=400)
 
    # ── Update status if a valid one was supplied ──────────────
    valid_statuses = ["open", "in_progress", "resolved", "closed"]
    if new_status in valid_statuses:
        complaint.status = new_status
        complaint.save()
 
    # ── Send email to the user who raised the ticket ───────────
    user_email = complaint.user.email
    user_name  = complaint.user.get_full_name() or complaint.user.username
    manager_name = request.user.get_full_name() or request.user.username
 
    subject = f"Re: Your Complaint Ticket #{complaint.ticket_number} – {complaint.subject}"
 
    body = f"""Dear {user_name},
 
Thank you for contacting us. Our support team has reviewed your complaint and would like to respond as follows:
 
Ticket:     #{complaint.ticket_number}
Category:   {complaint.get_category_display()}
Status:     {complaint.get_status_display()}

{response_text}
 
 
If you have further questions, please raise a new ticket or reply to this email.
 
Regards,
{manager_name}
Support Team
"""
 
    try:
        from django.core.mail import send_mail
        from django.conf import settings
 
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False,
        )
        messages.success(request, "Response sent successfully and email delivered.")

    except Exception as e:
        messages.warning(request, f"Response saved but email failed: {str(e)}")

    return redirect("manager_complaints")
 
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

        case = ReportCases.objects.create(
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
        email_incident_submitted(request.user, case)

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
            email_complaint_status_updated(complaint.user, complaint, new_status)
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

    profile = get_object_or_404(UserProfile, user=request.user)

    if profile.role != "manager":
        messages.error(request, "You are not authorized to perform this action.")
        return redirect("manager_cases")

    case_id = request.POST.get("case_id")
    status = request.POST.get("status")

    valid_statuses = ["open", "investigating", "resolved", "closed"]

    if status not in valid_statuses:
        messages.error(request, "Invalid case status selected.")
        return redirect("manager_cases")

    case = get_object_or_404(ReportCases, id=case_id)

    case.status = status
    case.save()

    email_incident_status_updated(case.reporter, case, status)

    messages.success(
        request,
        f"Case #{case.id} status updated successfully to '{status.title()}'."
    )

    return redirect("manager_cases")

@login_required
def respond_to_case(request, pk):

    case = get_object_or_404(ReportCases, pk=pk)

    if request.method == "POST":

        response = request.POST.get("response_message")

        case.manager_response = response
        case.save()

        email_case_response(
            case.reporter,
            case,
            response
        )

        messages.success(
            request,
            "Response sent successfully."
        )

    return redirect("manager_cases")

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
    saccos = SaccoMember.objects.annotate(
        vehicle_count=Count("vehicles")
    )
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
 
    # ─────────────────────────────────────────────────────────
    # MEMBERSHIP
    # ─────────────────────────────────────────────────────────
    individual_count = IndividualMember.objects.count()
    sacco_count      = SaccoMember.objects.count()
    partner_count    = PartnerMember.objects.count()
    total_members    = individual_count + sacco_count + partner_count
 
    active_individuals = IndividualMember.objects.filter(payment_status="paid").count()
    active_saccos      = SaccoMember.objects.filter(payment_status="paid").count()
    active_partners    = PartnerMember.objects.filter(payment_status="paid").count()
    active_members     = active_individuals + active_saccos + active_partners
    # Individual subscriptions
    monthly_individual = [] 
    monthly_sacco = []
    monthly_partner = []
    months_labels = []

    for month_num in range(1, 13):
        month_label = datetime.datetime(current_year, month_num, 1).strftime('%b')
        months_labels.append(month_label)
        monthly_individual.append(
            IndividualMember.objects.filter(
                user__date_joined__year=current_year,
                user__date_joined__month=month_num
            ).count()
        )
        monthly_sacco.append(
            SaccoMember.objects.filter(
                created_at__year=current_year,
                created_at__month=month_num
            ).count()
        )
        monthly_partner.append(
            PartnerMember.objects.filter(
                created_at__year=current_year,
                created_at__month=month_num
            ).count()
        )
 
    payment_rate = round(
        (active_members / total_members) * 100, 1
    ) if total_members else 0
 
    # ─────────────────────────────────────────────────────────
    # REVENUE
    # ─────────────────────────────────────────────────────────
    individual_revenue = IndividualMember.objects.filter(
        payment_status="paid"
    ).aggregate(total=Sum("amount"))["total"] or 0
 
    sacco_revenue = Vehicle.objects.filter(
        payment_status="paid"
    ).aggregate(total=Sum("amount"))["total"] or 0
 
    partner_revenue = PartnerDonation.objects.filter(
        status="paid"
    ).aggregate(total=Sum("amount"))["total"] or 0
 
    total_revenue = individual_revenue + sacco_revenue + partner_revenue
 
    # ─────────────────────────────────────────────────────────
    # COMPLAINTS
    # ─────────────────────────────────────────────────────────
    complaint_open     = Complaint.objects.filter(status="open").count()
    complaint_progress = Complaint.objects.filter(status="in_progress").count()
    complaint_resolved = Complaint.objects.filter(status="resolved").count()
    complaint_closed   = Complaint.objects.filter(status="closed").count()
    total_complaints   = Complaint.objects.count()
 
    recent_complaints = Complaint.objects.select_related("user").order_by("-created_at")[:10]
 
    # ─────────────────────────────────────────────────────────
    # INCIDENT CASES
    # ─────────────────────────────────────────────────────────
    open_cases         = ReportCases.objects.filter(status="open").count()
    investigating_cases = ReportCases.objects.filter(status="investigating").count()
    resolved_cases     = ReportCases.objects.filter(status="resolved").count()
    closed_cases       = ReportCases.objects.filter(status="closed").count()
    total_cases        = ReportCases.objects.count()
 
    recent_cases = ReportCases.objects.select_related(
        "sacco", "reporter"
    ).order_by("-created_at")[:10]
 
    # ─────────────────────────────────────────────────────────
    # VEHICLE ANALYTICS
    # ─────────────────────────────────────────────────────────
    total_vehicles = Vehicle.objects.count()
    town_service   = Vehicle.objects.filter(vehicle_type="town_service").count()
    long_distance  = Vehicle.objects.filter(vehicle_type="long_distance").count()
 
    # ─────────────────────────────────────────────────────────
    # MONTHLY REVENUE TREND (12 months)
    # ─────────────────────────────────────────────────────────
    months       = []
    revenue_data = []
 
    for month in range(1, 13):
        ind = IndividualMember.objects.filter(
            payment_status="paid",
            created_at__year=current_year,
            created_at__month=month,
        ).aggregate(total=Sum("amount"))["total"] or 0
 
        sac = Vehicle.objects.filter(
            payment_status="paid",
            created_at__year=current_year,
            created_at__month=month,
        ).aggregate(total=Sum("amount"))["total"] or 0
 
        par = PartnerDonation.objects.filter(
            status="paid",
            created_at__year=current_year,
            created_at__month=month,
        ).aggregate(total=Sum("amount"))["total"] or 0
 
        months.append(calendar.month_abbr[month])
        revenue_data.append(float(ind + sac + par))
 
    # ─────────────────────────────────────────────────────────
    # SMART INSIGHTS  (enhanced)
    # ─────────────────────────────────────────────────────────
    insights = []
 
    if payment_rate < 50:
        insights.append(f"⚠ Low payment compliance ({payment_rate}%) — follow-up emails recommended.")
 
    if complaint_open > complaint_resolved:
        insights.append(
            f"⚠ Open complaints ({complaint_open}) exceed resolved ({complaint_resolved})."
        )
 
    if total_revenue > 500_000:
        insights.append(
            f"✅ Revenue performance strong — KES {total_revenue:,.0f} collected this year."
        )
 
    if total_cases > 20:
        insights.append(
            f"🚨 High incident volume ({total_cases} reports). Safety review advised."
        )
 
    if not insights:
        insights.append("✅ No critical anomalies detected this cycle.")
 
    # ─────────────────────────────────────────────────────────
    # OPTIONAL: auto-send weekly digest when page is loaded
    # on Mondays (remove if you prefer scheduled task only)
    # ─────────────────────────────────────────────────────────
    # import datetime
    # if timezone.now().weekday() == 0:  # Monday
    #     send_manager_weekly_digest(request.user, {
    #         "total_members":  total_members,
    #         "active_members": active_members,
    #         "total_revenue":  total_revenue,
    #         "payment_rate":   payment_rate,
    #         "complaint_open": complaint_open,
    #         "open_cases":     open_cases,
    #     })
 
    context = {
        # membership
        "total_members":    total_members,
        "active_members":   active_members,
        "payment_rate":     payment_rate,
        "individual_count": individual_count,
        "sacco_count":      sacco_count,
        "partner_count":    partner_count,
        "months": json.dumps(months_labels),
        "monthly_individual": json.dumps(monthly_individual),
        "monthly_sacco": json.dumps(monthly_sacco),
        "monthly_partner": json.dumps(monthly_partner),
 
        # revenue
        "total_revenue":      total_revenue,
        "individual_revenue": individual_revenue,
        "sacco_revenue":      sacco_revenue,
        "partner_revenue":    partner_revenue,
 
        # complaints
        "total_complaints":   total_complaints,
        "complaint_open":     complaint_open,
        "complaint_progress": complaint_progress,
        "complaint_resolved": complaint_resolved,
        "complaint_closed":   complaint_closed,
        "recent_complaints":  recent_complaints,
 
        # cases
        "total_cases":         total_cases,
        "open_cases":          open_cases,
        "investigating_cases": investigating_cases,
        "resolved_cases":      resolved_cases,
        "closed_cases":        closed_cases,
        "recent_cases":        recent_cases,
 
        # vehicles
        "total_vehicles": total_vehicles,
        "town_service":   town_service,
        "long_distance":  long_distance,
 
        # chart data
        "months":       json.dumps(months),
        "revenue_data": json.dumps(revenue_data),
 
        # insights
        "insights":     insights,
 
        # meta
        "current_year": current_year,
    }
 
    return render(request, "System/manager_report.html", context)

# ==========================================
# SETTINGS — COMPLETE IMPLEMENTATION
# Drop these views into views.py, replacing
# the existing settings_page stub.
# Add the URL patterns shown at the bottom.
# ==========================================



# ==========================================
# SETTINGS PAGE  (main hub)
# ==========================================
@login_required
def settings_page(request):
    """
    Renders the settings hub and passes every
    sub-model the template needs.
    """
    user = request.user

    user_settings, _ = UserSettings.objects.get_or_create(user=user)
    profile, _        = UserProfile.objects.get_or_create(user=user)

    context = {
        "settings":         user_settings,
        "profile":          profile,
        "password_form":    PasswordChangeForm(user),   # empty; POST handled separately
    }

    return render(request, "System/settings.html", context)

@login_required
def manager_vehicles(request):

    profile = get_object_or_404(
        UserProfile,
        user=request.user
    )

    if profile.role != "manager":
        return redirect("home")

    query = request.GET.get("q", "").strip()

    vehicles = Vehicle.objects.select_related(
        "sacco"
    )

    if query:
        vehicles = vehicles.filter(
            Q(number_plate__icontains=query) |
            Q(route__icontains=query) |
            Q(sacco__sacco_name__icontains=query)
        )

    vehicles = vehicles.order_by("-created_at")

    # Stats
    total_vehicles = vehicles.count()

    paid_count = vehicles.filter(
        payment_status="paid"
    ).count()

    pending_count = vehicles.filter(
        payment_status="pending"
    ).count()

    total_revenue = vehicles.filter(
        payment_status="paid"
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0

    return render(
        request,
        "System/manager_vehicles.html",
        {
            "vehicles": vehicles,
            "query": query,

            "total_vehicles": total_vehicles,
            "paid_count": paid_count,
            "pending_count": pending_count,
            "total_revenue": total_revenue,
        }
    )

# ==========================================
# SAVE NOTIFICATIONS / PRIVACY / SYSTEM
# (single AJAX-friendly POST — handles all
#  three toggle sections at once)
# ==========================================
@login_required
@require_POST
def settings_save_preferences(request):
    """
    Handles the Notifications, Privacy, and
    System Preferences sections of the settings
    page via a single POST.

    Works for both normal form submits and
    fetch()/AJAX requests.
    """
    user_settings, _ = UserSettings.objects.get_or_create(user=request.user)

    # --------------------------------------------------
    # NOTIFICATIONS
    # --------------------------------------------------
    user_settings.email_notifications = "email_notifications" in request.POST
    user_settings.sms_notifications   = "sms_notifications"   in request.POST
    user_settings.complaint_updates   = "complaint_updates"   in request.POST
    user_settings.payment_reminders   = "payment_reminders"   in request.POST

    # --------------------------------------------------
    # EMAIL & LOGIN
    # --------------------------------------------------
    user_settings.two_factor_enabled  = "two_factor_enabled"  in request.POST
    user_settings.login_alerts        = "login_alerts"        in request.POST

    # --------------------------------------------------
    # PRIVACY
    # --------------------------------------------------
    user_settings.profile_visibility  = "profile_visibility"  in request.POST
    user_settings.show_email          = "show_email"          in request.POST
    user_settings.show_phone          = "show_phone"          in request.POST

    # --------------------------------------------------
    # SYSTEM PREFERENCES
    # --------------------------------------------------
    user_settings.dark_mode = "dark_mode" in request.POST
    user_settings.language  = request.POST.get("language", "en")

    user_settings.save()

    # Support both JSON (AJAX) and redirect (normal form)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"status": "ok", "message": "Preferences saved."})

    messages.success(request, "Your preferences have been updated.")
    return redirect("settings_page")


# ==========================================
# CHANGE PASSWORD
# ==========================================
@login_required
@require_POST
def settings_change_password(request):
    """
    Uses Django's built-in PasswordChangeForm so
    validation (old password check, confirm match)
    is handled automatically.

    Calls update_session_auth_hash so the user
    stays logged in after changing their password.
    """
    form = PasswordChangeForm(user=request.user, data=request.POST)

    if form.is_valid():
        form.save()
        # Keep the session alive — without this Django
        # logs the user out immediately.
        update_session_auth_hash(request, form.user)
        email_password_changed(request.user)
        messages.success(request, "Password changed successfully.")
    else:
        # Collect all form errors into one readable message.
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, error)

    return redirect("settings_page")


# ==========================================
# UPDATE PROFILE  (name / phone)
# ==========================================
@login_required
@require_POST
def settings_update_profile(request):
    """
    Updates the fields that are editable from the
    Settings page:
      - phone_number  →  UserProfile
      - first_name / last_name  →  User (Django built-in)

    For IndividualMember it also syncs first_name /
    second_name so the member record stays consistent.
    """
    user    = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    # --------------------------------------------------
    # PROFILE PICTURE — saved independently so later
    # profile.save() calls never accidentally clear it
    # --------------------------------------------------
    if 'profile_picture' in request.FILES:
        profile.profile_picture = request.FILES['profile_picture']
        profile.save(update_fields=['profile_picture'])

    # --------------------------------------------------
    # CORE USER FIELDS
    # --------------------------------------------------
    first_name = request.POST.get("first_name", "").strip()
    last_name  = request.POST.get("last_name",  "").strip()
    phone      = request.POST.get("phone_number", "").strip()

    if first_name:
        user.first_name = first_name
    if last_name:
        user.last_name = last_name
    user.save()

    # --------------------------------------------------
    # PROFILE PHONE NUMBER
    # --------------------------------------------------
    if phone:
        profile.phone_number = phone
        profile.save(update_fields=['phone_number'])

    # --------------------------------------------------
    # SYNC TO MEMBER TABLE  (role-specific)
    # --------------------------------------------------
    if profile.role == "individual":
        try:
            member = IndividualMember.objects.get(user=user)
            if first_name:
                member.first_name  = first_name
            if last_name:
                member.second_name = last_name
            if phone:
                member.phone_number = phone
            member.save()
        except IndividualMember.DoesNotExist:
            pass

    elif profile.role == "sacco":
        try:
            member = SaccoMember.objects.get(user=user)
            if phone:
                member.phone_number = phone
            member.save()
        except SaccoMember.DoesNotExist:
            pass

    elif profile.role == "partner":
        try:
            member = PartnerMember.objects.get(user=user)
            if phone:
                member.phone_number = phone
            member.save()
        except PartnerMember.DoesNotExist:
            pass

    messages.success(request, "Profile updated successfully.")
    return redirect("settings_page")


# ==========================================
# DELETE ACCOUNT
# ==========================================
@login_required
@require_POST
def settings_delete_account(request):
    """
    Permanently deletes the logged-in user's account
    after verifying their password.

    The cascade rules on the models mean every
    related record (member, complaints, OTP, etc.)
    is deleted automatically by the database.
    """
    password = request.POST.get("confirm_password", "")
    user     = request.user

    if not user.check_password(password):
        messages.error(request, "Incorrect password. Account not deleted.")
        return redirect("settings_page")

    # Log out first so Django doesn't try to
    # update a now-deleted session user.
    logout(request)
    user.delete()

    messages.success(request, "Your account has been permanently deleted.")
    return redirect("home")


# ==========================================
# TOGGLE SINGLE SETTING  (AJAX only)
# ==========================================
@login_required
@require_POST
def settings_toggle(request):
    """
    Lightweight AJAX endpoint for individual
    toggle switches (e.g. dark mode, 2FA) without
    a full page reload.

    POST body (JSON or form-encoded):
        field   — the UserSettings field name
        value   — "true" / "false"

    Example JS usage:
        await fetch("/settings/toggle/", {
            method: "POST",
            headers: {"X-CSRFToken": getCookie("csrftoken"),
                      "Content-Type": "application/json"},
            body: JSON.stringify({field: "dark_mode", value: "true"})
        });
    """
    TOGGLEABLE_FIELDS = {
        "email_notifications",
        "sms_notifications",
        "complaint_updates",
        "payment_reminders",
        "two_factor_enabled",
        "login_alerts",
        "profile_visibility",
        "show_email",
        "show_phone",
        "dark_mode",
    }

    try:
        # Accept both JSON body and form-encoded
        if request.content_type == "application/json":
            body  = json.loads(request.body)
            field = body.get("field", "")
            value = body.get("value", "false")
        else:
            field = request.POST.get("field", "")
            value = request.POST.get("value", "false")

        if field not in TOGGLEABLE_FIELDS:
            return JsonResponse(
                {"status": "error", "message": f"Unknown field: {field}"},
                status=400
            )

        user_settings, _ = UserSettings.objects.get_or_create(user=request.user)
        setattr(user_settings, field, value in ("true", "True", True, "1", "on"))
        user_settings.save(update_fields=[field])

        return JsonResponse({"status": "ok", "field": field, "value": getattr(user_settings, field)})

    except Exception as exc:
        return JsonResponse({"status": "error", "message": str(exc)}, status=500)

@login_required
@require_POST
def settings_upload_avatar(request):
    if not request.FILES.get('profile_picture'):
        return JsonResponse({'status': 'error', 'error': 'No file received.'}, status=400)

    file = request.FILES['profile_picture']

    # Validate type
    if not file.content_type.startswith('image/'):
        return JsonResponse({'status': 'error', 'error': 'Only image files are allowed.'}, status=400)

    # Validate size (5 MB max)
    if file.size > 5 * 1024 * 1024:
        return JsonResponse({'status': 'error', 'error': 'Image must be under 5 MB.'}, status=400)

    profile = request.user.userprofile
    profile.profile_picture = file
    profile.save()

    return JsonResponse({'status': 'ok', 'url': profile.profile_picture.url})