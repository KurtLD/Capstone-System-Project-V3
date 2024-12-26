from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.generic.edit import FormView
from django.views import View
from .forms import (
    CustomUserCreationForm, 
    AccountSettingsForm, 
    EmailAuthenticationForm, 
    LoginForm,
    OTPForm, 
    ForgotPasswordForm, 
    VerifyOTPForm, 
    ResetPasswordForm,

    # the following forms are used for the PreOral defense
    PreOral_EvaluationSectionForm, CriteriaForm, CriterionDescriptionForm, VerdictForm, CheckboxForm,

    # the following forms are used for the Mock defense
    Mock_EvaluationSectionForm, Mock_CriteriaForm, Mock_CriterionDescriptionForm, Mock_VerdictForm, Mock_CheckboxForm,

    # the following forms are used for the Mock defense
    Final_EvaluationSectionForm, Final_CriteriaForm, Final_CriterionDescriptionForm, Final_VerdictForm, Final_CheckboxForm,
)
from reco_app.models import Faculty, Expertise, Adviser
from .models import (
    Profile, 
    CustomUser, 
    Grade, 
    AuditTrail, 
    SchoolYear,

    # the follwing models are used for the PreOral
    PreOral_EvaluationSection, 
    PreOral_Criteria, 
    CriterionDescription, 
    Verdict, 
    Checkbox, 
    PreOral_Grade, 
    PreOral_Recos,

    # the following models are used for the Mock defense
    Mock_EvaluationSection, 
    Mock_Criteria, 
    MockCriterionDescription,
    Mock_Verdict, 
    Mock_Checkbox,
    Mock_Grade, 
    Mock_Recos, 

    # the following models are used for the Mock defense
    Final_EvaluationSection, 
    Final_Criteria, 
    FinalCriterionDescription,
    Final_Verdict, 
    Final_Checkbox,
    Final_Grade, 
    Final_Recos, 

    Notif,
    UserNotif
    )
from .utils import generate_otp, send_otp_email, send_reset_password_email
from django.core.mail import send_mail
from django.db.models import Q, Sum
from scheduler_app.models import Schedule, SchedulePOD, GroupInfoPOD, GroupInfoMD, ScheduleMD, GroupInfoFD, ScheduleFD
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import random
from datetime import datetime
from django.utils.text import slugify
from django.conf import settings
from django.contrib import messages
import json
from urllib.parse import urlencode
from django.urls import reverse
from django.utils.html import escape
from django.http import HttpResponseForbidden
from django.template.loader import render_to_string
import json 
from django.utils.html import escape
from django.contrib import messages
from urllib.parse import urlencode
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden
import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Case, When, Value, IntegerField, Subquery, OuterRef, Exists, BooleanField
from django.db import transaction
from datetime import datetime

# Custom decorator to check if the user is a superuser
# apply it to the views that accessible only to the superuser/admin
def superuser_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponse("You need to be logged in to access this page.", status=401)  # Custom message for unauthenticated users
        
        if not request.user.is_superuser:
            return HttpResponseForbidden("You are not authorized to access this page.")  # Message for authenticated but non-superusers
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view

# Custom decorator for regular users (authenticated but not superusers)
# apply it to the views that accessible only to the regular users(non admin)
def regular_user_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponse("You need to be logged in to access this file.", status=401)
        
        if request.user.is_superuser:
            return HttpResponseForbidden("Superusers are not authorized to access this file.")
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


def home_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('base')
            else:
                form.add_error(None, 'Invalid username or password')
    else:
        form = LoginForm()
    return render(request, '01_base.html', {'form': form})


def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp_email(email, otp):
    subject = 'Your OTP for Registration'
    message = f'Your OTP for registration is {otp}'
    email_from = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]
    send_mail(subject, message, email_from, recipient_list)

def send_reset_password_email(email, otp):
    subject = 'Your OTP for Password Reset'
    message = f'Your OTP to reset your password is {otp}. Please enter this code to proceed with resetting your password.'
    email_from = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]
    send_mail(subject, message, email_from, recipient_list)

    


def generate_username(first_name, last_name):
    username = f"{slugify(first_name)}_{slugify(last_name)}"
    if CustomUser.objects.filter(username=username).exists():
        # Add a random number to the username if it already exists
        username = f"{username}{random.randint(1000, 9999)}"
    return username

# SIGN-UP ORGINAL WITH OTP

def signup_view(request):
    if request.method == 'POST':
        if 'otp' in request.POST:
            otp_form = OTPForm(request.POST)
            if otp_form.is_valid():
                otp = otp_form.cleaned_data['otp']
                if otp == request.session.get('otp'):
                    user_data = request.session.get('user_data')
                    date_of_birth = datetime.fromisoformat(user_data['date_of_birth']).date()
                    username = generate_username(user_data['first_name'], user_data['last_name'])
                    user = CustomUser.objects.create_user(
                        username=username,
                        email=user_data['email'],
                        password=user_data['password'],
                        first_name=user_data['first_name'],
                        middle_name=user_data['middle_name'],
                        last_name=user_data['last_name'],
                        date_of_birth=date_of_birth,
                        address=user_data['address'],
                        years_of_teaching=user_data['years_of_teaching'],
                        has_master_degree=user_data['has_master_degree'],
                        is_active=True
                    )

                    faculty = Faculty.objects.create(
                        custom_user=user,
                        name=f"{user.first_name} {user.middle_name} {user.last_name}",
                        years_of_teaching=user.years_of_teaching,
                        has_master_degree=user.has_master_degree,
                        highest_degree=','.join(request.session.get('highest_degrees', [])),
                        is_active=True,
                    )

                    expertise_ids = request.session.get('expertise', [])
                    expertise_list = Expertise.objects.filter(id__in=expertise_ids)
                    faculty.expertise.set(expertise_list)

                    custom_expertise = request.session.get('new_expertise')
                    if custom_expertise:
                        expertise, created = Expertise.objects.get_or_create(name=custom_expertise)
                        faculty.expertise.add(expertise)

                    faculty.save()

                    login(request, user)
                    return redirect('login')
                else:
                    otp_form.add_error('otp', 'Invalid OTP')
                    return render(request, 'signup_otp_verification.html', {'otp_form': otp_form})
        else:
            form = CustomUserCreationForm(request.POST)
            if form.is_valid():
                user_data = {
                    'email': form.cleaned_data['email'],
                    'password': form.cleaned_data['password1'],
                    'first_name': form.cleaned_data['first_name'],
                    'middle_name': form.cleaned_data['middle_name'],
                    'last_name': form.cleaned_data['last_name'],
                    'date_of_birth': form.cleaned_data['date_of_birth'].isoformat(),
                    'address': form.cleaned_data['address'],
                    'years_of_teaching': form.cleaned_data['years_of_teaching'],
                    'has_master_degree': form.cleaned_data['has_master_degree'],
                }
                request.session['user_data'] = user_data
                request.session['highest_degrees'] = list(form.cleaned_data.get('highest_degrees', []))
                request.session['expertise'] = list(form.cleaned_data.get('expertise', []).values_list('id', flat=True))
                request.session['new_expertise'] = form.cleaned_data.get('new_expertise')

                otp = generate_otp()
                request.session['otp'] = otp
                send_otp_email(user_data['email'], otp)
                return render(request, 'signup_otp_verification.html', {'otp_form': OTPForm()})
    else:
        form = CustomUserCreationForm()
    return render(request, '03_signup.html', {'form': form})


 # FOR ADDING USER WITHOUT OTP VERIFICATION

# def signup_view(request):
#     if request.method == 'POST':
#         form = CustomUserCreationForm(request.POST)
#         if form.is_valid():
#             user_data = {
#                 'email': form.cleaned_data['email'],
#                 'password': form.cleaned_data['password1'],
#                 'first_name': form.cleaned_data['first_name'],
#                 'middle_name': form.cleaned_data['middle_name'],
#                 'last_name': form.cleaned_data['last_name'],
#                 'date_of_birth': form.cleaned_data['date_of_birth'].isoformat(),
#                 'address': form.cleaned_data['address'],
#                 'years_of_teaching': form.cleaned_data['years_of_teaching'],
#                 'has_master_degree': form.cleaned_data['has_master_degree'],
#             }
#             request.session['user_data'] = user_data
#             request.session['highest_degrees'] = list(form.cleaned_data.get('highest_degrees', []))
#             request.session['expertise'] = list(form.cleaned_data.get('expertise', []).values_list('id', flat=True))
#             request.session['new_expertise'] = form.cleaned_data.get('new_expertise')

#             # Directly create the user and faculty without OTP verification
#             date_of_birth = datetime.fromisoformat(user_data['date_of_birth']).date()
#             username = generate_username(user_data['first_name'], user_data['last_name'])
#             user = CustomUser.objects.create_user(
#                 username=username,
#                 email=user_data['email'],
#                 password=user_data['password'],
#                 first_name=user_data['first_name'],
#                 middle_name=user_data['middle_name'],
#                 last_name=user_data['last_name'],
#                 date_of_birth=date_of_birth,
#                 address=user_data['address'],
#                 years_of_teaching=user_data['years_of_teaching'],
#                 has_master_degree=user_data['has_master_degree'],
#                 is_active=True
#             )

#             faculty = Faculty.objects.create(
#                 custom_user=user,
#                 name=f"{user.first_name} {user.middle_name} {user.last_name}",
#                 years_of_teaching=user.years_of_teaching,
#                 has_master_degree=user.has_master_degree,
#                 highest_degree=','.join(request.session.get('highest_degrees', [])),
#                 is_active=True,
#             )

#             expertise_ids = request.session.get('expertise', [])
#             expertise_list = Expertise.objects.filter(id__in=expertise_ids)
#             faculty.expertise.set(expertise_list)

#             custom_expertise = request.session.get('new_expertise')
#             if custom_expertise:
#                 expertise, created = Expertise.objects.get_or_create(name=custom_expertise)
#                 faculty.expertise.add(expertise)

#             faculty.save()

#             login(request, user)
#             return redirect('login')
#     else:
#         form = CustomUserCreationForm()
#     return render(request, '03_signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = EmailAuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Record the login event with the current time
            action = 'Admin logged in' if user.is_superuser else 'User logged in'
            AuditTrail.objects.create(
                user=user,
                action=action,
                time=timezone.now(),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            if user.is_superuser:
                return redirect('admin_dashboard')
            else:
                return redirect('faculty_dashboard')
        else:
            form.add_error(None, 'Invalid email or password')
    else:
        form = EmailAuthenticationForm()
    return render(request, '01_base.html', {'form': form})

@login_required
def logout_view(request):
    # Record the logout event with the current time
    action = 'Admin logged out' if request.user.is_superuser else 'User logged out'
    AuditTrail.objects.create(
        user=request.user,
        action=action,
        time=timezone.now(),
        ip_address=request.META.get('REMOTE_ADDR')
    )
    logout(request)
    return redirect('login')

@login_required
@superuser_required
def admin_dashboard(request):
    # # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()

    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # faculty_count = Faculty.objects.filter(is_active=True).count()  # Count only active faculty
    # adviser_count = Adviser.objects.filter(school_year=current_school_year).count()
    # schedule_count = Schedule.objects.filter(school_year=current_school_year, has_been_rescheduled=False).count() 
    # schedulePOD_count = SchedulePOD.objects.filter(school_year=current_school_year, has_been_rescheduled=False).count()
    # scheduleMD_count = ScheduleMD.objects.filter(school_year=current_school_year, has_been_rescheduled=False).count()
    # scheduleFD_count = ScheduleFD.objects.filter(school_year=current_school_year, has_been_rescheduled=False).count()
    # disable_faculty_count = Faculty.objects.filter(is_active=False).count()
    # grade_count = PreOral_Grade.objects.filter(school_year=current_school_year).count()

    faculty_count = Faculty.objects.filter(is_active=True).count()  # Count only active faculty
    adviser_count = Adviser.objects.filter(school_year=selected_school_year).count()
    schedule_count = Schedule.objects.filter(school_year=selected_school_year, has_been_rescheduled=False).count() 
    schedulePOD_count = SchedulePOD.objects.filter(school_year=selected_school_year, has_been_rescheduled=False).count()
    scheduleMD_count = ScheduleMD.objects.filter(school_year=selected_school_year, has_been_rescheduled=False).count()
    scheduleFD_count = ScheduleFD.objects.filter(school_year=selected_school_year, has_been_rescheduled=False).count()
    disable_faculty_count = Faculty.objects.filter(is_active=False).count()
    grade_count = PreOral_Grade.objects.filter(school_year=selected_school_year).count()
    
    # Get all available school years
    school_years = SchoolYear.objects.all().order_by('start_year')
    if school_years.count() == 0:
        SchoolYear.create_new_school_year()
        school_years = SchoolYear.objects.all().order_by('start_year')
    
    context = {
        'faculty_count': faculty_count,
        'adviser_count': adviser_count,
        'schedule_count': schedule_count,
        'schedulePOD_count': schedulePOD_count,
        'scheduleMD_count': scheduleMD_count,
        'scheduleFD_count': scheduleFD_count,
        'disable_faculty_count': disable_faculty_count,
        'grade_count': grade_count,
        'school_years': school_years,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year
    }
    return render(request, 'users/admin_dashboard.html', context)

def school_year_selection(request):
    # Get all available school years
    school_years = SchoolYear.objects.all().order_by('start_year')

    # Handle POST request to change the active school year
    if request.method == "POST":
        selected_school_year_id = request.POST.get('school_year')
        print('selected_school_year_id: ', selected_school_year_id)
        next_page = request.POST.get('next', 'admin_dashboard')  # Default redirect to admin_dashboard if next is not provided

        if selected_school_year_id:
            # Get the selected school year
            selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)
            print('selected year: ', selected_school_year)

            # Get the current active school year
            current_active_school_year = SchoolYear.get_active_school_year()

            # Deactivate the current active school year if it exists
            if current_active_school_year and current_active_school_year != selected_school_year:
                current_active_school_year.is_active = False
                current_active_school_year.save()

            # Activate the selected school year
            selected_school_year.is_active = True
            selected_school_year.save()

            # Add audit trail entry for changing the school year
            AuditTrail.objects.create(
                user=request.user,
                action=f'Changed active school year to {selected_school_year}',
                time=timezone.now(),
                ip_address=request.META.get('REMOTE_ADDR')
            )

        elif 'add_new_school_year' in request.POST:
            # Create a new school year
            new_school_year = SchoolYear.create_new_school_year()
            
            # Update the session to reflect the new active school year
            request.session['selected_school_year_id'] = new_school_year.id

            # Add audit trail entry for adding a new school year
            AuditTrail.objects.create(
                user=request.user,
                action=f'Added new school year {new_school_year}',
                time=timezone.now(),
                ip_address=request.META.get('REMOTE_ADDR')
            )

            # creating a notif
            Notif.objects.create(
                created_by=request.user,
                notif=f"Added new school year {new_school_year}",
            )

        # Redirect to the specified page instead of always going back to the admin dashboard
        return redirect(next_page)

    # Get the current active school year to highlight in the dropdown
    active_school_year = SchoolYear.get_active_school_year()

    return render(request, 'users/school_year_selection.html', {
        'school_years': school_years,
        'current_school_year': active_school_year,
    })

def select_school_year(request):
    if request.method == "POST":
        selected_year_id = request.POST.get("school_year")
        try:
            selected_year = SchoolYear.objects.get(id=selected_year_id)
            request.session['selected_school_year_id'] = selected_year.id
            messages.success(request, f"School year changed to {selected_year}.")
        except SchoolYear.DoesNotExist:
            messages.error(request, "Selected school year does not exist.")
    return redirect(request.POST.get('next', 'faculty_dashboard'))




@login_required
def account_settings(request):
    school_years = SchoolYear.objects.all().order_by('start_year')
    # get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    if request.method == 'POST':
        form = AccountSettingsForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            
            # Log the action in AuditTrail
            full_name = request.user.get_full_name()
            if not full_name.strip():
                full_name = request.user.username
            AuditTrail.objects.create(
                user=request.user,
                action=f"Updated account settings",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors.as_json()})
    else:
        form = AccountSettingsForm(instance=request.user)
    
    if request.user.is_superuser:
        template_name = 'users/account_settings.html'
    else:
        template_name = 'faculty/faculty_account_settings.html'
    
    return render(request, template_name, 
    {'form': form,
    # 'current_school_year': current_school_year,
    'selected_school_year': selected_school_year,
    'last_school_year': last_school_year,
    'school_years': school_years
    })





class ForgotPasswordView(FormView):
    template_name = 'forgot_password.html'
    form_class = ForgotPasswordForm

    def form_valid(self, form):
        email = form.cleaned_data['email']
        try:
            user = get_user_model().objects.get(email=email)
            profile, created = Profile.objects.get_or_create(user=user)
            otp = generate_otp()
            profile.otp = otp
            profile.save()
            send_reset_password_email(email, otp)
            messages.success(self.request, 'Your OTP to reset your password has been sent to your email.')
            return redirect('verify_otp')
        except get_user_model().DoesNotExist:
            form.add_error('email', 'Email not found')
            return self.form_invalid(form)

class VerifyOTPView(FormView):
    template_name = 'verify_otp.html'
    form_class = VerifyOTPForm

    def form_valid(self, form):
        otp = form.cleaned_data['otp']
        try:
            user = get_user_model().objects.get(profile__otp=otp)
            self.request.session['user_id'] = user.id
            return redirect('reset_password')
        except get_user_model().DoesNotExist:
            form.add_error('otp', 'Invalid OTP')
            return self.form_invalid(form)


class ResetPasswordView(View):
    def get(self, request):
        form = ResetPasswordForm()
        return render(request, 'reset_password.html', {'form': form})

    def post(self, request):
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data['password']
            confirm_password = form.cleaned_data['confirm_password']
            
            if password != confirm_password:
                form.add_error('confirm_password', "Passwords do not match")
                return render(request, 'reset_password.html', {'form': form})

            user_id = request.session.get('user_id')
            user = get_user_model().objects.filter(id=user_id).first()
            if user:
                user.set_password(password)
                user.save()
                del request.session['user_id']
                return redirect('login')
        return render(request, 'reset_password.html', {'form': form})
    




# display the audit logs
def audit_logs(request):
    school_years = SchoolYear.objects.all().order_by('start_year')
    # get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # get the current school year
    # current_school_year = SchoolYear.get_active_school_year()

    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)
    
    # Fetch the CustomUser object associated with the logged-in user
    user_profile = get_object_or_404(CustomUser, id=request.user.id)

    # Ensure the user is logged in
    if request.user.is_authenticated:
        # Fetch the Faculty object associated with the CustomUser
        try:
            faculty_member = Faculty.objects.get(custom_user=user_profile)
            # Fetch records from the Adviser model where the faculty is an adviser
            adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year)
        except Faculty.DoesNotExist:
            faculty_member = None
            adviser_records = None

        # Filter audit logs based on user type
        if request.user.is_superuser:
            audit_logs = AuditTrail.objects.filter(user__is_superuser=True).order_by('-time')
        else:
            audit_logs = AuditTrail.objects.filter(user=request.user).order_by('-time')
        
        # Get the per_page parameter from the request
        per_page = request.GET.get('per_page', '10')
        
        # Handle 'all' case and invalid per_page values
        if per_page == 'all':
            paginator = Paginator(audit_logs, audit_logs.count())
        else:
            try:
                per_page = int(per_page)
            except ValueError:
                per_page = 10  # Default to 10 if conversion fails
            paginator = Paginator(audit_logs, per_page)
        
        # Get the current page number
        page_number = request.GET.get('page')
        try:
            page_obj = paginator.get_page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        
        # Render the appropriate template based on user type
        if request.user.is_superuser:
            return render(request, 'users/logs.html', 
            {'audit_logs': page_obj,
            # 'current_school_year': current_school_year,
            'selected_school_year': selected_school_year,
            'last_school_year': last_school_year,
            'school_years': school_years
            })
        else:
            return render(request, 'users/log.html', 
            {'audit_logs': page_obj,
            # 'current_school_year': current_school_year,
            'selected_school_year': selected_school_year,
            'last_school_year': last_school_year,
            'school_years': school_years,
            'adviser_records': adviser_records
            })
    else:
        return redirect('login')

# Ensure only superusers can access this view
def is_superuser(user):
    return user.is_superuser


def faculty_logs(request):
    school_years = SchoolYear.objects.all().order_by('start_year')
    # get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # get the current school year
    # current_school_year = SchoolYear.get_active_school_year()

    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # Fetch audit logs for all non-superuser users
    audit_logs = AuditTrail.objects.filter(user__is_superuser=False).order_by('-time')
    
    # Get the per_page parameter from the request
    per_page = request.GET.get('per_page', '10')
    
    # Handle 'all' case and invalid per_page values
    if per_page == 'all':
        paginator = Paginator(audit_logs, audit_logs.count())
    else:
        try:
            per_page = int(per_page)
        except ValueError:
            per_page = 10  # Default to 10 if conversion fails
        paginator = Paginator(audit_logs, per_page)
    
    # Get the current page number
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    return render(request, 'users/faculty_logs.html', 
    {'audit_logs': page_obj,
    # 'current_school_year': current_school_year,
    'selected_school_year': selected_school_year,
    'last_school_year': last_school_year,
    'school_years': school_years
    })


@login_required
def faculty_dashboard(request):
    # Get all available school years
    school_years = SchoolYear.objects.all().order_by('start_year')
    if school_years.count() == 0:
        SchoolYear.create_new_school_year()
        school_years = SchoolYear.objects.all().order_by('start_year')
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # current_school_year = SchoolYear.get_active_school_year()

    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # Fetch the CustomUser object associated with the logged-in user
    user_profile = get_object_or_404(CustomUser, id=request.user.id)

    # Fetch the Faculty object associated with the CustomUser
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)

    # Fetch records from the Adviser model where the faculty is an adviser
    adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=False, declined=False)
    adviser_records2 = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)
    

    # Fetch schedules, including rescheduled ones, but exclude original schedules that have been rescheduled
    schedules_th = Schedule.objects.filter(school_year=selected_school_year, has_been_rescheduled=False)
    schedules_pod = SchedulePOD.objects.filter(school_year=selected_school_year, has_been_rescheduled=False)
    schedules_md = ScheduleMD.objects.filter(school_year=selected_school_year, has_been_rescheduled=False)
    schedules_fd = ScheduleFD.objects.filter(school_year=selected_school_year, has_been_rescheduled=False)

    # Add day of the week to each schedule
    for schedule in schedules_th:
        schedule_date = datetime.strptime(schedule.date, '%B %d, %Y')  # Adjust format to match 'October 19, 2024'
        schedule.day_of_week = schedule_date.strftime('%A')
    
    for schedule in schedules_pod:
        schedule_date = datetime.strptime(schedule.date, '%B %d, %Y')  # Adjust format to match 'October 19, 2024'
        schedule.day_of_week = schedule_date.strftime('%A')
    
    for schedule in schedules_md:
        schedule_date = datetime.strptime(schedule.date, '%B %d, %Y')  # Adjust format to match 'October 19, 2024'
        schedule.day_of_week = schedule_date.strftime('%A')
    
    for schedule in schedules_fd:
        schedule_date = datetime.strptime(schedule.date, '%B %d, %Y')  # Adjust format to match 'October 19, 2024'
        schedule.day_of_week = schedule_date.strftime('%A')

    # Paginate each schedule type
    paginator_th = Paginator(schedules_th, 20)
    paginator_pod = Paginator(schedules_pod, 20)
    paginator_md = Paginator(schedules_md, 20)
    paginator_fd = Paginator(schedules_fd, 20)

    page_number_th = request.GET.get('page_th')
    page_number_pod = request.GET.get('page_pod')
    page_number_md = request.GET.get('page_md')
    page_number_fd = request.GET.get('page_fd')

    page_obj_th = paginator_th.get_page(page_number_th)
    page_obj_pod = paginator_pod.get_page(page_number_pod)
    page_obj_md = paginator_md.get_page(page_number_md)
    page_obj_fd = paginator_fd.get_page(page_number_fd)

    context = {
        'page_obj_th': page_obj_th,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
        'page_obj_pod': page_obj_pod,
        'page_obj_md': page_obj_md,
        'page_obj_fd': page_obj_fd,
        'adviser_records': adviser_records,
        'adviser_records2': adviser_records2
    }
    return render(request, 'faculty/view_all_schedules.html', context)



@login_required
def title_hearing_view(request):
    school_years = SchoolYear.objects.all().order_by('start_year')
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    user_profile = get_object_or_404(CustomUser, id=request.user.id)
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)

    # Fetch records from the Adviser model where the faculty is an adviser
    adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=False, declined=False)
    adviser_records2 = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)

    schedules_th = Schedule.objects.filter(
        Q(faculty1=faculty_member) |
        Q(faculty2=faculty_member) |
        Q(faculty3=faculty_member),
        school_year=selected_school_year
    )

    # Add day of the week to each schedule
    for schedule in schedules_th:
        schedule_date = datetime.strptime(schedule.date, '%B %d, %Y')  # Adjust format to match 'October 19, 2024'
        schedule.day_of_week = schedule_date.strftime('%A')

    paginator = Paginator(schedules_th, 5)  # Show 5 schedules per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'faculty/view_section/title_hearing.html', {
        'page_obj': page_obj,
        'last_school_year': last_school_year,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'school_years': school_years,
        'faculty_member': faculty_member,
        'adviser_records': adviser_records,
        'adviser_records2': adviser_records2
    })

@login_required
def pre_oral_defense_view(request):
    school_years = SchoolYear.objects.all().order_by('start_year')
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)
    print('current year: ', selected_school_year)
    user_profile = get_object_or_404(CustomUser, id=request.user.id)

    # Fetch the Faculty object associated with the CustomUser
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)

    # Fetch records from the Adviser model where the faculty is an adviser
    adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=False, declined=False)
    adviser_records2 = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)

    # Fetch schedules where the faculty is involved (as Panelist, Adviser, or Capstone Teacher)
    schedules_pod = SchedulePOD.objects.filter(
        Q(faculty1=faculty_member) |
        Q(faculty2=faculty_member) |
        Q(faculty3=faculty_member),
        school_year=selected_school_year
    )

    # Add day of the week to each schedule
    for schedule in schedules_pod:
        schedule_date = datetime.strptime(schedule.date, '%B %d, %Y')  # Adjust format to match 'October 19, 2024'
        schedule.day_of_week = schedule_date.strftime('%A')

    # Construct schedules_pod_status with each schedule and its grade existence status
    schedules_pod_status = []
    for schedule in schedules_pod:
        faculty1_exists = PreOral_Grade.objects.filter(
            faculty=schedule.faculty1,
            project_title=schedule.title,
            school_year=selected_school_year
        ).exists()

        faculty2_exists = PreOral_Grade.objects.filter(
            faculty=schedule.faculty2,
            project_title=schedule.title,
            school_year=selected_school_year
        ).exists()

        faculty3_exists = PreOral_Grade.objects.filter(
            faculty=schedule.faculty3,
            project_title=schedule.title,
            school_year=selected_school_year
        ).exists()

        # Determine if the current faculty member has graded
        current_faculty_graded = PreOral_Grade.objects.filter(
            faculty=faculty_member,
            project_title=schedule.title,
            school_year=selected_school_year
        ).exists()

        recent_recommendation = PreOral_Recos.objects.filter(
            project_title=schedule.title,
            school_year=selected_school_year
        ).exists()

        schedules_pod_status.append((schedule, current_faculty_graded, recent_recommendation))

    paginator = Paginator(schedules_pod_status, 5)  # Show 5 schedules per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
        'adviser_records': adviser_records,
        'adviser_records2': adviser_records2
    }

    return render(request, 'faculty/view_section/pre_oral_defense.html', context)

