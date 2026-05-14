from django.shortcuts import render, redirect, get_object_or_404
from .forms import MembershipForm
from .models import Membership
from django.http import HttpResponse, Http404
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from django.conf import settings
import os
from django.contrib.staticfiles import finders

def join_membership(request):
    if request.method == 'POST':
        form = MembershipForm(request.POST)

        if form.is_valid():
            member = form.save()
            return redirect('payment', member_id=member.id)  # ✅ redirect here
        else:
            print(form.errors)  # 🔥 VERY IMPORTANT (debug)

    else:
        form = MembershipForm()

    return render(request, 'System/join.html', {'form': form})

def payment_page(request, member_id):
    member = get_object_or_404(Membership, id=member_id)

    if request.method == 'POST':
        transaction_code = request.POST.get('transaction_code')

        # Save transaction code
        member.transaction_code = transaction_code
        member.payment_status = 'pending'  # still pending until admin confirms
        member.save()

        return redirect('payment_status', member_id=member.id)

    return render(request, 'System/payment.html', {'member': member})

def payment_status(request, member_id):
    member = get_object_or_404(Membership, id=member_id)

    return render(request, 'System/payment_status.html', {
        'member': member
    })


def download_membership_card(request, member_id):
    member = get_object_or_404(Membership, id=member_id)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="COCOWA_Card_{member.id}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # --- COLORS ---
    navy = colors.HexColor("#001C3D")
    cream = colors.HexColor("#FDF2E2")
    accent_green = colors.HexColor("#28A745")

    # --- CARD BACKGROUND ---
    p.setFillColor(cream)
    p.rect(50, height - 350, width - 100, 300, fill=1, stroke=0)

    # --- BORDER ---
    p.setStrokeColor(navy)
    p.setLineWidth(2)
    p.rect(50, height - 350, width - 100, 300)

    # =========================
    # HEADER (LOGO + TITLE)
    # =========================
    header_y = height - 100

    # LOGO (LEFT)
    logo_path = finders.find('images/cocowalogo.png')
    if logo_path and os.path.exists(logo_path):
        p.drawImage(
            logo_path,
            70,
            header_y - 25,
            width=60,
            height=60,
            mask='auto'
        )

    # TITLE (RIGHT)
    p.setFillColor(navy)
    p.setFont("Helvetica-Bold", 20)
    p.drawRightString(width - 70, header_y, "MEMBERSHIP CARD")

    # HEADER LINE
    p.setLineWidth(1)
    p.line(70, header_y - 30, width - 70, header_y - 30)

    # =========================
    # MEMBER DETAILS
    # =========================
    y_pos = header_y - 70

    details = [
        ("NAME:", f"{member.first_name.upper()} {member.second_name.upper()}"),
        ("MEMBER NO:", f"{member.membership_number}"),
        ("PACKAGE:", f"{member.package.upper()}"),
        ("PHONE:", f"{member.phone_number}"),
        ("EMAIL:", f"{member.email.lower()}"),
    ]

    for label, value in details:
        p.setFillColor(navy)
        p.setFont("Helvetica-Bold", 10)
        p.drawString(70, y_pos, label)

        p.setFillColor(colors.black)
        p.setFont("Helvetica", 12)
        p.drawString(170, y_pos, value)

        y_pos -= 25

    # =========================
    # STATUS BADGE
    # =========================
    status_text = "ACTIVE" if member.payment_status == "paid" else "INACTIVE"
    status_color = accent_green if member.payment_status == "paid" else colors.red

    p.setFillColor(status_color)
    p.roundRect(width - 160, height - 330, 90, 30, 5, fill=1, stroke=0)

    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 10)
    p.drawCentredString(width - 115, height - 318, status_text)

    # =========================
    # FOOTER
    # =========================
    p.setFillColor(colors.grey)
    p.setFont("Helvetica-Oblique", 8)
    p.drawString(70, height - 340, f"Generated on: {member.created_at.strftime('%Y-%m-%d')}")
    p.drawRightString(width - 70, height - 340, "Verification Required for Access")

    p.showPage()
    p.save()

    return response

def home(request):
    return render(request, 'System/home.html')

def about(request):
    return render(request, 'System/about.html')

def contact(request):
    return render(request, 'System/contact.html')

def services(request):
    return render(request, 'System/services.html')