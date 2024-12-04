from django import forms
from django.forms import ModelForm, ClearableFileInput
from .models import Review

class ReviewForm(ModelForm):
    text = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Write your review here...'
            }
        ),
        label=''
    )

    class Meta:
        model = Review
        fields = ['text']