@login_required
def mock_defense_view(request):
    school_years = SchoolYear.objects.all().order_by('start_year')
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # current_school_year = SchoolYear.get_active_school_year()
    # print('current year: ', current_school_year)
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # Fetch the CustomUser object associated with the logged-in user
    user_profile = get_object_or_404(CustomUser, id=request.user.id)

    # Fetch the Faculty object associated with the CustomUser
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)

    # Fetch records from the Adviser model where the faculty is an adviser
    adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=False, declined=False)
    adviser_records2 = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)

    # Fetch schedules where the faculty is involved (as Panelist, Adviser, or Capstone Teacher)
    schedules_md = ScheduleMD.objects.filter(
        Q(faculty1=faculty_member) |
        Q(faculty2=faculty_member) |
        Q(faculty3=faculty_member),
        school_year=selected_school_year
    )

    # Add day of the week to each schedule
    for schedule in schedules_md:
        schedule_date = datetime.strptime(schedule.date, '%B %d, %Y')  # Adjust format to match 'October 19, 2024'
        schedule.day_of_week = schedule_date.strftime('%A')

    # Construct schedules_md_status with each schedule and its grade existence status
    schedules_md_status = []
    for schedule in schedules_md:
        faculty1_exists = Mock_Grade.objects.filter(
            faculty=schedule.faculty1,
            project_title=schedule.title,
            school_year=selected_school_year
        ).exists()

        faculty2_exists = Mock_Grade.objects.filter(
            faculty=schedule.faculty2,
            project_title=schedule.title,
            school_year=selected_school_year
        ).exists()

        faculty3_exists = Mock_Grade.objects.filter(
            faculty=schedule.faculty3,
            project_title=schedule.title,
            school_year=selected_school_year
        ).exists()

        # Determine if the current faculty member has graded
        current_faculty_graded = Mock_Grade.objects.filter(
            faculty=faculty_member,
            project_title=schedule.title,
            school_year=selected_school_year
        ).exists()

        recent_recommendation = Mock_Recos.objects.filter(
            project_title=schedule.title,
            school_year=selected_school_year
        ).exists()

        schedules_md_status.append((schedule, current_faculty_graded, recent_recommendation))

    paginator = Paginator(schedules_md_status, 5)  # Show 5 schedules per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
        'adviser_records': adviser_records,
        'adviser_records2': adviser_records2
    }

    return render(request, 'faculty/view_section/mock_defense.html', context)

@login_required
def final_defense_view(request):
    school_years = SchoolYear.objects.all().order_by('start_year')
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # current_school_year = SchoolYear.get_active_school_year()
    # print('current year: ', current_school_year)
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # Fetch the CustomUser object associated with the logged-in user
    user_profile = get_object_or_404(CustomUser, id=request.user.id)

    # Fetch the Faculty object associated with the CustomUser
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)

    # Fetch records from the Adviser model where the faculty is an adviser
    adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=False, declined=False)
    adviser_records2 = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)

    # Fetch schedules where the faculty is involved (as Panelist, Adviser, or Capstone Teacher)
    schedules_fd = ScheduleFD.objects.filter(
        Q(faculty1=faculty_member) |
        Q(faculty2=faculty_member) |
        Q(faculty3=faculty_member),
        school_year=selected_school_year
    )

    # Add day of the week to each schedule
    for schedule in schedules_fd:
        schedule_date = datetime.strptime(schedule.date, '%B %d, %Y')  # Adjust format to match 'October 19, 2024'
        schedule.day_of_week = schedule_date.strftime('%A')

    # Construct schedules_fd_status with each schedule and its grade existence status
    schedules_fd_status = []
    for schedule in schedules_fd:
        faculty1_exists = Final_Grade.objects.filter(
            faculty=schedule.faculty1,
            project_title=schedule.title,
            school_year=selected_school_year
        ).exists()

        faculty2_exists = Final_Grade.objects.filter(
            faculty=schedule.faculty2,
            project_title=schedule.title,
            school_year=selected_school_year
        ).exists()

        faculty3_exists = Final_Grade.objects.filter(
            faculty=schedule.faculty3,
            project_title=schedule.title,
            school_year=selected_school_year
        ).exists()

        # Determine if the current faculty member has graded
        current_faculty_graded = Final_Grade.objects.filter(
            faculty=faculty_member,
            project_title=schedule.title,
            school_year=selected_school_year
        ).exists()

        recent_recommendation = Final_Recos.objects.filter(
            project_title=schedule.title,
            school_year=selected_school_year
        ).exists()

        schedules_fd_status.append((schedule, current_faculty_graded, recent_recommendation))

    paginator = Paginator(schedules_fd_status, 5)  # Show 5 schedules per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
        'adviser_records': adviser_records,
        'adviser_records2': adviser_records2
    }

    return render(request, 'faculty/view_section/final_defense.html', context)

@login_required
def adviser_records_view(request):
    school_years = SchoolYear.objects.all().order_by('start_year')
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)
    
    # Get all available school years
    school_years = SchoolYear.objects.all().order_by('start_year')
    if school_years.count() == 0:
        SchoolYear.create_new_school_year()
        school_years = SchoolYear.objects.all().order_by('start_year')

    # Fetch the CustomUser object associated with the logged-in user
    user_profile = get_object_or_404(CustomUser, id=request.user.id)

    # Fetch the Faculty object associated with the CustomUser
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)

    # Fetch records from the Adviser model where the faculty is an adviser
    adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=False, declined=False)
    adviser_records2 = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)

    paginator = Paginator(adviser_records2, 5)  # Show 5 records per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
        'adviser_records': adviser_records,
        'adviser_records2': adviser_records2
    }

    return render(request, 'faculty/view_section/pre_oral_adviser_records.html', context)

@login_required
def mock_adviser_records_view(request):
    school_years = SchoolYear.objects.all().order_by('start_year')
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # Get all available school years
    if school_years.count() == 0:
        SchoolYear.create_new_school_year()
        school_years = SchoolYear.objects.all().order_by('start_year')

    # Fetch the CustomUser object associated with the logged-in user
    user_profile = get_object_or_404(CustomUser, id=request.user.id)

    # Fetch the Faculty object associated with the CustomUser
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)

    # Fetch records from the Adviser model where the faculty is an adviser
    adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=False, declined=False)
    adviser_records2 = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)

    paginator = Paginator(adviser_records, 5)  # Show 5 records per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
        'adviser_records': adviser_records,
        'adviser_records2': adviser_records2
    }

    return render(request, 'faculty/view_section/mock_adviser_records.html', context)

@login_required
def final_adviser_records_view(request):
    school_years = SchoolYear.objects.all().order_by('start_year')
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)
    
    # Get all available school years
    school_years = SchoolYear.objects.all().order_by('start_year')
    if school_years.count() == 0:
        SchoolYear.create_new_school_year()
        school_years = SchoolYear.objects.all().order_by('start_year')

    # Fetch the CustomUser object associated with the logged-in user
    user_profile = get_object_or_404(CustomUser, id=request.user.id)

    # Fetch the Faculty object associated with the CustomUser
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)

    # Fetch records from the Adviser model where the faculty is an adviser
    adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=False, declined=False)
    adviser_records2 = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)

    paginator = Paginator(adviser_records, 5)  # Show 5 records per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
        'adviser_records': adviser_records,
        'adviser_records2': adviser_records2
    }

    return render(request, 'faculty/view_section/final_adviser_records.html', context)

    
@login_required
def pre_oral_class_record(request):
    # Get the last and current school year
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)
    
    # Get all available school years
    school_years = SchoolYear.objects.all().order_by('start_year')
    if school_years.count() == 0:
        SchoolYear.create_new_school_year()
        school_years = SchoolYear.objects.all().order_by('start_year')

    # Fetch the CustomUser object associated with the logged-in user
    user_profile = get_object_or_404(CustomUser, id=request.user.id)

    # Fetch the Faculty object associated with the CustomUser
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)

    # Fetch records from the Adviser model where the faculty is an adviser
    adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=False, declined=False)
    adviser_records2 = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)

    # Subquery to count graded groups for each GroupInfoPOD
    graded_groups = PreOral_Grade.objects.filter(project_title=OuterRef('title'), school_year=selected_school_year)
    graded_group = PreOral_Grade.objects.filter( school_year=selected_school_year)
    graded_count = graded_groups.values('project_title').annotate(graded_count=Count('*')).values('graded_count')
    

    # Annotate each GroupInfoPOD with grading status
    class_records = GroupInfoPOD.objects.filter(
        capstone_teacher=faculty_member, 
        school_year=selected_school_year
    ).annotate(
        is_graded=Exists(graded_groups),
        graded_count=Subquery(graded_count, output_field=IntegerField())
    ).annotate(
        is_fully_graded=Case(
            When(graded_count=3, then=1),  # Fully graded
            When(graded_count__lt=3, then=0),  # Incomplete
            default=0,
            output_field=IntegerField(),
        )
    ).order_by('-is_fully_graded', '-is_graded')
    print(graded_group)

    # Paginate the class records, showing 5 records per page
    paginator = Paginator(class_records, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'faculty/view_section/pre_oral_class_records.html', {
        'page_obj': page_obj,
        'current_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
        'adviser_records': adviser_records,
        'adviser_records2': adviser_records2
    })

@login_required
def mock_class_record(request):
    # Get the last and current school year
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)
    
    # Get all available school years
    school_years = SchoolYear.objects.all().order_by('start_year')
    if school_years.count() == 0:
        SchoolYear.create_new_school_year()
        school_years = SchoolYear.objects.all().order_by('start_year')

    # Fetch the CustomUser object associated with the logged-in user
    user_profile = get_object_or_404(CustomUser, id=request.user.id)

    # Fetch the Faculty object associated with the CustomUser
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)

    # Fetch records from the Adviser model where the faculty is an adviser
    adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=False, declined=False)
    adviser_records2 = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)

    # Subquery to count graded groups for each GroupInfoPOD
    graded_groups = Mock_Grade.objects.filter(project_title=OuterRef('title'), school_year=selected_school_year)
    graded_count = graded_groups.values('project_title').annotate(graded_count=Count('*')).values('graded_count')

    # Annotate each GroupInfoPOD with grading status
    class_records = GroupInfoMD.objects.filter(
        capstone_teacher=faculty_member, 
        school_year=selected_school_year
    ).annotate(
        is_graded=Exists(graded_groups),
        graded_count=Subquery(graded_count, output_field=IntegerField())
    ).annotate(
        is_fully_graded=Case(
            When(graded_count=3, then=1),  # Fully graded
            When(graded_count__lt=3, then=0),  # Incomplete
            default=0,
            output_field=IntegerField(),
        )
    ).order_by('-is_fully_graded', '-is_graded')

    # Paginate the class records, showing 5 records per page
    paginator = Paginator(class_records, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'faculty/view_section/mock_class_records.html', {
        'page_obj': page_obj,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
        'adviser_records': adviser_records,
        'adviser_records2': adviser_records2
    })

@login_required
def final_class_record(request):
    # Get the last and current school year
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)
    
    # Get all available school years
    school_years = SchoolYear.objects.all().order_by('start_year')
    if school_years.count() == 0:
        SchoolYear.create_new_school_year()
        school_years = SchoolYear.objects.all().order_by('start_year')

    # Fetch the CustomUser object associated with the logged-in user
    user_profile = get_object_or_404(CustomUser, id=request.user.id)

    # Fetch the Faculty object associated with the CustomUser
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)

    # Fetch records from the Adviser model where the faculty is an adviser
    adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=False, declined=False)
    adviser_records2 = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)

    # Subquery to count graded groups for each GroupInfoPOD
    graded_groups = Final_Grade.objects.filter(project_title=OuterRef('title'), school_year=selected_school_year)
    graded_count = graded_groups.values('project_title').annotate(graded_count=Count('*')).values('graded_count')

    # Annotate each GroupInfoPOD with grading status
    class_records = GroupInfoFD.objects.filter(
        capstone_teacher=faculty_member, 
        school_year=selected_school_year
    ).annotate(
        is_graded=Exists(graded_groups),
        graded_count=Subquery(graded_count, output_field=IntegerField())
    ).annotate(
        is_fully_graded=Case(
            When(graded_count=3, then=1),  # Fully graded
            When(graded_count__lt=3, then=0),  # Incomplete
            default=0,
            output_field=IntegerField(),
        )
    ).order_by('-is_fully_graded', '-is_graded')

    # Paginate the class records, showing 5 records per page
    paginator = Paginator(class_records, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'faculty/view_section/final_class_records.html', {
        'page_obj': page_obj,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
        'adviser_records': adviser_records,
        'adviser_records2': adviser_records2
    })


# the following functions are used for the pre oral evaluation
# functions for the adding, updating and deleting sections
@csrf_exempt  # Use CSRF exempt for AJAX requests
@superuser_required
def add_section(request):
    if request.method == 'POST':
        form = PreOral_EvaluationSectionForm(request.POST)
        if form.is_valid():
            # Create the section
            section_name = form.cleaned_data['name']
            active_school_year = SchoolYear.get_active_school_year()

            selected_school_year_id = request.session.get('selected_school_year_id')
            # get the last school year added to the db
            last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

            # Get the selected school year from session or fallback to the active school year
            selected_school_year = ''
            if not selected_school_year_id:
                selected_school_year = last_school_year
                request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
            else:
                # Retrieve the selected school year based on the session
                selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

            if selected_school_year:
                if PreOral_EvaluationSection.objects.filter(name=section_name, school_year=selected_school_year).exists():
                    return JsonResponse({
                        'status': 'error',
                        'message': 'A section with this name already exists for the active school year.'
                    })

                section = form.save(commit=False)
                section.school_year = selected_school_year
                section.save()

                # Add audit trail entry
                AuditTrail.objects.create(
                    user=request.user,
                    action=f'Create a new PreOral Rubric: {section_name}',
                    time=timezone.now(),
                    ip_address=request.META.get('REMOTE_ADDR')
                )

                # Handle subcriteria creation
                subcriteria_count = 0
                while True:
                    criteria_name = request.POST.get(f'criteria_name_{subcriteria_count + 1}')
                    criteria_percentage = request.POST.get(f'criteria_percentage_{subcriteria_count + 1}')
                    criteria_description = request.POST.get(f'criteria_description_{subcriteria_count + 1}')

                    if criteria_name and criteria_percentage:
                        # Create subcriteria
                        criteria = PreOral_Criteria.objects.create(
                            section=section,
                            name=criteria_name,
                            percentage=criteria_percentage,
                            school_year=selected_school_year
                        )

                        # Create description
                        if criteria_description:
                            CriterionDescription.objects.create(
                                criterion=criteria,
                                text=criteria_description,
                                school_year=selected_school_year
                            )

                        subcriteria_count += 1
                        # Add audit trail entry
                        AuditTrail.objects.create(
                            user=request.user,
                            action=f'Add subcriteria: {criteria_name} to PreOral Rubric: {section_name}',
                            time=timezone.now(),
                            ip_address=request.META.get('REMOTE_ADDR')
                        )
                    else:
                        break

                return JsonResponse({'status': 'success', 'section_id': section.id, 'name': section.name})

            else:
                return JsonResponse({'status': 'error', 'message': 'No active school year.'})

        return JsonResponse({'status': 'error', 'message': 'Invalid form submission.'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


@csrf_exempt
@superuser_required
def get_section_details(request, section_id):
    try:
        section = PreOral_EvaluationSection.objects.get(id=section_id)
        subcriteria = PreOral_Criteria.objects.filter(section=section).values('name', 'percentage', 'descriptions__text')

        # Prepare the response with subcriteria data
        subcriteria_data = []
        for criterion in subcriteria:
            description = criterion.get('descriptions__text', "")
            subcriteria_data.append({
                'name': criterion['name'],
                'percentage': criterion['percentage'],
                'description': description
            })

        return JsonResponse({'status': 'success', 'name': section.name, 'subcriteria': subcriteria_data})

    except PreOral_EvaluationSection.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Section not found.'})

@csrf_exempt
@superuser_required
def edit_section(request, section_id):
    if request.method == 'POST':
        # section_id = request.POST.get('section_id')
        # print('id: ', section_id)
        try:
            section = get_object_or_404(PreOral_EvaluationSection, pk=section_id)
            form = PreOral_EvaluationSectionForm(request.POST, instance=section)

            if form.is_valid():
                section_name = form.cleaned_data['name']
                section.name = section_name
                section.save()

                # Add audit trail entry
                AuditTrail.objects.create(
                    user=request.user,
                    action=f'Update a PreOral Rubric: {section_name} with ID {section_id}',
                    time=timezone.now(),
                    ip_address=request.META.get('REMOTE_ADDR')
                )

                # Update subcriteria
                PreOral_Criteria.objects.filter(section=section).delete()  # Remove all subcriteria first
                subcriteria_count = 0

                while True:
                    criteria_name = request.POST.get(f'criteria_name_{subcriteria_count + 1}')
                    criteria_percentage = request.POST.get(f'criteria_percentage_{subcriteria_count + 1}')
                    criteria_description = request.POST.get(f'criteria_description_{subcriteria_count + 1}')

                    if criteria_name and criteria_percentage:
                        # Recreate subcriteria
                        criteria = PreOral_Criteria.objects.create(
                            section=section,
                            name=criteria_name,
                            percentage=criteria_percentage,
                            school_year=section.school_year
                        )

                        # Recreate description
                        if criteria_description:
                            CriterionDescription.objects.create(
                                criterion=criteria,
                                text=criteria_description,
                                school_year=section.school_year
                            )

                        subcriteria_count += 1
                        # Add audit trail entry
                        AuditTrail.objects.create(
                            user=request.user,
                            action=f'Updtae a subcriteria {criteria_name} for PreOral Rubric: {section_name}',
                            time=timezone.now(),
                            ip_address=request.META.get('REMOTE_ADDR')
                        )
                    else:
                        break

                return JsonResponse({'status': 'success'})

            return JsonResponse({'status': 'error', 'message': 'Invalid form submission.'})
        
        except PreOral_EvaluationSection.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Section not found.'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


@csrf_exempt
@superuser_required
def delete_section(request, section_id):
    section = get_object_or_404(PreOral_EvaluationSection, pk=section_id)
    section_name = section.name
    section.delete()
    # Add audit trail entry
    AuditTrail.objects.create(
        user=request.user,
        action=f'Delete a PreOral Rubric: {section_name} with ID {section_id}',
        time=timezone.now(),
        ip_address=request.META.get('REMOTE_ADDR')
    )
    return JsonResponse({'status': 'success'})


@csrf_exempt
@superuser_required
def add_criteria(request, section_id):
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    section = get_object_or_404(PreOral_EvaluationSection, pk=section_id)
    if request.method == 'POST':
        form = CriteriaForm(request.POST)
        if form.is_valid():
            criteria = form.save(commit=False)
            criteria.section = section
            criteria.school_year = selected_school_year
            criteria.save()
            return JsonResponse({'status': 'success', 'criteria_id': criteria.id, 'name': criteria.name})
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})



@csrf_exempt
@superuser_required
def edit_criteria(request, criterion_id):
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    criterion = get_object_or_404(PreOral_Criteria, pk=criterion_id)
    if request.method == 'POST':
        form = CriteriaForm(request.POST, instance=criterion)
        if form.is_valid():
            form.school_year = selected_school_year
            form.save()
            return JsonResponse({'status': 'success', 'name': criterion.name})
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})



@csrf_exempt
@superuser_required
def delete_criteria(request, criterion_id):
    criterion = get_object_or_404(PreOral_Criteria, pk=criterion_id)
    criterion.delete()
    return JsonResponse({'status': 'success'})



@csrf_exempt
@superuser_required
def add_criteria_description(request, criterion_id):
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    criterion = get_object_or_404(PreOral_Criteria, pk=criterion_id)
    if request.method == 'POST':
        form = CriterionDescriptionForm(request.POST)
        if form.is_valid():
            description = form.save(commit=False)
            description.criterion = criterion
            description.school_year = selected_school_year
            description.save()
            return JsonResponse({'status': 'success', 'description_id': description.id, 'text': description.text})
        return JsonResponse({'status': 'error', 'errors': form.errors})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})



@csrf_exempt
@superuser_required
def edit_criteria_description(request, description_id):
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    description = get_object_or_404(CriterionDescription, pk=description_id)
    if request.method == 'POST':
        form = CriterionDescriptionForm(request.POST, instance=description)
        if form.is_valid():
            form.school_year = selected_school_year
            form.save()
            return JsonResponse({'status': 'success', 'text': description.text})
        return JsonResponse({'status': 'error', 'errors': form.errors})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})



@csrf_exempt
@superuser_required
def delete_criteria_description(request, description_id):
    description = get_object_or_404(CriterionDescription, pk=description_id)
    description.delete()
    return JsonResponse({'status': 'success'})



@csrf_exempt
@superuser_required
def add_verdict(request):
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    if request.method == 'POST':
        # Initialize forms with POST data
        verdict_form = VerdictForm(request.POST)
        checkbox_form = CheckboxForm(request.POST)
        
        # Debug print statements
        print('POST data received:', request.POST)
        
        # Validate the verdict form
        if verdict_form.is_valid():
            verdict = verdict_form.save(commit=False)
            verdict.school_year = selected_school_year
            verdict.save()
            # Add audit trail entry
            AuditTrail.objects.create(
                user=request.user,
                action=f'Create a new PreOral Verdict: {verdict.name}',
                time=timezone.now(),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            # Now handle the checkboxes
            if checkbox_form.is_valid():
                try:
                    checkbox_form.save_checkboxes(verdict, school_year=selected_school_year)
                    # Return success response if everything goes well
                    return JsonResponse({
                        'status': 'success',
                        'verdict_id': verdict.id,
                        'name': verdict.name
                    })
                except Exception as e:
                    # If there's an exception saving the checkboxes, print it
                    print("Error saving checkboxes:", e)
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Failed to save checkboxes.',
                        'verdict_id': verdict.id,
                        'errors': str(e)
                    })
            else:
                # If the checkbox form is invalid, return the errors
                print('Checkbox Form Errors:', checkbox_form.errors)
                return JsonResponse({
                    'status': 'error',
                    'message': 'Checkbox form is invalid.',
                    'verdict_id': verdict.id,  # Optionally provide the saved verdict ID
                    'checkbox_errors': checkbox_form.errors
                })
        else:
            # If the verdict form is invalid, return errors
            print('Verdict Form Errors:', verdict_form.errors)
            return JsonResponse({
                'status': 'error',
                'errors': {
                    'verdict_errors': verdict_form.errors
                }
            })

    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method.'
    })



@superuser_required
def edit_verdict(request, verdict_id):
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # Retrieve the verdict object
    verdict = get_object_or_404(Verdict, pk=verdict_id)

    if request.method == 'POST':
        # Handle form submission
        form = VerdictForm(request.POST, instance=verdict)

        if form.is_valid():
            form.school_year = selected_school_year
            form.save()  # Save the Verdict form first
            verdict.checkboxes.filter(school_year=selected_school_year).delete()

            # Handle dynamic checkboxes
            index = 0
            while True:
                label = request.POST.get(f'checkboxes[{index}][label]')
                if label is None:
                    break
                is_checked = request.POST.get(f'checkboxes[{index}][is_checked]', False) == 'on'
                
                # Create new checkbox or update if ID exists
                Checkbox.objects.create(
                    verdict=verdict,
                    label=label,
                    is_checked=is_checked,
                    school_year=selected_school_year
                )
                index += 1

                
            # Add audit trail entry
            AuditTrail.objects.create(
                user=request.user,
                action=f'Update a PreOral Verdict: {verdict.name} with ID {verdict_id}',
                time=timezone.now(),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return JsonResponse({'success': True, 'message': 'Verdict updated successfully!'})

        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    # For GET request, provide the form and existing checkboxes
    checkbox_data = list(verdict.checkboxes.values('id', 'label', 'is_checked'))
    checkbox_data_json = json.dumps(checkbox_data)

    return JsonResponse({
        'form': VerdictForm(instance=verdict).as_p(),
        'checkbox_data': checkbox_data_json,
        'csrf_token': request.META.get('CSRF_COOKIE'),  # Send CSRF token
    })



@csrf_exempt
@superuser_required
def delete_verdict(request, verdict_id):
    verdict = get_object_or_404(Verdict, pk=verdict_id)
    verdict.delete()
    # Add audit trail entry
    AuditTrail.objects.create(
        user=request.user,
        action=f'Delete a PreOral Verdict: {verdict.name}, with ID {verdict_id}',
        time=timezone.now(),
        ip_address=request.META.get('REMOTE_ADDR')
    )
    return JsonResponse({'status': 'success'})

# functions for the viewing of the sections and criteria
@superuser_required #use to prevent access from not admin users 
def view_section(request):
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)
    
    # Get all available school years
    school_years = SchoolYear.objects.all().order_by('start_year')
    if school_years.count() == 0:
        SchoolYear.create_new_school_year()
        school_years = SchoolYear.objects.all().order_by('start_year')

    sy_count = school_years.count()

    # Check for the conflict query parameter
    empty_str = request.GET.get('empty')  # Should return True if 'conflict' param is 'True'
    message = request.GET.get('message')
    empty = empty_str.lower() == 'true' if empty_str else False #variable to hold a bolean value

    # Fetch all sections and prefetch related Mock_Criteria and their related MockCriterionDescription (mdescriptions)
    sections = PreOral_EvaluationSection.objects.filter(school_year=selected_school_year).prefetch_related('criteria__descriptions')
    verdicts = Verdict.objects.prefetch_related('checkboxes').filter(school_year=selected_school_year)
    description_count = CriterionDescription.objects.filter(school_year=selected_school_year).count()
    return render(request, 'admin/pre_oral/PreOral_Evaluation/view_section.html', {
        'sections': sections, 
        'verdicts': verdicts,
        'school_years': school_years,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'sy_count': sy_count,
        'empty': empty,
        'message': message,
        'description_count': description_count
        })


@superuser_required
def view_criteria(request, criterion_id):
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    criterion = get_object_or_404(PreOral_Criteria, pk=criterion_id)
    descriptions = CriterionDescription.objects.filter(criterion=criterion, school_year = selected_school_year)
    return render(request, 'admin/mock/Mock_Evaluation/mock_view_criteria.html', {'criterion': criterion, 'descriptions': descriptions})

@superuser_required
def view_criteria(request, criterion_id):
    criterion = get_object_or_404(PreOral_Criteria, pk=criterion_id)
    descriptions = CriterionDescription.objects.filter(criterion=criterion)
    return render(request, 'admin/pre_oral/PreOral_Evaluation/view_criteria.html', {'criterion': criterion, 'descriptions': descriptions})

