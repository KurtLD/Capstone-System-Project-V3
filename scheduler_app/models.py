from django.db import models
from reco_app.models import Faculty  # Import the Faculty model
from django.utils import timezone
from users.models import SchoolYear

class Room(models.Model):
    name = models.CharField(max_length=255)
    status = models.PositiveIntegerField(default=None)

    def __str__(self):
        return self.name

class GroupInfoTH(models.Model):
    member1 = models.CharField(max_length=100, null=True, blank=True, default=None)
    member2 = models.CharField(max_length=100, null=True, blank=True, default=None)
    member3 = models.CharField(max_length=100, null=True, blank=True, default=None)
    section = models.CharField(max_length=50)
    subject_teacher = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    # Record the current active school year
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Group {self.section} with members:<br> {self.member1}<br> {self.member2}<br> {self.member3}<br>"

class Schedule(models.Model):
    group = models.ForeignKey(GroupInfoTH, on_delete=models.CASCADE, default=None)
    faculty1 = models.ForeignKey(Faculty, related_name='faculty1', on_delete=models.CASCADE)
    faculty2 = models.ForeignKey(Faculty, related_name='faculty2', on_delete=models.CASCADE)
    faculty3 = models.ForeignKey(Faculty, related_name='faculty3', on_delete=models.CASCADE)
    slot = models.CharField(max_length=20)  # e.g., "8AM-9AM", "1PM-2PM"
    date = models.CharField(max_length=10)
    day = models.CharField(max_length=10, default="Day 0")  # ex. Day 1, Day 2.....n
    # room = models.ForeignKey(Room, on_delete=models.CASCADE, default=None) 
    room = models.CharField(max_length=255, default=None)
    created_at = models.DateTimeField(default=timezone.now)
    new_sched = models.BooleanField(default=False)

    # New field to track if a schedule has been rescheduled
    has_been_rescheduled = models.BooleanField(default=False)
    

    # Optional: Add a timestamp for when the schedule was last modified
    modified_at = models.DateTimeField(auto_now=True)


    # Record the current active school year
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)

    def __str__(self):
        return f"{self.group} - {self.slot} on {self.date} in {self.room}"

    def get_members(self):
        return [self.group.member1, self.group.member2, self.group.member3]

    def get_faculties_by_members(self):
        return [self.faculty1, self.faculty2, self.faculty3]


# Models for the pre-oral
class GroupInfoPOD(models.Model):
    member1 = models.CharField(max_length=100, null=True, blank=True, default=None)
    member2 = models.CharField(max_length=100, null=True, blank=True, default=None)
    member3 = models.CharField(max_length=100, null=True, blank=True, default=None)
    title = models.CharField(max_length=200, null=True, default="")
    capstone_teacher = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='capstone_teacher')
    section = models.CharField(max_length=50)
    adviser = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='technical_adviser')
    # Record the current active school year
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Group {self.section} with members:<br> {self.member1}<br> {self.member2}<br> {self.member3}<br>"

    def get_members(self):
        return [self.member1, self.member2, self.member3]

    def get_members_html(self):
        members = self.get_members()
        return "<br>".join(filter(None, members))

class SchedulePOD(models.Model):
    group = models.ForeignKey(GroupInfoPOD, on_delete=models.CASCADE, related_name="members_POD", default=None)
    title = models.CharField(max_length=100, null=True, default="None")
    faculty1 = models.ForeignKey(Faculty, related_name='faculty1POD', on_delete=models.CASCADE)
    faculty2 = models.ForeignKey(Faculty, related_name='faculty2POD', on_delete=models.CASCADE)
    faculty3 = models.ForeignKey(Faculty, related_name='faculty3POD', on_delete=models.CASCADE)
    slot = models.CharField(max_length=20)  # e.g., "8AM-9AM", "1PM-2PM"
    date = models.CharField(max_length=10)  # e.g., "Day 1"
    day = models.CharField(max_length=10, default="Day 0")  # ex. Day 1, Day 2.....n
    # room = models.ForeignKey(Room, on_delete=models.CASCADE, default=None) 
    room = models.CharField(max_length=255, default=None)
    adviser = models.ForeignKey(Faculty, related_name='adviserPOD_sched', on_delete=models.CASCADE)
    capstone_teacher = models.ForeignKey(Faculty, related_name='capstone_teacherPOD_sched', on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    has_been_rescheduled = models.BooleanField(default=False)
    new_sched = models.BooleanField(default=False)
    
    # Optional: Add a timestamp for when the schedule was last modified
    modified_at = models.DateTimeField(auto_now=True)

    # Record the current active school year
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)
    
    def get_members(self):
        return [self.group.member1, self.group.member2, self.group.member3]
        
    def get_faculties_by_members(self):
        return [self.faculty1, self.faculty2, self.faculty3]

    def __str__(self):
        return f"{self.group} - {self.slot} on {self.date} in {self.room}"


