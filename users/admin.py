from django.contrib import admin
from .models import (
    CustomUser, 
    Grade, 
    AuditTrail, 
    SchoolYear,

    # models used for pre oral
    PreOral_EvaluationSection, 
    PreOral_Criteria, 
    Verdict, 
    PreOral_Grade, 
    PreOral_Recos, 
    Checkbox,
    CriterionDescription,

    # models used for mock
    Mock_EvaluationSection, 
    Mock_Criteria, 
    Mock_Verdict, 
    Mock_Grade, 
    Mock_Recos, 
    Mock_Checkbox,

    # models used for final
    Final_EvaluationSection, 
    Final_Criteria, 
    Final_Verdict, 
    Final_Grade, 
    Final_Recos, 
    Final_Checkbox,

    Notif
    )
from .forms import CustomUserCreationForm

class CustomUserAdmin(admin.ModelAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserCreationForm
    model = CustomUser
    list_display = ['email', 'last_name', 'first_name', 'middle_name', 'age']

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Grade)
admin.site.register(AuditTrail)
admin.site.register(SchoolYear)
admin.site.register(Notif)


# Pre oral
admin.site.register(PreOral_Grade)
admin.site.register(PreOral_Recos)
admin.site.register(Verdict)
admin.site.register(Checkbox)
admin.site.register(CriterionDescription)


@admin.register(PreOral_EvaluationSection)
class PreOral_EvaluationSectionAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(PreOral_Criteria)
class PreOral_CriteriaAdmin(admin.ModelAdmin):
    list_display = ('section', 'name', 'percentage')


# Mock
admin.site.register(Mock_Verdict)
admin.site.register(Mock_Grade)
admin.site.register(Mock_Recos)
admin.site.register(Mock_Checkbox)

@admin.register(Mock_EvaluationSection)
class Mock_EvaluationSectionAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Mock_Criteria)
class Mock_CriteriaAdmin(admin.ModelAdmin):
    list_display = ('section', 'name', 'percentage')


# Final
admin.site.register(Final_Verdict)
admin.site.register(Final_Grade)
admin.site.register(Final_Recos)
admin.site.register(Final_Checkbox)

@admin.register(Final_EvaluationSection)
class Final_EvaluationSectionAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Final_Criteria)
class Final_CriteriaAdmin(admin.ModelAdmin):
    list_display = ('section', 'name', 'percentage')