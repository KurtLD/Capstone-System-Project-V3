from django import forms
from .models import GroupInfoTH, GroupInfoPOD, Faculty, GroupInfoMD, GroupInfoFD, Room
from django.core.exceptions import ValidationError


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['name', 'status']

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super(RoomForm, self).__init__(*args, **kwargs)

        # Get the count of rooms
        room_count = Room.objects.count()

        # Start with the 'None' option
        # status_choices = [(0, 'None')]
        status_choices = []

        # Generate status options based on room count
        for i in range(1, room_count + 2):  # room_count + 1 to include the next ordinal
            status_label = self.get_ordinal(i)
            status_choices.append((i, status_label))

        # Update the status choices
        self.fields['status'].choices = status_choices

    def get_ordinal(self, n):
        """Return ordinal representation of a number, e.g., 1 -> '1st', 2 -> '2nd', etc."""
        if 10 <= n % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return f"{n}{suffix}"

    def clean_name(self):
        name = self.cleaned_data.get('name')

        # If we're editing an existing room, exclude its current name from the duplicate check
        if Room.objects.filter(name=name).exclude(id=self.instance.id).exists():
            raise ValidationError(f'A room with the name "{name}" already exists.')

        return name


class GroupInfoTHForm(forms.ModelForm):
    class Meta:
        model = GroupInfoTH
        fields = ['member1', 'member2', 'member3', 'section', 'subject_teacher']
        widgets = {
            'member1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(e.g., Delacruz, Juan T.)', 'required': 'required'}),
            'member2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(e.g., Delacruz, Juan T.)', 'required': 'required'}),
            'member3': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(e.g., Delacruz, Juan T.)', 'required': 'required'}),
            'section': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Section', 'required': 'required'}),
            'subject_teacher': forms.Select(attrs={'class': 'form-control', 'required': 'required'}),
        }

class UploadFileForm(forms.Form):
    upload_file = forms.FileField()

class GenerateScheduleForm(forms.Form):
    # No fields needed, just a submit button
    pass

class GroupInfoPODForm(forms.ModelForm):
    class Meta:
        model = GroupInfoPOD
        fields = ['member1', 'member2', 'member3', 'title', 'capstone_teacher', 'section', 'adviser']
        widgets = {
            'member1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(e.g., Delacruz, Juan T.)', 'required': 'required'}),
            'member2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(e.g., Delacruz, Juan T.)', 'required': 'required'}),
            'member3': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(e.g., Delacruz, Juan T.)'}),
            'title': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter the approved title', 'required': 'required'}),
            'section': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Section', 'required': 'required'}),
        }

    def __init__(self, *args, **kwargs):
        super(GroupInfoPODForm, self).__init__(*args, **kwargs)
        active_faculty = Faculty.objects.filter(is_active=True)
        self.fields['adviser'].queryset = active_faculty
        self.fields['capstone_teacher'].queryset = active_faculty

class GroupInfoMDForm(forms.ModelForm):
    class Meta:
        model = GroupInfoMD
        fields = ['member1', 'member2', 'member3', 'title', 'capstone_teacher', 'section', 'adviser']
        widgets = {
            'member1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(e.g., Delacruz, Juan T.)', 'required': 'required'}),
            'member2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(e.g., Delacruz, Juan T.)', 'required': 'required'}),
            'member3': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(e.g., Delacruz, Juan T.)'}),
            'title': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter the approved title', 'required': 'required'}),
            'section': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Section', 'required': 'required'}),
        }

    def __init__(self, *args, **kwargs):
        super(GroupInfoMDForm, self).__init__(*args, **kwargs)
        active_faculty = Faculty.objects.filter(is_active=True)
        self.fields['adviser'].queryset = active_faculty
        self.fields['capstone_teacher'].queryset = active_faculty

class GroupInfoFDForm(forms.ModelForm):
    class Meta:
        model = GroupInfoFD
        fields = ['member1', 'member2', 'member3', 'title', 'capstone_teacher', 'section', 'adviser']
        widgets = {
            'member1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(e.g., Delacruz, Juan T.)', 'required': 'required'}),
            'member2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(e.g., Delacruz, Juan T.)', 'required': 'required'}),
            'member3': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(e.g., Delacruz, Juan T.)'}),
            'title': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter the approved title', 'required': 'required'}),
            'section': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Section', 'required': 'required'}),
        }

    def __init__(self, *args, **kwargs):
        super(GroupInfoFDForm, self).__init__(*args, **kwargs)
        active_faculty = Faculty.objects.filter(is_active=True)
        self.fields['adviser'].queryset = active_faculty
        self.fields['capstone_teacher'].queryset = active_faculty