# function to redirect to the preoral evaluation form
@login_required
def input_grade(request, schedule_id):
    school_years = SchoolYear.objects.all().order_by('start_year')
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    schedule = get_object_or_404(SchedulePOD, id=schedule_id)
    user_profile = get_object_or_404(CustomUser, id=request.user.id)
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)
    # Fetch records from the Adviser model where the faculty is an adviser
    adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=False, declined=False)
    adviser_records2 = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)
    is_lead_panel = (schedule.faculty1 == faculty_member)

    # Fetch all criteria and verdicts from the database
    criteria_list = PreOral_EvaluationSection.objects.filter(school_year=selected_school_year).annotate(total_criteria_percentage=Sum('criteria__percentage'))
    criteria_percentage = PreOral_Criteria.objects.filter(school_year=selected_school_year)
    verdicts = Verdict.objects.filter(school_year=selected_school_year)
    sections = PreOral_EvaluationSection.objects.prefetch_related('criteria__descriptions').filter(school_year=selected_school_year)

    # Fetch group members from the schedule
    group_members = [schedule.group.member1, schedule.group.member2, schedule.group.member3]
    
    # total_criteria_percentage = PreOral_EvaluationSection.objects.annotate(total_percentage=Sum('criteria__percentage'))

    
    total_percentage = sum(criteria.percentage for criteria in criteria_percentage) 

    # Retrieve all PreOral_Grade objects with the given project title
    grades = PreOral_Grade.objects.filter(project_title=schedule.title, school_year=selected_school_year)
    
    # Initialize a dictionary to hold aggregated summary data
    summary_totals = {}
    
    for grade_by_panel in grades:
        # Decode grades data from JSON
        summary_grades_data = grade_by_panel.get_grades_data()
        print(f"Summary points from grade_by_panel: {grade_by_panel} {summary_grades_data}")
        
        # Aggregate data by section name
        for section_name, section_grades in summary_grades_data.items():
            if section_name not in summary_totals:
                # Initialize totals for new sections
                summary_totals[section_name] = {'total': 0, 'count': 0}
            
            if isinstance(section_grades, dict):
                # Sum values for each section
                total = sum(section_grades.values())
                summary_totals[section_name]['total'] += total
                summary_totals[section_name]['count'] += 1
            elif isinstance(section_grades, list):
                # Average values for lists
                try:
                    average = sum(section_grades) / len(section_grades)
                except ZeroDivisionError:
                    average = 0
                summary_totals[section_name]['total'] += average
                summary_totals[section_name]['count'] += 1
            else:
                print(f"Unexpected data format for section: {section_name}, data: {section_grades}")
    
    # Finalize totals by averaging over the count
    # for section_name, data in summary_totals.items():
    #     if data['count'] > 0:
    #         summary_totals[section_name] = data['total'] / 3 #data['count'] 
            
    #     else:
    #         summary_totals[section_name] = 0
    
    # Finalize totals by averaging over the count
    for section_name, data in summary_totals.items():
        if "Oral Presentation" in section_name or "Individual Grade" in section_name:
            # Divide by 3 for specific sections
            if data['count'] > 0:
                summary_totals[section_name] = data['total'] / 3
                summary_totals[section_name] = summary_totals[section_name] / 3
            else:
                summary_totals[section_name] = 0
        else:
            # For other sections, just average over the count
            if data['count'] > 0:
                summary_totals[section_name] = data['total'] / 3 #data['count']
            else:
                summary_totals[section_name] = 0
            
    total_earned_points = sum(summary_totals.values())
    print('summary total: ', summary_totals.values())
    print(f"Final Summary Totals: {total_earned_points}")

    # Determine the verdict based on total earned points
    records = grades.count()
    if records < 3:
        selected_verdict = "Verdict is not available since not all of the panels submit the evaluation!"
    else:
        for verdict in verdicts:
            if total_earned_points <= verdict.percentage:
                selected_verdict = verdict
                
    print(f"verdict: {selected_verdict}")

    context = {
        'schedule': schedule,
        'faculty_member': faculty_member,
        'is_lead_panel': is_lead_panel,
        'schedule_id': schedule_id,
        'criteria_list': criteria_list,
        'verdicts': verdicts,
        'group_members': group_members,
        'total_percentage': total_percentage,
        'summary_totals': summary_totals,
        'total_earned_points': total_earned_points,
        'selected_verdict': selected_verdict,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
        'sections': sections,
        'adviser_records': adviser_records,
        'adviser_records2': adviser_records2
        # 'total_criteria_percentage': total_criteria_percentage,
    }

    return render(request, 'faculty/pre_oral_grade/input_grade.html', context)

# function to save the data from the evaluation form for preoral
@login_required
def evaluate_capstone(request, schedule_id):
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    schedule = get_object_or_404(SchedulePOD, id=schedule_id)
    user_profile = get_object_or_404(CustomUser, id=request.user.id)
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)
    is_lead_panel = (schedule.faculty1 == faculty_member)

    sections = PreOral_EvaluationSection.objects.prefetch_related('criteria').filter(school_year=selected_school_year)
    group_members = [schedule.group.member1, schedule.group.member2, schedule.group.member3]
    verdicts = Verdict.objects.filter(school_year=selected_school_year).order_by('-percentage')

    if request.method == 'POST':
        grades_data = {}
        member_grades = {'member1': {}, 'member2': {}, 'member3': {}}

        for section in sections:
            section_grades = {}
            for criteria in section.criteria.filter(school_year=selected_school_year):
                if "Oral Presentation" in section.name or "Individual Grade" in section.name:
                    for member in group_members:
                        member_index = group_members.index(member) + 1
                        member_grade_key = f'criteria_{criteria.id}_member{member_index}'
                        grade_value = request.POST.get(member_grade_key)
                        if grade_value:
                            section_grades[f"{criteria.id}_member{member_index}"] = float(grade_value)
                            member_key = f'member{member_index}'
                            member_grades[member_key][criteria.id] = float(grade_value)
                else:
                    grade_key = f'criteria_{criteria.id}'
                    grade_value = request.POST.get(grade_key)
                    if grade_value:
                        section_grades[str(criteria.id)] = float(grade_value)

            grades_data[section.name] = section_grades

        # Prepare to save the member grades in the new fields
        member1_avg = sum(member_grades['member1'].values()) if member_grades['member1'] else -1
        member2_avg = sum(member_grades['member2'].values()) if member_grades['member2'] else -1
        member3_avg = sum(member_grades['member3'].values()) if member_grades['member3'] else -1
        print(f'member1: {member1_avg}')
        print(f'member2: {member2_avg}')
        print(f'member3: {member3_avg}')

        # Save the data to the PreOral_Grade model
        selected_verdict = 'None'
        grades_json = json.dumps(grades_data)

        PreOral_Grade.objects.create(
            faculty=faculty_member.name,
            project_title=schedule.title,
            grades_data=grades_json,
            verdict=selected_verdict,
            member1_grade=member1_avg,  # Store the calculated average for member 1
            member2_grade=member2_avg,  # Store the calculated average for member 2
            member3_grade=member3_avg,   # Store the calculated average for member 3
            school_year=selected_school_year
        )

        # Log the action in the audit trail
        AuditTrail.objects.create(
            user=request.user,
            action=f"Submitted evaluation in Pre-Oral Defense Schedule for project title '{schedule.title}'",
            ip_address=request.META.get('REMOTE_ADDR')
        )

        # creating a notif
        Notif.objects.create(
            created_by=request.user,
            notif=f"Faculty: '{request.user}', Submitted evaluation in Pre-Oral Defense Schedule for project title '{schedule.title}'",
        )

        # Retrieve all PreOral_Grade objects with the given project title
        grades = PreOral_Grade.objects.filter(project_title=schedule.title, school_year=selected_school_year)
        print("count: ", grades.count())
        # Aggregate data
        summary_totals = {}
        for grade_by_panel in grades:
            summary_grades_data = grade_by_panel.get_grades_data()
            for section_name, section_grades in summary_grades_data.items():
                if section_name not in summary_totals:
                    summary_totals[section_name] = {'total': 0, 'count': 0}
                if isinstance(section_grades, dict):
                    total = sum(section_grades.values())
                    summary_totals[section_name]['total'] += total
                    summary_totals[section_name]['count'] += 1
                elif isinstance(section_grades, list):
                    try:
                        average = sum(section_grades) / len(section_grades)
                    except ZeroDivisionError:
                        average = 0
                    summary_totals[section_name]['total'] += average
                    summary_totals[section_name]['count'] += 1

        # Finalize totals by averaging over the count
        for section_name, data in summary_totals.items():
            if "Oral Presentation" in section_name or "Individual Grade" in section_name:
                # Divide by 3 for specific sections
                if data['count'] > 0:
                    summary_totals[section_name] = data['total'] / 3
                    summary_totals[section_name] = summary_totals[section_name] / 3
                else:
                    summary_totals[section_name] = 0
            else:
                # For other sections, just average over the count
                if data['count'] > 0:
                    summary_totals[section_name] = data['total'] / 3
                else:
                    summary_totals[section_name] = 0

        total_earned_points = sum(summary_totals.values())
        print(f"total points: {total_earned_points}")
        # Determine the verdict based on total earned points
        records = grades.count()
        if records < 3:
            selected_verdict = "Verdict is not available since not all of the panels submit the evaluation!"
        else:
            for verdict in verdicts:
                if total_earned_points >= verdict.percentage:
                    selected_verdict = f"{verdict.name} ({verdict.percentage}%)"
                    break

        print(f"verdict: {selected_verdict}")

        # Only update the verdict if there are exactly 3 records
        if records >= 3:
            for grade in grades:
                grade.verdict = selected_verdict if selected_verdict else None
                grade.save()
        if is_lead_panel:
            verdict_message = "Please check the verdict and submit it again!"
            url = reverse('update_evaluate_capstone', kwargs={'schedule_id': schedule_id})
            query_string = urlencode({'verdict_has_changed': True, 'verdict_message': verdict_message})
            return redirect(f'{url}?{query_string}')
        else:
            return redirect("pre_oral_defense")

# function to reirect to the preoral evaluation form and save the updated data
@login_required
def update_evaluate_capstone(request, schedule_id):
    school_years = SchoolYear.objects.all().order_by('start_year')
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)


    schedule = get_object_or_404(SchedulePOD, id=schedule_id)
    user_profile = get_object_or_404(CustomUser, id=request.user.id)
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)
    # Fetch records from the Adviser model where the faculty is an adviser
    adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=False, declined=False)
    adviser_records2 = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)
    is_lead_panel = (schedule.faculty1 == faculty_member)

    criteria_list = PreOral_EvaluationSection.objects.filter(school_year=selected_school_year).annotate(total_criteria_percentage=Sum('criteria__percentage'))
    criteria_percentage = PreOral_Criteria.objects.filter(school_year=selected_school_year)
    total_points = sum(criteria.percentage for criteria in criteria_percentage) 
    group_members = [schedule.group.member1, schedule.group.member2, schedule.group.member3]
    verdicts = Verdict.objects.filter(school_year=selected_school_year).order_by('-percentage')

    # Fetch the PreOral_Grade entry for this schedule and faculty
    grade_entries = PreOral_Grade.objects.filter(faculty=faculty_member.name, project_title=schedule.title, school_year=selected_school_year)

    # Initialize a dictionary to hold the aggregated grades data
    existing_grades_data = {}
    member_grades = {'member1': {}, 'member2': {}, 'member3': {}}

    grade_entry = None
    existing_checkbox_data = None
    # Iterate over each grade entry to decode and aggregate the grades data
    for grade_entry in grade_entries:
        # Retrieve existing data from the PreOral_Grade entry
        grades_data = grade_entry.get_grades_data()

        # Retrieve existing checkbox data from the PreOral_Grade entry
        existing_checkbox_data = grade_entry.get_checkbox_data()
        
        # Merge this entry's grades data into the aggregated data
        for section_name, section_grades in grades_data.items():
            if section_name not in existing_grades_data:
                existing_grades_data[section_name] = section_grades
            else:
                # Combine the grades if the section already exists
                for criteria, value in section_grades.items():
                    if criteria not in existing_grades_data[section_name]:
                        existing_grades_data[section_name][criteria] = value
                    else:
                        existing_grades_data[section_name][criteria] += value

    # Flatten the existing grades data for easy access in the template
    flattened_grades_data = {}
    for section_name, section_grades in existing_grades_data.items():
        for criteria_key, value in section_grades.items():
            flattened_key = f"{criteria_key}"
            flattened_grades_data[flattened_key] = value

    # Dynamically calculate totals for each category
    totals = {}
    # Calculate total for individual grades by summing values grouped by each member
    member_totals = {}
    for section_name, section_grades in existing_grades_data.items():
        if "Oral Presentation" in section_name or "Individual Grade" in section_name:
            
            for criteria_key, value in section_grades.items():
                member_key = criteria_key.split('_')[-1]  # e.g., 'member1' from 'criteria_1_member1'
                if member_key not in member_totals:
                    member_totals[member_key] = 0
                member_totals[member_key] += value

            # Calculate the average for each member
            number_of_members = len(member_totals)
            if number_of_members > 0:
                average_totals = {member: total / number_of_members for member, total in member_totals.items()}
            else:
                average_totals = member_totals
            
            totals[section_name] = average_totals
            print("individual grade: ", average_totals)
        else:
            # For other sections, just sum the values directly
            totals[section_name] = sum(section_grades.values())


    # Retrieve all PreOral_Grade objects with the given project title
    grades = PreOral_Grade.objects.filter(project_title=schedule.title, school_year=selected_school_year)

    # Initialize a dictionary to hold aggregated summary data
    summary_totals = {}

    for grade_by_panel in grades:
        # Decode grades data from JSON
        summary_grades_data = grade_by_panel.get_grades_data()

        # Aggregate data by section name
        for section_name, section_grades in summary_grades_data.items():
            if section_name not in summary_totals:
                # Initialize totals for new sections
                summary_totals[section_name] = {'total': 0, 'count': 0}

            if isinstance(section_grades, dict):
                # Sum values for each section
                total = sum(section_grades.values())
                summary_totals[section_name]['total'] += total
                summary_totals[section_name]['count'] += 1
            elif isinstance(section_grades, list):
                # Average values for lists
                try:
                    average = sum(section_grades) / len(section_grades)
                except ZeroDivisionError:
                    average = 0
                summary_totals[section_name]['total'] += average
                summary_totals[section_name]['count'] += 1
            else:
                print(f"Unexpected data format for section: {section_name}, data: {section_grades}")

    # Finalize totals by averaging over the count
    for section_name, data in summary_totals.items():
        if "Oral Presentation" in section_name or "Individual Grade" in section_name:
            # Divide by 3 for specific sections
            if data['count'] > 0:
                summary_totals[section_name] = data['total'] / 3
                summary_totals[section_name] = summary_totals[section_name] / 3
            else:
                summary_totals[section_name] = 0
        else:
            # For other sections, just average over the count
            if data['count'] > 0:
                summary_totals[section_name] = data['total'] / data['count']
            else:
                summary_totals[section_name] = 0


    total_earned_points = sum(summary_totals.values())
    print(f"total points1: {total_earned_points}") # for debugging purposes

    # Determine the verdict based on total earned points
    records = grades.count()
    verdict_name = ''
    checkboxes = []
    selected_verdict = ""
    if records < 3:
        selected_verdict = "Verdict is not available since not all of the panels submit the evaluation!"
    else:
        for verdict in verdicts:
            if total_earned_points >= verdict.percentage:
                selected_verdict = f"{verdict.name} ({verdict.percentage}%)"
                verdict_name = verdict.name
                if selected_verdict:
                    checkboxes = Checkbox.objects.filter(verdict=verdict, school_year=selected_school_year)
                    print(checkboxes)
                break
                
    print(f"verdict: {selected_verdict}") # for debugging purposes
    
    previous_verdict = None
    if grade_entries.exists():
        # If records are found, assign the first entry to grade_entry and retrieve the verdict
        previous_verdict = grade_entry.verdict if grade_entry.verdict else None
    else:
        # Handle cases where no grade entries exist (e.g., default verdict behavior)
        print("No grade entries found for this schedule and faculty.")
    new_verdict = None #variable to hold the new verdict
    # When form is submitted
    if request.method == 'POST':
        # Retrieve hidden input values
        member1_grade = request.POST.get('member1_grades', 0)
        member2_grade = request.POST.get('member2_grades', 0)
        member3_grade = request.POST.get('member3_grades', 0)
        print('member grade1', member1_grade)
        print('member grade2', member2_grade)
        print('member grade3', member3_grade)
        

        # Convert these values to floats
        try:
            member1_grade = float(member1_grade)
            member2_grade = float(member2_grade)
            member3_grade = float(member3_grade)
        except ValueError:
            member1_grade = member2_grade = member3_grade = 0
            print('error')

        # Prepare a dictionary to hold all updated grades
        updated_grades_data = {}

        # Process the submitted form data
        for section in criteria_list:
            section_grades = {}
            for criteria in section.criteria.filter(school_year=selected_school_year):
                if "Oral Presentation" in section.name or "Individual Grade" in section.name:
                    for member in group_members:
                        member_index = group_members.index(member) + 1
                        member_grade_key = f'criteria_{criteria.id}_member{member_index}'
                        grade_value = request.POST.get(member_grade_key)
                        if grade_value:
                            section_grades[f"{criteria.id}_member{member_index}"] = float(grade_value)
                else:
                    grade_key = f'criteria_{criteria.id}'
                    grade_value = request.POST.get(grade_key)
                    if grade_value:
                        section_grades[str(criteria.id)] = float(grade_value)

            updated_grades_data[section.name] = section_grades

        # Convert updated grades_data to JSON format
        grades_json = json.dumps(updated_grades_data)
        print('grades: ', grades_json)

        # this is to get the previous total points of this specific user
        # Initialize a variable to store the total grade
        total_grade_points = 0

        # Loop through the grade entries to extract the grades from grades_data (assuming it's a JSON field)
        for individual_grade_entry in grade_entries:
            # Extract the grades data (JSON field) for this entry
            grades_data = json.loads(individual_grade_entry.grades_data)  # Assuming `grades_data` is a JSON field in string format

            # Loop through the grades data to calculate the total for this specific record
            for section_name, section_grades in grades_data.items():
                # If the grades data is a dictionary (criteria-based grading)
                if "Oral Presentation" in section_name or "Individual Grade" in section_name:
                    # Add up the values of the section's grades
                    total_grade_points += sum(section_grades.values())/3
                    print('prepoints: ', total_grade_points)
                    # updated_total_points = updated_total_points / 3
                else:
                    total_grade_points += sum(section_grades.values())
           
        total_grade_points = total_grade_points/3
        print('prev points: ', total_grade_points)

        # this is to get the updated total points of the specific user
        updated_total_points = 0

        # Loop through the updated grades to calculate the total
        for section_name, section_grades in updated_grades_data.items():
            if isinstance(section_grades, dict):
                if "Oral Presentation" in section_name or "Individual Grade" in section_name:
                    # Add up the values of the section's grades
                    updated_total_points += sum(section_grades.values())/3
                    print('upoints: ', updated_total_points)
                    # updated_total_points = updated_total_points / 3
                else:
                    updated_total_points += sum(section_grades.values())
           
        updated_total_points = updated_total_points/3
        print('updated points: ', updated_total_points)

        # Fetch all PreOral_Grade records for the same project title
        related_grades = PreOral_Grade.objects.filter(project_title=schedule.title, school_year=selected_school_year)
        records_count = related_grades.count()

        # Initialize a dictionary to hold aggregated summary data
        summary_totals = {}

        for grade_by_panel in grades:
            # Decode grades data from JSON
            summary_grades_data = grade_by_panel.get_grades_data()

            # Aggregate data by section name
            for section_name, section_grades in summary_grades_data.items():
                if section_name not in summary_totals:
                    # Initialize totals for new sections
                    summary_totals[section_name] = {'total': 0, 'count': 0}

                if isinstance(section_grades, dict):
                    # Sum values for each section
                    total = sum(section_grades.values())
                    summary_totals[section_name]['total'] += total
                    summary_totals[section_name]['count'] += 1
                elif isinstance(section_grades, list):
                    # Average values for lists
                    try:
                        average = sum(section_grades) / len(section_grades)
                    except ZeroDivisionError:
                        average = 0
                    summary_totals[section_name]['total'] += average
                    summary_totals[section_name]['count'] += 1
                else:
                    print(f"Unexpected data format for section: {section_name}, data: {section_grades}")

        # Finalize totals by averaging over the count
        for section_name, data in summary_totals.items():
            if "Oral Presentation" in section_name or "Individual Grade" in section_name:
                # Divide by 3 for specific sections
                if data['count'] > 0:
                    summary_totals[section_name] = data['total'] / 3
                    summary_totals[section_name] = summary_totals[section_name] / 3
                else:
                    summary_totals[section_name] = 0
            else:
                # For other sections, just average over the count
                if data['count'] > 0:
                    summary_totals[section_name] = data['total'] / 3
                else:
                    summary_totals[section_name] = 0

        
        # this is the updated grades/average
        total_earned_points2 = sum(summary_totals.values())
        print('summary_totals: ', sum(summary_totals.values()))
        total_earned_points2 = (total_earned_points2 - total_grade_points) + updated_total_points
        print(f"total points2: {total_earned_points2}")
        selected_verdict2 = ''
        verdict_variable = 0
        # set new verdict
        for verdict in verdicts:
            if total_earned_points2 >= verdict.percentage:
                selected_verdict2 = f"{verdict.name} ({verdict.percentage}%)"
                verdict_name = verdict.name
                verdict_variable = verdict
                print('updated verdict: ',selected_verdict2)
                new_verdict = selected_verdict2
                print('prev verdict: ', previous_verdict)
                break

        # Only update the verdict if there are exactly 3 records
        if records_count >= 3:
            for grade in related_grades:
                grade.verdict = selected_verdict2 if selected_verdict2 else None
                grade.school_year = selected_school_year
                grade.save()

        # save the updated grades   
        grade_entry.grades_data = grades_json
        grade_entry.verdict = selected_verdict2 if selected_verdict2 else None
        grade_entry.member1_grade = member1_grade
        grade_entry.member2_grade = member2_grade
        grade_entry.member3_grade = member3_grade
        grade_entry.school_year = selected_school_year
        grade_entry.save()
        print('success saving')
        print(f"Verdict '{selected_verdict2}' updated for all related records.")
        

        
        # Log the action in the audit trail
        AuditTrail.objects.create(
            user=request.user,
            action=f"Updated evaluation in Pre-Oral Defense Schedule for project title '{schedule.title}'",
            ip_address=request.META.get('REMOTE_ADDR')
        )

        # creating a notif
        Notif.objects.create(
            created_by=request.user,
            notif=f"Faculty: '{request.user}', Updated evaluation in Pre-Oral Defense Schedule for project title '{schedule.title}'",
        )




        # Process the checkboxes
        all_checkboxes = Checkbox.objects.filter(school_year=selected_school_year)
        checkboxes = Checkbox.objects.filter(verdict=verdict_variable, school_year=selected_school_year) if selected_verdict != "Verdict is not available since not all of the panels submit the evaluation!" else []
        
        verdict_has_changed = "False" #variable to handle whether the verdict has changed or not
        
        # Update checkbox states
        checkbox_data = {}

        for checkbox in all_checkboxes:
            checkbox_id = checkbox.id
            if previous_verdict != new_verdict:
                is_checked = False
                checkbox_data[checkbox_id] = is_checked 
                verdict_has_changed = "True"
            else:
                is_checked = request.POST.get(f'checkbox_{checkbox_id}', 'off') == 'on'
                checkbox_data[checkbox_id] = is_checked  # Store the checkbox state in a dictionary
            
            print('ch_jason: ', checkbox_data)
            print('is_check?: ', is_checked)
            print(f'POST data for checkbox_{checkbox_id}: {request.POST.get(f"checkbox_{checkbox_id}", "Not Found")}')
            print(checkbox_id)
            print(f'Looking for checkbox: checkbox_{checkbox_id}')
            # Only update the verdict if there are exactly 3 records
            if records_count >= 3:
                for grade in related_grades:
                    grade.checkbox_data = checkbox_data
                    grade.school_year = selected_school_year
                    grade.save()
            grade_entry.school_year = selected_school_year
            grade_entry.checkbox_data = checkbox_data
            grade_entry.save()
            
            # Check if the label contains 'Other' or 'Specify'
            if 'other' in checkbox.label.lower() or 'specify' in checkbox.label.lower():
                # Retrieve the 'Others' input field value if the checkbox is checked
                other_value = request.POST.get(f'other_input_{checkbox_id}', '')
                print("other: ", other_value)
                if records_count >= 3:
                    for grade in related_grades:
                        grade.othervalue = other_value 
                        grade.school_year = selected_school_year
                        grade.save()
                grade_entry.school_year = selected_school_year
                grade_entry.othervalue = other_value 
                grade_entry.save()

        # for debugging purposes only can be deleted
        if checkboxes:
            print(" TRUE, check: ",checkboxes)
        else:
            print('no checkbox')


        # applies only to the lead panel since he/she is the one who will choose the specific category based on the verdict selected 
        if is_lead_panel:
            # check if the selected verdict is not the default value which is equal to < 3 panels who graded the project
            if selected_verdict != "Verdict is not available since not all of the panels submit the evaluation!":
                # check if the selected verdict has checkboxes associated to it
                if checkboxes.exists():
                    related_grades2 = PreOral_Grade.objects.filter(faculty=faculty_member.name, project_title=schedule.title, school_year=selected_school_year)
                    for grade in related_grades2:
                        checkbox_data = grade.checkbox_data
                        any_checkbox_checked = any(value for value in grade.checkbox_data.values()) #check if the value in checkbox_data has True
                        print(checkbox_data)
                        print('value: ', any_checkbox_checked)
                        # if the value has True meaning there is a checkbox selected
                        if any_checkbox_checked:
                            return redirect('pre_oral_defense')
                        else:
                            print('success saving')
                            verdict_message = "Please confirm the verdict and submit it again!"
                            url = reverse('update_evaluate_capstone', kwargs={'schedule_id': schedule_id})
                            query_string = urlencode({'verdict_has_changed': verdict_has_changed, 'verdict_message': verdict_message})
                            return redirect(f'{url}?{query_string}')
                else:
                    return redirect('pre_oral_defense')
            else:
                # Redirect to the faculty dashboard if verdict is not available
                # messages.success(request, "Evaluation successfully submitted!")
                return redirect('pre_oral_defense')
        else:
            return redirect('pre_oral_defense')
    
    # use to get the pass verdict_has_changed variable from redirect
    verdict_has_changed_str = request.GET.get('verdict_has_changed') #variable to hold the value of the verdict_has_changed
    verdict_has_changed = verdict_has_changed_str.lower() == 'true' if verdict_has_changed_str else False #variable to hold a bolean value
    verdict_message = request.GET.get('verdict_message')
    print("true or false: ", verdict_has_changed)

    # Prepare context data for the form with existing data
    context = {
        'schedule': schedule,
        'faculty_member': faculty_member,
        'is_lead_panel': is_lead_panel,
        'criteria_list': criteria_list,
        'group_members': group_members,
        'existing_grades_data': flattened_grades_data,  # Pass flattened grades to the template
        'grade_entry': grade_entry,
        'total_points': total_points,
        'totals': totals, 
        'member_totals': member_totals,
        'summary_totals': summary_totals,
        'total_earned_points': total_earned_points,
        'verdicts': verdicts,
        'selected_verdict': selected_verdict,
        'verdict_name': verdict_name, 
        'checkboxes': checkboxes,
        'all_checkboxes': Checkbox.objects.filter(school_year=selected_school_year),
        'existing_checkbox_data': existing_checkbox_data,
        'verdict_has_changed': verdict_has_changed,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
        'verdict_message': verdict_message,
        'adviser_records': adviser_records,
        'adviser_records2': adviser_records2
    }
    

    return render(request, 'faculty/pre_oral_grade/update_input_grade.html', context)

