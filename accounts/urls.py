from django.urls import path
from . import views

urlpatterns = [
    # ─── Pages ───
    path('register/', views.register_page, name='signup'),

    # ─── Legacy ───
    path('verify-otp/', views.verify_otp, name='verify_otp'),

    # ─── API Endpoints ───
    path('api/check-username/', views.check_username, name='check_username'),
    path('api/check-email/', views.check_email, name='check_email'),
    path('api/send-email-otp/', views.send_email_otp, name='send_email_otp'),
    path('api/verify-email-otp/', views.verify_email_otp, name='verify_email_otp'),
    path('api/send-mobile-otp/', views.send_mobile_otp, name='send_mobile_otp'),
    path('api/verify-mobile-otp/', views.verify_mobile_otp, name='verify_mobile_otp'),

    # ─── Registration (AJAX POST) ───
    path('register/submit/', views.register, name='register_submit'),
]
