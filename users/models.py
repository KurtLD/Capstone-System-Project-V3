from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, datetime
import json
from reco_app.models import Faculty

class CustomUser(AbstractUser):
    email = models.EmailField(max_length=254, unique=True)
    first_name = models.CharField(max_length=30, null=True, blank=True)
    middle_name = models.CharField(max_length=30, null=True, blank=True)
    last_name = models.CharField(max_length=30, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    address = models.CharField(max_length=100, null=True, blank=True)
    years_of_teaching = models.IntegerField(null=True, blank=True)
    has_master_degree = models.BooleanField(default=False)
    highest_degree = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Expertise fields
    mobile_development = models.BooleanField(default=False)
    database_management = models.BooleanField(default=False)
    artificial_intelligence_and_machine_learning = models.BooleanField(default=False)
    internet_of_things = models.BooleanField(default=False)
    cybersecurity = models.BooleanField(default=False)
    geographic_information_systems = models.BooleanField(default=False)
    data_analytics_and_business_intelligence = models.BooleanField(default=False)
    ecommerce_digital_marketing = models.BooleanField(default=False)
    educational_technology = models.BooleanField(default=False)
    healthcare_informatics = models.BooleanField(default=False)
    game_development = models.BooleanField(default=False)
    human_computer_interaction = models.BooleanField(default=False)
    agricultural_technology = models.BooleanField(default=False)
    smart_city_technologies = models.BooleanField(default=False)
    fintechnology = models.BooleanField(default=False)
    computer_networks = models.BooleanField(default=False)
    software_engineering = models.BooleanField(default=False)
    multimedia_graphics = models.BooleanField(default=False)

    faculty = models.OneToOneField(
        Faculty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='custom_user_profile'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        # Calculate age if date_of_birth is provided
        if self.date_of_birth:
            today = date.today()
            self.age = today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        else:
            self.age = None

        super().save(*args, **kwargs)


User = get_user_model()

class AuditTrail(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=255, default="NONE")
    time = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(null=True, blank=True)  # Added field for IP address

    def __str__(self):
        return f"User: {self.user} (ID: {self.user_id}) performed action: '{self.action}' at {self.time} from IP {self.ip_address}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6, blank=True, null=True)


class Grade(models.Model):
    manuscript_mechanics = models.FloatField(default=0)
    chapter_1 = models.FloatField(default=0)
    chapter_2 = models.FloatField(default=0)
    chapter_3 = models.FloatField(default=0)
    system_performance = models.FloatField(default=0)
    user_interface = models.FloatField(default=0)
    system_input = models.FloatField(default=0)
    system_output = models.FloatField(default=0)
    system_control = models.FloatField(default=0)
    oral_presentation_1 = models.FloatField(default=0)
    oral_presentation_2 = models.FloatField(default=0)
    oral_presentation_3 = models.FloatField(default=0)
    overall_grade = models.FloatField(default=0)
    comments = models.TextField(blank=True, null=True)
    verdict = models.CharField(max_length=255)
    specific_verdict = models.TextField(blank=True, null=True)
    faculty = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    member1 = models.CharField(max_length=255)
    member2 = models.CharField(max_length=255)
    member3 = models.CharField(max_length=255)
    m1_content_organization = models.FloatField(default=0)
    m1_presentation_skills = models.FloatField(default=0)
    m1_QA = models.FloatField(default=0)
    m2_content_organization = models.FloatField(default=0)
    m2_presentation_skills = models.FloatField(default=0)
    m2_QA = models.FloatField(default=0)
    m3_content_organization = models.FloatField(default=0)
    m3_presentation_skills = models.FloatField(default=0)
    m3_QA = models.FloatField(default=0)

    def __str__(self):
        return f"{self.title} - {self.member1, self.member2, self.member3}"

class SchoolYear(models.Model):
    start_year = models.PositiveIntegerField()
    end_year = models.PositiveIntegerField()
    is_active = models.BooleanField(default=False)  # Indicates if it’s the current school year

    def __str__(self):
        return f"{self.start_year}-{self.end_year}"

    @classmethod
    def get_active_school_year(cls):
        # Return the currently active school year
        return cls.objects.filter(is_active=True).first()

    @classmethod
    def create_new_school_year(cls):
        # Get the current active year
        current_year = cls.get_active_school_year()

        # Get the last school year by ordering by end_year
        last_school_year = cls.objects.all().order_by('-end_year').first()

        if current_year:
            # Deactivate the current active year
            current_year.is_active = False
            current_year.save()

            # Create the next school year by incrementing start and end year of the last school year
            new_start_year = last_school_year.start_year + 1
            new_end_year = last_school_year.end_year + 1
        else:
            # If no school year exists, create the initial school year
            current_year_value = datetime.now().year
            new_start_year = current_year_value
            new_end_year = current_year_value + 1

        # Create and activate the new school year
        new_school_year = cls.objects.create(start_year=new_start_year, end_year=new_end_year, is_active=True)
        return new_school_year


# The following models are used for storing information for the pre-oral
class PreOral_EvaluationSection(models.Model):
    name = models.CharField(max_length=100)
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)

    def __str__(self):
        return self.name

class PreOral_Criteria(models.Model):
    section = models.ForeignKey(PreOral_EvaluationSection, related_name='criteria', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)  # Allows up to 100.00%
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)

    class Meta:
        unique_together = ('section', 'name')

    def __str__(self):
        return f"{self.name} ({self.percentage}%)"