# function to view the grade status of the group for the preoral and for the adviser to input recommendations of the panels
@login_required
def adviser_record_detail(request, adviser_id):
    school_years = SchoolYear.objects.all().order_by('start_year')

    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()

    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # Fetch the CustomUser object associated with the logged-in user
    user_profile = get_object_or_404(CustomUser, id=request.user.id)

    # Fetch the Faculty object associated with the CustomUser
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)
    print("faculty_member: ", faculty_member)

    # Fetch records from the Adviser model where the faculty is an adviser
    adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=False, declined=False)
    adviser_records2 = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)
    
    adviser_id = adviser_id
    print('adviser_id', adviser_id)

    adviser = get_object_or_404(Adviser, id=adviser_id)
    print("Adviser: ", adviser.faculty)
    adviser_id2 = adviser.id
    print('adviser_id2', adviser_id2)
    verdicts = Verdict.objects.filter(school_year=selected_school_year).order_by('-percentage')
    print(verdicts)
    title = adviser.approved_title
    preoral_grade_record = PreOral_Grade.objects.filter(project_title=title, school_year=selected_school_year)
    recos = PreOral_Recos.objects.filter(project_title=title, school_year=selected_school_year)
    all_checkboxes = Checkbox.objects.filter(school_year=selected_school_year)
    for reco in recos:
        reco.recommendation = escape(reco.recommendation)

    # Fetch group members
    groups = GroupInfoPOD.objects.filter(title=title, school_year=selected_school_year)
    advisee_groups = Adviser.objects.filter(approved_title=title, school_year=selected_school_year)
    member1 = None
    member2 = None
    member3 = None
    if groups.exists():
        # Fetch members directly from GroupInfoPOD
        group = groups.first()  # Get the first group object
        member1 = group.member1
        member2 = group.member2
        member3 = group.member3
    else:
        # Fall back to splitting `group_name` from Adviser model
        if advisee_groups.exists():
            # Get the first matching adviser record
            advisee = advisee_groups.first()
            members = advisee.group_name.split('<br>') if advisee.group_name else []
            # Pad the members list to ensure it has at least 3 elements
            while len(members) < 3:
                members.append(None)  # Use `None` or an empty string as padding
            member1, member2, member3 = members[0], members[1], members[2]
            print("member1: ", member1)
        else:
            # If no matching adviser record, set members to None
            member1, member2, member3 = None, None, None
    group_members = f"Member1: {member1}, Member2: {member2}, Member3: {member3}"

    # Handle form submission
    if request.method == "POST":
        recommendation = request.POST.get("recommendation")
        print("recosss: ", recommendation)
        
        # Try to find an existing PreOral_Recos record with the same title
        reco = PreOral_Recos.objects.filter(project_title=title, school_year=selected_school_year).first()
        
        if reco:
            # If recommendation record exists, update the recommendation
            reco.recommendation = recommendation
            if recommendation == "":
                print("Empty reco")
                reco.recommendation = recommendation
                reco.school_year = selected_school_year
                reco.delete()
                # Log the action in the audit trail
                AuditTrail.objects.create(
                    user=request.user,
                    action=f"Deleted recommendation in Pre-oral Group Advisee Record for project title '{title}'",
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            else:
                reco.school_year = selected_school_year
                reco.recommendation = recommendation
                # Save the recommendation record (updated)
                print("empyt also")
                reco.save()
                # Log the action in the audit trail
                AuditTrail.objects.create(
                    user=request.user,
                    action=f"Updated recommendation in Pre-oral Group Advisee Record for project title '{title}'",
                    ip_address=request.META.get('REMOTE_ADDR')
                )
        else:
            # If no recommendation record exists, create a new one
            if recommendation == "":
                print("Empty reco")
            else:
                reco = PreOral_Recos(
                    project_title=title,  # Assuming `title` is defined elsewhere in the view
                    recommendation=recommendation,
                    school_year=selected_school_year
                )
                # Save the recommendation record (new)
                reco.save()
                # Log the action in the audit trail
                AuditTrail.objects.create(
                    user=request.user,
                    action=f"Submitted recommendation in Pre-oral Group Advisee Record for project title '{title}'",
                    ip_address=request.META.get('REMOTE_ADDR')
                )
        
        print(f"Redirecting with adviser_id: {adviser_id}")  # Debugging line
        return redirect('adviser_record_detail', adviser_id=adviser_id)
    
    # Fetch grades with the same title
    grades = PreOral_Grade.objects.filter(project_title=title, school_year=selected_school_year)
    criteria_list = PreOral_EvaluationSection.objects.filter(school_year=selected_school_year).annotate(total_criteria_percentage=Sum('criteria__percentage'))
    criteria_percentage = PreOral_Criteria.objects.filter(school_year=selected_school_year)
    total_points = sum(criteria.percentage for criteria in criteria_percentage)
    
    print("group_members: ", group_members)
    if not grades.exists():
        return render(request, 'faculty/pre_oral_grade/adviser_record_detailPOD.html', {
            'error': 'No grades found for this title',
            'title': title, 
            'member1': member1, 
            'member2': member2, 
            'member3': member3,
            'adviser': adviser,
            'recos': recos,
            'faculty_member': faculty_member,
            'school_years': school_years,  # Ensure this is passed to the template
            'adviser_records': adviser_records,
            'last_school_year': last_school_year,
            # 'current_school_year': current_school_year,
            'selected_school_year': selected_school_year,
            'adviser_records2': adviser_records2
        })

    # Initialize member variables
    member1_grade = grades.first().member1_grade if grades.exists() else None
    member2_grade = grades.first().member2_grade if grades.exists() else None
    member3_grade = grades.first().member3_grade if grades.exists() else None
    recommendation = grades.first().recommendation if grades.exists() else None
    total_grade1 = grades.aggregate(Sum('member1_grade'))['member1_grade__sum']
    total_grade2 = grades.aggregate(Sum('member2_grade'))['member2_grade__sum']
    total_grade3 = grades.aggregate(Sum('member3_grade'))['member3_grade__sum']

    #grade for the member1
    if total_grade1 is not None and grades.count() != 0:
        average_grade1 = total_grade1 / 3
        print('the grade is no 0')
        
    else:
        average_grade1 = 0  # Handle the case where no grades exist
        print('the grade is 0')
    print('member grade1', average_grade1)

    #grade for the member2
    if total_grade2 is not None and grades.count() != 0:
        average_grade2 = total_grade2 / 3
        print('the grade is no 0')
        
    else:
        average_grade2 = 0  # Handle the case where no grades exist
        print('the grade is 0')
    print('member grade3', average_grade2)

    #grade for the member3
    if total_grade3 is not None and grades.count() != 0:
        average_grade3 = total_grade3 / 3
        print('the grade is no 0')
        
    else:
        average_grade3 = 0  # Handle the case where no grades exist
        print('the grade is 0')
    print('member grade3', average_grade3)

    member1 = groups.first().member1 if groups.exists() else None
    member2 = groups.first().member2 if groups.exists() else None
    member3 = groups.first().member3 if groups.exists() else None

    # Aggregate data
    summary_totals = {}
    for grade_by_panel in grades:
        summary_grades_data = grade_by_panel.get_grades_data()
        for section_name, section_grades in summary_grades_data.items():
            if section_name not in summary_totals:
                summary_totals[section_name] = {'total': 0, 'count': 0}
            if isinstance(section_grades, dict):
                total = sum(section_grades.values())
                summary_totals[section_name]['total'] += total
                summary_totals[section_name]['count'] += 1
            elif isinstance(section_grades, list):
                try:
                    average = sum(section_grades) / len(section_grades)
                except ZeroDivisionError:
                    average = 0
                summary_totals[section_name]['total'] += average
                summary_totals[section_name]['count'] += 1

    # Finalize totals
    for section_name, data in summary_totals.items():
            if "Oral Presentation" in section_name or "Individual Grade" in section_name:
                # Divide by 3 for specific sections
                if data['count'] > 0:
                    summary_totals[section_name] = data['total'] / 3
                    summary_totals[section_name] = summary_totals[section_name] / 3
                else:
                    summary_totals[section_name] = 0
            else:
                # For other sections, just average over the count
                if data['count'] > 0:
                    summary_totals[section_name] = data['total'] / 3
                else:
                    summary_totals[section_name] = 0

    total_earned_points = sum(summary_totals.values())
    print(f"total points: {total_earned_points}")

    # Determine the verdict based on total earned points
    records = grades.count()
    selected_verdict = ''
    # Decode the checkbox_data from the PreOral_Grade instance
    for checkbox_entry in preoral_grade_record:
        checkbox_data = checkbox_entry.get_checkbox_data() 
    if records < 3:
        selected_verdict = "Verdict is not available since not all of the panels submit the evaluation!"
    else:
        for verdict in verdicts:
            print(f"verdict percentage: {verdict.percentage}")
            if total_earned_points >= verdict.percentage:
                selected_verdict = f"{verdict.name} ({verdict.percentage}%)"
                break

    context = {
        'adviser_id': adviser_id,
        'adviser': adviser,
        'faculty_member': faculty_member,
        'title': title,
        'verdicts': verdicts,
        'selected_verdict': selected_verdict,
        'member1': member1,
        'member2': member2, 
        'member3': member3,
        'member1_grade': average_grade1,
        'member2_grade': average_grade2,
        'member3_grade': average_grade3,
        'criteria_list': criteria_list,
        'summary_totals': summary_totals,
        'total_points': total_points,
        'total_earned_points': total_earned_points,
        'recommendation': recommendation,
        'recos': recos,
        'checkbox_data': checkbox_data,
        'all_checkboxes': Checkbox.objects.filter(school_year=selected_school_year),
        'preoral_grade_record': preoral_grade_record,
        'checkbox_entry': checkbox_entry,
        'last_school_year': last_school_year,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'school_years': school_years,
        'adviser_records': adviser_records,
        'adviser_records2': adviser_records2
    }
    
    return render(request, 'faculty/pre_oral_grade/adviser_record_detailPOD.html', context)

# function to fetch the preoral recommendations based on the project title
def reco(request, schedule_id):
    school_years = SchoolYear.objects.all().order_by('start_year')
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()

    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # Fetch the CustomUser object associated with the logged-in user
    user_profile = get_object_or_404(CustomUser, id=request.user.id)

    # Fetch the Faculty object associated with the CustomUser
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)

    # Fetch records from the Adviser model where the faculty is an adviser
    adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=False, declined=False)
    adviser_records2 = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)

    schedule = get_object_or_404(SchedulePOD, id=schedule_id)
    recos = PreOral_Recos.objects.filter(project_title=schedule.title, school_year=selected_school_year)
    print(recos)
    for reco in recos:
        reco.recommendation = escape(reco.recommendation)

    context = {
        'schedule': schedule,
        'recos': recos,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
        'adviser_records': adviser_records,
        'adviser_records2': adviser_records2
    }
    return render(request, 'faculty/pre_oral_grade/reco.html', context)




# functions for the mock evaluation
@csrf_exempt  # Use CSRF exempt for AJAX requests
@superuser_required
def mock_add_section(request):
    if request.method == 'POST':
        form = Mock_EvaluationSectionForm(request.POST)
        if form.is_valid():
            # Create the section
            section_name = form.cleaned_data['name']
            active_school_year = SchoolYear.get_active_school_year()
            selected_school_year_id = request.session.get('selected_school_year_id')
            # get the last school year added to the db
            last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

            # Get the selected school year from session or fallback to the active school year
            selected_school_year = ''
            if not selected_school_year_id:
                selected_school_year = last_school_year
                request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
            else:
                # Retrieve the selected school year based on the session
                selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

            if selected_school_year:
                if Mock_EvaluationSection.objects.filter(name=section_name, school_year=selected_school_year).exists():
                    return JsonResponse({
                        'status': 'error',
                        'message': 'A section with this name already exists for the active school year.'
                    })

                section = form.save(commit=False)
                section.school_year = selected_school_year
                section.save()
                # Add audit trail entry
                AuditTrail.objects.create(
                    user=request.user,
                    action=f'Create a new Mock Rubric: {section_name}',
                    time=timezone.now(),
                    ip_address=request.META.get('REMOTE_ADDR')
                )

                # Handle subcriteria creation
                subcriteria_count = 0
                while True:
                    criteria_name = request.POST.get(f'criteria_name_{subcriteria_count + 1}')
                    criteria_percentage = request.POST.get(f'criteria_percentage_{subcriteria_count + 1}')
                    criteria_description = request.POST.get(f'criteria_description_{subcriteria_count + 1}')

                    if criteria_name and criteria_percentage:
                        # Create subcriteria
                        criteria = Mock_Criteria.objects.create(
                            section=section,
                            name=criteria_name,
                            percentage=criteria_percentage,
                            school_year=selected_school_year
                        )

                        # Create description
                        if criteria_description:
                            MockCriterionDescription.objects.create(
                                criterion=criteria,
                                text=criteria_description,
                                school_year=selected_school_year
                            )

                        subcriteria_count += 1

                        # Add audit trail entry
                        AuditTrail.objects.create(
                            user=request.user,
                            action=f'Add a subcriteria: {criteria_name} for Mock Rubric: {section_name}',
                            time=timezone.now(),
                            ip_address=request.META.get('REMOTE_ADDR')
                        )
                    else:
                        break

                return JsonResponse({'status': 'success', 'section_id': section.id, 'name': section.name})

            else:
                return JsonResponse({'status': 'error', 'message': 'No active school year.'})

        return JsonResponse({'status': 'error', 'message': 'Invalid form submission.'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


@csrf_exempt
@superuser_required
def mock_get_section_details(request, section_id):
    try:
        section = Mock_EvaluationSection.objects.get(id=section_id)
        subcriteria = Mock_Criteria.objects.filter(section=section).values('name', 'percentage', 'mdescriptions__text')

        # Prepare the response with subcriteria data
        subcriteria_data = []
        for criterion in subcriteria:
            description = criterion.get('mdescriptions__text', "")
            subcriteria_data.append({
                'name': criterion['name'],
                'percentage': criterion['percentage'],
                'description': description
            })

        return JsonResponse({'status': 'success', 'name': section.name, 'subcriteria': subcriteria_data})

    except Mock_EvaluationSection.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Section not found.'})

@csrf_exempt
@superuser_required
def mock_edit_section(request, section_id):
    if request.method == 'POST':
        # section_id = request.POST.get('section_id')
        # print('id: ', section_id)
        try:
            section = get_object_or_404(Mock_EvaluationSection, pk=section_id)
            form = Mock_EvaluationSectionForm(request.POST, instance=section)

            if form.is_valid():
                section_name = form.cleaned_data['name']
                section.name = section_name
                section.save()
                # Add audit trail entry
                AuditTrail.objects.create(
                    user=request.user,
                    action=f'Update a Mock Rubric: {section_name} with ID {section_id}',
                    time=timezone.now(),
                    ip_address=request.META.get('REMOTE_ADDR')
                )

                # Update subcriteria
                Mock_Criteria.objects.filter(section=section).delete()  # Remove all subcriteria first
                subcriteria_count = 0

                while True:
                    criteria_name = request.POST.get(f'criteria_name_{subcriteria_count + 1}')
                    criteria_percentage = request.POST.get(f'criteria_percentage_{subcriteria_count + 1}')
                    criteria_description = request.POST.get(f'criteria_description_{subcriteria_count + 1}')

                    if criteria_name and criteria_percentage:
                        # Recreate subcriteria
                        criteria = Mock_Criteria.objects.create(
                            section=section,
                            name=criteria_name,
                            percentage=criteria_percentage,
                            school_year=section.school_year
                        )

                        # Recreate description
                        if criteria_description:
                            MockCriterionDescription.objects.create(
                                criterion=criteria,
                                text=criteria_description,
                                school_year=section.school_year
                            )

                        subcriteria_count += 1
                    else:
                        break

                # Add audit trail entry
                AuditTrail.objects.create(
                    user=request.user,
                    action=f'Update a subcriteria: {criteria_name} for Mock Rubric: {section_name}',
                    time=timezone.now(),
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                return JsonResponse({'status': 'success'})

            return JsonResponse({'status': 'error', 'message': 'Invalid form submission.'})
        
        except Mock_EvaluationSection.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Section not found.'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})

@csrf_exempt
@superuser_required
def mock_delete_section(request, section_id):
    section = get_object_or_404(Mock_EvaluationSection, pk=section_id)
    section_name = section.name
    section.delete()
    # Add audit trail entry
    AuditTrail.objects.create(
        user=request.user,
        action=f'Delete a Mock Rubric: {section_name} with ID {section_id}',
        time=timezone.now(),
        ip_address=request.META.get('REMOTE_ADDR')
    )
    return JsonResponse({'status': 'success'})


@csrf_exempt
@superuser_required
def mock_add_criteria(request, section_id):
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    section = get_object_or_404(Mock_EvaluationSection, pk=section_id)
    if request.method == 'POST':
        form = Mock_CriteriaForm(request.POST)
        if form.is_valid():
            criteria = form.save(commit=False)
            criteria.section = section
            criteria.school_year = selected_school_year
            criteria.save()
            return JsonResponse({'status': 'success', 'criteria_id': criteria.id, 'name': criteria.name})
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


@csrf_exempt
@superuser_required
def mock_edit_criteria(request, criterion_id):
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    criterion = get_object_or_404(Mock_Criteria, pk=criterion_id)
    if request.method == 'POST':
        form = Mock_CriteriaForm(request.POST, instance=criterion)
        if form.is_valid():
            form.school_year = selected_school_year
            form.save()
            return JsonResponse({'status': 'success', 'name': criterion.name})
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


@csrf_exempt
@superuser_required
def mock_delete_criteria(request, criterion_id):
    criterion = get_object_or_404(Mock_Criteria, pk=criterion_id)
    criterion.delete()
    return JsonResponse({'status': 'success'})


@csrf_exempt
@superuser_required
def mock_add_criteria_description(request, criterion_id):
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()

    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    criterion = get_object_or_404(Mock_Criteria, pk=criterion_id)
    if request.method == 'POST':
        form = Mock_CriterionDescriptionForm(request.POST)
        if form.is_valid():
            description = form.save(commit=False)
            description.criterion = criterion
            description.school_year = selected_school_year
            description.save()
            return JsonResponse({'status': 'success', 'description_id': description.id, 'text': description.text})
        return JsonResponse({'status': 'error', 'errors': form.errors})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


@csrf_exempt
@superuser_required
def mock_edit_criteria_description(request, description_id):
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    description = get_object_or_404(MockCriterionDescription, pk=description_id)
    if request.method == 'POST':
        form = Mock_CriterionDescriptionForm(request.POST, instance=description)
        if form.is_valid():
            form.school_year = selected_school_year
            form.save()
            return JsonResponse({'status': 'success', 'text': description.text})
        return JsonResponse({'status': 'error', 'errors': form.errors})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


@csrf_exempt
@superuser_required
def mock_delete_criteria_description(request, description_id):
    description = get_object_or_404(MockCriterionDescription, pk=description_id)
    description.delete()
    return JsonResponse({'status': 'success'})


@csrf_exempt
@superuser_required
def mock_add_verdict(request):
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    if request.method == 'POST':
        # Initialize forms with POST data
        verdict_form = Mock_VerdictForm(request.POST)
        checkbox_form = Mock_CheckboxForm(request.POST)
        
        # Debug print statements
        print('POST data received:', request.POST)
        
        # Validate the verdict form
        if verdict_form.is_valid():
            verdict = verdict_form.save(commit=False)
            verdict.school_year = selected_school_year
            verdict.save()

            # Add audit trail entry
            AuditTrail.objects.create(
                user=request.user,
                action=f'Create a new Mock Verdict: {verdict.name}',
                time=timezone.now(),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            # Now handle the checkboxes
            if checkbox_form.is_valid():
                try:
                    checkbox_form.save_checkboxes(verdict, school_year=selected_school_year)
                    # Return success response if everything goes well
                    return JsonResponse({
                        'status': 'success',
                        'verdict_id': verdict.id,
                        'name': verdict.name
                    })
                except Exception as e:
                    # If there's an exception saving the checkboxes, print it
                    print("Error saving checkboxes:", e)
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Failed to save checkboxes.',
                        'verdict_id': verdict.id,
                        'errors': str(e)
                    })
            else:
                # If the checkbox form is invalid, return the errors
                print('Checkbox Form Errors:', checkbox_form.errors)
                return JsonResponse({
                    'status': 'error',
                    'message': 'Checkbox form is invalid.',
                    'verdict_id': verdict.id,  # Optionally provide the saved verdict ID
                    'checkbox_errors': checkbox_form.errors
                })
        else:
            # If the verdict form is invalid, return errors
            print('Verdict Form Errors:', verdict_form.errors)
            return JsonResponse({
                'status': 'error',
                'errors': {
                    'verdict_errors': verdict_form.errors
                }
            })

    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method.'
    })


@superuser_required
def mock_edit_verdict(request, verdict_id):
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()

    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # Retrieve the verdict object
    verdict = get_object_or_404(Mock_Verdict, pk=verdict_id)

    if request.method == 'POST':
        # Handle form submission
        form = Mock_VerdictForm(request.POST, instance=verdict)

        if form.is_valid():
            form.school_year = selected_school_year
            form.save()  # Save the Verdict form first
            verdict.mcheckboxes.all().delete()

            # Handle dynamic checkboxes
            index = 0
            while True:
                label = request.POST.get(f'checkboxes[{index}][label]')
                if label is None:
                    break
                is_checked = request.POST.get(f'checkboxes[{index}][is_checked]', False) == 'on'
                
                # Create new checkbox or update if ID exists
                Mock_Checkbox.objects.create(
                    verdict=verdict,
                    label=label,
                    is_checked=is_checked,
                    school_year=selected_school_year
                )
                index += 1

            # Add audit trail entry
            AuditTrail.objects.create(
                user=request.user,
                action=f'Update a Mock Verdict: {verdict.name} with ID {verdict_id}',
                time=timezone.now(),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return JsonResponse({'success': True, 'message': 'Verdict updated successfully!'})

        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    # For GET request, provide the form and existing checkboxes
    checkbox_data = list(verdict.mcheckboxes.values('id', 'label', 'is_checked'))
    checkbox_data_json = json.dumps(checkbox_data)

    return JsonResponse({
        'form': Mock_VerdictForm(instance=verdict).as_p(),
        'checkbox_data': checkbox_data_json,
        'csrf_token': request.META.get('CSRF_COOKIE'),  # Send CSRF token
    })


@csrf_exempt
@superuser_required
def mock_delete_verdict(request, verdict_id):
    verdict = get_object_or_404(Mock_Verdict, pk=verdict_id)
    verdict.delete()
    # Add audit trail entry
    AuditTrail.objects.create(
        user=request.user,
        action=f'Delete a Mock Verdict: {verdict.name} with ID {verdict_id}',
        time=timezone.now(),
        ip_address=request.META.get('REMOTE_ADDR')
    )
    return JsonResponse({'status': 'success'})

# functions for the viewing of the sections and criteria
@superuser_required #use to prevent access from not admin users 
def mock_view_section(request):
    # Check for the conflict query parameter
    empty_str = request.GET.get('empty')  # Should return True if 'conflict' param is 'True'
    message = request.GET.get('message')
    empty = empty_str.lower() == 'true' if empty_str else False #variable to hold a bolean value


    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)
    
    # Get all available school years
    school_years = SchoolYear.objects.all().order_by('start_year')
    if school_years.count() == 0:
        SchoolYear.create_new_school_year()
        school_years = SchoolYear.objects.all().order_by('start_year')
    
    sy_count = school_years.count()

    # Fetch all sections and prefetch related Mock_Criteria and their related MockCriterionDescription (mdescriptions)
    sections = Mock_EvaluationSection.objects.filter(school_year=selected_school_year).prefetch_related('mcriteria__mdescriptions')
    verdicts = Mock_Verdict.objects.prefetch_related('mcheckboxes').filter(school_year=selected_school_year)
    description_count = MockCriterionDescription.objects.filter(school_year=selected_school_year).count()
    return render(request, 'admin/mock/Mock_Evaluation/mock_view_section.html', {
        'sections': sections, 
        'verdicts': verdicts,
        'school_years': school_years,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'sy_count': sy_count,
        'empty': empty,
        'message': message,
        'description_count': description_count
        })


@superuser_required
def mock_view_criteria(request, criterion_id):
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    criterion = get_object_or_404(Mock_Criteria, pk=criterion_id)
    descriptions = MockCriterionDescription.objects.filter(criterion=criterion, school_year = selected_school_year)
    return render(request, 'admin/mock/Mock_Evaluation/mock_view_criteria.html', {'criterion': criterion, 'descriptions': descriptions})


# function to redirect to the preoral evaluation form
@login_required
def mock_input_grade(request, schedule_id):
    school_years = SchoolYear.objects.all().order_by('start_year')
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    schedule = get_object_or_404(ScheduleMD, id=schedule_id)
    user_profile = get_object_or_404(CustomUser, id=request.user.id)
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)
    # Fetch records from the Adviser model where the faculty is an adviser
    adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=False, declined=False)
    adviser_records2 = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)
    is_lead_panel = (schedule.faculty1 == faculty_member)

    # Fetch all criteria and verdicts from the database
    criteria_list = Mock_EvaluationSection.objects.filter(school_year=selected_school_year).annotate(total_criteria_percentage=Sum('mcriteria__percentage'))
    criteria_percentage = Mock_Criteria.objects.filter(school_year=selected_school_year)
    verdicts = Mock_Verdict.objects.filter(school_year=selected_school_year)
    sections = Mock_EvaluationSection.objects.filter(school_year=selected_school_year).prefetch_related('mcriteria__descriptions')

    # Fetch group members from the schedule
    group_members = [schedule.group.member1, schedule.group.member2, schedule.group.member3]
    
    # total_criteria_percentage = PreOral_EvaluationSection.objects.annotate(total_percentage=Sum('criteria__percentage'))

    
    total_percentage = sum(criteria.percentage for criteria in criteria_percentage) 

    # Retrieve all PreOral_Grade objects with the given project title
    grades = Mock_Grade.objects.filter(project_title=schedule.title, school_year=selected_school_year)
    
    # Initialize a dictionary to hold aggregated summary data
    summary_totals = {}
    
    for grade_by_panel in grades:
        # Decode grades data from JSON
        summary_grades_data = grade_by_panel.get_grades_data()
        print(f"Summary points from grade_by_panel: {grade_by_panel} {summary_grades_data}")
        
        # Aggregate data by section name
        for section_name, section_grades in summary_grades_data.items():
            if section_name not in summary_totals:
                # Initialize totals for new sections
                summary_totals[section_name] = {'total': 0, 'count': 0}
            
            if isinstance(section_grades, dict):
                # Sum values for each section
                total = sum(section_grades.values())
                summary_totals[section_name]['total'] += total
                summary_totals[section_name]['count'] += 1
            elif isinstance(section_grades, list):
                # Average values for lists
                try:
                    average = sum(section_grades) / len(section_grades)
                except ZeroDivisionError:
                    average = 0
                summary_totals[section_name]['total'] += average
                summary_totals[section_name]['count'] += 1
            else:
                print(f"Unexpected data format for section: {section_name}, data: {section_grades}")
    
    # Finalize totals by averaging over the count
    # for section_name, data in summary_totals.items():
    #     if data['count'] > 0:
    #         summary_totals[section_name] = data['total'] / 3 #data['count'] 
            
    #     else:
    #         summary_totals[section_name] = 0
    
    # Finalize totals by averaging over the count
    for section_name, data in summary_totals.items():
        if "Oral Presentation" in section_name or "Individual Grade" in section_name:
            # Divide by 3 for specific sections
            if data['count'] > 0:
                summary_totals[section_name] = data['total'] / 3
                summary_totals[section_name] = summary_totals[section_name] / 3
            else:
                summary_totals[section_name] = 0
        else:
            # For other sections, just average over the count
            if data['count'] > 0:
                summary_totals[section_name] = data['total'] / 3 #data['count']
            else:
                summary_totals[section_name] = 0
            
    total_earned_points = sum(summary_totals.values())
    print('summary total: ', summary_totals.values())
    print(f"Final Summary Totals: {total_earned_points}")

    # Determine the verdict based on total earned points
    records = grades.count()
    if records < 3:
        selected_verdict = "Verdict is not available since not all of the panels submit the evaluation!"
    else:
        for verdict in verdicts:
            if total_earned_points <= verdict.percentage:
                selected_verdict = verdict
                
    print(f"verdict: {selected_verdict}")

    context = {
        'schedule': schedule,
        'faculty_member': faculty_member,
        'is_lead_panel': is_lead_panel,
        'schedule_id': schedule_id,
        'criteria_list': criteria_list,
        'verdicts': verdicts,
        'group_members': group_members,
        'total_percentage': total_percentage,
        'summary_totals': summary_totals,
        'total_earned_points': total_earned_points,
        'selected_verdict': selected_verdict,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
        'sections': sections,
        'adviser_records': adviser_records,
        'adviser_records2': adviser_records2
        # 'total_criteria_percentage': total_criteria_percentage,
    }

    return render(request, 'faculty/mock_grade/mock_input_grade.html', context)

