from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import authenticate
from users.models import (
    CustomUser,

    # models used for PreOral
    PreOral_EvaluationSection, 
    PreOral_Criteria, 
    CriterionDescription, 
    Verdict, 
    Checkbox,

    # models used for mock
    Mock_EvaluationSection, 
    Mock_Criteria, 
    MockCriterionDescription,
    Mock_Verdict,  
    Mock_Checkbox,

    # models used for final
    Final_EvaluationSection, 
    Final_Criteria, 
    FinalCriterionDescription,
    Final_Verdict,  
    Final_Checkbox,

    ) 

from reco_app.models import Expertise, Faculty
from django.utils.text import slugify
import random
import string

class CustomUserCreationForm(UserCreationForm):
    DEGREE_CHOICES = [
        ('Doctor of Philosophy', 'Doctor of Philosophy (PhD)'),
        ('Doctor of Education', 'Doctor of Education (EdD)'),
        ('Specialist Degree', 'Specialist Degree (EdS)'),
        ('Professional Doctorates', 'Professional Doctorates')
    ]

    highest_degrees = forms.MultipleChoiceField(
        choices=DEGREE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'custom-checkbox'}),
        required=False,
        label="Select your Highest Degree"
    )

    new_expertise = forms.CharField(
        max_length=1000,
        required=False,
        label="",
        widget=forms.Textarea(attrs={
            'placeholder': "Please specify your other expertise (one per line)",
            'class': 'form-control',
            'aria-label': 'Other Expertise',
            'rows': 3,
            'id': 'expertiseInput'  # Add an ID to target it with JS
        })
    )

    expertise = forms.ModelMultipleChoiceField(
        queryset=Expertise.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'custom-checkbox'}),
        required=False,
        label="Select your expertise"
    )

    class Meta:
        model = CustomUser
        fields = [
            'email', 'first_name', 'middle_name', 'last_name', 'ext_name',
            'date_of_birth', 'address', 'years_of_teaching', 'has_master_degree',
            'highest_degrees', 'new_expertise', 'expertise', 'password1', 'password2'
        ]
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your first name'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your middle name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your last name'}),
            'ext_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Extension name (e.g., Jr., Sr.)'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'placeholder': 'Enter your date of birth'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your address'}),
            'years_of_teaching': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter your years of teaching'}),
            'has_master_degree': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def generate_username(self, first_name, last_name):
        username = f"{slugify(first_name)}_{slugify(last_name)}"
        if CustomUser.objects.filter(username=username).exists():
            # Add a random number to the username if it already exists
            username = f"{username}{random.randint(1000, 9999)}"
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.generate_username(user.first_name, user.last_name)
        if commit:
            user.save()
        return user

class OTPForm(forms.Form):
    otp = forms.CharField(max_length=6, required=True)
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('This email address is already in use.')
        return email
    

class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Enter your Email', 'class': 'form-control'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter your Password', 'class': 'form-control'})
    )