class CriterionDescription(models.Model):
    criterion = models.ForeignKey(PreOral_Criteria, related_name='descriptions', on_delete=models.CASCADE)
    text = models.TextField()
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)

    def __str__(self):
        return self.text[:1000]  # Display the first 50 characters of the description

class Verdict(models.Model):
    name = models.CharField(max_length=255)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)  # Equivalent percentage for the verdict
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.percentage}%)"

class Checkbox(models.Model):
    verdict = models.ForeignKey(Verdict, related_name='checkboxes', on_delete=models.CASCADE)
    label = models.CharField(max_length=255)
    is_checked = models.BooleanField(default=False)
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)

    def __str__(self):
        return f"{self.label} (Checked: {self.is_checked})"

class PreOral_Grade(models.Model):
    faculty = models.CharField(max_length=255, default="NONE")  # Name or ID of the faculty member who is grading
    project_title = models.CharField(max_length=255, default="NONE")  # Stores the capstone project title
    grades_data = models.TextField(default="NONE")  # Use TextField to store JSON-encoded grades
    verdict = models.CharField(max_length=255, blank=True, null=True, default="NONE")  # Store verdict, if applicable
    checkbox_data = models.JSONField(default=dict)
    othervalue = models.TextField(blank=True, null=True, default=None)
    member1_grade = models.FloatField(default=-1)  # Default value of -1 indicates no data
    member2_grade = models.FloatField(default=-1)
    member3_grade = models.FloatField(default=-1)
    recommendation = models.TextField(default="NONE")
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)

    def __str__(self):
        return f"Grades by {self.faculty} - Project: {self.project_title} - Verdict: {self.verdict}"

    def get_grades_data(self):
        """Utility method to decode grades_data from JSON format"""
        try:
            return json.loads(self.grades_data)
        except json.JSONDecodeError:
            return {}

    def get_checkbox_data(self):
        return self.checkbox_data 

class PreOral_Recos(models.Model):
    project_title = models.CharField(max_length=255, default="NONE")
    recommendation = models.TextField(default="NONE")
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)

    def __str__(self):
        return f"Recommendation for the title: {self.project_title}"


# The following models are used for storing the mock defense information
class Mock_EvaluationSection(models.Model):
    name = models.CharField(max_length=100)
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)

    def __str__(self):
        return self.name

class Mock_Criteria(models.Model):
    section = models.ForeignKey(Mock_EvaluationSection, related_name='mcriteria', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)  # Allows up to 100.00%
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)

    class Meta:
        unique_together = ('section', 'name')

    def __str__(self):
        return f"{self.name} ({self.percentage}%)"

class MockCriterionDescription(models.Model):
    criterion = models.ForeignKey(Mock_Criteria, related_name='mdescriptions', on_delete=models.CASCADE)
    text = models.TextField()
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)

    def __str__(self):
        return self.text[:1000]  # Display the first 50 characters of the description

class Mock_Verdict(models.Model):
    name = models.CharField(max_length=255)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)  # Equivalent percentage for the verdict
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.percentage}%)"

class Mock_Checkbox(models.Model):
    verdict = models.ForeignKey(Mock_Verdict, related_name='mcheckboxes', on_delete=models.CASCADE)
    label = models.CharField(max_length=255)
    is_checked = models.BooleanField(default=False)
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)

    def __str__(self):
        return f"{self.label} (Checked: {self.is_checked})"