# function to save the data from the evaltion form for preoral
@login_required
def mock_evaluate_capstone(request, schedule_id):
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    schedule = get_object_or_404(ScheduleMD, id=schedule_id)
    user_profile = get_object_or_404(CustomUser, id=request.user.id)
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)
    is_lead_panel = (schedule.faculty1 == faculty_member)

    sections = Mock_EvaluationSection.objects.filter(school_year=selected_school_year).prefetch_related('mcriteria')
    group_members = [schedule.group.member1, schedule.group.member2, schedule.group.member3]
    verdicts = Mock_Verdict.objects.filter(school_year=selected_school_year).order_by('-percentage')

    if request.method == 'POST':
        grades_data = {}
        member_grades = {'member1': {}, 'member2': {}, 'member3': {}}

        for section in sections:
            section_grades = {}
            for criteria in section.mcriteria.all():
                if "Oral Presentation" in section.name or "Individual Grade" in section.name:
                    for member in group_members:
                        member_index = group_members.index(member) + 1
                        member_grade_key = f'criteria_{criteria.id}_member{member_index}'
                        grade_value = request.POST.get(member_grade_key)
                        if grade_value:
                            section_grades[f"{criteria.id}_member{member_index}"] = float(grade_value)
                            member_key = f'member{member_index}'
                            member_grades[member_key][criteria.id] = float(grade_value)
                else:
                    grade_key = f'criteria_{criteria.id}'
                    grade_value = request.POST.get(grade_key)
                    if grade_value:
                        section_grades[str(criteria.id)] = float(grade_value)

            grades_data[section.name] = section_grades

        # Prepare to save the member grades in the new fields
        member1_avg = sum(member_grades['member1'].values()) if member_grades['member1'] else -1
        member2_avg = sum(member_grades['member2'].values()) if member_grades['member2'] else -1
        member3_avg = sum(member_grades['member3'].values()) if member_grades['member3'] else -1
        print(f'member1: {member1_avg}')
        print(f'member2: {member2_avg}')
        print(f'member3: {member3_avg}')

        # Save the data to the PreOral_Grade model
        selected_verdict = 'None'
        grades_json = json.dumps(grades_data)

        
        Mock_Grade.objects.create(
            faculty=faculty_member.name,
            project_title=schedule.title,
            grades_data=grades_json,
            verdict=selected_verdict,
            member1_grade=member1_avg,  # Store the calculated average for member 1
            member2_grade=member2_avg,  # Store the calculated average for member 2
            member3_grade=member3_avg,   # Store the calculated average for member 3
            school_year=selected_school_year
        )
        

         # Log the action in the audit trail
        AuditTrail.objects.create(
            user=request.user,
            action=f"Submitted evaluation in Mock Defense Schedule for project title '{schedule.title}'",
            ip_address=request.META.get('REMOTE_ADDR')
        )

        # creating a notif
        Notif.objects.create(
            created_by=request.user,
            notif=f"Faculty: '{request.user}', Submitted evaluation in Mock Defense Schedule for project title '{schedule.title}'",
        )

        # Retrieve all PreOral_Grade objects with the given project title
        grades = Mock_Grade.objects.filter(project_title=schedule.title, school_year=selected_school_year)
        print("count: ", grades.count())
        # Aggregate data
        summary_totals = {}
        for grade_by_panel in grades:
            summary_grades_data = grade_by_panel.get_grades_data()
            for section_name, section_grades in summary_grades_data.items():
                if section_name not in summary_totals:
                    summary_totals[section_name] = {'total': 0, 'count': 0}
                if isinstance(section_grades, dict):
                    total = sum(section_grades.values())
                    summary_totals[section_name]['total'] += total
                    summary_totals[section_name]['count'] += 1
                elif isinstance(section_grades, list):
                    try:
                        average = sum(section_grades) / len(section_grades)
                    except ZeroDivisionError:
                        average = 0
                    summary_totals[section_name]['total'] += average
                    summary_totals[section_name]['count'] += 1

        # Finalize totals by averaging over the count
        for section_name, data in summary_totals.items():
            if "Oral Presentation" in section_name or "Individual Grade" in section_name:
                # Divide by 3 for specific sections
                if data['count'] > 0:
                    summary_totals[section_name] = data['total'] / 3
                    summary_totals[section_name] = summary_totals[section_name] / 3
                else:
                    summary_totals[section_name] = 0
            else:
                # For other sections, just average over the count
                if data['count'] > 0:
                    summary_totals[section_name] = data['total'] / 3
                else:
                    summary_totals[section_name] = 0

        total_earned_points = sum(summary_totals.values())
        print(f"total points: {total_earned_points}")
        # Determine the verdict based on total earned points
        records = grades.count()
        if records < 3:
            selected_verdict = "Verdict is not available since not all of the panels submit the evaluation!"
        else:
            for verdict in verdicts:
                if total_earned_points >= verdict.percentage:
                    selected_verdict = f"{verdict.name} ({verdict.percentage}%)"
                    break
                
        print(f"verdict: {selected_verdict}")
        
        # Only update the verdict if there are exactly 3 records
        if records >= 3:
            for grade in grades:
                grade.verdict = selected_verdict if selected_verdict else None
                grade.save()
        if is_lead_panel:
            verdict_message = "Please check the verdict and submit it again!"
            url = reverse('mock_update_evaluate_capstone', kwargs={'schedule_id': schedule_id})
            query_string = urlencode({'verdict_has_changed': True, 'verdict_message': verdict_message})
            return redirect(f'{url}?{query_string}')
        else:
            return redirect("mock_defense")

# function to reirect to the preoral evaluation form and save the updated data
@login_required
def mock_update_evaluate_capstone(request, schedule_id):
    school_years = SchoolYear.objects.all().order_by('start_year')
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)


    schedule = get_object_or_404(ScheduleMD, id=schedule_id)
    user_profile = get_object_or_404(CustomUser, id=request.user.id)
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)
    # Fetch records from the Adviser model where the faculty is an adviser
    adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=False, declined=False)
    adviser_records2 = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)
    is_lead_panel = (schedule.faculty1 == faculty_member)

    criteria_list = Mock_EvaluationSection.objects.filter(school_year=selected_school_year).annotate(total_criteria_percentage=Sum('mcriteria__percentage'))
    criteria_percentage = Mock_Criteria.objects.filter(school_year=selected_school_year)
    total_points = sum(criteria.percentage for criteria in criteria_percentage) 
    group_members = [schedule.group.member1, schedule.group.member2, schedule.group.member3]
    verdicts = Mock_Verdict.objects.filter(school_year=selected_school_year).order_by('-percentage')

    # Fetch the PreOral_Grade entry for this schedule and faculty
    grade_entries = Mock_Grade.objects.filter(faculty=faculty_member.name, project_title=schedule.title, school_year=selected_school_year)

    # Initialize a dictionary to hold the aggregated grades data
    existing_grades_data = {}
    member_grades = {'member1': {}, 'member2': {}, 'member3': {}}


    existing_checkbox_data = None
    grade_entry = None
    # Iterate over each grade entry to decode and aggregate the grades data
    for grade_entry in grade_entries:
        # Retrieve existing data from the PreOral_Grade entry
        grades_data = grade_entry.get_grades_data()

        # Retrieve existing checkbox data from the PreOral_Grade entry
        existing_checkbox_data = grade_entry.get_checkbox_data()
        
        # Merge this entry's grades data into the aggregated data
        for section_name, section_grades in grades_data.items():
            if section_name not in existing_grades_data:
                existing_grades_data[section_name] = section_grades
            else:
                # Combine the grades if the section already exists
                for criteria, value in section_grades.items():
                    if criteria not in existing_grades_data[section_name]:
                        existing_grades_data[section_name][criteria] = value
                    else:
                        existing_grades_data[section_name][criteria] += value

    # Flatten the existing grades data for easy access in the template
    flattened_grades_data = {}
    for section_name, section_grades in existing_grades_data.items():
        for criteria_key, value in section_grades.items():
            flattened_key = f"{criteria_key}"
            flattened_grades_data[flattened_key] = value

    # Dynamically calculate totals for each category
    totals = {}
    # Calculate total for individual grades by summing values grouped by each member
    member_totals = {}
    for section_name, section_grades in existing_grades_data.items():
        if "Oral Presentation" in section_name or "Individual Grade" in section_name:
            
            for criteria_key, value in section_grades.items():
                member_key = criteria_key.split('_')[-1]  # e.g., 'member1' from 'criteria_1_member1'
                if member_key not in member_totals:
                    member_totals[member_key] = 0
                member_totals[member_key] += value

            # Calculate the average for each member
            number_of_members = len(member_totals)
            if number_of_members > 0:
                average_totals = {member: total / number_of_members for member, total in member_totals.items()}
            else:
                average_totals = member_totals
            
            totals[section_name] = average_totals
            print("individual grade: ", average_totals)
        else:
            # For other sections, just sum the values directly
            totals[section_name] = sum(section_grades.values())


    # Retrieve all Mock_Grade objects with the given project title
    grades = Mock_Grade.objects.filter(project_title=schedule.title, school_year=selected_school_year)

    # Initialize a dictionary to hold aggregated summary data
    summary_totals = {}

    for grade_by_panel in grades:
        # Decode grades data from JSON
        summary_grades_data = grade_by_panel.get_grades_data()

        # Aggregate data by section name
        for section_name, section_grades in summary_grades_data.items():
            if section_name not in summary_totals:
                # Initialize totals for new sections
                summary_totals[section_name] = {'total': 0, 'count': 0}

            if isinstance(section_grades, dict):
                # Sum values for each section
                total = sum(section_grades.values())
                summary_totals[section_name]['total'] += total
                summary_totals[section_name]['count'] += 1
            elif isinstance(section_grades, list):
                # Average values for lists
                try:
                    average = sum(section_grades) / len(section_grades)
                except ZeroDivisionError:
                    average = 0
                summary_totals[section_name]['total'] += average
                summary_totals[section_name]['count'] += 1
            else:
                print(f"Unexpected data format for section: {section_name}, data: {section_grades}")

    # Finalize totals by averaging over the count
    for section_name, data in summary_totals.items():
        if "Oral Presentation" in section_name or "Individual Grade" in section_name:
            # Divide by 3 for specific sections
            if data['count'] > 0:
                summary_totals[section_name] = data['total'] / 3
                summary_totals[section_name] = summary_totals[section_name] / 3
            else:
                summary_totals[section_name] = 0
        else:
            # For other sections, just average over the count
            if data['count'] > 0:
                summary_totals[section_name] = data['total'] / data['count']
            else:
                summary_totals[section_name] = 0


    total_earned_points = sum(summary_totals.values())
    print(f"total points1: {total_earned_points}") # for debugging purposes

    # Determine the verdict based on total earned points
    records = grades.count()
    verdict_name = ''
    checkboxes = []
    if records < 3:
        selected_verdict = "Verdict is not available since not all of the panels submit the evaluation!"
    else:
        for verdict in verdicts:
            if total_earned_points >= verdict.percentage:
                selected_verdict = f"{verdict.name} ({verdict.percentage}%)"
                verdict_name = verdict.name
                if selected_verdict:
                    checkboxes = Mock_Checkbox.objects.filter(verdict=verdict, school_year=selected_school_year)
                    print(checkboxes)
                break
                
    print(f"verdict: {selected_verdict}") # for debugging purposes
    
    # Initialize grade_entry and previous_verdict to None in case no records are found
    # grade_entry = None
    previous_verdict = None
    if grade_entries.exists():
        previous_verdict = grade_entry.verdict if grade_entry.verdict else None #variable to hold the previous verdict
    else:
        # Handle cases where no grade entries exist (e.g., default verdict behavior)
        print("No grade entries found for this schedule and faculty.")
        previous_verdict = None
    new_verdict = None #variable to hold the new verdict
    # When form is submitted
    if request.method == 'POST':
        # Retrieve hidden input values
        member1_grade = request.POST.get('member1_grades', 0)
        member2_grade = request.POST.get('member2_grades', 0)
        member3_grade = request.POST.get('member3_grades', 0)
        

        # Convert these values to floats
        try:
            member1_grade = float(member1_grade)
            member2_grade = float(member2_grade)
            member3_grade = float(member3_grade)
        except ValueError:
            member1_grade = member2_grade = member3_grade = 0
            print('error')

        # Prepare a dictionary to hold all updated grades
        updated_grades_data = {}

        # Process the submitted form data
        for section in criteria_list:
            section_grades = {}
            for criteria in section.mcriteria.all():
                if "Oral Presentation" in section.name or "Individual Grade" in section.name:
                    for member in group_members:
                        member_index = group_members.index(member) + 1
                        member_grade_key = f'criteria_{criteria.id}_member{member_index}'
                        grade_value = request.POST.get(member_grade_key)
                        if grade_value:
                            section_grades[f"{criteria.id}_member{member_index}"] = float(grade_value)
                else:
                    grade_key = f'criteria_{criteria.id}'
                    grade_value = request.POST.get(grade_key)
                    if grade_value:
                        section_grades[str(criteria.id)] = float(grade_value)

            updated_grades_data[section.name] = section_grades

        # Convert updated grades_data to JSON format
        grades_json = json.dumps(updated_grades_data)
        print('grades: ', grades_json)

        # this is to get the previous total points of this specific user
        # Initialize a variable to store the total grade
        total_grade_points = 0

        # Loop through the grade entries to extract the grades from grades_data (assuming it's a JSON field)
        for individual_grade_entry in grade_entries:
            # Extract the grades data (JSON field) for this entry
            grades_data = json.loads(individual_grade_entry.grades_data)  # Assuming `grades_data` is a JSON field in string format

            # Loop through the grades data to calculate the total for this specific record
            for section_name, section_grades in grades_data.items():
                # If the grades data is a dictionary (criteria-based grading)
                if "Oral Presentation" in section_name or "Individual Grade" in section_name:
                    # Add up the values of the section's grades
                    total_grade_points += sum(section_grades.values())/3
                    print('prepoints: ', total_grade_points)
                    # updated_total_points = updated_total_points / 3
                else:
                    total_grade_points += sum(section_grades.values())
           
        total_grade_points = total_grade_points/3
        print('prev points: ', total_grade_points)

        # this is to get the updated total points of the specific user
        updated_total_points = 0

        # Loop through the updated grades to calculate the total
        for section_name, section_grades in updated_grades_data.items():
            if isinstance(section_grades, dict):
                if "Oral Presentation" in section_name or "Individual Grade" in section_name:
                    # Add up the values of the section's grades
                    updated_total_points += sum(section_grades.values())/3
                    print('upoints: ', updated_total_points)
                    # updated_total_points = updated_total_points / 3
                else:
                    updated_total_points += sum(section_grades.values())
           
        updated_total_points = updated_total_points/3
        print('updated points: ', updated_total_points)

        # Fetch all PreOral_Grade records for the same project title
        related_grades = Mock_Grade.objects.filter(project_title=schedule.title, school_year=selected_school_year)
        records_count = related_grades.count()

        # Initialize a dictionary to hold aggregated summary data
        summary_totals = {}

        for grade_by_panel in grades:
            # Decode grades data from JSON
            summary_grades_data = grade_by_panel.get_grades_data()

            # Aggregate data by section name
            for section_name, section_grades in summary_grades_data.items():
                if section_name not in summary_totals:
                    # Initialize totals for new sections
                    summary_totals[section_name] = {'total': 0, 'count': 0}

                if isinstance(section_grades, dict):
                    # Sum values for each section
                    total = sum(section_grades.values())
                    summary_totals[section_name]['total'] += total
                    summary_totals[section_name]['count'] += 1
                elif isinstance(section_grades, list):
                    # Average values for lists
                    try:
                        average = sum(section_grades) / len(section_grades)
                    except ZeroDivisionError:
                        average = 0
                    summary_totals[section_name]['total'] += average
                    summary_totals[section_name]['count'] += 1
                else:
                    print(f"Unexpected data format for section: {section_name}, data: {section_grades}")

        # Finalize totals by averaging over the count
        for section_name, data in summary_totals.items():
            if "Oral Presentation" in section_name or "Individual Grade" in section_name:
                # Divide by 3 for specific sections
                if data['count'] > 0:
                    summary_totals[section_name] = data['total'] / 3
                    summary_totals[section_name] = summary_totals[section_name] / 3
                else:
                    summary_totals[section_name] = 0
            else:
                # For other sections, just average over the count
                if data['count'] > 0:
                    summary_totals[section_name] = data['total'] / 3
                else:
                    summary_totals[section_name] = 0

        
        # this is the updated grades/average
        total_earned_points2 = sum(summary_totals.values())
        print('summary_totals: ', sum(summary_totals.values()))
        total_earned_points2 = (total_earned_points2 - total_grade_points) + updated_total_points
        print(f"total points2: {total_earned_points2}")
        selected_verdict2 = ''
        verdict_variable = 0
        # set new verdict
        for verdict in verdicts:
            if total_earned_points2 >= verdict.percentage:
                selected_verdict2 = f"{verdict.name} ({verdict.percentage}%)"
                verdict_name = verdict.name
                verdict_variable = verdict
                print('updated verdict: ',selected_verdict2)
                new_verdict = selected_verdict2
                print('prev verdict: ', previous_verdict)
                break

        # Only update the verdict if there are exactly 3 records
        if records_count >= 3:
            for grade in related_grades:
                grade.verdict = selected_verdict2 if selected_verdict2 else None
                grade.school_year = selected_school_year
                grade.save()

        # save the updated grades   
        grade_entry.grades_data = grades_json
        grade_entry.verdict = selected_verdict2 if selected_verdict2 else None
        grade_entry.member1_grade = member1_grade
        grade_entry.member2_grade = member2_grade
        grade_entry.member3_grade = member3_grade
        grade_entry.school_year = selected_school_year
        grade_entry.save()
        print('success saving')
        print(f"Verdict '{selected_verdict2}' updated for all related records.")


          # Log the action in the audit trail
        AuditTrail.objects.create(
            user=request.user,
            action=f"Updated evaluation in Mock Defense Schedule for project title '{schedule.title}'",
            ip_address=request.META.get('REMOTE_ADDR')
        )

        # creating a notif
        Notif.objects.create(
            created_by=request.user,
            notif=f"Updated evaluation in Mock Defense Schedule for project title '{schedule.title}'",
        )


        # Process the checkboxes
        all_checkboxes = Mock_Checkbox.objects.filter(school_year=selected_school_year)
        checkboxes = Mock_Checkbox.objects.filter(verdict=verdict_variable, school_year=selected_school_year) if selected_verdict != "Verdict is not available since not all of the panels submit the evaluation!" else []
        
        verdict_has_changed = "False" #variable to handle whether the verdict has changed or not
        
        # Update checkbox states
        checkbox_data = {}

        for checkbox in all_checkboxes:
            checkbox_id = checkbox.id
            if previous_verdict != new_verdict:
                is_checked = False
                checkbox_data[checkbox_id] = is_checked 
                verdict_has_changed = "True"
            else:
                is_checked = request.POST.get(f'checkbox_{checkbox_id}', 'off') == 'on'
                checkbox_data[checkbox_id] = is_checked  # Store the checkbox state in a dictionary
            
            print('ch_jason: ', checkbox_data)
            print('is_check?: ', is_checked)
            print(f'POST data for checkbox_{checkbox_id}: {request.POST.get(f"checkbox_{checkbox_id}", "Not Found")}')
            print(checkbox_id)
            print(f'Looking for checkbox: checkbox_{checkbox_id}')
            # Only update the verdict if there are exactly 3 records
            if records_count >= 3:
                for grade in related_grades:
                    grade.checkbox_data = checkbox_data
                    grade.school_year = selected_school_year
                    grade.save()
            grade_entry.school_year = selected_school_year
            grade_entry.checkbox_data = checkbox_data
            grade_entry.save()
            
            # Check if the label contains 'Other' or 'Specify'
            if 'other' in checkbox.label.lower() or 'specify' in checkbox.label.lower():
                # Retrieve the 'Others' input field value if the checkbox is checked
                other_value = request.POST.get(f'other_input_{checkbox_id}', '')
                print("other: ", other_value)
                if records_count >= 3:
                    for grade in related_grades:
                        grade.othervalue = other_value 
                        grade.school_year = selected_school_year
                        grade.save()
                grade_entry.school_year = selected_school_year
                grade_entry.othervalue = other_value 
                grade_entry.save()

        # for debugging purposes only can be deleted
        if checkboxes:
            print(" TRUE, check: ",checkboxes)
        else:
            print('no checkbox')


        # applies only to the lead panel since he/she is the one who will choose the specific category based on the verdict selected 
        if is_lead_panel:
            # check if the selected verdict is not the default value which is equal to < 3 panels who graded the project
            if selected_verdict != "Verdict is not available since not all of the panels submit the evaluation!":
                # check if the selected verdict has checkboxes associated to it
                if checkboxes.exists():
                    related_grades2 = Mock_Grade.objects.filter(faculty=faculty_member.name, project_title=schedule.title, school_year=selected_school_year)
                    for grade in related_grades2:
                        checkbox_data = grade.checkbox_data
                        any_checkbox_checked = any(value for value in grade.checkbox_data.values()) #check if the value in checkbox_data has True
                        print(checkbox_data)
                        print('value: ', any_checkbox_checked)
                        # if the value has True meaning there is a checkbox selected
                        if any_checkbox_checked:
                            return redirect('mock_defense')
                        else:
                            print('success saving')
                            verdict_message = "Please confirm the verdict and submit it again!"
                            url = reverse('mock_update_evaluate_capstone', kwargs={'schedule_id': schedule_id})
                            query_string = urlencode({'verdict_has_changed': verdict_has_changed, 'verdict_message': verdict_message})
                            return redirect(f'{url}?{query_string}')
                else:
                    return redirect('mock_defense')
            else:
                # Redirect to the faculty dashboard if verdict is not available
                # messages.success(request, "Evaluation successfully submitted!")
                return redirect('mock_defense')
        else:
            return redirect('mock_defense')
    
    # use to get the pass verdict_has_changed variable from redirect
    verdict_has_changed_str = request.GET.get('verdict_has_changed') #variable to hold the value of the verdict_has_changed
    verdict_has_changed = verdict_has_changed_str.lower() == 'true' if verdict_has_changed_str else False #variable to hold a bolean value
    verdict_message = request.GET.get('verdict_message')
    print("true or false: ", verdict_has_changed)

    # Prepare context data for the form with existing data
    context = {
        'schedule': schedule,
        'faculty_member': faculty_member,
        'is_lead_panel': is_lead_panel,
        'criteria_list': criteria_list,
        'group_members': group_members,
        'existing_grades_data': flattened_grades_data,  # Pass flattened grades to the template
        'grade_entry': grade_entry,
        'total_points': total_points,
        'totals': totals, 
        'member_totals': member_totals,
        'summary_totals': summary_totals,
        'total_earned_points': total_earned_points,
        'verdicts': verdicts,
        'selected_verdict': selected_verdict,
        'verdict_name': verdict_name, 
        'checkboxes': checkboxes,
        'all_checkboxes': Mock_Checkbox.objects.filter(school_year=selected_school_year),
        'existing_checkbox_data': existing_checkbox_data,
        'verdict_has_changed': verdict_has_changed,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
        'verdict_message': verdict_message,
        'adviser_records': adviser_records,
        'adviser_records2': adviser_records2
    }
    

    return render(request, 'faculty/mock_grade/mock_update_input_grade.html', context)
# function to view the grade status of the group for the mock and for the adviser to input recommendations of the panels

