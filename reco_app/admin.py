from django.contrib import admin
from .models import Faculty, Adviser, Expertise

class FacultyAdmin(admin.ModelAdmin):
    list_display = ['name', 'years_of_teaching', 'has_master_degree', 'highest_degree', 'is_active', 'is_capstone_teacher']
    search_fields = ['name', 'highest_degree']
    list_filter = ['is_active', 'has_master_degree', 'years_of_teaching']

class AdviserAdmin(admin.ModelAdmin):
    list_display = ['approved_title', 'faculty']
    search_fields = ['approved_title']
    list_filter = ['faculty']

admin.site.register(Faculty, FacultyAdmin)
admin.site.register(Adviser, AdviserAdmin)
admin.site.register(Expertise)

