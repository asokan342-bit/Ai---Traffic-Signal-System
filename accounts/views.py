from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.core.mail import send_mail
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import OTP
from .utils import generate_otp

import json


def register_page(request):
    """Render the unified auth page in register mode."""
    return render(request, 'accounts/auth.html', {'tab': 'register'})


def register(request):
    """Handle registration via AJAX POST."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

        full_name = data.get('full_name', '').strip()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        country_code = data.get('country_code', '+91')
        mobile = data.get('mobile', '').strip()
        email_verified = data.get('email_verified', False)

        # Validations
        if not all([full_name, username, email, password]):
            return JsonResponse({'success': False, 'error': 'All fields are required', 'field': 'general'})

        if not email_verified:
            return JsonResponse({'success': False, 'error': 'Email must be verified before registration', 'field': 'email'})

        if User.objects.filter(username=username).exists():
            return JsonResponse({'success': False, 'error': 'Username is already taken', 'field': 'username'})

        if User.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'error': 'This email is already taken', 'field': 'email'})

        # Password validation
        if len(password) < 8:
            return JsonResponse({'success': False, 'error': 'Password must be at least 8 characters', 'field': 'password'})

        # Create user
        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        user.is_active = True
        user.save()

        # Save phone to UserProfile if exists
        try:
            from signal_app.models import UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.phone = f"{country_code}{mobile}"
            profile.save()
        except Exception:
            pass

        return JsonResponse({'success': True, 'message': 'Account created successfully'})

    return render(request, 'accounts/register.html')


def verify_otp(request):
    """Legacy OTP verification page (kept for backward compatibility)."""
    if request.method == 'POST':
        otp_input = request.POST.get('otp', '')
        username = request.session.get('username')

        try:
            user = User.objects.get(username=username)
            otp_obj = OTP.objects.get(user=user)

            if otp_obj.otp == otp_input:
                otp_obj.is_verified = True
                otp_obj.save()
                user.is_active = True
                user.save()
                messages.success(request, 'Account verified successfully')
                return redirect('login')
            else:
                messages.error(request, 'Invalid OTP')
        except (User.DoesNotExist, OTP.DoesNotExist):
            messages.error(request, 'Verification failed')

    return render(request, 'accounts/otp_verify.html')


def user_login(request):
    """Standard login view (form-based POST from auth.html)."""
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')

        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid credentials')

    return render(request, 'accounts/login.html')


# ============================================================
# API ENDPOINTS (AJAX)
# ============================================================

@require_GET
def check_username(request):
    """Check if a username is available."""
    username = request.GET.get('username', '').strip()
    if not username or len(username) < 3:
        return JsonResponse({'available': False, 'error': 'Username too short'})

    available = not User.objects.filter(username=username).exists()
    return JsonResponse({'available': available})


@require_GET
def check_email(request):
    """Check if an email is available."""
    email = request.GET.get('email', '').strip()
    if not email:
        return JsonResponse({'available': False, 'error': 'Email is required'})

    available = not User.objects.filter(email=email).exists()
    return JsonResponse({'available': available})


@require_POST
def send_email_otp(request):
    """Generate and send OTP to email."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

    email = data.get('email', '').strip()
    if not email:
        return JsonResponse({'success': False, 'error': 'Email is required'})

    otp = generate_otp()
    # Store OTP in session
    request.session['email_otp'] = otp
    request.session['email_otp_target'] = email

    # Send email via SMTP
    from django.conf import settings as django_settings

    html_message = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 30px; background: #0f172a; border-radius: 16px; border: 1px solid #6366f1;">
        <h2 style="color: #22d3ee; text-align: center; margin-bottom: 10px;">🚦 Smart Traffic AI</h2>
        <p style="color: #94a3b8; text-align: center; font-size: 14px;">Email Verification Code</p>
        <div style="background: #1e293b; border-radius: 12px; padding: 24px; text-align: center; margin: 24px 0;">
            <h1 style="color: #6366f1; font-size: 36px; letter-spacing: 8px; margin: 0;">{otp}</h1>
        </div>
        <p style="color: #94a3b8; text-align: center; font-size: 13px;">This code expires in 10 minutes. Do not share it with anyone.</p>
    </div>
    """

    try:
        from django.core.mail import EmailMultiAlternatives
        msg = EmailMultiAlternatives(
            subject='Smart Traffic AI – Email Verification Code',
            body=f'Your verification code is: {otp}\nThis code expires in 10 minutes.',
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send(fail_silently=False)
        print(f"[OTP] Email sent successfully to {email}, OTP: {otp}")
        return JsonResponse({'success': True, 'message': 'OTP sent to your email'})
    except Exception as e:
        print(f"[OTP ERROR] Failed to send email to {email}: {e}")
        print(f"[OTP FALLBACK] OTP for {email}: {otp}")
        # Still return success since OTP is stored in session
        # The user can check the Django console in dev mode
        return JsonResponse({
            'success': True,
            'message': 'OTP generated! Check your email (or Django terminal in dev mode)',
            'dev_note': f'If SMTP is not configured, check Django terminal. OTP: {otp}' if django_settings.DEBUG else None
        })


@require_POST
def verify_email_otp(request):
    """Verify the email OTP from session."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

    otp_input = data.get('otp', '').strip()
    stored_otp = request.session.get('email_otp', '')

    if not stored_otp:
        return JsonResponse({'success': False, 'error': 'No OTP found. Please request a new one.'})

    if otp_input == stored_otp:
        request.session['email_verified'] = True
        # Clear OTP
        del request.session['email_otp']
        return JsonResponse({'success': True, 'message': 'Email verified successfully'})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid OTP. Please try again.'})


@require_POST
def send_mobile_otp(request):
    """Generate and store mobile OTP (SMS provider placeholder)."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

    mobile = data.get('mobile', '').strip()
    country_code = data.get('country_code', '+91')

    if not mobile or len(mobile) < 10:
        return JsonResponse({'success': False, 'error': 'Valid mobile number is required'})

    otp = generate_otp()
    request.session['mobile_otp'] = otp
    request.session['mobile_otp_target'] = f"{country_code}{mobile}"

    from django.conf import settings as django_settings

    # TODO: Integrate SMS provider (Twilio / Fast2SMS)
    # For now, print to console and return in dev_note
    print(f"[OTP] Mobile OTP for {country_code}{mobile}: {otp}")

    return JsonResponse({
        'success': True,
        'message': 'OTP sent to mobile',
        'dev_note': f'SMS not configured yet. Your OTP is: {otp}' if django_settings.DEBUG else None
    })


@require_POST
def verify_mobile_otp(request):
    """Verify the mobile OTP from session."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

    otp_input = data.get('otp', '').strip()
    stored_otp = request.session.get('mobile_otp', '')

    if not stored_otp:
        return JsonResponse({'success': False, 'error': 'No OTP found. Please request a new one.'})

    if otp_input == stored_otp:
        request.session['mobile_verified'] = True
        del request.session['mobile_otp']
        return JsonResponse({'success': True, 'message': 'Mobile verified successfully'})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid OTP. Please try again.'})