@login_required
def mock_adviser_record_detail(request, adviser_id):
    # Fetch the CustomUser object associated with the logged-in user
    user_profile = get_object_or_404(CustomUser, id=request.user.id)

    # Fetch the Faculty object associated with the CustomUser
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)

    # Get all the school years
    school_years = SchoolYear.objects.all().order_by('start_year')

    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # Fetch records from the Adviser model where the faculty is an adviser
    adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=False, declined=False)
    adviser_records2 = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)

    adviser = get_object_or_404(Adviser, id=adviser_id)
    verdicts = Mock_Verdict.objects.filter(school_year=selected_school_year).order_by('-percentage')
    title = adviser.approved_title
    mock_grade_record = Mock_Grade.objects.filter(project_title=title, school_year=selected_school_year)
    recos = Mock_Recos.objects.filter(project_title=title, school_year=selected_school_year)
    all_checkboxes = Mock_Checkbox.objects.filter(school_year=selected_school_year)

    for reco in recos:
        reco.recommendation = escape(reco.recommendation)

    # Fetch group members
    # groups = GroupInfoMD.objects.filter(title=title, school_year=current_school_year)
    # member1 = groups.first().member1 if groups.exists() else None
    # member2 = groups.first().member2 if groups.exists() else None
    # member3 = groups.first().member3 if groups.exists() else None
    # group_members = f"Member1: {member1}, Member2: {member2}, Member3: {member3}"

    # Fetch group members
    groups = GroupInfoMD.objects.filter(title=title, school_year=selected_school_year)
    advisee_groups = Adviser.objects.filter(approved_title=title, school_year=selected_school_year)
    member1 = None
    member2 = None
    member3 = None
    if groups.exists():
        # Fetch members directly from GroupInfoPOD
        group = groups.first()  # Get the first group object
        member1 = group.member1
        member2 = group.member2
        member3 = group.member3
    else:
        # Fall back to splitting `group_name` from Adviser model
        if advisee_groups.exists():
            # Get the first matching adviser record
            advisee = advisee_groups.first()
            members = advisee.group_name.split('<br>') if advisee.group_name else []
            # Pad the members list to ensure it has at least 3 elements
            while len(members) < 3:
                members.append(None)  # Use `None` or an empty string as padding
            member1, member2, member3 = members[0], members[1], members[2]
            print("member1: ", member1)
        else:
            # If no matching adviser record, set members to None
            member1, member2, member3 = None, None, None
    group_members = f"Member1: {member1}, Member2: {member2}, Member3: {member3}"

    # Handle form submission
    if request.method == "POST":
        recommendation = request.POST.get("recommendation")
        reco = Mock_Recos.objects.filter(project_title=title, school_year=selected_school_year).first()

        if reco:
            reco.recommendation = recommendation
            if recommendation == "":
                reco.delete()
                # Log the action in the audit trail
                AuditTrail.objects.create(
                    user=request.user,
                    action=f"Deleted recommendation for in Mock Group Advisee Record project title '{title}'",
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            else:
                reco.save()
                # Log the action in the audit trail
                AuditTrail.objects.create(
                    user=request.user,
                    action=f"Updated recommendation in Mock Group Advisee Record for project title '{title}'",
                    ip_address=request.META.get('REMOTE_ADDR')
                )
        else:
            if recommendation != "":
                reco = Mock_Recos(
                    project_title=title,
                    recommendation=recommendation,
                    school_year=selected_school_year
                )
                reco.save()
                # Log the action in the audit trail
                AuditTrail.objects.create(
                    user=request.user,
                    action=f"Submitted recommendation in Mock Group Advisee Record for project title '{title}'",
                    ip_address=request.META.get('REMOTE_ADDR')
                )

        return redirect('mock_adviser_record_detail', adviser_id=adviser_id)

    grades = Mock_Grade.objects.filter(project_title=title, school_year=selected_school_year)
    criteria_list = Mock_EvaluationSection.objects.filter(school_year=selected_school_year).annotate(total_criteria_percentage=Sum('mcriteria__percentage'))
    criteria_percentage = Mock_Criteria.objects.filter(school_year=selected_school_year)
    total_points = sum(criteria.percentage for criteria in criteria_percentage)

    if not grades.exists():
        return render(request, 'faculty/mock_grade/adviser_record_detailMD.html', {
            'error': 'No grades found for this title',
            'title': title,
            'member1': member1,
            'member2': member2,
            'member3': member3,
            'adviser': adviser,
            'recos': recos,
            'faculty_member': faculty_member,
            'school_years': school_years,
            # 'current_school_year': current_school_year,
            'selected_school_year': selected_school_year,
            'last_school_year': last_school_year,
            'adviser_records': adviser_records,
            'adviser_records2': adviser_records2
        })

    member1_grade = grades.first().member1_grade if grades.exists() else None
    member2_grade = grades.first().member2_grade if grades.exists() else None
    member3_grade = grades.first().member3_grade if grades.exists() else None
    recommendation = grades.first().recommendation if grades.exists() else None
    total_grade1 = grades.aggregate(Sum('member1_grade'))['member1_grade__sum']
    total_grade2 = grades.aggregate(Sum('member2_grade'))['member2_grade__sum']
    total_grade3 = grades.aggregate(Sum('member3_grade'))['member3_grade__sum']

    average_grade1 = total_grade1 / 3 if total_grade1 is not None and grades.count() != 0 else 0
    average_grade2 = total_grade2 / 3 if total_grade2 is not None and grades.count() != 0 else 0
    average_grade3 = total_grade3 / 3 if total_grade3 is not None and grades.count() != 0 else 0

    summary_totals = {}
    for grade_by_panel in grades:
        summary_grades_data = grade_by_panel.get_grades_data()
        for section_name, section_grades in summary_grades_data.items():
            if section_name not in summary_totals:
                summary_totals[section_name] = {'total': 0, 'count': 0}
            if isinstance(section_grades, dict):
                total = sum(section_grades.values())
                summary_totals[section_name]['total'] += total
                summary_totals[section_name]['count'] += 1
            elif isinstance(section_grades, list):
                average = sum(section_grades) / len(section_grades) if section_grades else 0
                summary_totals[section_name]['total'] += average
                summary_totals[section_name]['count'] += 1

    for section_name, data in summary_totals.items():
        if "Oral Presentation" in section_name or "Individual Grade" in section_name:
            summary_totals[section_name] = data['total'] / 3 if data['count'] > 0 else 0
        else:
            summary_totals[section_name] = data['total'] / 3 if data['count'] > 0 else 0

    total_earned_points = sum(summary_totals.values())

    records = grades.count()
    selected_verdict = ''
    for checkbox_entry in mock_grade_record:
        checkbox_data = checkbox_entry.get_checkbox_data()
    if records < 3:
        selected_verdict = "Verdict is not available since not all of the panels submit the evaluation!"
    else:
        for verdict in verdicts:
            if total_earned_points >= verdict.percentage:
                selected_verdict = f"{verdict.name} ({verdict.percentage}%)"
                break

    context = {
        'adviser_id': adviser_id,
        'adviser': adviser,
        'title': title,
        'verdicts': verdicts,
        'selected_verdict': selected_verdict,
        'member1': member1,
        'member2': member2,
        'member3': member3,
        'member1_grade': average_grade1,
        'member2_grade': average_grade2,
        'member3_grade': average_grade3,
        'criteria_list': criteria_list,
        'summary_totals': summary_totals,
        'total_points': total_points,
        'total_earned_points': total_earned_points,
        'recommendation': recommendation,
        'recos': recos,
        'checkbox_data': checkbox_data,
        'all_checkboxes': all_checkboxes,
        'mock_grade_record': mock_grade_record,
        'checkbox_entry': checkbox_entry,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
        'faculty_member': faculty_member,
        'adviser_records': adviser_records,
        'adviser_records2': adviser_records2
    }

    return render(request, 'faculty/mock_grade/adviser_record_detailMD.html', context)
    
# function to fetch the preoral recommendations based on the project title
def mock_reco(request, schedule_id):
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # Fetch the CustomUser object associated with the logged-in user
    user_profile = get_object_or_404(CustomUser, id=request.user.id)

    # Fetch the Faculty object associated with the CustomUser
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)

    # Fetch records from the Adviser model where the faculty is an adviser
    adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=False, declined=False)
    adviser_records2 = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)

    schedule = get_object_or_404(ScheduleMD, id=schedule_id)
    recos = Mock_Recos.objects.filter(project_title=schedule.title, school_year=selected_school_year)
    print(recos)
    for reco in recos:
        reco.recommendation = escape(reco.recommendation)
    context = {
        'schedule': schedule,
        'recos': recos,
        'adviser_records': adviser_records,
        'adviser_records2': adviser_records2
    }
    return render(request, 'faculty/mock_grade/mock_reco.html', context)





# the following functions are used in the making of the final evaluation form
@csrf_exempt  # Use CSRF exempt for AJAX requests
@superuser_required
def final_add_section(request):
    if request.method == 'POST':
        form = Final_EvaluationSectionForm(request.POST)
        if form.is_valid():
            # Create the section
            section_name = form.cleaned_data['name']
            active_school_year = SchoolYear.get_active_school_year()
            selected_school_year_id = request.session.get('selected_school_year_id')
            # get the last school year added to the db
            last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

            # Get the selected school year from session or fallback to the active school year
            selected_school_year = ''
            if not selected_school_year_id:
                selected_school_year = last_school_year
                request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
            else:
                # Retrieve the selected school year based on the session
                selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

            if selected_school_year:
                if Final_EvaluationSection.objects.filter(name=section_name, school_year=selected_school_year).exists():
                    return JsonResponse({
                        'status': 'error',
                        'message': 'A section with this name already exists for the active school year.'
                    })

                section = form.save(commit=False)
                section.school_year = selected_school_year
                section.save()

                # Add audit trail entry
                AuditTrail.objects.create(
                    user=request.user,
                    action=f'Create a new Final Rubric: {section_name}',
                    time=timezone.now(),
                    ip_address=request.META.get('REMOTE_ADDR')
                )

                # Handle subcriteria creation
                subcriteria_count = 0
                while True:
                    criteria_name = request.POST.get(f'criteria_name_{subcriteria_count + 1}')
                    criteria_percentage = request.POST.get(f'criteria_percentage_{subcriteria_count + 1}')
                    criteria_description = request.POST.get(f'criteria_description_{subcriteria_count + 1}')

                    if criteria_name and criteria_percentage:
                        # Create subcriteria
                        criteria = Final_Criteria.objects.create(
                            section=section,
                            name=criteria_name,
                            percentage=criteria_percentage,
                            school_year=selected_school_year
                        )

                        # Create description
                        if criteria_description:
                            FinalCriterionDescription.objects.create(
                                criterion=criteria,
                                text=criteria_description,
                                school_year=selected_school_year
                            )

                        subcriteria_count += 1

                        # Add audit trail entry
                        AuditTrail.objects.create(
                            user=request.user,
                            action=f'Add subcriteria: {criteria_name} for Final Rubric: {section_name}',
                            time=timezone.now(),
                            ip_address=request.META.get('REMOTE_ADDR')
                        )
                    else:
                        break

                return JsonResponse({'status': 'success', 'section_id': section.id, 'name': section.name})

            else:
                return JsonResponse({'status': 'error', 'message': 'No active school year.'})

        return JsonResponse({'status': 'error', 'message': 'Invalid form submission.'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


@csrf_exempt
@superuser_required
def final_get_section_details(request, section_id):
    try:
        section = Final_EvaluationSection.objects.get(id=section_id)
        subcriteria = Final_Criteria.objects.filter(section=section).values('name', 'percentage', 'fdescriptions__text')

        # Prepare the response with subcriteria data
        subcriteria_data = []
        for criterion in subcriteria:
            description = criterion.get('fdescriptions__text', "")
            subcriteria_data.append({
                'name': criterion['name'],
                'percentage': criterion['percentage'],
                'description': description
            })

        return JsonResponse({'status': 'success', 'name': section.name, 'subcriteria': subcriteria_data})

    except Final_EvaluationSection.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Section not found.'})

@csrf_exempt
@superuser_required
def final_edit_section(request, section_id):
    if request.method == 'POST':
        # section_id = request.POST.get('section_id')
        # print('id: ', section_id)
        try:
            section = get_object_or_404(Final_EvaluationSection, pk=section_id)
            form = Final_EvaluationSectionForm(request.POST, instance=section)

            if form.is_valid():
                section_name = form.cleaned_data['name']
                section.name = section_name
                section.save()

                # Add audit trail entry
                AuditTrail.objects.create(
                    user=request.user,
                    action=f'Update a Final Rubric: {section_name} with ID {section_id}',
                    time=timezone.now(),
                    ip_address=request.META.get('REMOTE_ADDR')
                )

                # Update subcriteria
                Final_Criteria.objects.filter(section=section).delete()  # Remove all subcriteria first
                subcriteria_count = 0

                while True:
                    criteria_name = request.POST.get(f'criteria_name_{subcriteria_count + 1}')
                    criteria_percentage = request.POST.get(f'criteria_percentage_{subcriteria_count + 1}')
                    criteria_description = request.POST.get(f'criteria_description_{subcriteria_count + 1}')

                    if criteria_name and criteria_percentage:
                        # Recreate subcriteria
                        criteria = Final_Criteria.objects.create(
                            section=section,
                            name=criteria_name,
                            percentage=criteria_percentage,
                            school_year=section.school_year
                        )

                        # Recreate description
                        if criteria_description:
                            FinalCriterionDescription.objects.create(
                                criterion=criteria,
                                text=criteria_description,
                                school_year=section.school_year
                            )

                        subcriteria_count += 1
                        
                        # Add audit trail entry
                        AuditTrail.objects.create(
                            user=request.user,
                            action=f'Update subcriteria: {criteria_name} for Final Rubric: {section_name}',
                            time=timezone.now(),
                            ip_address=request.META.get('REMOTE_ADDR')
                        )
                    else:
                        break

                return JsonResponse({'status': 'success'})

            return JsonResponse({'status': 'error', 'message': 'Invalid form submission.'})
        
        except Final_EvaluationSection.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Section not found.'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


@csrf_exempt
@superuser_required
def final_delete_section(request, section_id):
    section = get_object_or_404(Final_EvaluationSection, pk=section_id)
    section_name = section.name
    section.delete()
    # Add audit trail entry
    AuditTrail.objects.create(
        user=request.user,
        action=f'Delete a Final Rubric: {section_name} with ID {section_id}',
        time=timezone.now(),
        ip_address=request.META.get('REMOTE_ADDR')
    )
    return JsonResponse({'status': 'success'})


@csrf_exempt
@superuser_required
def final_add_criteria(request, section_id):
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    section = get_object_or_404(Final_EvaluationSection, pk=section_id)

    if request.method == 'POST':
        form = Final_CriteriaForm(request.POST)
        if form.is_valid():
            criteria = form.save(commit=False)
            criteria.section = section
            criteria.school_year = selected_school_year
            criteria.save()
            return JsonResponse({'status': 'success', 'criteria_id': criteria.id, 'name': criteria.name})
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


@csrf_exempt
@superuser_required
def final_edit_criteria(request, criterion_id):
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    criterion = get_object_or_404(Final_Criteria, pk=criterion_id)

    if request.method == 'POST':
        form = Final_CriteriaForm(request.POST, instance=criterion)
        if form.is_valid():
            form.school_year = selected_school_year
            form.save()
            return JsonResponse({'status': 'success', 'name': criterion.name})
        else:
            return JsonResponse({'status': 'error', 'errors': form.errors})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


@csrf_exempt
@superuser_required
def final_delete_criteria(request, criterion_id):
    criterion = get_object_or_404(Final_Criteria, pk=criterion_id)
    criterion.delete()
    return JsonResponse({'status': 'success'})


@csrf_exempt
@superuser_required
def final_add_criteria_description(request, criterion_id):
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    criterion = get_object_or_404(Final_Criteria, pk=criterion_id)
    if request.method == 'POST':
        form = Final_CriterionDescriptionForm(request.POST)
        if form.is_valid():
            description = form.save(commit=False)
            description.criterion = criterion
            description.school_year = selected_school_year
            description.save()
            return JsonResponse({'status': 'success', 'description_id': description.id, 'text': description.text})
        return JsonResponse({'status': 'error', 'errors': form.errors})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


@csrf_exempt
@superuser_required
def final_edit_criteria_description(request, description_id):
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    description = get_object_or_404(FinalCriterionDescription, pk=description_id)
    if request.method == 'POST':
        form = Final_CriterionDescriptionForm(request.POST, instance=description)
        if form.is_valid():
            form.school_year = selected_school_year
            form.save()
            return JsonResponse({'status': 'success', 'text': description.text})
        return JsonResponse({'status': 'error', 'errors': form.errors})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


@csrf_exempt
@superuser_required
def final_delete_criteria_description(request, description_id):
    description = get_object_or_404(FinalCriterionDescription, pk=description_id)
    description.delete()
    return JsonResponse({'status': 'success'})


@csrf_exempt
@superuser_required
def final_add_verdict(request):
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    if request.method == 'POST':
        # Initialize forms with POST data
        verdict_form = Final_VerdictForm(request.POST)
        checkbox_form = Final_CheckboxForm(request.POST)
        
        # Debug print statements
        print('POST data received:', request.POST)
        
        # Validate the verdict form
        if verdict_form.is_valid():
            verdict = verdict_form.save(commit=False)
            verdict.school_year = selected_school_year
            verdict.save()

            # Add audit trail entry
            AuditTrail.objects.create(
                user=request.user,
                action=f'Create a new Final Verdict: {verdict.name}',
                time=timezone.now(),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            # Now handle the checkboxes
            if checkbox_form.is_valid():
                try:
                    checkbox_form.save_checkboxes(verdict, school_year=selected_school_year)
                    # Return success response if everything goes well
                    return JsonResponse({
                        'status': 'success',
                        'verdict_id': verdict.id,
                        'name': verdict.name
                    })
                except Exception as e:
                    # If there's an exception saving the checkboxes, print it
                    print("Error saving checkboxes:", e)
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Failed to save checkboxes.',
                        'verdict_id': verdict.id,
                        'errors': str(e)
                    })
            else:
                # If the checkbox form is invalid, return the errors
                print('Checkbox Form Errors:', checkbox_form.errors)
                return JsonResponse({
                    'status': 'error',
                    'message': 'Checkbox form is invalid.',
                    'verdict_id': verdict.id,  # Optionally provide the saved verdict ID
                    'checkbox_errors': checkbox_form.errors
                })
        else:
            # If the verdict form is invalid, return errors
            print('Verdict Form Errors:', verdict_form.errors)
            return JsonResponse({
                'status': 'error',
                'errors': {
                    'verdict_errors': verdict_form.errors
                }
            })

    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method.'
    })


@superuser_required
def final_edit_verdict(request, verdict_id):
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # Retrieve the verdict object
    verdict = get_object_or_404(Final_Verdict, pk=verdict_id)

    if request.method == 'POST':
        # Handle form submission
        form = Final_VerdictForm(request.POST, instance=verdict)

        if form.is_valid():
            form.school_year = selected_school_year
            form.save()  # Save the Verdict form first
            verdict.fcheckboxes.all().delete()

            # Handle dynamic checkboxes
            index = 0
            while True:
                label = request.POST.get(f'checkboxes[{index}][label]')
                if label is None:
                    break
                is_checked = request.POST.get(f'checkboxes[{index}][is_checked]', False) == 'on'
                
                # Create new checkbox or update if ID exists
                Final_Checkbox.objects.create(
                    verdict=verdict,
                    label=label,
                    is_checked=is_checked,
                    school_year=selected_school_year
                )
                index += 1

            # Add audit trail entry
            AuditTrail.objects.create(
                user=request.user,
                action=f'Update a Final Verdict: {verdict.name} with ID {verdict_id}',
                time=timezone.now(),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return JsonResponse({'success': True, 'message': 'Verdict updated successfully!'})

        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    # For GET request, provide the form and existing checkboxes
    checkbox_data = list(verdict.fcheckboxes.values('id', 'label', 'is_checked'))
    checkbox_data_json = json.dumps(checkbox_data)

    return JsonResponse({
        'form': Final_VerdictForm(instance=verdict).as_p(),
        'checkbox_data': checkbox_data_json,
        'csrf_token': request.META.get('CSRF_COOKIE'),  # Send CSRF token
    })


@csrf_exempt
@superuser_required
def final_delete_verdict(request, verdict_id):
    verdict = get_object_or_404(Final_Verdict, pk=verdict_id)
    verdict.delete()
    # Add audit trail entry
    AuditTrail.objects.create(
        user=request.user,
        action=f'Delete a Final Verdict: {verdict.name} with ID {verdict_id}',
        time=timezone.now(),
        ip_address=request.META.get('REMOTE_ADDR')
    )
    return JsonResponse({'status': 'success'})

# functions for the viewing of the sections and criteria
@superuser_required #use to prevent access from not admin users 
def final_view_section(request):
    # Check for the conflict query parameter
    empty_str = request.GET.get('empty')  # Should return True if 'conflict' param is 'True'
    message = request.GET.get('message')
    empty = empty_str.lower() == 'true' if empty_str else False #variable to hold a bolean value

    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()

    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)
    
    # Get all available school years
    school_years = SchoolYear.objects.all().order_by('start_year')
    if school_years.count() == 0:
        SchoolYear.create_new_school_year()
        school_years = SchoolYear.objects.all().order_by('start_year')

    sy_count = school_years.count()

    # Fetch all sections and prefetch related Final_Criteria and their related FinalCriterionDescription (fdescriptions)
    sections = Final_EvaluationSection.objects.filter(school_year=selected_school_year).prefetch_related('fcriteria__fdescriptions')
    verdicts = Final_Verdict.objects.prefetch_related('fcheckboxes').filter(school_year=selected_school_year)
    description_count = FinalCriterionDescription.objects.filter(school_year=selected_school_year).count()
    return render(request, 'admin/final/Final_Evaluation/final_view_section.html', {
        'sections': sections, 
        'verdicts': verdicts,
        'school_years': school_years,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'sy_count': sy_count,
        'empty': empty,
        'message': message,
        'description_count': description_count
        })


# function to redirect to the preoral evaluation form
@login_required
def final_input_grade(request, schedule_id):
    school_years = SchoolYear.objects.all().order_by('start_year')
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    schedule = get_object_or_404(ScheduleFD, id=schedule_id)
    user_profile = get_object_or_404(CustomUser, id=request.user.id)
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)
    # Fetch records from the Adviser model where the faculty is an adviser
    adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=False, declined=False)
    adviser_records2 = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)
    is_lead_panel = (schedule.faculty1 == faculty_member)

    # Fetch all criteria and verdicts from the database
    criteria_list = Final_EvaluationSection.objects.filter(school_year=selected_school_year).annotate(total_criteria_percentage=Sum('fcriteria__percentage'))
    criteria_percentage = Final_Criteria.objects.filter(school_year=selected_school_year)
    verdicts = Final_Verdict.objects.filter(school_year=selected_school_year)
    sections = Final_EvaluationSection.objects.filter(school_year=selected_school_year).prefetch_related('fcriteria__descriptions')

    # Fetch group members from the schedule
    group_members = [schedule.group.member1, schedule.group.member2, schedule.group.member3]
    
    # total_criteria_percentage = PreOral_EvaluationSection.objects.annotate(total_percentage=Sum('criteria__percentage'))

    
    total_percentage = sum(criteria.percentage for criteria in criteria_percentage) 

    # Retrieve all PreOral_Grade objects with the given project title
    grades = Final_Grade.objects.filter(project_title=schedule.title, school_year=selected_school_year)
    
    # Initialize a dictionary to hold aggregated summary data
    summary_totals = {}
    
    for grade_by_panel in grades:
        # Decode grades data from JSON
        summary_grades_data = grade_by_panel.get_grades_data()
        print(f"Summary points from grade_by_panel: {grade_by_panel} {summary_grades_data}")
        
        # Aggregate data by section name
        for section_name, section_grades in summary_grades_data.items():
            if section_name not in summary_totals:
                # Initialize totals for new sections
                summary_totals[section_name] = {'total': 0, 'count': 0}
            
            if isinstance(section_grades, dict):
                # Sum values for each section
                total = sum(section_grades.values())
                summary_totals[section_name]['total'] += total
                summary_totals[section_name]['count'] += 1
            elif isinstance(section_grades, list):
                # Average values for lists
                try:
                    average = sum(section_grades) / len(section_grades)
                except ZeroDivisionError:
                    average = 0
                summary_totals[section_name]['total'] += average
                summary_totals[section_name]['count'] += 1
            else:
                print(f"Unexpected data format for section: {section_name}, data: {section_grades}")
    
    # Finalize totals by averaging over the count
    # for section_name, data in summary_totals.items():
    #     if data['count'] > 0:
    #         summary_totals[section_name] = data['total'] / 3 #data['count'] 
            
    #     else:
    #         summary_totals[section_name] = 0
    
    # Finalize totals by averaging over the count
    for section_name, data in summary_totals.items():
        if "Oral Presentation" in section_name or "Individual Grade" in section_name:
            # Divide by 3 for specific sections
            if data['count'] > 0:
                summary_totals[section_name] = data['total'] / 3
                summary_totals[section_name] = summary_totals[section_name] / 3
            else:
                summary_totals[section_name] = 0
        else:
            # For other sections, just average over the count
            if data['count'] > 0:
                summary_totals[section_name] = data['total'] / 3 #data['count']
            else:
                summary_totals[section_name] = 0
            
    total_earned_points = sum(summary_totals.values())
    print('summary total: ', summary_totals.values())
    print(f"Final Summary Totals: {total_earned_points}")

    # Determine the verdict based on total earned points
    records = grades.count()
    if records < 3:
        selected_verdict = "Verdict is not available since not all of the panels submit the evaluation!"
    else:
        for verdict in verdicts:
            if total_earned_points <= verdict.percentage:
                selected_verdict = verdict
                
    print(f"verdict: {selected_verdict}")

    context = {
        'schedule': schedule,
        'faculty_member': faculty_member,
        'is_lead_panel': is_lead_panel,
        'schedule_id': schedule_id,
        'criteria_list': criteria_list,
        'verdicts': verdicts,
        'group_members': group_members,
        'total_percentage': total_percentage,
        'summary_totals': summary_totals,
        'total_earned_points': total_earned_points,
        'selected_verdict': selected_verdict,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
        'sections': sections,
        'adviser_records': adviser_records,
        'adviser_records2': adviser_records2
        # 'total_criteria_percentage': total_criteria_percentage,
    }

    return render(request, 'faculty/final_grade/final_input_grade.html', context)

# function to save the data from the evaltion form for preoral
@login_required
def final_evaluate_capstone(request, schedule_id):
    school_years = SchoolYear.objects.all().order_by('start_year')
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    schedule = get_object_or_404(ScheduleFD, id=schedule_id)
    user_profile = get_object_or_404(CustomUser, id=request.user.id)
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)
    is_lead_panel = (schedule.faculty1 == faculty_member)

    sections = Final_EvaluationSection.objects.filter(school_year=selected_school_year).prefetch_related('fcriteria')
    group_members = [schedule.group.member1, schedule.group.member2, schedule.group.member3]
    verdicts = Final_Verdict.objects.filter(school_year=selected_school_year).order_by('-percentage')

    if request.method == 'POST':
        grades_data = {}
        member_grades = {'member1': {}, 'member2': {}, 'member3': {}}

        for section in sections:
            section_grades = {}
            for criteria in section.fcriteria.all():
                if "Oral Presentation" in section.name or "Individual Grade" in section.name:
                    for member in group_members:
                        member_index = group_members.index(member) + 1
                        member_grade_key = f'criteria_{criteria.id}_member{member_index}'
                        grade_value = request.POST.get(member_grade_key)
                        if grade_value:
                            section_grades[f"{criteria.id}_member{member_index}"] = float(grade_value)
                            member_key = f'member{member_index}'
                            member_grades[member_key][criteria.id] = float(grade_value)
                else:
                    grade_key = f'criteria_{criteria.id}'
                    grade_value = request.POST.get(grade_key)
                    if grade_value:
                        section_grades[str(criteria.id)] = float(grade_value)

            grades_data[section.name] = section_grades

        # Prepare to save the member grades in the new fields
        member1_avg = sum(member_grades['member1'].values()) if member_grades['member1'] else -1
        member2_avg = sum(member_grades['member2'].values()) if member_grades['member2'] else -1
        member3_avg = sum(member_grades['member3'].values()) if member_grades['member3'] else -1
        print(f'member1: {member1_avg}')
        print(f'member2: {member2_avg}')
        print(f'member3: {member3_avg}')

        # Save the data to the PreOral_Grade model
        selected_verdict = 'None'
        grades_json = json.dumps(grades_data)

        
        Final_Grade.objects.create(
            faculty=faculty_member.name,
            project_title=schedule.title,
            grades_data=grades_json,
            verdict=selected_verdict,
            member1_grade=member1_avg,  # Store the calculated average for member 1
            member2_grade=member2_avg,  # Store the calculated average for member 2
            member3_grade=member3_avg,   # Store the calculated average for member 3
            school_year=selected_school_year
        )
        

         # Log the action in the audit trail
        AuditTrail.objects.create(
            user=request.user,
            action=f"Submitted evaluation in Final Defense Schedule for project title '{schedule.title}'",
            ip_address=request.META.get('REMOTE_ADDR')
        )

        # creating a notif
        Notif.objects.create(
            created_by=request.user,
            notif=f"Faculty: '{request.user}', Submitted evaluation in Final Defense Schedule for project title '{schedule.title}'",
        )


        # Retrieve all PreOral_Grade objects with the given project title
        grades = Final_Grade.objects.filter(project_title=schedule.title, school_year=selected_school_year)
        print("count: ", grades.count())
        # Aggregate data
        summary_totals = {}
        for grade_by_panel in grades:
            summary_grades_data = grade_by_panel.get_grades_data()
            for section_name, section_grades in summary_grades_data.items():
                if section_name not in summary_totals:
                    summary_totals[section_name] = {'total': 0, 'count': 0}
                if isinstance(section_grades, dict):
                    total = sum(section_grades.values())
                    summary_totals[section_name]['total'] += total
                    summary_totals[section_name]['count'] += 1
                elif isinstance(section_grades, list):
                    try:
                        average = sum(section_grades) / len(section_grades)
                    except ZeroDivisionError:
                        average = 0
                    summary_totals[section_name]['total'] += average
                    summary_totals[section_name]['count'] += 1

        # Finalize totals by averaging over the count
        for section_name, data in summary_totals.items():
            if "Oral Presentation" in section_name or "Individual Grade" in section_name:
                # Divide by 3 for specific sections
                if data['count'] > 0:
                    summary_totals[section_name] = data['total'] / 3
                    summary_totals[section_name] = summary_totals[section_name] / 3
                else:
                    summary_totals[section_name] = 0
            else:
                # For other sections, just average over the count
                if data['count'] > 0:
                    summary_totals[section_name] = data['total'] / 3
                else:
                    summary_totals[section_name] = 0

        total_earned_points = sum(summary_totals.values())
        print(f"total points: {total_earned_points}")
        # Determine the verdict based on total earned points
        records = grades.count()
        if records < 3:
            selected_verdict = "Verdict is not available since not all of the panels submit the evaluation!"
        else:
            for verdict in verdicts:
                if total_earned_points >= verdict.percentage:
                    selected_verdict = f"{verdict.name} ({verdict.percentage}%)"
                    break
                
        print(f"verdict: {selected_verdict}")
        
        # Only update the verdict if there are exactly 3 records
        if records >= 3:
            for grade in grades:
                grade.verdict = selected_verdict if selected_verdict else None
                grade.save()
        if is_lead_panel:
            verdict_message = "Please check the verdict and submit it again!"
            url = reverse('final_update_evaluate_capstone', kwargs={'schedule_id': schedule_id})
            query_string = urlencode({'verdict_has_changed': True, 'verdict_message': verdict_message})
            return redirect(f'{url}?{query_string}')
        else:
            return redirect("final_defense")

