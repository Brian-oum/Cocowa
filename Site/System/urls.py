from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('services/', views.services, name='services'),
    path('join/', views.join_membership, name='join'),
    path("payment/<str:member_type>/<int:member_id>/",views.payment_page, name="payment_page"),
    path('payment-status/<int:member_id>/', views.payment_status, name='payment_status'),
    path('membership/check/',views.check_membership,name='check_membership'),
    path("login/", views.custom_login, name="login"),
    path("dashboard/sacco/", views.sacco_dashboard, name="sacco_dashboard"),
    path("dashboard/individual/", views.individual_dashboard, name="individual_dashboard"),
    path("dashboard/partner/", views.partner_dashboard, name="partner_dashboard"),
    path("dashboard/manager/", views.manager_dashboard, name="manager_dashboard"),
    path("logout/", views.custom_logout, name="logout"),
    path("dashboard-redirect/", views.dashboard_redirect, name="dashboard_redirect"),
    path("partner/donation/", views.partner_donation, name="partner_donation"),
    path("partner/report/", views.partner_report, name="partner_report"),
    path('partner/report/pdf/', views.partner_report_pdf, name='partner_report_pdf'),
    path("complete-individual-profile/", views.complete_individual_profile, name="complete_individual_profile"),
    path('download-membership-card/', views.download_membership_card, name='download_membership_card'),
    path("complete-sacco-profile/", views.complete_sacco_profile, name="complete_sacco_profile"),
    path("complete-partner-profile/", views.complete_partner_profile, name="complete_partner_profile"),
    path('membership-card/', views.membership_card, name='membership_card'),
    path("tickets/new/", views.raise_complaint, name="raise_complaint"),
    path("tickets/", views.my_complaints, name="my_complaints"),
    path("report-cases/new/", views.report_cases, name="report_cases"),
    path("report-cases/", views.my_cases, name="my_cases"),
    path("manager/cases/", views.manager_cases, name="manager_cases"),
    path("manager/complaints/", views.manager_complaints, name="manager_complaints"),
    path("manager/complaints/update/<int:pk>/", views.update_complaint_status, name="update_complaint_status"),
    path("manager/report/", views.manager_report, name="manager_report"),
    path("manager/cases/update/", views.update_case_status, name="update_case_status"),
    path("members/individuals/", views.individuals_list, name="individuals_list"),
    path("members/saccos/", views.sacco_list, name="sacco_list"),
    path("vehicles/", views.vehicle_list, name="vehicle_list"),
    path("members/partners/", views.partners_list, name="partners_list"),
    path("members/autocomplete/", views.member_autocomplete, name="member_autocomplete"),
    path("saccos/autocomplete/", views.sacco_autocomplete, name="sacco_autocomplete"),
    path("partners/autocomplete/", views.partner_autocomplete, name="partner_autocomplete"),  
    path("accounts/google/redirect/", views.google_redirect, name="google_redirect"), 
    path("select-role/", views.select_role, name="select_role"),
    path("verify-email/", views.verify_email, name="verify_email"),
    path("resend-otp/", views.resend_otp, name="resend_otp"),
    path("settings/",                   views.settings_page,               name="settings_page"),
    path("settings/preferences/",       views.settings_save_preferences,   name="settings_save_preferences"),
    path("settings/change-password/",   views.settings_change_password,    name="settings_change_password"),
    path("settings/update-profile/",    views.settings_update_profile,     name="settings_update_profile"),
    path("settings/delete-account/",    views.settings_delete_account,     name="settings_delete_account"),
    path("settings/toggle/",            views.settings_toggle,             name="settings_toggle"),
    path('saccos/analytics-report/', views.sacco_report, name='sacco_report'),
    path("manager/vehicles/", views.manager_vehicles, name="manager_vehicles"),
    path("complaints/<int:pk>/respond/", views.respond_to_complaint, name="respond_to_complaint"),
    path('profile/individual/', views.complete_individual_profile, name='complete_individual_profile'),
    path('profile/next-of-kin/save/', views.save_next_of_kin, name='save_next_of_kin'),
    path('profile/dependants/add/',               views.add_dependant,    name='add_dependant'),
    path('profile/dependants/<int:dependant_id>/remove/', views.remove_dependant, name='remove_dependant'),
    path('profile/beneficiaries/add/',                     views.add_beneficiary,    name='add_beneficiary'),
    path('profile/beneficiaries/<int:beneficiary_id>/remove/', views.remove_beneficiary, name='remove_beneficiary'),
    path('profile/consent/update/', views.update_data_consent, name='update_data_consent'),
    path('profile/dependants/<int:dependant_id>/update/', views.update_dependant, name='update_dependant'),
    path('profile/beneficiaries/<int:beneficiary_id>/update/', views.update_beneficiary, name='update_beneficiary'),
    path("settings/upload-avatar/", views.settings_upload_avatar, name="settings_upload_avatar"),
    path('cases/<int:pk>/respond/', views.respond_to_case, name='respond_to_case'),
     # Forgot Password
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="System/password_reset_form.html"
        ),
        name="password_reset"
    ),

    # Email Sent
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="System/password_reset_done.html"
        ),
        name="password_reset_done"
    ),

    # Link in Email
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="System/password_reset_confirm.html"
        ),
        name="password_reset_confirm"
    ),

    # Success
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="System/password_reset_complete.html"
        ),
        name="password_reset_complete"
    ),
]