class CustomAuthenticationForm(AuthenticationForm):
    email = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label='Email', max_length=254)

    def clean(self):
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if email and password:
            self.user_cache = authenticate(username=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError('Invalid email or password')
            elif not self.user_cache.is_active:
                raise forms.ValidationError('This account is inactive.')
        return self.cleaned_data

class AccountSettingsForm(forms.ModelForm):
    DEGREE_CHOICES = [
        ('Doctor of Philosophy', 'Doctor of Philosophy (PhD)'),
        ('Doctor of Education', 'Doctor of Education (EdD)'),
        ('Specialist Degree', 'Specialist Degree (EdS)'),
        ('Professional Doctorates', 'Professional Doctorates')
    ]

    highest_degrees = forms.MultipleChoiceField(
        choices=DEGREE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'custom-checkbox'}),
        required=False,
        label="Select your highest degrees"
    )

    # new_expertise = forms.CharField(
    #     max_length=100,
    #     required=False,
    #     label="New Expertise",
    #     widget=forms.TextInput(attrs={'placeholder': "Please specify"})
    # )

    new_expertise = forms.CharField(
        max_length=1000,
        required=False,
        label="",
        widget=forms.Textarea(attrs={
            'placeholder': "Please specify your other expertise (one per line)",
            'class': 'form-control',
            'aria-label': 'Other Expertise',
            'rows': 3,
            'id': 'expertiseInput'  # Add an ID to target it with JS
        })
    )


    expertise = forms.ModelMultipleChoiceField(
        queryset=Expertise.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'custom-checkbox'}),
        required=False,
        label="Select your expertise"
    )

    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'first_name', 'middle_name', 
            'last_name', 'ext_name', 'date_of_birth', 'age', 'address', "years_of_teaching", "has_master_degree"
        ]
        # Add conditional fields if the user is not a superuser
        admin_excluded_fields = [
             'has_master_degree', 'highest_degrees'
        ]

        widgets = {
            'username': forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'required': True}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'autofocus': 'autofocus'}),
            'ext_name': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'age': forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
        }

    # def __init__(self, *args, **kwargs):
    #     user = kwargs.get('instance')  # Get the instance, which is the user
    #     super().__init__(*args, **kwargs)
        
    #     # Exclude fields if the user is an admin (superuser)
    #     if user and user.is_superuser:
    #         self.fields.pop('years_of_teaching', None)
    #         self.fields.pop('has_master_degree', None)
    #         self.fields.pop('highest_degrees', None)
    #         self.fields.pop('new_expertise', None)
    #         self.fields.pop('expertise', None)
    #     else:
    #         # Initialize highest_degrees from the user's data
    #         self.fields['highest_degrees'].initial = self.instance.highest_degree.split(',') if self.instance.highest_degree else []
    #         faculty = Faculty.objects.filter(custom_user=self.instance).first()
    #         if faculty:
    #             # Initialize expertise from the Faculty model
    #             self.fields['expertise'].initial = faculty.expertise.all()

    def __init__(self, *args, **kwargs):
        user = kwargs.get('instance')  # Get the instance, which is the user
        super().__init__(*args, **kwargs)
        
        # Exclude fields if the user is an admin (superuser)
        if user and user.is_superuser:
            self.fields.pop('years_of_teaching', None)
            self.fields.pop('has_master_degree', None)
            self.fields.pop('highest_degrees', None)
            self.fields.pop('new_expertise', None)
            self.fields.pop('expertise', None)
        else:
            # Initialize highest_degrees from the user's data
            self.fields['highest_degrees'].initial = self.instance.highest_degree.split(',') if self.instance.highest_degree else []
            faculty = Faculty.objects.filter(custom_user=self.instance).first()
            if faculty:
                # Initialize expertise from the Faculty model
                self.fields['expertise'].initial = faculty.expertise.all()

        # Initialize ext_name field
        self.fields['ext_name'].initial = self.instance.ext_name

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()

            if not user.is_superuser:
                # Save highest_degrees if not a superuser
                highest_degrees = self.cleaned_data.get('highest_degrees', [])
                user.highest_degree = ','.join(highest_degrees)
                user.save()

                # Update or create the corresponding Faculty record
                faculty, created = Faculty.objects.get_or_create(custom_user=user)
                faculty.name = f"{user.first_name} {user.middle_name} {user.last_name} {user.ext_name}"
                faculty.years_of_teaching = user.years_of_teaching
                faculty.has_master_degree = user.has_master_degree
                faculty.highest_degree = ','.join(highest_degrees)
                faculty.save()

                # Save expertise (checkbox selections)
                expertise_list = self.cleaned_data.get('expertise', [])
                faculty.expertise.set(expertise_list)

                # Handle custom expertise (split by new lines and remove bullets)
                custom_expertise = self.cleaned_data.get('new_expertise', "")
                if custom_expertise:
                    for expertise_name in custom_expertise.split('\n'):
                        expertise_name = expertise_name.strip().replace("•", "").strip()  # Remove bullet and trim spaces
                        if expertise_name:  # Skip empty lines
                            expertise, created = Expertise.objects.get_or_create(name=expertise_name)
                            faculty.expertise.add(expertise)

                faculty.save()

        return user

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'}))

class VerifyOTPForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter OTP'})
    )

class ResetPasswordForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter new password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'}))

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match")

