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
    path('download-card/<int:member_id>/', views.download_membership_card, name='download_card'),
]