# function to reirect to the preoral evaluation form and save the updated data
@login_required
def final_update_evaluate_capstone(request, schedule_id):
    school_years = SchoolYear.objects.all().order_by('start_year')
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)


    schedule = get_object_or_404(ScheduleFD, id=schedule_id)
    user_profile = get_object_or_404(CustomUser, id=request.user.id)
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)
    # Fetch records from the Adviser model where the faculty is an adviser
    adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=False, declined=False)
    adviser_records2 = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)
    is_lead_panel = (schedule.faculty1 == faculty_member)

    criteria_list = Final_EvaluationSection.objects.filter(school_year=selected_school_year).annotate(total_criteria_percentage=Sum('fcriteria__percentage'))
    criteria_percentage = Final_Criteria.objects.filter(school_year=selected_school_year)
    total_points = sum(criteria.percentage for criteria in criteria_percentage) 
    group_members = [schedule.group.member1, schedule.group.member2, schedule.group.member3]
    verdicts = Final_Verdict.objects.filter(school_year=selected_school_year).order_by('-percentage')

    # Fetch the PreOral_Grade entry for this schedule and faculty
    grade_entries = Final_Grade.objects.filter(faculty=faculty_member.name, project_title=schedule.title, school_year=selected_school_year)

    # Initialize a dictionary to hold the aggregated grades data
    existing_grades_data = {}
    member_grades = {'member1': {}, 'member2': {}, 'member3': {}}

    grade_entry = None
    existing_checkbox_data = None
    # Iterate over each grade entry to decode and aggregate the grades data
    for grade_entry in grade_entries:
        # Retrieve existing data from the PreOral_Grade entry
        grades_data = grade_entry.get_grades_data()

        # Retrieve existing checkbox data from the PreOral_Grade entry
        existing_checkbox_data = grade_entry.get_checkbox_data()
        
        # Merge this entry's grades data into the aggregated data
        for section_name, section_grades in grades_data.items():
            if section_name not in existing_grades_data:
                existing_grades_data[section_name] = section_grades
            else:
                # Combine the grades if the section already exists
                for criteria, value in section_grades.items():
                    if criteria not in existing_grades_data[section_name]:
                        existing_grades_data[section_name][criteria] = value
                    else:
                        existing_grades_data[section_name][criteria] += value

    # Flatten the existing grades data for easy access in the template
    flattened_grades_data = {}
    for section_name, section_grades in existing_grades_data.items():
        for criteria_key, value in section_grades.items():
            flattened_key = f"{criteria_key}"
            flattened_grades_data[flattened_key] = value

    # Dynamically calculate totals for each category
    totals = {}
    # Calculate total for individual grades by summing values grouped by each member
    member_totals = {}
    for section_name, section_grades in existing_grades_data.items():
        if "Oral Presentation" in section_name or "Individual Grade" in section_name:
            
            for criteria_key, value in section_grades.items():
                member_key = criteria_key.split('_')[-1]  # e.g., 'member1' from 'criteria_1_member1'
                if member_key not in member_totals:
                    member_totals[member_key] = 0
                member_totals[member_key] += value

            # Calculate the average for each member
            number_of_members = len(member_totals)
            if number_of_members > 0:
                average_totals = {member: total / number_of_members for member, total in member_totals.items()}
            else:
                average_totals = member_totals
            
            totals[section_name] = average_totals
            print("individual grade: ", average_totals)
        else:
            # For other sections, just sum the values directly
            totals[section_name] = sum(section_grades.values())


    # Retrieve all Final_Grade objects with the given project title
    grades = Final_Grade.objects.filter(project_title=schedule.title, school_year=selected_school_year)

    # Initialize a dictionary to hold aggregated summary data
    summary_totals = {}

    for grade_by_panel in grades:
        # Decode grades data from JSON
        summary_grades_data = grade_by_panel.get_grades_data()

        # Aggregate data by section name
        for section_name, section_grades in summary_grades_data.items():
            if section_name not in summary_totals:
                # Initialize totals for new sections
                summary_totals[section_name] = {'total': 0, 'count': 0}

            if isinstance(section_grades, dict):
                # Sum values for each section
                total = sum(section_grades.values())
                summary_totals[section_name]['total'] += total
                summary_totals[section_name]['count'] += 1
            elif isinstance(section_grades, list):
                # Average values for lists
                try:
                    average = sum(section_grades) / len(section_grades)
                except ZeroDivisionError:
                    average = 0
                summary_totals[section_name]['total'] += average
                summary_totals[section_name]['count'] += 1
            else:
                print(f"Unexpected data format for section: {section_name}, data: {section_grades}")

    # Finalize totals by averaging over the count
    for section_name, data in summary_totals.items():
        if "Oral Presentation" in section_name or "Individual Grade" in section_name:
            # Divide by 3 for specific sections
            if data['count'] > 0:
                summary_totals[section_name] = data['total'] / 3
                summary_totals[section_name] = summary_totals[section_name] / 3
            else:
                summary_totals[section_name] = 0
        else:
            # For other sections, just average over the count
            if data['count'] > 0:
                summary_totals[section_name] = data['total'] / data['count']
            else:
                summary_totals[section_name] = 0


    total_earned_points = sum(summary_totals.values())
    print(f"total points1: {total_earned_points}") # for debugging purposes

    # Determine the verdict based on total earned points
    records = grades.count()
    verdict_name = ''
    checkboxes = []
    if records < 3:
        selected_verdict = "Verdict is not available since not all of the panels submit the evaluation!"
    else:
        for verdict in verdicts:
            if total_earned_points >= verdict.percentage:
                selected_verdict = f"{verdict.name} ({verdict.percentage}%)"
                verdict_name = verdict.name
                if selected_verdict:
                    checkboxes = Final_Checkbox.objects.filter(verdict=verdict, school_year=selected_school_year)
                    print(checkboxes)
                break
                
    print(f"verdict: {selected_verdict}") # for debugging purposes
    

    previous_verdict = None
    if grade_entries.exists():
        # If records are found, assign the first entry to grade_entry and retrieve the verdict
        previous_verdict = grade_entry.verdict if grade_entry.verdict else None
    else:
        # Handle cases where no grade entries exist (e.g., default verdict behavior)
        print("No grade entries found for this schedule and faculty.")
    new_verdict = None #variable to hold the new verdict
    # When form is submitted
    if request.method == 'POST':
        # Retrieve hidden input values
        member1_grade = request.POST.get('member1_grades', 0)
        member2_grade = request.POST.get('member2_grades', 0)
        member3_grade = request.POST.get('member3_grades', 0)
        

        # Convert these values to floats
        try:
            member1_grade = float(member1_grade)
            member2_grade = float(member2_grade)
            member3_grade = float(member3_grade)
        except ValueError:
            member1_grade = member2_grade = member3_grade = 0
            print('error')

        # Prepare a dictionary to hold all updated grades
        updated_grades_data = {}

        # Process the submitted form data
        for section in criteria_list:
            section_grades = {}
            for criteria in section.fcriteria.all():
                if "Oral Presentation" in section.name or "Individual Grade" in section.name:
                    for member in group_members:
                        member_index = group_members.index(member) + 1
                        member_grade_key = f'criteria_{criteria.id}_member{member_index}'
                        grade_value = request.POST.get(member_grade_key)
                        if grade_value:
                            section_grades[f"{criteria.id}_member{member_index}"] = float(grade_value)
                else:
                    grade_key = f'criteria_{criteria.id}'
                    grade_value = request.POST.get(grade_key)
                    if grade_value:
                        section_grades[str(criteria.id)] = float(grade_value)

            updated_grades_data[section.name] = section_grades

        # Convert updated grades_data to JSON format
        grades_json = json.dumps(updated_grades_data)
        print('grades: ', grades_json)

        # this is to get the previous total points of this specific user
        # Initialize a variable to store the total grade
        total_grade_points = 0

        # Loop through the grade entries to extract the grades from grades_data (assuming it's a JSON field)
        for individual_grade_entry in grade_entries:
            # Extract the grades data (JSON field) for this entry
            grades_data = json.loads(individual_grade_entry.grades_data)  # Assuming `grades_data` is a JSON field in string format

            # Loop through the grades data to calculate the total for this specific record
            for section_name, section_grades in grades_data.items():
                # If the grades data is a dictionary (criteria-based grading)
                if "Oral Presentation" in section_name or "Individual Grade" in section_name:
                    # Add up the values of the section's grades
                    total_grade_points += sum(section_grades.values())/3
                    print('prepoints: ', total_grade_points)
                    # updated_total_points = updated_total_points / 3
                else:
                    total_grade_points += sum(section_grades.values())
           
        total_grade_points = total_grade_points/3
        print('prev points: ', total_grade_points)

        # this is to get the updated total points of the specific user
        updated_total_points = 0

        # Loop through the updated grades to calculate the total
        for section_name, section_grades in updated_grades_data.items():
            if isinstance(section_grades, dict):
                if "Oral Presentation" in section_name or "Individual Grade" in section_name:
                    # Add up the values of the section's grades
                    updated_total_points += sum(section_grades.values())/3
                    print('upoints: ', updated_total_points)
                    # updated_total_points = updated_total_points / 3
                else:
                    updated_total_points += sum(section_grades.values())
           
        updated_total_points = updated_total_points/3
        print('updated points: ', updated_total_points)

        # Fetch all PreOral_Grade records for the same project title
        related_grades = Final_Grade.objects.filter(project_title=schedule.title, school_year=selected_school_year)
        records_count = related_grades.count()

        # Initialize a dictionary to hold aggregated summary data
        summary_totals = {}

        for grade_by_panel in grades:
            # Decode grades data from JSON
            summary_grades_data = grade_by_panel.get_grades_data()

            # Aggregate data by section name
            for section_name, section_grades in summary_grades_data.items():
                if section_name not in summary_totals:
                    # Initialize totals for new sections
                    summary_totals[section_name] = {'total': 0, 'count': 0}

                if isinstance(section_grades, dict):
                    # Sum values for each section
                    total = sum(section_grades.values())
                    summary_totals[section_name]['total'] += total
                    summary_totals[section_name]['count'] += 1
                elif isinstance(section_grades, list):
                    # Average values for lists
                    try:
                        average = sum(section_grades) / len(section_grades)
                    except ZeroDivisionError:
                        average = 0
                    summary_totals[section_name]['total'] += average
                    summary_totals[section_name]['count'] += 1
                else:
                    print(f"Unexpected data format for section: {section_name}, data: {section_grades}")

        # Finalize totals by averaging over the count
        for section_name, data in summary_totals.items():
            if "Oral Presentation" in section_name or "Individual Grade" in section_name:
                # Divide by 3 for specific sections
                if data['count'] > 0:
                    summary_totals[section_name] = data['total'] / 3
                    summary_totals[section_name] = summary_totals[section_name] / 3
                else:
                    summary_totals[section_name] = 0
            else:
                # For other sections, just average over the count
                if data['count'] > 0:
                    summary_totals[section_name] = data['total'] / 3
                else:
                    summary_totals[section_name] = 0

        
        # this is the updated grades/average
        total_earned_points2 = sum(summary_totals.values())
        print('summary_totals: ', sum(summary_totals.values()))
        total_earned_points2 = (total_earned_points2 - total_grade_points) + updated_total_points
        print(f"total points2: {total_earned_points2}")
        selected_verdict2 = ''
        verdict_variable = 0
        # set new verdict
        for verdict in verdicts:
            if total_earned_points2 >= verdict.percentage:
                selected_verdict2 = f"{verdict.name} ({verdict.percentage}%)"
                verdict_name = verdict.name
                verdict_variable = verdict
                print('updated verdict: ',selected_verdict2)
                new_verdict = selected_verdict2
                print('prev verdict: ', previous_verdict)
                break

        # Only update the verdict if there are exactly 3 records
        if records_count >= 3:
            for grade in related_grades:
                grade.verdict = selected_verdict2 if selected_verdict2 else None
                grade.school_year = selected_school_year
                grade.save()

        # save the updated grades   
        grade_entry.grades_data = grades_json
        grade_entry.verdict = selected_verdict2 if selected_verdict2 else None
        grade_entry.member1_grade = member1_grade
        grade_entry.member2_grade = member2_grade
        grade_entry.member3_grade = member3_grade
        grade_entry.school_year = selected_school_year
        grade_entry.save()
        print('success saving')
        print(f"Verdict '{selected_verdict2}' updated for all related records.")

         # Log the action in the audit trail
        AuditTrail.objects.create(
            user=request.user,
            action=f"Updated evaluation in Final Defense Schedule for project title '{schedule.title}'",
            ip_address=request.META.get('REMOTE_ADDR')
        )

        # creating a notif
        Notif.objects.create(
            created_by=request.user,
            notif=f"Faculty: '{request.user}', Updated evaluation in Final Defense Schedule for project title '{schedule.title}'",
        )

        # Process the checkboxes
        all_checkboxes = Final_Checkbox.objects.filter(school_year=selected_school_year)
        checkboxes = Final_Checkbox.objects.filter(verdict=verdict_variable, school_year=selected_school_year) if selected_verdict != "Verdict is not available since not all of the panels submit the evaluation!" else []
        
        verdict_has_changed = "False" #variable to handle whether the verdict has changed or not
        
        # Update checkbox states
        checkbox_data = {}

        for checkbox in all_checkboxes:
            checkbox_id = checkbox.id
            if previous_verdict != new_verdict:
                is_checked = False
                checkbox_data[checkbox_id] = is_checked 
                verdict_has_changed = "True"
            else:
                is_checked = request.POST.get(f'checkbox_{checkbox_id}', 'off') == 'on'
                checkbox_data[checkbox_id] = is_checked  # Store the checkbox state in a dictionary
            
            print('ch_jason: ', checkbox_data)
            print('is_check?: ', is_checked)
            print(f'POST data for checkbox_{checkbox_id}: {request.POST.get(f"checkbox_{checkbox_id}", "Not Found")}')
            print(checkbox_id)
            print(f'Looking for checkbox: checkbox_{checkbox_id}')
            # Only update the verdict if there are exactly 3 records
            if records_count >= 3:
                for grade in related_grades:
                    grade.checkbox_data = checkbox_data
                    grade.school_year = selected_school_year
                    grade.save()
            grade_entry.school_year = selected_school_year
            grade_entry.checkbox_data = checkbox_data
            grade_entry.save()
            
            # Check if the label contains 'Other' or 'Specify'
            if 'other' in checkbox.label.lower() or 'specify' in checkbox.label.lower():
                # Retrieve the 'Others' input field value if the checkbox is checked
                other_value = request.POST.get(f'other_input_{checkbox_id}', '')
                print("other: ", other_value)
                if records_count >= 3:
                    for grade in related_grades:
                        grade.othervalue = other_value 
                        grade.school_year = selected_school_year
                        grade.save()
                grade_entry.school_year = selected_school_year
                grade_entry.othervalue = other_value 
                grade_entry.save()

        # for debugging purposes only can be deleted
        if checkboxes:
            print(" TRUE, check: ",checkboxes)
        else:
            print('no checkbox')


        # applies only to the lead panel since he/she is the one who will choose the specific category based on the verdict selected 
        if is_lead_panel:
            # check if the selected verdict is not the default value which is equal to < 3 panels who graded the project
            if selected_verdict != "Verdict is not available since not all of the panels submit the evaluation!":
                # check if the selected verdict has checkboxes associated to it
                if checkboxes.exists():
                    related_grades2 = Final_Grade.objects.filter(faculty=faculty_member.name, project_title=schedule.title, school_year=selected_school_year)
                    for grade in related_grades2:
                        checkbox_data = grade.checkbox_data
                        any_checkbox_checked = any(value for value in grade.checkbox_data.values()) #check if the value in checkbox_data has True
                        print(checkbox_data)
                        print('value: ', any_checkbox_checked)
                        # if the value has True meaning there is a checkbox selected
                        if any_checkbox_checked:
                            return redirect('final_defense')
                        else:
                            print('success saving')
                            verdict_message = "Please confirm the verdict and submit it again!"
                            url = reverse('final_update_evaluate_capstone', kwargs={'schedule_id': schedule_id})
                            query_string = urlencode({'verdict_has_changed': verdict_has_changed, 'verdict_message': verdict_message})
                            return redirect(f'{url}?{query_string}')
                else:
                    return redirect('final_defense')
            else:
                # Redirect to the faculty dashboard if verdict is not available
                # messages.success(request, "Evaluation successfully submitted!")
                return redirect('final_defense')
        else:
            return redirect('final_defense')
    
    # use to get the pass verdict_has_changed variable from redirect
    verdict_has_changed_str = request.GET.get('verdict_has_changed') #variable to hold the value of the verdict_has_changed
    verdict_has_changed = verdict_has_changed_str.lower() == 'true' if verdict_has_changed_str else False #variable to hold a bolean value
    print("true or false: ", verdict_has_changed)
    verdict_message = request.GET.get('verdict_message')

    # Prepare context data for the form with existing data
    context = {
        'schedule': schedule,
        'faculty_member': faculty_member,
        'is_lead_panel': is_lead_panel,
        'criteria_list': criteria_list,
        'group_members': group_members,
        'existing_grades_data': flattened_grades_data,  # Pass flattened grades to the template
        'grade_entry': grade_entry,
        'total_points': total_points,
        'totals': totals, 
        'member_totals': member_totals,
        'summary_totals': summary_totals,
        'total_earned_points': total_earned_points,
        'verdicts': verdicts,
        'selected_verdict': selected_verdict,
        'verdict_name': verdict_name, 
        'checkboxes': checkboxes,
        'all_checkboxes': Final_Checkbox.objects.filter(school_year=selected_school_year),
        'existing_checkbox_data': existing_checkbox_data,
        'verdict_has_changed': verdict_has_changed,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
        'verdict_message': verdict_message,
        'adviser_records': adviser_records,
        'adviser_records2': adviser_records2
    }
    

    return render(request, 'faculty/final_grade/final_update_input_grade.html', context)

# function to view the grade status of the group for the final and for the adviser to input recommendations of the panels
@login_required
def final_adviser_record_detail(request, adviser_id):
    # Fetch the CustomUser object associated with the logged-in user
    user_profile = get_object_or_404(CustomUser, id=request.user.id)

    # Fetch the Faculty object associated with the CustomUser
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)

    # get all the school year
    school_years = SchoolYear.objects.all().order_by('start_year')

    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # Fetch records from the Adviser model where the faculty is an adviser
    adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=False, declined=False)
    adviser_records2 = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)

    adviser_id = adviser_id
    print('adviser_id', adviser_id)

    adviser = get_object_or_404(Adviser, id=adviser_id)
    adviser_id2 = adviser.id
    print('adviser_id2', adviser_id2)
    verdicts = Final_Verdict.objects.filter(school_year=selected_school_year).order_by('-percentage')
    print(verdicts)
    title = adviser.approved_title
    final_grade_record = Final_Grade.objects.filter(project_title=title, school_year=selected_school_year)
    recos = Final_Recos.objects.filter(project_title=title, school_year=selected_school_year)
    all_checkboxes = Final_Checkbox.objects.filter(school_year=selected_school_year)
    for reco in recos:
        reco.recommendation = escape(reco.recommendation)

    # Handle form submission
    if request.method == "POST":
        recommendation = request.POST.get("recommendation")
        print("recosss: ", recommendation)
        
        # Try to find an existing Final_Recos record with the same title
        reco = Final_Recos.objects.filter(project_title=title, school_year=selected_school_year).first()
        
        if reco:
            # If recommendation record exists, update the recommendation
            reco.recommendation = recommendation
            if recommendation == "":
                print("Empty reco")
                reco.recommendation = recommendation
                reco.school_year = selected_school_year
                reco.delete()
                # Log the action in the audit trail
                AuditTrail.objects.create(
                    user=request.user,
                    action=f"Deleted recommendation in Final Group Advisee Record for project title '{title}'",
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            else:
                reco.school_year = selected_school_year
                reco.recommendation = recommendation
                # Save the recommendation record (updated)
                print("empyt also")
                reco.save()
                # Log the action in the audit trail
                AuditTrail.objects.create(
                    user=request.user,
                    action=f"Updated recommendation in Final Group Advisee Record for project title '{title}'",
                    ip_address=request.META.get('REMOTE_ADDR')
                )
        else:
            # If no recommendation record exists, create a new one
            if recommendation == "":
                print("Empty reco")
            else:
                reco = Final_Recos(
                    project_title=title,  # Assuming `title` is defined elsewhere in the view
                    recommendation=recommendation,
                    school_year=selected_school_year
                )
                # Save the recommendation record (new)
                reco.save()
                # Log the action in the audit trail
                AuditTrail.objects.create(
                    user=request.user,
                    action=f"Submitted recommendation in Final Group Advisee Record for project title '{title}'",
                    ip_address=request.META.get('REMOTE_ADDR')
                )
        
        print(f"Redirecting with adviser_id: {adviser_id}")  # Debugging line
        return redirect('final_adviser_record_detail', adviser_id=adviser_id)
    
    # Fetch grades with the same title
    grades = Final_Grade.objects.filter(project_title=title, school_year=selected_school_year)
    # groups = GroupInfoFD.objects.filter(title=title, school_year=current_school_year)
    criteria_list = Final_EvaluationSection.objects.filter(school_year=selected_school_year).annotate(total_criteria_percentage=Sum('fcriteria__percentage'))
    criteria_percentage = Final_Criteria.objects.filter(school_year=selected_school_year)
    total_points = sum(criteria.percentage for criteria in criteria_percentage)
    
    if not grades.exists():
        # Fetch group members
        groups = GroupInfoFD.objects.filter(title=title, school_year=selected_school_year)
        advisee_groups = Adviser.objects.filter(approved_title=title, school_year=selected_school_year)
        member1 = None
        member2 = None
        member3 = None
        if groups.exists():
            # Fetch members directly from GroupInfoPOD
            group = groups.first()  # Get the first group object
            member1 = group.member1
            member2 = group.member2
            member3 = group.member3
        else:
            # Fall back to splitting `group_name` from Adviser model
            if advisee_groups.exists():
                # Get the first matching adviser record
                advisee = advisee_groups.first()
                members = advisee.group_name.split('<br>') if advisee.group_name else []
                # Pad the members list to ensure it has at least 3 elements
                while len(members) < 3:
                    members.append(None)  # Use `None` or an empty string as padding
                member1, member2, member3 = members[0], members[1], members[2]
                print("member1: ", member1)
            else:
                # If no matching adviser record, set members to None
                member1, member2, member3 = None, None, None
        group_members = f"Member1: {member1}, Member2: {member2}, Member3: {member3}"

        return render(request, 'faculty/final_grade/adviser_record_detailFD.html', {
            'error': 'No grades found for this title',
            'title': title, 
            'member1': member1, 
            'member2': member2, 
            'member3': member3,
            'adviser': adviser,
            'recos': recos,
            'faculty_member': faculty_member,
            'school_years': school_years,  # Ensure this is passed to the template,
            'adviser_records': adviser_records,
            'last_school_year': last_school_year,
            # 'current_school_year': current_school_year,
            'selected_school_year': selected_school_year,
            'adviser_records2': adviser_records2
        })

    # Initialize member variables
    member1_grade = grades.first().member1_grade if grades.exists() else None
    member2_grade = grades.first().member2_grade if grades.exists() else None
    member3_grade = grades.first().member3_grade if grades.exists() else None
    recommendation = grades.first().recommendation if grades.exists() else None
    total_grade1 = grades.aggregate(Sum('member1_grade'))['member1_grade__sum']
    total_grade2 = grades.aggregate(Sum('member2_grade'))['member2_grade__sum']
    total_grade3 = grades.aggregate(Sum('member3_grade'))['member3_grade__sum']

    #grade for the member1
    if total_grade1 is not None and grades.count() != 0:
        average_grade1 = total_grade1 / 3
        print('the grade is no 0')
        
    else:
        average_grade1 = 0  # Handle the case where no grades exist
        print('the grade is 0')
    print('member grade1', average_grade1)

    #grade for the member2
    if total_grade2 is not None and grades.count() != 0:
        average_grade2 = total_grade2 / 3
        print('the grade is no 0')
        
    else:
        average_grade2 = 0  # Handle the case where no grades exist
        print('the grade is 0')
    print('member grade3', average_grade2)

    #grade for the member3
    if total_grade3 is not None and grades.count() != 0:
        average_grade3 = total_grade3 / 3
        print('the grade is no 0')
        
    else:
        average_grade3 = 0  # Handle the case where no grades exist
        print('the grade is 0')
    print('member grade3', average_grade3)

    member1 = groups.first().member1 if groups.exists() else None
    member2 = groups.first().member2 if groups.exists() else None
    member3 = groups.first().member3 if groups.exists() else None

    # Aggregate data
    summary_totals = {}
    for grade_by_panel in grades:
        summary_grades_data = grade_by_panel.get_grades_data()
        for section_name, section_grades in summary_grades_data.items():
            if section_name not in summary_totals:
                summary_totals[section_name] = {'total': 0, 'count': 0}
            if isinstance(section_grades, dict):
                total = sum(section_grades.values())
                summary_totals[section_name]['total'] += total
                summary_totals[section_name]['count'] += 1
            elif isinstance(section_grades, list):
                try:
                    average = sum(section_grades) / len(section_grades)
                except ZeroDivisionError:
                    average = 0
                summary_totals[section_name]['total'] += average
                summary_totals[section_name]['count'] += 1

    # Finalize totals
    for section_name, data in summary_totals.items():
            if "Oral Presentation" in section_name or "Individual Grade" in section_name:
                # Divide by 3 for specific sections
                if data['count'] > 0:
                    summary_totals[section_name] = data['total'] / 3
                    summary_totals[section_name] = summary_totals[section_name] / 3
                else:
                    summary_totals[section_name] = 0
            else:
                # For other sections, just average over the count
                if data['count'] > 0:
                    summary_totals[section_name] = data['total'] / 3
                else:
                    summary_totals[section_name] = 0

    total_earned_points = sum(summary_totals.values())
    print(f"total points: {total_earned_points}")

    # Determine the verdict based on total earned points
    records = grades.count()
    selected_verdict = ''
    # Decode the checkbox_data from the Final_Grade instance
    for checkbox_entry in final_grade_record:
        checkbox_data = checkbox_entry.get_checkbox_data() 
    if records < 3:
        selected_verdict = "Verdict is not available since not all of the panels submit the evaluation!"
    else:
        for verdict in verdicts:
            print(f"verdict percentage: {verdict.percentage}")
            if total_earned_points >= verdict.percentage:
                selected_verdict = f"{verdict.name} ({verdict.percentage}%)"
                break

    context = {
        'adviser_id': adviser_id,
        'adviser': adviser,
        'title': title,
        'verdicts': verdicts,
        'selected_verdict': selected_verdict,
        'member1': member1,
        'member2': member2, 
        'member3': member3,
        'member1_grade': average_grade1,
        'member2_grade': average_grade2,
        'member3_grade': average_grade3,
        'criteria_list': criteria_list,
        'summary_totals': summary_totals,
        'total_points': total_points,
        'total_earned_points': total_earned_points,
        'recommendation': recommendation,
        'recos': recos,
        'checkbox_data': checkbox_data,
        'all_checkboxes': Final_Checkbox.objects.filter(school_year=selected_school_year),
        'final_grade_record': final_grade_record,
        'checkbox_entry': checkbox_entry,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
        'faculty_member': faculty_member,
        'adviser_records': adviser_records,
        'adviser_records2': adviser_records2
    }
    
    return render(request, 'faculty/final_grade/adviser_record_detailFD.html', context)
    
# function to fetch the preoral recommendations based on the project title
def final_reco(request, schedule_id):
    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # Fetch the CustomUser object associated with the logged-in user
    user_profile = get_object_or_404(CustomUser, id=request.user.id)

    # Fetch the Faculty object associated with the CustomUser
    faculty_member = get_object_or_404(Faculty, custom_user=user_profile)

    # Fetch records from the Adviser model where the faculty is an adviser
    adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=False, declined=False)
    adviser_records2 = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)

    schedule = get_object_or_404(ScheduleFD, id=schedule_id)
    recos = Final_Recos.objects.filter(project_title=schedule.title, school_year=selected_school_year)
    print(recos)
    for reco in recos:
        reco.recommendation = escape(reco.recommendation)
    context = {
        'schedule': schedule,
        'recos': recos,
        'adviser_records': adviser_records,
        'adviser_records2': adviser_records2
    }
    return render(request, 'faculty/final_grade/final_reco.html', context)