# the following forms are used for the PreOral Evaluation
class PreOral_EvaluationSectionForm(forms.ModelForm):
    class Meta:
        model = PreOral_EvaluationSection
        fields = ['name']

class CriteriaForm(forms.ModelForm):
    class Meta:
        model = PreOral_Criteria
        fields = ['name', 'percentage']

class CriterionDescriptionForm(forms.ModelForm):
    class Meta:
        model = CriterionDescription
        fields = ['text']

class VerdictForm(forms.ModelForm):
    class Meta:
        model = Verdict
        fields = ['name', 'percentage']

class CheckboxForm(forms.Form):
    checkboxes = forms.CharField(widget=forms.HiddenInput())

    def clean_checkboxes(self):
        data = self.cleaned_data['checkboxes']
        if data:
            import json
            return json.loads(data)
        return []

    def save_checkboxes(self, verdict, school_year):  # school_year is now passed from the view
        checkboxes = self.cleaned_data['checkboxes']
        print("Checkbox data being saved:", checkboxes)  # Debugging line
        for checkbox_data in checkboxes:
            print("Saving checkbox:", checkbox_data)  # Debugging line
            Checkbox.objects.create(
                verdict=verdict,
                school_year=school_year,
                label=checkbox_data['label'],
                is_checked=checkbox_data['is_checked']  # Ensure this matches your model
            )


# the following forms are used for the Mock Defense Evaluation
class Mock_EvaluationSectionForm(forms.ModelForm):
    class Meta:
        model = Mock_EvaluationSection
        fields = ['name']

class Mock_CriteriaForm(forms.ModelForm):
    class Meta:
        model = Mock_Criteria
        fields = ['name', 'percentage']

class Mock_CriterionDescriptionForm(forms.ModelForm):
    class Meta:
        model = MockCriterionDescription
        fields = ['text']

class Mock_VerdictForm(forms.ModelForm):
    class Meta:
        model = Mock_Verdict
        fields = ['name', 'percentage']

class Mock_CheckboxForm(forms.Form):
    checkboxes = forms.CharField(widget=forms.HiddenInput())

    def clean_checkboxes(self):
        data = self.cleaned_data['checkboxes']
        if data:
            import json
            return json.loads(data)
        return []

    def save_checkboxes(self, verdict, school_year):  # school_year is now passed from the view
        checkboxes = self.cleaned_data['checkboxes']
        print("Checkbox data being saved:", checkboxes)  # Debugging line
        for checkbox_data in checkboxes:
            print("Saving checkbox:", checkbox_data)  # Debugging line
            Mock_Checkbox.objects.create(
                verdict=verdict,
                school_year=school_year,
                label=checkbox_data['label'],
                is_checked=checkbox_data['is_checked']  # Ensure this matches your model
            )


# the following forms are used for the Final Defense Evaluation
class Final_EvaluationSectionForm(forms.ModelForm):
    class Meta:
        model = Final_EvaluationSection
        fields = ['name']

class Final_CriteriaForm(forms.ModelForm):
    class Meta:
        model = Final_Criteria
        fields = ['name', 'percentage']

class Final_CriterionDescriptionForm(forms.ModelForm):
    class Meta:
        model = FinalCriterionDescription
        fields = ['text']

class Final_VerdictForm(forms.ModelForm):
    class Meta:
        model = Final_Verdict
        fields = ['name', 'percentage']

class Final_CheckboxForm(forms.Form):
    checkboxes = forms.CharField(widget=forms.HiddenInput())

    def clean_checkboxes(self):
        data = self.cleaned_data['checkboxes']
        if data:
            import json
            return json.loads(data)
        return []

    def save_checkboxes(self, verdict, school_year):  # school_year is now passed from the view
        checkboxes = self.cleaned_data['checkboxes']
        print("Checkbox data being saved:", checkboxes)  # Debugging line
        for checkbox_data in checkboxes:
            print("Saving checkbox:", checkbox_data)  # Debugging line
            Final_Checkbox.objects.create(
                verdict=verdict,
                school_year=school_year,
                label=checkbox_data['label'],
                is_checked=checkbox_data['is_checked']  # Ensure this matches your model
            )

