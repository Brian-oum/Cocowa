from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('services/', views.services, name='services'),
    path('join/', views.join_membership, name='join'),
    path('payment/<int:member_id>/', views.payment_page, name='payment'),
    path('payment-status/<int:member_id>/', views.payment_status, name='payment_status'),
    path('membership/check/',views.check_membership,name='check_membership'),
    path("login/", views.custom_login, name="login"),

    path("dashboard/sacco/", views.sacco_dashboard, name="sacco_dashboard"),
    path("dashboard/individual/", views.individual_dashboard, name="individual_dashboard"),
    path("dashboard/partner/", views.partner_dashboard, name="partner_dashboard"),
    path("logout/", views.custom_logout, name="logout"),
    path(
    "dashboard-redirect/", views.dashboard_redirect, name="dashboard_redirect"),
path(
    "partner/donation/",
    views.partner_donation,
    name="partner_donation"
),
path("partner/report/", views.partner_report, name="partner_report"),
path('partner/report/pdf/', views.partner_report_pdf, name='partner_report_pdf'),
path(
    "complete-individual-profile/",
    views.complete_individual_profile,
    name="complete_individual_profile"
),
path(
        'download-membership-card/',
        views.download_membership_card,
        name='download_membership_card'
    ),
path(
    "complete-sacco-profile/",
    views.complete_sacco_profile,
    name="complete_sacco_profile"
),

path(
    "complete-partner-profile/",
    views.complete_partner_profile,
    name="complete_partner_profile"
),
 path(
        'membership-card/',
        views.membership_card,
        name='membership_card'
    ),

]