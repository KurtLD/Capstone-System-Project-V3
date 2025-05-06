from django.db import models
from django.conf import settings

class Expertise(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Faculty(models.Model):
    name = models.CharField(max_length=100)
    years_of_teaching = models.PositiveIntegerField(null=True, blank=True)
    has_master_degree = models.BooleanField(default=False)
    highest_degree = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    expertise = models.ManyToManyField(Expertise, related_name='faculties', blank=True)
    custom_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='faculty_profile',
        null=True,
        blank=True
    )
    is_capstone_teacher = models.BooleanField(default=False)  # New field for capstone teacher
    is_available = models.BooleanField(default=True)
    # is_adviser = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def advisee_count(self):
        return Adviser.objects.filter(faculty=self).count()

    # def is_adviser_for_year(self):
    #     """
    #     Check if the faculty is an adviser for the given school year.
    #     """

    #     current_school_year = SchoolYear.get_active_school_year()
    #     adviser =  Adviser.objects.filter(faculty=self, school_year=current_school_year).exists()
    #     if adviser:
    #         self.is_adviser = True

class Adviser(models.Model):
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    approved_title = models.CharField(max_length=255)
    group_name = models.CharField(max_length=255, null=True, blank=True)
    # Defer the import to break circular dependency
    school_year = models.ForeignKey('users.SchoolYear', on_delete=models.CASCADE, default=None, null=True, blank=True)
    accepted = models.BooleanField(default=False)
    declined = models.BooleanField(default=False)
    has_been_replaced = models.BooleanField(default=False)

    notif = models.CharField(max_length=255, default=None, null=True)
    def __str__(self):
        return f"{self.approved_title} - {self.faculty}"