# models for the mock defense
class GroupInfoMD(models.Model):
    member1 = models.CharField(max_length=100, null=True, blank=True, default=None)
    member2 = models.CharField(max_length=100, null=True, blank=True, default=None)
    member3 = models.CharField(max_length=100, null=True, blank=True, default=None)
    title = models.CharField(max_length=200, null=True, default="None")
    capstone_teacher = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='capstone_teacherMD')
    section = models.CharField(max_length=50)
    adviser = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='technical_adviserMD')
    # record the current active school year
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Group {self.section} with members:<br> {self.member1}<br> {self.member2}<br> {self.member3}<br>"

    def get_members(self):
        return [self.member1, self.member2, self.member3]

    def get_members_html(self):
        members = self.get_members()
        return "<br>".join(filter(None, members))


class ScheduleMD(models.Model):
    group = models.ForeignKey(GroupInfoMD, on_delete=models.CASCADE, related_name="members_MD",default=None)
    title = models.CharField(max_length=100, null=True, default="None")
    faculty1 = models.ForeignKey(Faculty, related_name='faculty1MD', on_delete=models.CASCADE)
    faculty2 = models.ForeignKey(Faculty, related_name='faculty2MD', on_delete=models.CASCADE)
    faculty3 = models.ForeignKey(Faculty, related_name='faculty3MD', on_delete=models.CASCADE)
    slot = models.CharField(max_length=20)  # e.g., "8AM-9AM", "1PM-2PM"
    date = models.CharField(max_length=10)  # e.g., "Day 1"
    day = models.CharField(max_length=10, default="Day 0")  #ex. Day 1, Day 2.....n
    # room = models.ForeignKey(Room, on_delete=models.CASCADE, default=None) 
    room = models.CharField(max_length=255, default=None)
    adviser = models.ForeignKey(Faculty, related_name='adviserMD_sched', on_delete=models.CASCADE)
    capstone_teacher = models.ForeignKey(Faculty, related_name='capstone_teacherMD_sched', on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    has_been_rescheduled = models.BooleanField(default=False)
    new_sched = models.BooleanField(default=False)
    
    # Optional: Add a timestamp for when the schedule was last modified
    modified_at = models.DateTimeField(auto_now=True)

    # record the current active school year
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)

    def get_members(self):
        return [self.group.member1, self.group.member2, self.group.member3]
        
    def get_faculties_by_members(self):
        return [self.faculty1, self.faculty2, self.faculty3]

    def __str__(self):
        return f"{self.group} - {self.slot} on {self.date} in {self.room}"


# models for the final defense
class GroupInfoFD(models.Model):
    member1 = models.CharField(max_length=100, null=True, blank=True, default=None)
    member2 = models.CharField(max_length=100, null=True, blank=True, default=None)
    member3 = models.CharField(max_length=100, null=True, blank=True, default=None)
    title = models.CharField(max_length=200, null=True, default="None")
    capstone_teacher = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='capstone_teacherFD')
    section = models.CharField(max_length=50)
    adviser = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='technical_adviserFD')
    # record the current active school year
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Group {self.section} with members:<br> {self.member1}<br> {self.member2}<br> {self.member3}<br>"

    def get_members(self):
        return [self.member1, self.member2, self.member3]

    def get_members_html(self):
        members = self.get_members()
        return "<br>".join(filter(None, members))


class ScheduleFD(models.Model):
    group = models.ForeignKey(GroupInfoFD, on_delete=models.CASCADE, related_name="members_FD",default=None)
    title = models.CharField(max_length=100, null=True, default="None")
    faculty1 = models.ForeignKey(Faculty, related_name='faculty1FD', on_delete=models.CASCADE)
    faculty2 = models.ForeignKey(Faculty, related_name='faculty2FD', on_delete=models.CASCADE)
    faculty3 = models.ForeignKey(Faculty, related_name='faculty3FD', on_delete=models.CASCADE)
    slot = models.CharField(max_length=20)  # e.g., "8AM-9AM", "1PM-2PM"
    date = models.CharField(max_length=10)  # e.g., "Day 1"
    day = models.CharField(max_length=10, default="Day 0")  #ex. Day 1, Day 2.....n
    # room = models.ForeignKey(Room, on_delete=models.CASCADE, default=None) 
    room = models.CharField(max_length=255, default=None)
    adviser = models.ForeignKey(Faculty, related_name='adviserFD_sched', on_delete=models.CASCADE)
    capstone_teacher = models.ForeignKey(Faculty, related_name='capstone_teacherFD_sched', on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    has_been_rescheduled = models.BooleanField(default=False)
    new_sched = models.BooleanField(default=False)
    
    # Optional: Add a timestamp for when the schedule was last modified
    modified_at = models.DateTimeField(auto_now=True)

    # record the current active school year
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE, default=None, null=True, blank=True)

    def get_members(self):
        return [self.group.member1, self.group.member2, self.group.member3]
        
    def get_faculties_by_members(self):
        return [self.faculty1, self.faculty2, self.faculty3]

    def __str__(self):
        return f"{self.group} - {self.slot} on {self.date} in {self.room}"