# the following functions is used to clone the evaluation form
# cloning the pre oral evaluation form
def pre_oral_clone_records(request):

    # Get the last school year added to the db
    
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # Get the last school year added to the db
    if selected_school_year:  # Ensure current_school_year is not None
        last_school_year = SchoolYear.objects.filter(end_year__lt=selected_school_year.end_year).order_by('-end_year').first()
    else:
        # Handle the case where there is no active school year
        last_school_year = None

    # Delete all existing records for the current school year
    PreOral_EvaluationSection.objects.filter(school_year=selected_school_year).delete()
    PreOral_Criteria.objects.filter(school_year=selected_school_year).delete()
    CriterionDescription.objects.filter(school_year=selected_school_year).delete()
    Verdict.objects.filter(school_year=selected_school_year).delete()
    Checkbox.objects.filter(school_year=selected_school_year).delete()
    PreOral_Recos.objects.filter(school_year=selected_school_year).delete()
    PreOral_Grade.objects.filter(school_year=selected_school_year).delete()
    
    # Fetch all sections related to the previous school year
    evaluation_sections = PreOral_EvaluationSection.objects.filter(school_year=last_school_year)
    print("records last year: ", evaluation_sections)
    print("last year: ", last_school_year)

    # Begin a transaction so that if something goes wrong, we can rollback
    with transaction.atomic():
        for section in evaluation_sections:
            # Clone each section and assign the new school year
            new_section = PreOral_EvaluationSection.objects.create(
                name=section.name,
                school_year=selected_school_year
            )
            
            # Clone criteria for the section
            for criteria in section.criteria.all():
                new_criteria = PreOral_Criteria.objects.create(
                    section=new_section,
                    name=criteria.name,
                    percentage=criteria.percentage,
                    school_year=selected_school_year
                )

                # Clone criterion descriptions
                for description in criteria.descriptions.all():
                    CriterionDescription.objects.create(
                        criterion=new_criteria,
                        text=description.text,
                        school_year=selected_school_year
                    )

        # Clone verdicts
        verdicts = Verdict.objects.filter(school_year=last_school_year)
        for verdict in verdicts:
            new_verdict = Verdict.objects.create(
                name=verdict.name,
                percentage=verdict.percentage,
                school_year=selected_school_year
            )

            # Clone checkboxes for each verdict
            for checkbox in verdict.checkboxes.all():
                Checkbox.objects.create(
                    verdict=new_verdict,
                    label=checkbox.label,
                    is_checked=checkbox.is_checked,
                    school_year=selected_school_year
                )

        # Clone recommendations
        recos = PreOral_Recos.objects.filter(school_year=last_school_year)
        for reco in recos:
            PreOral_Recos.objects.create(
                project_title=reco.project_title,
                recommendation=reco.recommendation,
                school_year=selected_school_year
            )

        # Clone grades (optional, depends on your use case)
        grades = PreOral_Grade.objects.filter(school_year=last_school_year)
        for grade in grades:
            PreOral_Grade.objects.create(
                faculty=grade.faculty,
                project_title=grade.project_title,
                grades_data=grade.grades_data,
                verdict=grade.verdict,
                checkbox_data=grade.checkbox_data,
                othervalue=grade.othervalue,
                member1_grade=grade.member1_grade,
                member2_grade=grade.member2_grade,
                member3_grade=grade.member3_grade,
                recommendation=grade.recommendation,
                school_year=selected_school_year
            )

        return redirect('view_section')


# cloning the mock evaluation form
def mock_clone_records(request):

    # Get the last school year added to the db
    
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # Get the last school year added to the db
    if selected_school_year:  # Ensure current_school_year is not None
        last_school_year = SchoolYear.objects.filter(end_year__lt=selected_school_year.end_year).order_by('-end_year').first()
    else:
        # Handle the case where there is no active school year
        last_school_year = None

    # Delete all existing records for the current school year
    Mock_EvaluationSection.objects.filter(school_year=selected_school_year).delete()
    Mock_Criteria.objects.filter(school_year=selected_school_year).delete()
    MockCriterionDescription.objects.filter(school_year=selected_school_year).delete()
    Mock_Verdict.objects.filter(school_year=selected_school_year).delete()
    Mock_Checkbox.objects.filter(school_year=selected_school_year).delete()
    Mock_Recos.objects.filter(school_year=selected_school_year).delete()
    Mock_Grade.objects.filter(school_year=selected_school_year).delete()
    
    # Fetch all sections related to the previous school year
    evaluation_sections = Mock_EvaluationSection.objects.filter(school_year=last_school_year)
    print("records last year: ", evaluation_sections)
    print("last year: ", last_school_year)

    # Begin a transaction so that if something goes wrong, we can rollback
    with transaction.atomic():
        for section in evaluation_sections:
            # Clone each section and assign the new school year
            new_section = Mock_EvaluationSection.objects.create(
                name=section.name,
                school_year=selected_school_year
            )
            
            # Clone criteria for the section
            for criteria in section.mcriteria.all():
                new_criteria = Mock_Criteria.objects.create(
                    section=new_section,
                    name=criteria.name,
                    percentage=criteria.percentage,
                    school_year=selected_school_year
                )

                # Clone criterion descriptions
                for description in criteria.mdescriptions.all():
                    MockCriterionDescription.objects.create(
                        criterion=new_criteria,
                        text=description.text,
                        school_year=selected_school_year
                    )

        # Clone verdicts
        verdicts = Mock_Verdict.objects.filter(school_year=last_school_year)
        for verdict in verdicts:
            new_verdict = Mock_Verdict.objects.create(
                name=verdict.name,
                percentage=verdict.percentage,
                school_year=selected_school_year
            )

            # Clone checkboxes for each verdict
            for checkbox in verdict.mcheckboxes.all():
                Mock_Checkbox.objects.create(
                    verdict=new_verdict,
                    label=checkbox.label,
                    is_checked=checkbox.is_checked,
                    school_year=selected_school_year
                )

        # Clone recommendations
        recos = Mock_Recos.objects.filter(school_year=last_school_year)
        for reco in recos:
            Mock_Recos.objects.create(
                project_title=reco.project_title,
                recommendation=reco.recommendation,
                school_year=selected_school_year
            )

        # Clone grades (optional, depends on your use case)
        grades = Mock_Grade.objects.filter(school_year=last_school_year)
        for grade in grades:
            Mock_Grade.objects.create(
                faculty=grade.faculty,
                project_title=grade.project_title,
                grades_data=grade.grades_data,
                verdict=grade.verdict,
                checkbox_data=grade.checkbox_data,
                othervalue=grade.othervalue,
                member1_grade=grade.member1_grade,
                member2_grade=grade.member2_grade,
                member3_grade=grade.member3_grade,
                recommendation=grade.recommendation,
                school_year=selected_school_year
            )

        return redirect('mock_view_section')


# cloning the mock evaluation form
def final_clone_records(request):

    # Get the last school year added to the db
    
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # Get the last school year added to the db
    if selected_school_year:  # Ensure current_school_year is not None
        last_school_year = SchoolYear.objects.filter(end_year__lt=selected_school_year.end_year).order_by('-end_year').first()
    else:
        # Handle the case where there is no active school year
        last_school_year = None

    # Delete all existing records for the current school year
    Final_EvaluationSection.objects.filter(school_year=selected_school_year).delete()
    Final_Criteria.objects.filter(school_year=selected_school_year).delete()
    FinalCriterionDescription.objects.filter(school_year=selected_school_year).delete()
    Final_Verdict.objects.filter(school_year=selected_school_year).delete()
    Final_Checkbox.objects.filter(school_year=selected_school_year).delete()
    Final_Recos.objects.filter(school_year=selected_school_year).delete()
    Final_Grade.objects.filter(school_year=selected_school_year).delete()
    
    # Fetch all sections related to the previous school year
    evaluation_sections = Final_EvaluationSection.objects.filter(school_year=last_school_year)
    print("records last year: ", evaluation_sections)
    print("last year: ", last_school_year)

    # Begin a transaction so that if something goes wrong, we can rollback
    with transaction.atomic():
        for section in evaluation_sections:
            # Clone each section and assign the new school year
            new_section = Final_EvaluationSection.objects.create(
                name=section.name,
                school_year=selected_school_year
            )
            
            # Clone criteria for the section
            for criteria in section.fcriteria.all():
                new_criteria = Final_Criteria.objects.create(
                    section=new_section,
                    name=criteria.name,
                    percentage=criteria.percentage,
                    school_year=selected_school_year
                )

                # Clone criterion descriptions
                for description in criteria.fdescriptions.all():
                    FinalCriterionDescription.objects.create(
                        criterion=new_criteria,
                        text=description.text,
                        school_year=selected_school_year
                    )

        # Clone verdicts
        verdicts = Final_Verdict.objects.filter(school_year=last_school_year)
        for verdict in verdicts:
            new_verdict = Final_Verdict.objects.create(
                name=verdict.name,
                percentage=verdict.percentage,
                school_year=selected_school_year
            )

            # Clone checkboxes for each verdict
            for checkbox in verdict.fcheckboxes.all():
                Final_Checkbox.objects.create(
                    verdict=new_verdict,
                    label=checkbox.label,
                    is_checked=checkbox.is_checked,
                    school_year=selected_school_year
                )

        # Clone recommendations
        recos = Final_Recos.objects.filter(school_year=last_school_year)
        for reco in recos:
            Final_Recos.objects.create(
                project_title=reco.project_title,
                recommendation=reco.recommendation,
                school_year=selected_school_year
            )

        # Clone grades (optional, depends on your use case)
        grades = Final_Grade.objects.filter(school_year=last_school_year)
        for grade in grades:
            Final_Grade.objects.create(
                faculty=grade.faculty,
                project_title=grade.project_title,
                grades_data=grade.grades_data,
                verdict=grade.verdict,
                checkbox_data=grade.checkbox_data,
                othervalue=grade.othervalue,
                member1_grade=grade.member1_grade,
                member2_grade=grade.member2_grade,
                member3_grade=grade.member3_grade,
                recommendation=grade.recommendation,
                school_year=selected_school_year
            )

        return redirect('final_view_section')



# the following view are used to view the format of the evaluation form
# used in viewing the pre oral evaluation form
@superuser_required
@login_required
def view_input_grade(request):
    # Get all available school years
    school_years = SchoolYear.objects.all().order_by('start_year')
    if school_years.count() == 0:
        SchoolYear.create_new_school_year()
        school_years = SchoolYear.objects.all().order_by('start_year')
    
    # Get the current school year (optional; you may want to show this as part of the form)
    # current_school_year = SchoolYear.get_active_school_year()

    # Get the last added school year in the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # Fetch all criteria and verdicts from the database (for the form structure)
    criteria_list = PreOral_EvaluationSection.objects.filter(school_year=selected_school_year).annotate(total_criteria_percentage=Sum('criteria__percentage'))
    criteria_percentage = PreOral_Criteria.objects.filter(school_year=selected_school_year)
    verdicts = Verdict.objects.filter(school_year=selected_school_year)
    sections = PreOral_EvaluationSection.objects.filter(school_year=selected_school_year).prefetch_related('criteria__descriptions').all()

    # Validation: Check if any of the required models are empty
    if not criteria_list.exists() and not criteria_percentage.exists() and not verdicts.exists() and not sections.exists():
        # Redirect to 'view_section' if any of the required models are empty
        empty = "True"
        message = "You need to create first the evaluation form"
        url = reverse('view_section')
        query_string = urlencode({'empty': empty, 'message': message})
        return redirect(f'{url}?{query_string}')

    # Initialize a placeholder for total percentage calculation (this could be used in the form display)
    total_percentage = sum(criteria.percentage for criteria in criteria_percentage) 

    # Prepare the context for rendering the form
    context = {
        'criteria_list': criteria_list,
        'verdicts': verdicts,
        'total_percentage': total_percentage,
        'sections': sections,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'school_years': school_years,
        'last_school_year': last_school_year
    }

    return render(request, 'admin/pre_oral/PreOral_Evaluation/view_input_grade.html', context)

@superuser_required
@login_required
def view_mock_input_grade(request):
    # Get all available school years
    school_years = SchoolYear.objects.all().order_by('start_year')
    if school_years.count() == 0:
        SchoolYear.create_new_school_year()
        school_years = SchoolYear.objects.all().order_by('start_year')
    
    # Get the current school year (optional; you may want to show this as part of the form)
    # current_school_year = SchoolYear.get_active_school_year()

    # get the last added school year in the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # Fetch all criteria and verdicts from the database (for the form structure)
    criteria_list = Mock_EvaluationSection.objects.filter(school_year=selected_school_year).annotate(total_criteria_percentage=Sum('mcriteria__percentage'))
    criteria_percentage = Mock_Criteria.objects.filter(school_year=selected_school_year)
    verdicts = Mock_Verdict.objects.filter(school_year=selected_school_year)
    sections = Mock_EvaluationSection.objects.filter(school_year=selected_school_year).prefetch_related('mcriteria__descriptions').all()

    # Validation: Check if any of the required models are empty
    if not criteria_list.exists() and not criteria_percentage.exists() and not verdicts.exists() and not sections.exists():
        # Redirect to 'view_section' if any of the required models are empty
        empty = "True"
        message = "You need to create first the evaluation form"
        url = reverse('mock_view_section')
        query_string = urlencode({'empty': empty, 'message': message})
        return redirect(f'{url}?{query_string}')

    # Initialize a placeholder for total percentage calculation (this could be used in the form display)
    total_percentage = sum(criteria.percentage for criteria in criteria_percentage)

    # No schedule or group-related data is fetched now, only the form structure is sent to the template
    context = {
        'criteria_list': criteria_list,
        'verdicts': verdicts,
        'total_percentage': total_percentage,
        'sections': sections,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'school_years': school_years,
        'last_school_year': last_school_year
    }

    return render(request, 'admin/mock/Mock_Evaluation/view_mock_input_grade.html', context)


@superuser_required
@login_required
def view_final_input_grade(request):
    school_years = SchoolYear.objects.all().order_by('start_year')
    school_years = SchoolYear.objects.all().order_by('start_year')
    if school_years.count() == 0:
        SchoolYear.create_new_school_year()
        school_years = SchoolYear.objects.all().order_by('start_year')
    
    # Get the current school year (optional; you may want to show this as part of the form)
    # current_school_year = SchoolYear.get_active_school_year()

    # get the last added school year in the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # Fetch all criteria and verdicts from the database (for the form structure)
    criteria_list = Final_EvaluationSection.objects.filter(school_year=selected_school_year).annotate(total_criteria_percentage=Sum('fcriteria__percentage'))
    criteria_percentage = Final_Criteria.objects.filter(school_year=selected_school_year)
    verdicts = Final_Verdict.objects.filter(school_year=selected_school_year)
    sections = Final_EvaluationSection.objects.filter(school_year=selected_school_year).prefetch_related('fcriteria__descriptions')

    # Validation: Check if any of the required models are empty
    if not criteria_list.exists() and not criteria_percentage.exists() and not verdicts.exists() and not sections.exists():
        # Redirect to 'view_section' if any of the required models are empty
        empty = "True"
        message = "You need to create first the evaluation form"
        url = reverse('final_view_section')
        query_string = urlencode({'empty': empty, 'message': message})
        return redirect(f'{url}?{query_string}')


    # Initialize a placeholder for total percentage calculation (this could be used in the form display)
    total_percentage = sum(criteria.percentage for criteria in criteria_percentage)

    # No schedule, group member, or grades data is fetched now, only the form structure is sent to the template
    context = {
        'criteria_list': criteria_list,
        'verdicts': verdicts,
        'total_percentage': total_percentage,
        'sections': sections,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'school_years': school_years,
        'last_school_year': last_school_year
    }

    return render(request, 'admin/final/Final_Evaluation/view_final_input_grade.html', context)


@csrf_exempt
def create_new_account(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')

        if CustomUser.objects.filter(username=username).exists():
            return JsonResponse({'status': 'error', 'message': 'Username already exists.'})

        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Set the user as superuser and staff
        user.is_superuser = True
        user.is_staff = True
        user.save()

        return JsonResponse({'status': 'success', 'message': 'Superuser account created successfully.'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


# function to accept or declined recommended advisee
@login_required
def accept_adviser(request, adviser_id):
    adviser = get_object_or_404(Adviser, id=adviser_id)
    adviser.accepted = True
    adviser.declined = False  # Make sure to reset declined if accepting
    adviser.save()
    # Audit Trail Entry
    AuditTrail.objects.create(
        user=request.user,
        action=f"{adviser.faculty} has accepted the request for an adviser with title: {adviser.approved_title}",
        ip_address=request.META.get('REMOTE_ADDR')
    )

    # creating a notif
    Notif.objects.create(
        created_by=request.user,
        notif=f"{adviser.faculty} has accepted the request for an adviser with title: {adviser.approved_title}",
    )
    return redirect(reverse('adviser_record_detail', args=[adviser_id]))

@login_required
def decline_adviser(request, adviser_id):
    adviser = get_object_or_404(Adviser, id=adviser_id)
    adviser.accepted = False  # Make sure to reset accepted if declining
    adviser.declined = True
    adviser.save()
    # Audit Trail Entry
    AuditTrail.objects.create(
        user=request.user,
        action=f"{adviser.faculty} has declined the request for an adviser with title: {adviser.approved_title}",
        ip_address=request.META.get('REMOTE_ADDR')
    )

    # creating a notif
    Notif.objects.create(
        created_by=request.user,
        notif=f"{adviser.faculty} has declined the request for an adviser with title: {adviser.approved_title}",
    )
    return redirect('faculty_dashboard')


# function for the notifications
# def notification_list(request):
#     user = request.user
#     query = request.GET.get('search', '')

#     # Fetch notifications based on the user's permissions
#     if user.is_superuser:
#         notifications = Notif.objects.filter(
#             created_by__is_superuser=False,
#             notif__icontains=query
#         ).order_by('-time')
#     else:
#         notifications = Notif.objects.filter(
#             created_by__is_superuser=True,
#             notif__icontains=query
#         ).order_by('-time')

#     # Check if the request is an AJAX call
#     if request.headers.get('x-requested-with') == 'XMLHttpRequest':
#         # Render only the notification list as a partial response
#         return render(request, 'users/partials_notification_list.html', {
#             'notifications': notifications,
#         })

#     # If not an AJAX request, render the full page
#     return render(request, 'users/notifications.html', {
#         'notifications': notifications,
#     })

# def notification_list(request):
#     user = request.user
#     query = request.GET.get('search', '')

#     # Fetch all general notifications created by superusers
#     general_notifications = Notif.objects.filter(
#         created_by__is_superuser=True,
#         notif__icontains=query
#     ).exclude(
#         usernotif__notif__in=UserNotif.objects.filter(
#             notif__notif__icontains=query
#         ).values_list('notif', flat=True)  # Exclude specific notifications
#     ).order_by('-time')

#     # Fetch specific notifications intended for the logged-in user
#     targeted_notifications = Notif.objects.filter(
#         usernotif__user=user,
#         notif__icontains=query
#     ).distinct().order_by('-time')

#     # Combine general and targeted notifications
#     notifications = list(general_notifications) + list(targeted_notifications)
#     notifications.sort(key=lambda notif: notif.time, reverse=True)  # Sort by time descending

#     # Check if the request is an AJAX call
#     if request.headers.get('x-requested-with') == 'XMLHttpRequest':
#         # Render only the notification list as a partial response
#         return render(request, 'users/partials_notification_list.html', {
#             'notifications': notifications,
#         })

#     # If not an AJAX request, render the full page
#     return render(request, 'users/notifications.html', {
#         'notifications': notifications,
#     })

def notification_list(request):
    school_years = SchoolYear.objects.all().order_by('start_year')

    # Get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    # Get the current school year
    # current_school_year = SchoolYear.get_active_school_year()
    selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the active school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        # Retrieve the selected school year based on the session
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    user = request.user
    query = request.GET.get('search', '')
    adviser_records = None
    
    # Determine if the user is a superuser
    if user.is_superuser:
        # Superusers see notifications created by non-superusers
        general_notifications = Notif.objects.filter(
            created_by__is_superuser=False,
            notif__icontains=query
        ).exclude(
            usernotif__notif__in=UserNotif.objects.filter(
                notif__notif__icontains=query
            ).values_list('notif', flat=True)  # Exclude specific notifications
        ).order_by('-time')
    else:
        user_profile = get_object_or_404(CustomUser, id=request.user.id)
        faculty_member = get_object_or_404(Faculty, custom_user=user_profile)
        adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=False)

        # Non-superusers see general notifications created by superusers
        general_notifications = Notif.objects.filter(
            created_by__is_superuser=True,
            notif__icontains=query
        ).exclude(
            usernotif__notif__in=UserNotif.objects.filter(
                notif__notif__icontains=query
            ).values_list('notif', flat=True)  # Exclude specific notifications
        ).order_by('-time')

    # Fetch specific notifications intended for the logged-in user
    targeted_notifications = Notif.objects.filter(
        usernotif__user=user,
        notif__icontains=query
    ).distinct().order_by('-time')

    # Combine general and targeted notifications
    notifications = list(general_notifications) + list(targeted_notifications)
    notifications.sort(key=lambda notif: notif.time, reverse=True)  # Sort by time descending

    # Check if the request is an AJAX call
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Render only the notification list as a partial response
        return render(request, 'users/partials_notification_list.html', {
            'notifications': notifications,
            'adviser_records': adviser_records
        })

    # If not an AJAX request, render the full page
    return render(request, 'users/notifications.html', {
        'notifications': notifications,
        'adviser_records': adviser_records
    })


def mark_notification_as_read(request, notif_id):
    notif = get_object_or_404(Notif, id=notif_id)
    notif.read_by.add(request.user)  # Mark the notification as read for this user
    return redirect('notifications')  # Redirect back to the notifications list

@login_required
def mark_all_notifications_as_read(request):
    user = request.user
    if user.is_superuser:
        notifications = Notif.objects.filter(created_by__is_superuser=False)
    else:
        notifications = Notif.objects.filter(created_by__is_superuser=True)
    for notification in notifications:
        notification.read_by.add(user)
    return JsonResponse({'status': 'success'})

@login_required
def accept_adviser_and_mark_read(request, adviser_id, notif_id):
    # Fetch the adviser and mark as accepted
    adviser = get_object_or_404(Adviser, id=adviser_id)
    adviser.accepted = True
    adviser.declined = False  # Reset declined if accepting
    adviser.save()

    # Create an audit trail entry
    AuditTrail.objects.create(
        user=request.user,
        action=f"{adviser.faculty} has accepted the request for an adviser with title: {adviser.approved_title}",
        ip_address=request.META.get('REMOTE_ADDR')
    )

    # Create a notification (optional, based on your logic)
    Notif.objects.create(
        created_by=request.user,
        notif=f"{adviser.faculty} has accepted the request for an adviser with title: {adviser.approved_title}",
    )

    # Fetch the notification
    notif = get_object_or_404(Notif, id=notif_id)

    # Mark the notification as read for this user in Notif model
    notif.read_by.add(request.user)

    # Update or create an entry in UserNotif for this user and notification
    user_notif, created = UserNotif.objects.get_or_create(
        user=request.user,
        notif=notif,
        defaults={'read': True}  # Set read to True if created
    )
    if not created:
        user_notif.read = True  # Update the read status if it already exists
        user_notif.save()

    # Redirect to the adviser's detail page or any desired page
    return redirect(reverse('adviser_record_detail', args=[adviser_id]))



@login_required
def decline_adviser_and_mark_read(request, adviser_id, notif_id):
    # Fetch the adviser and mark as declined
    adviser = get_object_or_404(Adviser, id=adviser_id)
    adviser.accepted = False  # Reset accepted if declining
    adviser.declined = True
    adviser.save()

    # Create an audit trail entry
    AuditTrail.objects.create(
        user=request.user,
        action=f"{adviser.faculty} has declined the request for an adviser with title: {adviser.approved_title}",
        ip_address=request.META.get('REMOTE_ADDR')
    )

    # Create a notification
    Notif.objects.create(
        created_by=request.user,
        notif=f"{adviser.faculty} has declined the request for an adviser with title: {adviser.approved_title}",
    )

    # Fetch the notification
    notif = get_object_or_404(Notif, id=notif_id)

    # Mark the notification as read for this user in Notif model
    notif.read_by.add(request.user)

    # Update or create an entry in UserNotif for this user and notification
    user_notif, created = UserNotif.objects.get_or_create(
        user=request.user,
        notif=notif,
        defaults={'read': True}  # Set read to True if created
    )
    if not created:
        user_notif.read = True  # Update the read status if it already exists
        user_notif.save()

    # Redirect to the faculty dashboard or any desired page
    return redirect('faculty_dashboard')
