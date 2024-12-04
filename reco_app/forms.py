from django import forms
from .models import Faculty, Adviser, Expertise
from scheduler_app.models import GroupInfoTH

class TitleInputForm(forms.Form):
    title = forms.CharField(label='Project Title', max_length=200)

class AdviserForm(forms.ModelForm):
    members = forms.ModelChoiceField(
        queryset=GroupInfoTH.objects.all(),
        widget=forms.Select,
        required=False  # or True depending on your requirement
    )

    class Meta:
        model = Adviser
        fields = ['faculty', 'approved_title', 'members']
        widgets = {
            'approved_title': forms.TextInput(attrs={'placeholder': 'Enter the approved title'}),
        }

    def save(self, commit=True):
        adviser = super().save(commit=False)
        group_info = self.cleaned_data['members']
        
        # Concatenate member information with <br> tags
        if group_info:
            adviser.group_name = f"{group_info.member1}<br>{group_info.member2}<br>{group_info.member3}"
        else:
            adviser.group_name = ''  # Handle the case where no group_info is selected
        
        if commit:
            adviser.save()
        
        return adviser

class FacultyForm(forms.ModelForm):
    expertise = forms.ModelMultipleChoiceField(
        queryset=Expertise.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    new_expertise = forms.CharField(
        max_length=255,
        required=False,
        help_text="Add new expertise (comma separated for multiple)"
    )

    class Meta:
        model = Faculty
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.HiddenInput(),  # Hide the 'is_active' field
        }

    def save(self, commit=True):
        faculty = super().save(commit=False)
        expertise = self.cleaned_data['expertise']
        new_expertise_names = self.cleaned_data['new_expertise']
        new_expertise_list = [name.strip() for name in new_expertise_names.split(',') if name.strip()]

        if commit:
            faculty.save()

        for name in new_expertise_list:
            expertise_instance, created = Expertise.objects.get_or_create(name=name)
            expertise = expertise | Expertise.objects.filter(pk=expertise_instance.pk)

        faculty.expertise.set(expertise)

        if commit:
            faculty.save()

        return faculty

class DeleteFacultyForm(forms.Form):
    confirm = forms.BooleanField(label="Are you sure you want to delete this faculty member?", required=True)