class Mock_Grade(models.Model):
    faculty = models.CharField(max_length=255, default="NONE")  # Name or ID of the faculty member who is grading
    project_title = models.CharField(max_length=255, default="NONE")  # Stores the capstone project title
    grades_data = models.TextField(default="NONE")  # Use TextField to store JSON-encoded grades
    verdict = models.CharField(max_length=255, blank=True, null=True, default="NONE")  # Store verdict, if applicable
    checkbox_data = models.JSONField(default=dict)
    othervalue = models.TextField(blank=True, null=True, default=None)
    member1_grade = models.FloatField(default=-1)  # Default value of -1 indicates no data
    member2_grade = models.FloatField(default=-1)
    member3_grade = models.FloatField(default=-1)
    recommendation = models.TextField(default="NONE")
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)

    def __str__(self):
        return f"Grades by {self.faculty} - Project: {self.project_title} - Verdict: {self.verdict}"

    def get_grades_data(self):
        """Utility method to decode grades_data from JSON format"""
        try:
            return json.loads(self.grades_data)
        except json.JSONDecodeError:
            return {}

    def get_checkbox_data(self):
        return self.checkbox_data 

class Mock_Recos(models.Model):
    project_title = models.CharField(max_length=255, default="NONE")
    recommendation = models.TextField(default="NONE")
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)

    def __str__(self):
        return f"Recommendation for the title: {self.project_title}"


# The following models are used for storing the final defense information
class Final_EvaluationSection(models.Model):
    name = models.CharField(max_length=100)
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)

    def __str__(self):
        return self.name

class Final_Criteria(models.Model):
    section = models.ForeignKey(Final_EvaluationSection, related_name='fcriteria', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)  # Allows up to 100.00%
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)

    class Meta:
        unique_together = ('section', 'name')

    def __str__(self):
        return f"{self.name} ({self.percentage}%)"

class FinalCriterionDescription(models.Model):
    criterion = models.ForeignKey(Final_Criteria, related_name='fdescriptions', on_delete=models.CASCADE)
    text = models.TextField()
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)

    def __str__(self):
        return self.text[:1000]  # Display the first 50 characters of the description

class Final_Verdict(models.Model):
    name = models.CharField(max_length=255)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)  # Equivalent percentage for the verdict
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.percentage}%)"

class Final_Checkbox(models.Model):
    verdict = models.ForeignKey(Final_Verdict, related_name='fcheckboxes', on_delete=models.CASCADE)
    label = models.CharField(max_length=255)
    is_checked = models.BooleanField(default=False)
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)

    def __str__(self):
        return f"{self.label} (Checked: {self.is_checked})"

class Final_Grade(models.Model):
    faculty = models.CharField(max_length=255, default="NONE")  # Name or ID of the faculty member who is grading
    project_title = models.CharField(max_length=255, default="NONE")  # Stores the capstone project title
    grades_data = models.TextField(default="NONE")  # Use TextField to store JSON-encoded grades
    verdict = models.CharField(max_length=255, blank=True, null=True, default="NONE")  # Store verdict, if applicable
    checkbox_data = models.JSONField(default=dict)
    othervalue = models.TextField(blank=True, null=True, default=None)
    member1_grade = models.FloatField(default=-1)  # Default value of -1 indicates no data
    member2_grade = models.FloatField(default=-1)
    member3_grade = models.FloatField(default=-1)
    recommendation = models.TextField(default="NONE")
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)

    def __str__(self):
        return f"Grades by {self.faculty} - Project: {self.project_title} - Verdict: {self.verdict}"

    def get_grades_data(self):
        """Utility method to decode grades_data from JSON format"""
        try:
            return json.loads(self.grades_data)
        except json.JSONDecodeError:
            return {}

    def get_checkbox_data(self):
        return self.checkbox_data 

class Final_Recos(models.Model):
    project_title = models.CharField(max_length=255, default="NONE")
    recommendation = models.TextField(default="NONE")
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)

    def __str__(self):
        return f"Recommendation for the title: {self.project_title}"


class Notif(models.Model):
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, default=None)
    notif = models.CharField(max_length=255, default="NONE")
    time = models.DateTimeField(default=timezone.now)
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)
    read_by = models.ManyToManyField(User, related_name='read_notifications', blank=True)
    personal_notif = models.BooleanField(default=False)

    def __str__(self):
        return f"A notif created: '{self.notif}' at {self.time}"

class UserNotif(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    notif = models.ForeignKey(Notif, on_delete=models.CASCADE)
    read = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('user', 'notif')  # Ensures a user can only have one entry per notification

    def __str__(self):
        return f"User {self.user.username} has read {self.notif.notif}"