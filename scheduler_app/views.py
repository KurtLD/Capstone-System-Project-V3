import logging
import pandas as pd
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.core.files.storage import FileSystemStorage
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import GroupInfoTHForm, UploadFileForm, GenerateScheduleForm, GroupInfoPODForm, GroupInfoPODEditForm, GroupInfoMDForm, GroupInfoMDEditForm, GroupInfoFDForm, GroupInfoFDEditForm, RoomForm
from .models import GroupInfoTH, Faculty, Schedule, GroupInfoPOD, SchedulePOD, GroupInfoMD, ScheduleMD, GroupInfoFD, ScheduleFD, Room
from .utils import generate_schedule, get_faculty_assignments
from .utils2 import generate_schedulePOD, get_faculty_assignmentsPOD
from .utils3 import generate_scheduleMD, get_faculty_assignmentsMD
from .utils4 import generate_scheduleFD, get_faculty_assignmentsFD
from django.http import HttpResponse
from django.template.loader import render_to_string
from datetime import datetime, timedelta
from django.utils import timezone
from users.models import (
    CustomUser,
    Grade, 
    AuditTrail, 

    # the following models are used for the preoral
    Verdict, 
    PreOral_Grade, 
    PreOral_Recos, 
    Checkbox, 
    PreOral_EvaluationSection, 
    PreOral_Criteria,

    # the following models are used for the Mock defense
    Mock_EvaluationSection, 
    Mock_Criteria, 
    MockCriterionDescription,
    Mock_Verdict, 
    Mock_Checkbox,
    Mock_Grade, 
    Mock_Recos, 

    # the following models are used for the Final defense
    Final_EvaluationSection, 
    Final_Criteria, 
    FinalCriterionDescription,
    Final_Verdict, 
    Final_Checkbox,
    Final_Grade, 
    Final_Recos, 

    Notif
    )
from django.core.paginator import Paginator
from reco_app.models import Adviser
from django.db import transaction
from django.utils.dateparse import parse_date
from users.models import SchoolYear
from urllib.parse import urlencode
from django.utils.html import escape
from django.db.models import Q, Sum
from django.db.models import Exists, OuterRef
from fuzzywuzzy import fuzz
from fuzzywuzzy import process as fuzzy_process
import re
from collections import defaultdict
from django.db import models

# Set up logging
logger = logging.getLogger(__name__)

from django.db.models import Count, Case, When, Value, IntegerField, Subquery, OuterRef, Exists, BooleanField

def room_list(request):
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
    rooms = Room.objects.all().order_by('status')
    taken_statuses = Room.objects.values_list('status', flat=True).distinct()  # Get all distinct statuses

    # Handle room creation
    if request.method == 'POST':
        form = RoomForm(request.POST)
        if form.is_valid():
            room = form.save(commit=False)
            if room.status == 'None':
                room.status = 0  # Set status to 0 when 'None' is selected
            room.save()
            AuditTrail.objects.create(
                user=request.user,
                action=f"Created room {room.name} with status {room.status}",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return redirect('room_list')
        else:
            print("Unsuccess")
    else:
        form = RoomForm()

    return render(request, 'admin/rooms/room_management.html', {
        'rooms': rooms,
        'form': form,
        'taken_statuses': taken_statuses,
        'school_years': school_years, 
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
    })

def room_edit(request, pk):
    room = get_object_or_404(Room, pk=pk)
    if request.method == 'POST':
        form = RoomForm(request.POST, instance=room)
        if form.is_valid():
            room = form.save(commit=False)
            if room.status == 'None':
                room.status = 0  # Set status to 0 when 'None' is selected
            room.save()
            AuditTrail.objects.create(
                user=request.user,
                action=f"Edited room {room.name} with status {room.status}",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return redirect('room_list')
        else:
            print("Unsuccess")
    else:
        form = RoomForm(instance=room)
    
    return render(request, 'admin/rooms/room_management.html', {
        'rooms': Room.objects.all(),
        'form': form,
        'taken_statuses': Room.objects.values_list('status', flat=True).distinct()
    })

# Handle room deletion
def room_delete(request, pk):
    room = get_object_or_404(Room, pk=pk)
    if request.method == 'POST':
        room_name = room.name
        room.delete()

        # Reassign statuses to remaining rooms after deletion
        rooms = Room.objects.all().order_by('status')
        for i, room in enumerate(rooms):
            room.status = i + 1
            room.save()

        AuditTrail.objects.create(
            user=request.user,
            action=f"Deleted room {room_name}",
            ip_address=request.META.get('REMOTE_ADDR')
        )

        return redirect('room_list')

    return redirect('room_list')

# this check if there are already groups for the title hearing
def checker1(request):
    # get the current active school year
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

    if not GroupInfoTH.objects.filter(school_year=selected_school_year).exists():
        messages.warning(request, 'No groups found. Please add groups first to generate schedule for title hearing.')
        empty = "True"
        message = "No groups found. Please add groups first to generate schedule for title hearing."
        url = reverse('add_group')
        query_string = urlencode({'empty': empty, 'message': message})
        return redirect(f'{url}?{query_string}')
    else:
        return redirect('schedule_list')
    
@login_required
def add_group(request):
    # Check for the conflict query parameter
    empty_str = request.GET.get('empty')  # Should return True if 'conflict' param is 'True'
    message = request.GET.get('message')
    empty = empty_str.lower() == 'true' if empty_str else False #variable to hold a bolean value

    # Get the last added school year in the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the current active school year
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

    # Check if the active school year is same as the last added school year
    if selected_school_year != last_school_year:
        return HttpResponse("Oops, you are no longer allowed to access this page.")

    if request.method == 'POST':
        if 'upload_file' in request.FILES:
            upload_file_form = UploadFileForm(request.POST, request.FILES)
            if upload_file_form.is_valid():
                file = request.FILES['upload_file']
                fs = FileSystemStorage()
                filename = fs.save(file.name, file)
                file_path = fs.path(filename)

                try:
                    process_excel_file(file_path)
                    messages.success(request, 'File uploaded and processed successfully.')
                    
                    # Log the action in AuditTrail
                    AuditTrail.objects.create(
                        user=request.user,
                        action="Uploaded and processed file for group addition in Title Hearing",
                        ip_address=request.META.get('REMOTE_ADDR')
                    )
                except Exception as e:
                    logger.error(f'Error processing file: {e}')
                    messages.error(request, f'Error processing file: {e}')
                return redirect(reverse('carousel_page') + '#title-hearing-details')
        else:
            form = GroupInfoTHForm(request.POST)
            if form.is_valid():
                section = form.save(commit=False)  # Create the section instance but don't save yet

                # Normalize names for the three members
                section.member1 = normalize_name_improved(section.member1)
                section.member2 = normalize_name_improved(section.member2)
                section.member3 = normalize_name_improved(section.member3) if section.member3 else section.member3

                # Get the current active school year
                active_school_year = SchoolYear.get_active_school_year()
                
                # If no active school year exists, create a new one
                if not active_school_year:
                    active_school_year = SchoolYear.create_new_school_year()

                # Now that we are sure there is an active school year, we can use it
                section.school_year = active_school_year
                section.save()
                messages.success(request, 'Group added successfully.')
                
                # Log the action in AuditTrail
                AuditTrail.objects.create(
                    user=request.user,
                    action="Added a New Group in Title Hearing",
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                return redirect(reverse('carousel_page') + '#title-hearing-details')
    else:
        form = GroupInfoTHForm()
        upload_file_form = UploadFileForm()
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

    return render(request, 'admin/title_hearing/add_group.html', {
        'form': form, 
        'upload_file_form': upload_file_form, 
        'school_years': school_years, 
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'empty': empty,
        'message': message
    })


# def normalize_name_improved(name):
#     """
#     Normalizes a name by handling cases like:
#     - "Lastname, Firstname" → "Firstname Lastname"
#     - "Firstname Middlename Lastname" → "Firstname Middlename Lastname"
#     It strips unnecessary spaces, handles commas, and preserves middle names/initials.
#     """
#     # Convert name to a string to handle cases where it's not a string
#     name = str(name).strip()
    
#     # Replace any sequences of whitespace with a single space
#     name = re.sub(r'\s+', ' ', name)
    
#     # Handle "Last, First" format
#     if ',' in name:
#         last, first = name.split(',', 1)
#         normalized_name = f"{first.strip()} {last.strip()}"
#     else:
#         # If it's already in "First Last" format, just use it
#         normalized_name = name

#     # Optionally, remove special characters
#     normalized_name = re.sub(r'[^\w\s]', '', normalized_name)

#     return normalized_name

def normalize_name_improved(name):
    """
    Normalizes name to 'Lastname, Firstname, M.I.' format
    
    Handles various name formats more robustly:
    - Single names
    - First Last
    - First Middle Last
    - Last, First
    - Last, First Middle
    """
    # Convert to string and strip whitespace
    name = str(name).strip()
    
    # Replace multiple spaces with single space
    name = re.sub(r'\s+', ' ', name)
    
    # Handle "Last, First" format
    if ',' in name:
        last, first = name.split(',', 1)
        last = last.strip()
        first = first.strip()
    else:
        # Split name into parts
        parts = name.split()
        if len(parts) == 1:
            return parts[0]  # Single name
        
        # More robust last name extraction
        # Assume last name is the last part, but with some intelligence
        last = parts[-1]
        first_parts = parts[:-1]
        first = ' '.join(first_parts)
    
    # Extract middle initial (if exists)
    name_parts = first.split()
    mi = ''
    if len(name_parts) > 1:
        # Check the last part for potential middle initial
        potential_mi = name_parts[-1]
        # If it's a single letter or single letter followed by a period
        if len(potential_mi) == 1 or (len(potential_mi) == 2 and potential_mi[1] == '.'):
            mi = potential_mi if potential_mi.endswith('.') else potential_mi + '.'
            # Remove the middle initial from the first name
            first = ' '.join(name_parts[:-1])
    
    # Return normalized name 
    return f"{last}, {first} {mi}".rstrip(', ')

# Function to find matching faculty using normalized names and fuzzy logic
def find_matching_faculty(subject_teacher_name):
    """
    Finds a matching faculty member in the database using fuzzy string matching.
    It compares the first and last names and returns the best match with a threshold.
    """
    normalized_name = normalize_name_improved(subject_teacher_name)
    potential_faculties = Faculty.objects.all()

    best_match = None
    best_score = 0

    for faculty in potential_faculties:
        faculty_normalized_name = normalize_name_improved(faculty.name)
        match_score = fuzz.ratio(normalized_name, faculty_normalized_name)

        if match_score > best_score:
            best_score = match_score
            best_match = faculty

    # Define a threshold for considering a match good enough
    if best_score >= 85:  # This threshold can be adjusted
        return best_match
    return None


# Updated function to process the uploaded Excel file
# def process_excel_file(file_path):
#     try:
#         # Read the Excel file
#         df = pd.read_excel(file_path)

#         # Validate the required columns
#         required_columns = ['Member 1', 'Member 2', 'Member 3', 'Section', 'Subject Teacher']
#         for col in required_columns:
#             if col not in df.columns:
#                 raise ValueError(f"Missing required column: {col}")

#         # Process each row
#         for _, row in df.iterrows():
#             # Get subject teacher name and normalize
#             subject_teacher_name = row['Subject Teacher']
#             subject_teacher = find_matching_faculty(subject_teacher_name)
            
#             if not subject_teacher:
#                 logger.error(f"Subject Teacher '{subject_teacher_name}' not found or matched in the system.")
#                 continue  # Skip this row if no matching teacher is found

#             # Normalize and clean member names
#             member1 = normalize_name_improved(row['Member 1'])
#             member2 = normalize_name_improved(row['Member 2'])
#             member3 = normalize_name_improved(row['Member 3'])

#             # Get the current active school year
#             active_school_year = SchoolYear.get_active_school_year()

#             # If no active school year exists, create a new one
#             if not active_school_year:
#                 active_school_year = SchoolYear.create_new_school_year()
            
#             # Create GroupInfoTH record
#             GroupInfoTH.objects.create(
#                 member1=member1,
#                 member2=member2,
#                 member3=member3,
#                 section=row['Section'],
#                 subject_teacher=subject_teacher,
#                 school_year=active_school_year
#             )
        
#     except Exception as e:
#         logger.error(f"Error processing file: {e}")
#         raise

def process_excel_file(file_path):
    try:
        # Read the Excel file
        df = pd.read_excel(file_path)

        # Validate the required columns
        required_columns = ['Member 1', 'Member 2', 'Member 3', 'Section', 'Subject Teacher']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        # Process each row
        for _, row in df.iterrows():
            # Get subject teacher name and normalize
            subject_teacher_name = row['Subject Teacher']
            subject_teacher = find_matching_faculty(subject_teacher_name)
            
            if not subject_teacher:
                logger.error(f"Subject Teacher '{subject_teacher_name}' not found or matched in the system.")
                continue  # Skip this row if no matching teacher is found

            # Normalize and clean member names, or set to None if blank
            member1 = normalize_name_improved(row['Member 1']) if pd.notna(row['Member 1']) and row['Member 1'].strip() else None
            member2 = normalize_name_improved(row['Member 2']) if pd.notna(row['Member 2']) and row['Member 2'].strip() else None
            member3 = normalize_name_improved(row['Member 3']) if pd.notna(row['Member 3']) and row['Member 3'].strip() else None

            # Get the current active school year
            active_school_year = SchoolYear.get_active_school_year()

            # If no active school year exists, create a new one
            if not active_school_year:
                active_school_year = SchoolYear.create_new_school_year()
            
            # Create GroupInfoTH record
            GroupInfoTH.objects.create(
                member1=member1,
                member2=member2,
                member3=member3,
                section=row['Section'],
                subject_teacher=subject_teacher,
                school_year=active_school_year
            )
        
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise


def faculty_assignments_view(request):
    if request.method == 'GET':
        faculty_assignments = get_faculty_assignmentsPOD()
        return JsonResponse({'success': True, 'faculty_assignments': faculty_assignments})
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

# Use for generating and displaying the schedule for title hearing
def schedule_list(request):
    # get the last added school year in the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # get the current active school year
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

    last_used_date_str = request.GET.get('last_used_date')
    print("last_used_date_str: ", last_used_date_str)

    last_used_date = None
    if last_used_date_str:
        last_used_date = last_used_date_str
    else:
        # Fetch the latest schedule date
        last_schedule = Schedule.objects.filter(school_year=selected_school_year).order_by('-date').first()
        last_used_date = last_schedule.date if last_schedule else None
    print("last_used_date: ", last_used_date)

    # Check for the conflict query parameter
    conflict_str = request.GET.get('conflict')  # Should return True if 'conflict' param is 'True'
    message = request.GET.get('message')
    conflict = conflict_str.lower() == 'true' if conflict_str else False #variable to hold a bolean value
    print('Conflict query parameter received:', conflict_str)  # Debugging line
    print('Query parameters:', request.GET)  # Debugging output
    print('Conflict status:', conflict)  # Check what the conflict value is

    if request.method == 'POST':
        start_date_str = request.POST.get('start_date')
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                generate_schedule(request, start_date=start_date)
                messages.success(request, 'Schedule generated successfully.')
            except Exception as e:
                messages.error(request, f'Error generating schedule: {e}')

            # Record the recommendation event in the audit trail
            AuditTrail.objects.create(
                user=request.user,
                action=f"Generate Schedule for Title Hearing starting date is {start_date.strftime('%B %d, %Y')}",
                ip_address=request.META.get('REMOTE_ADDR')
            )

            # creating a notif
            Notif.objects.create(
                created_by=request.user,
                notif=f"Generate New Schedule for Title Hearing starting date is {start_date.strftime('%B %d, %Y')}",
            )
            return redirect('schedule_list')

    # current_school_year = SchoolYear.get_active_school_year()
    # Fetch all schedules from the database, ordered by date, room, and slot
    schedules = Schedule.objects.filter(school_year=selected_school_year).order_by('date')
    grouped_schedules = {}

    # Helper function to convert slot time to sortable format
    def convert_slot_to_sortable(slot):
        start_time = slot.split('-')[0].strip()
        period = start_time[-2:]  # AM or PM
        time_parts = start_time[:-2].strip().split(':')
        
        hour = int(time_parts[0])
        minute = int(time_parts[1]) if len(time_parts) == 2 else 0

        if period == 'PM' and hour != 12:
            hour += 12
        if period == 'AM' and hour == 12:
            hour = 0

        return hour * 60 + minute

    # Group schedules by (date, room, day)
    for schedule in schedules:
        day_room = (schedule.day, schedule.date, schedule.room)
        if day_room not in grouped_schedules:
            grouped_schedules[day_room] = []
        grouped_schedules[day_room].append(schedule)

    # Sort schedules within each group by slot time
    for day_room in grouped_schedules:
        grouped_schedules[day_room].sort(key=lambda x: convert_slot_to_sortable(x.slot))
    
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
    
    rooms = Room.objects.all().order_by("status")

    # new_slot = request.GET.get('new_slot')
    # new_date = request.GET.get('new_date')
    # new_day = request.GET.get('new_day')
    # new_room = request.GET.get('new_room')
    new_group = request.GET.get('new_group')
    print('new_group: ', new_group)

    new_schedule = Schedule.objects.order_by('-created_at').first()

    return render(request, 'admin/title_hearing/schedule_list.html', {
        'grouped_schedules': grouped_schedules,
        'school_years': school_years, 
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'conflict': conflict,
        'message': message,
        'last_used_date': last_used_date,
        'rooms': rooms,
        # 'new_slot': new_slot,
        # 'new_date': new_date,
        # 'new_day': new_day,
        # 'new_room': new_room,
        'new_group': new_group,
        'new_schedule': new_schedule
        })

def reschedule(request, schedule_id):
    # Get the last added school year in the database
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the current active school year
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

    # Check if the active school year is the same as the last added school year
    if selected_school_year != last_school_year:
        return HttpResponse("Oops, you are no longer allowed to access this page.")

    # Get the schedule object by ID
    schedule = get_object_or_404(Schedule, id=schedule_id)
    base_time_slots = ["8AM-9AM", "9AM-10AM", "10AM-11AM", "11AM-12PM", "1PM-2PM", "2PM-3PM", "3PM-4PM", "4PM-5PM"]
    rooms = Room.objects.all().order_by("status")

    # Adjust time slots based on whether the day is Monday or a weekend
    def get_valid_time_slots(current_date):
        weekday = current_date.weekday()
        if weekday == 0:  # Monday
            return base_time_slots[1:]  # Exclude 8AM-9AM on Monday
        elif weekday >= 5:  # Saturday or Sunday
            return []  # No scheduling on weekends
        return base_time_slots

    # Check if a faculty is already booked for the slot on the same day
    def is_faculty_available(faculty_list, date, slot):
        for faculty in faculty_list:
            if Schedule.objects.filter(
                (Q(faculty1=faculty) | Q(faculty2=faculty) | Q(faculty3=faculty)),
                date=date.strftime('%B %d, %Y'),
                slot=slot,
                school_year=selected_school_year
            ).exists():
                return False  # Faculty is booked for that slot
        return True

    # Get the last schedule to ensure we reschedule after the last slot
    last_schedule = Schedule.objects.filter(school_year=selected_school_year).order_by('-date').first()
    print("last sched: ", last_schedule)
    if not last_schedule:
        return JsonResponse({'success': False, 'message': 'No existing schedules found.'})

    last_date_str = last_schedule.date
    last_date = datetime.strptime(last_date_str, '%B %d, %Y')
    last_slot = last_schedule.slot
    last_day_str = last_schedule.day
    last_day_number = int(last_day_str.split()[1])  # Extract day number (e.g., "Day 2" -> 2)

    next_date = datetime.strptime(schedule.date, '%B %d, %Y')
    next_day_number = int(schedule.day.split()[1])  # Extract the day number from the current schedule

    # Step 1: Find any available vacant slots that have no records and don't cause a conflict
    while next_date <= last_date:
        valid_time_slots = get_valid_time_slots(next_date)
        if not valid_time_slots:  # Skip weekends or invalid days
            next_date += timedelta(days=1)
            # next_day_number += 1
            continue

        for slot in valid_time_slots:  # Iterate over available time slots
            for room in rooms:  # Iterate over rooms
                faculties = [schedule.faculty1, schedule.faculty2, schedule.faculty3]
                if is_faculty_available(faculties, next_date, slot):
                    if not Schedule.objects.filter(
                        date=next_date.strftime('%B %d, %Y'),
                        room=room,
                        slot=slot,
                        school_year=selected_school_year
                    ).exists():
                        # Found a vacant slot
                        next_slot = slot
                        next_room = room

                        # Query to check if there is a SchedulePOD with the given criteria
                        schedule_day = Schedule.objects.filter(
                            date=next_date.strftime('%B %d, %Y'),
                            room=room,
                            school_year=selected_school_year
                        ).first() 

                        # Mark the existing schedule as rescheduled
                        schedule.has_been_rescheduled = True
                        schedule.save()
                        print("next_slot: ", next_slot)
                        if schedule_day:
                            # Create the new schedule entry
                            new_schedule = Schedule.objects.create(
                                group=schedule.group,
                                faculty1=schedule.faculty1,
                                faculty2=schedule.faculty2,
                                faculty3=schedule.faculty3,
                                slot=next_slot,
                                date=next_date.strftime('%B %d, %Y'),
                                day=schedule_day.day,
                                room=next_room,
                                school_year=selected_school_year,
                                new_sched = True
                            )
                        else:
                            # Create the new schedule entry
                            new_schedule = Schedule.objects.create(
                                group=schedule.group,
                                faculty1=schedule.faculty1,
                                faculty2=schedule.faculty2,
                                faculty3=schedule.faculty3,
                                slot=next_slot,
                                date=next_date.strftime('%B %d, %Y'),
                                day=f"Day {next_day_number}",
                                room=next_room,
                                school_year=selected_school_year,
                                new_sched = True
                            )

                        # Log the action in AuditTrail
                        AuditTrail.objects.create(
                            user=request.user,
                            action=f"Rescheduled Title Hearing Group: {schedule.group} from {schedule.slot} on {schedule.date} ({schedule.day}) to {next_slot} on {next_date.strftime('%B %d, %Y')} (Day {next_day_number})",
                            ip_address=request.META.get('REMOTE_ADDR')
                        )

                        # creating a notif
                        Notif.objects.create(
                            created_by=request.user,
                            notif=f"This Title Hearing Group: {schedule.group} has been rescheduled from {schedule.slot} on {schedule.date} ({schedule.day}) to {next_slot} on {next_date.strftime('%B %d, %Y')} (Day {next_day_number})"
                        )


                        # return redirect('schedule_list')
                        url = reverse('schedule_list')
                        new_slot=next_slot,
                        new_date=next_date.strftime('%B %d, %Y'),
                        new_day=f"Day {next_day_number}",
                        new_room=next_room,
                        new_group=schedule.group
                        print("new_groupr: ", new_group)
                        query_string = urlencode({'new_slot': new_slot, 'new_date': new_date, 'new_day': new_day, 'new_room': new_room, 'new_group': new_group})
                        return redirect(f'{url}?{query_string}')


        # Move to the next day if no available slot was found on the current date
        next_date += timedelta(days=1)
        next_day_number += 1

    # Step 2: Find slots after the last scheduled date, similar logic
    max_reschedule_date = last_date + timedelta(weeks=3)
    next_date = last_date
    next_day_number = last_day_number
    next_slot_index = 0  # Start with the first slot in valid time slots for each day

    while next_date <= max_reschedule_date:
        valid_time_slots = get_valid_time_slots(next_date)  # Adjusts for Mondays and weekends
        if not valid_time_slots:  # Skip weekends or invalid days
            next_date += timedelta(days=1)
            # next_day_number += 1
            continue

        for slot in valid_time_slots[next_slot_index:]:  # Start from next_slot_index for valid slots
            for room in rooms:
                faculties = [schedule.faculty1, schedule.faculty2, schedule.faculty3]
                if is_faculty_available(faculties, next_date, slot):
                    if not Schedule.objects.filter(
                        date=next_date.strftime('%B %d, %Y'),
                        room=room,
                        slot=slot,
                        school_year=selected_school_year
                    ).exists():

                        # Determine the day label for this schedule entry
                        schedule_day = Schedule.objects.filter(
                            date=next_date.strftime('%B %d, %Y'),
                            room=room,
                            school_year=selected_school_year
                        ).first()

                        # Room and slot are available, reschedule
                        next_slot = slot
                        next_room = room

                        # Mark the existing schedule as rescheduled
                        schedule.has_been_rescheduled = True
                        schedule.save()

                        if schedule_day:
                            # Create the new schedule entry
                            new_schedule = Schedule.objects.create(
                                group=schedule.group,
                                faculty1=schedule.faculty1,
                                faculty2=schedule.faculty2,
                                faculty3=schedule.faculty3,
                                slot=slot,
                                date=next_date.strftime('%B %d, %Y'),
                                day=schedule_day.day,
                                room=next_room,
                                school_year=selected_school_year,
                                new_sched = True
                            )
                        else:
                            # Create the new schedule entry
                            new_schedule = Schedule.objects.create(
                                group=schedule.group,
                                faculty1=schedule.faculty1,
                                faculty2=schedule.faculty2,
                                faculty3=schedule.faculty3,
                                slot=slot,
                                date=next_date.strftime('%B %d, %Y'),
                                day=f"Day {next_day_number}",
                                room=next_room,
                                school_year=selected_school_year,
                                new_sched = True
                            )

                        # Log the action in AuditTrail
                        AuditTrail.objects.create(
                            user=request.user,
                            action=f"Rescheduled Title Hearing Group: {schedule.group} from {schedule.slot} on {schedule.date} ({schedule.day}) to {slot} on {next_date.strftime('%B %d, %Y')} (Day {next_day_number})",
                            ip_address=request.META.get('REMOTE_ADDR')
                        )

                        # creating a notif
                        Notif.objects.create(
                            created_by=request.user,
                            notif=f"This Title Hearing Group: {schedule.group} has been rescheduled from {schedule.slot} on {schedule.date} ({schedule.day}) to {next_slot} on {next_date.strftime('%B %d, %Y')} (Day {next_day_number})"
                        )

                        # return redirect('schedule_list')
                        url = reverse('schedule_list')
                        new_slot=next_slot,
                        new_date=next_date.strftime('%B %d, %Y'),
                        new_day=f"Day {next_day_number}",
                        new_room=next_room,
                        new_group=schedule.group
                        query_string = urlencode({'new_slot': new_slot, 'new_date': new_date, 'new_day': new_day, 'new_room': new_room, 'new_group': new_group})
                        return redirect(f'{url}?{query_string}')

        # Move to the next day if no available slot was found on the current date
        next_date += timedelta(days=1)
        next_day_number += 1
        next_slot_index = 0  # Reset index for new day


    # If no available slots found within 2 weeks
    return JsonResponse({'success': False, 'message': 'No available slots to reschedule within the 2-week limit.'})


def reassign(request, schedule_id):
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
        new_date_str = request.POST.get('new_date')
        new_time_str = request.POST.get('new_time')
        new_lab_id = request.POST.get('new_lab')  # Fetch the room ID
        last_used_date_str = request.POST.get('last_used_date')  # Fetch the last used date

        if new_date_str and new_time_str and new_lab_id:
            try:
                new_date = datetime.strptime(new_date_str, '%Y-%m-%d')
                print("new_date: ", new_date)

                # Fetch the Room instance using the new_lab_id
                new_lab = get_object_or_404(Room, id=new_lab_id)

                # Get the earliest schedule date (the start date)
                earliest_schedule = Schedule.objects.filter(school_year=selected_school_year).order_by('date').first()
                if not earliest_schedule:
                    messages.error(request, 'No schedules found for the current school year.')
                    return redirect('schedule_list')

                earliest_date = datetime.strptime(earliest_schedule.date, '%B %d, %Y')
                print("earliest_date: ", earliest_date)

                # Ensure new date is not earlier than the earliest schedule
                if new_date < earliest_date:
                    conflict = "True"
                    message = "Cannot reschedule to a date earlier than the original schedule."
                    url = reverse('schedule_list')
                    query_string = urlencode({'conflict': conflict, 'message': message, 'last_used_date': last_used_date_str})
                    return redirect(f'{url}?{query_string}')

                # Check if the new date is within one to two weeks from the earliest schedule date
                if not (earliest_date <= new_date <= earliest_date + timedelta(weeks=3)):
                    conflict = "True"
                    message = "Rescheduling is only allowed within one to two weeks from the original schedule."
                    url = reverse('schedule_list')
                    query_string = urlencode({'conflict': conflict, 'message': message, 'last_used_date': last_used_date_str})
                    return redirect(f'{url}?{query_string}')

                # Check if the new schedule already exists
                if Schedule.objects.filter(date=new_date.strftime('%B %d, %Y'), slot=new_time_str, room=new_lab, school_year=selected_school_year).exists():
                    conflict = "True"
                    message = "Schedule already exists for the selected date, time, and room. Please choose a different slot."
                    url = reverse('schedule_list')
                    query_string = urlencode({'conflict': conflict, 'message': message, 'last_used_date': last_used_date_str})
                    return redirect(f'{url}?{query_string}')

                schedule = get_object_or_404(Schedule, id=schedule_id)
                faculties = [schedule.faculty1, schedule.faculty2, schedule.faculty3]

                # Check if any faculty is double-booked for the new date and time
                for faculty in faculties:
                    if Schedule.objects.filter(
                        date=new_date.strftime('%B %d, %Y'),
                        slot=new_time_str,
                        school_year=selected_school_year
                    ).filter(
                        (Q(faculty1=faculty) | Q(faculty2=faculty) | Q(faculty3=faculty))
                    ).exists():
                        conflict = "True"
                        message = f"Faculty {faculty.name} already has a schedule on {new_date.strftime('%B %d, %Y')} at {new_time_str}. Please choose a different slot or adjust the faculty assignment."
                        url = reverse('schedule_list')
                        query_string = urlencode({'conflict': conflict, 'message': message, 'last_used_date': last_used_date_str})
                        return redirect(f'{url}?{query_string}')

                # Calculate day_count excluding weekends
                current_date = earliest_date
                day_count = 0
                while current_date <= new_date:
                    if current_date.weekday() < 5:  # Only count weekdays (Mon-Fri)
                        day_count += 1
                    current_date += timedelta(days=1)
                
                print("day count (excluding weekends): ", day_count)

                # Mark the existing schedule as rescheduled
                schedule.has_been_rescheduled = True
                schedule.save()

                # Create the new schedule entry with the updated information
                new_schedule = Schedule.objects.create(
                    group=schedule.group,
                    faculty1=schedule.faculty1,
                    faculty2=schedule.faculty2,
                    faculty3=schedule.faculty3,
                    slot=new_time_str,
                    date=new_date.strftime('%B %d, %Y'),
                    day=f"Day {day_count}",  # Use the calculated day count
                    room=new_lab,
                    school_year=selected_school_year,
                    new_sched = True
                )

                # Log the action in AuditTrail
                AuditTrail.objects.create(
                    user=request.user,
                    action=f"Rescheduled Title Hearing Group: {schedule.group} from {schedule.slot} on {schedule.date} ({schedule.day}) to {new_time_str} on {new_date.strftime('%B %d, %Y')} (Day {day_count})",
                    ip_address=request.META.get('REMOTE_ADDR')
                )

                # creating a notif
                Notif.objects.create(
                    created_by=request.user,
                    notif=f"This Title Hearing Group: {schedule.group} has been rescheduled from {schedule.slot} on {schedule.date} ({schedule.day}) to {new_time_str} on {new_date.strftime('%B %d, %Y')} (Day {day_count})"
                )

                messages.success(request, 'Schedule rescheduled successfully.')
                # Redirect to schedule_list with last_used_date included
                url = reverse('schedule_list')
                new_group = schedule.group
                query_string = urlencode({'last_used_date': last_used_date_str, 'new_group': new_group})
                return redirect(f'{url}?{query_string}')


            except Exception as e:
                messages.error(request, f'Error during rescheduling: {e}')
                # Include last_used_date in error redirect
                url = reverse('schedule_list')
                query_string = urlencode({'last_used_date': last_used_date_str})
                return redirect(f'{url}?{query_string}')
        else:
            messages.error(request, 'Please provide a date, time, and room.')
            # Include last_used_date in the redirect
            url = reverse('schedule_list')
            query_string = urlencode({'last_used_date': last_used_date_str})
            return redirect(f'{url}?{query_string}')
    else:
        messages.error(request, 'Invalid request method.')
        return redirect('schedule_list')



# def reassign(request, schedule_id):
#     current_school_year = SchoolYear.get_active_school_year()
#     if request.method == 'POST':
#         new_date_str = request.POST.get('new_date')
#         new_time_str = request.POST.get('new_time')
#         new_lab_id = request.POST.get('new_lab')  # Fetch the room ID
#         last_used_date_str = request.POST.get('last_used_date')  # Fetch the last used date
#         print("r_last_used_date: ", last_used_date_str)
#         print("room id: ", new_lab_id)
#         print("Request POST data:", request.POST)

#         if new_date_str and new_time_str and new_lab_id:
#             try:
#                 new_date = datetime.strptime(new_date_str, '%Y-%m-%d')

#                 # Fetch the Room instance using the new_lab_id
#                 new_lab = get_object_or_404(Room, id=new_lab_id)

#                 # Get the earliest schedule for the current school year
#                 earliest_schedule = Schedule.objects.filter(school_year=current_school_year).order_by('date').first()
#                 if earliest_schedule:
#                     earliest_date = datetime.strptime(earliest_schedule.date, '%B %d, %Y')

#                     # Calculate day_count excluding weekends
#                     current_date = earliest_date
#                     day_count = 0
#                     while current_date <= new_date:
#                         if current_date.weekday() < 5:  # Only count weekdays (Mon-Fri)
#                             day_count += 1
#                         current_date += timedelta(days=1)
#                     print("day count (excluding weekends): ", day_count)

#                     # Ensure the new date is not earlier than the earliest schedule
#                     if new_date < earliest_date:
#                         conflict = "True"
#                         message = "Cannot reschedule to a date earlier than the original schedule."
#                         url = reverse('schedule_list')
#                         query_string = urlencode({'conflict': conflict, 'message': message, 'last_used_date': last_used_date_str})
#                         return redirect(f'{url}?{query_string}')

#                     # Check if the new date is within three weeks from the earliest schedule date
#                     if not (earliest_date <= new_date <= earliest_date + timedelta(weeks=3)):
#                         conflict = "True"
#                         message = "Rescheduling is only allowed within one to three weeks from the original schedule."
#                         url = reverse('schedule_list')
#                         query_string = urlencode({'conflict': conflict, 'message': message, 'last_used_date': last_used_date_str})
#                         return redirect(f'{url}?{query_string}')

#                 # Check if the selected room and time slot is already booked
#                 if Schedule.objects.filter(date=new_date.strftime('%B %d, %Y'), slot=new_time_str, room=new_lab, school_year=current_school_year).exists():
#                     conflict = "True"
#                     message = "Schedule already exists for the selected date, time, and room. Please choose a different slot."
#                     url = reverse('schedule_list')
#                     query_string = urlencode({'conflict': conflict, 'message': message, 'last_used_date': last_used_date_str})
#                     return redirect(f'{url}?{query_string}')

#                 # Check for conflicts with faculty assignments
#                 schedule = get_object_or_404(Schedule, id=schedule_id)
#                 faculties = [schedule.faculty1, schedule.faculty2, schedule.faculty3]

#                 for faculty in faculties:
#                     if Schedule.objects.filter(
#                         date=new_date.strftime('%B %d, %Y'),
#                         slot=new_time_str,
#                         school_year=current_school_year
#                     ).filter(
#                         (Q(faculty1=faculty) | Q(faculty2=faculty) | Q(faculty3=faculty))
#                     ).exists():
#                         conflict = "True"
#                         message = f"Faculty {faculty.name} already has a schedule on {new_date.strftime('%B %d, %Y')} at {new_time_str}. Please choose a different slot or adjust the faculty assignment."
#                         url = reverse('schedule_list')
#                         query_string = urlencode({'conflict': conflict, 'message': message, 'last_used_date': last_used_date_str})
#                         return redirect(f'{url}?{query_string}')
                        
#                 # Mark the current schedule as rescheduled
#                 schedule.has_been_rescheduled = True
#                 schedule.save()

#                 # Create the new schedule
#                 new_schedule = Schedule.objects.create(
#                     group=schedule.group,
#                     faculty1=schedule.faculty1,
#                     faculty2=schedule.faculty2,
#                     faculty3=schedule.faculty3,
#                     slot=new_time_str,
#                     date=new_date.strftime('%B %d, %Y'),
#                     day=f"Day {day_count}",  # Use calculated day count
#                     room=new_lab,  # Use the Room instance
#                     school_year=current_school_year
#                 )
#                 print("success")

#                 # Log the reassignment in the audit trail
#                 AuditTrail.objects.create(
#                     user=request.user,
#                     action=f"Reassigned Title Hearing Group: {schedule.group} to {new_date.strftime('%B %d, %Y')} at {new_time_str} in {new_lab.name}.",
#                     ip_address=request.META.get('REMOTE_ADDR')
#                 )

#                 messages.success(request, "Schedule reassigned successfully.")
#                 # Redirect to schedule_list with last_used_date included
#                 url = reverse('schedule_list')
#                 query_string = urlencode({'last_used_date': last_used_date_str})
#                 return redirect(f'{url}?{query_string}')

#             except Exception as e:
#                 messages.error(request, f'Error rescheduling: {e}')
#                 print(f"Error rescheduling: {e}")
#                 # Include last_used_date in error redirect
#                 url = reverse('schedule_list')
#                 query_string = urlencode({'last_used_date': last_used_date_str})
#                 return redirect(f'{url}?{query_string}')
#         else:
#             messages.error(request, 'Please provide a date, time, and room.')
#             # Include last_used_date in the redirect
#             url = reverse('schedule_list')
#             query_string = urlencode({'last_used_date': last_used_date_str})
#             return redirect(f'{url}?{query_string}')
#     else:
#         messages.error(request, 'Invalid request method.')
#         return redirect('schedule_list')

def faculty_tally_view(request):
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

    # Initialize a dictionary to hold faculty assignments
    faculty_tally = defaultdict(lambda: defaultdict(int))

    # Get all schedules
    schedules = Schedule.objects.filter(school_year=selected_school_year)

    # Count the number of groups each faculty is assigned as a panel member
    for schedule in schedules:
        # Extract the actual date from the string
        date_str = schedule.date  # Assuming date is in 'Month Day, Year' format
        date = datetime.strptime(date_str, '%B %d, %Y')  # Parse the date string
        weekday = date.strftime('%A')  # Get the day name, e.g., "Monday"

        # Count assignments for each faculty
        faculty_tally[schedule.faculty1.id][weekday] += 1
        faculty_tally[schedule.faculty2.id][weekday] += 1
        faculty_tally[schedule.faculty3.id][weekday] += 1

    # Prepare data for the template
    faculty_summary = []

    # To store the mapping of weekday to actual dates for this week
    week_dates = {}
    
    # Iterate through the schedules to create a mapping of weekday to actual dates
    for schedule in schedules:
        date_str = schedule.date
        date = datetime.strptime(date_str, '%B %d, %Y')
        weekday = date.strftime('%A')
        if weekday not in week_dates:
            week_dates[weekday] = date_str  # Store the first occurrence of the date for that weekday

    for faculty_id, days in faculty_tally.items():
        faculty = Faculty.objects.get(id=faculty_id)
        row = {
            'faculty_name': faculty.name,
            'monday_count': days.get('Monday', 0),
            'tuesday_count': days.get('Tuesday', 0),
            'wednesday_count': days.get('Wednesday', 0),
            'thursday_count': days.get('Thursday', 0),
            'friday_count': days.get('Friday', 0),
        }
        # Calculate total assignments
        total = sum(row[day] for day in ['monday_count', 'tuesday_count', 'wednesday_count', 'thursday_count', 'friday_count'])
        row['total'] = total
        
        # Add actual dates for each weekday
        row['monday_date'] = week_dates.get('Monday', '')
        row['tuesday_date'] = week_dates.get('Tuesday', '')
        row['wednesday_date'] = week_dates.get('Wednesday', '')
        row['thursday_date'] = week_dates.get('Thursday', '')
        row['friday_date'] = week_dates.get('Friday', '')

        faculty_summary.append(row)

    context = {
        'faculty_summary': faculty_summary,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
    }


    return render(request, 'admin/title_hearing/faculty_tally.html', context)


# the folllowing function are for generating schedule for title hearing together with uploading group info
def group_info_list(request):
    # Fetch and order the group info
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
    groups = GroupInfoTH.objects.filter(school_year=selected_school_year).order_by('section', 'subject_teacher')
     # Paginate the groups, showing 10 groups per page
    paginator = Paginator(groups, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)


    return render(request, 'admin/title_hearing/group_info_list.html', {'page_obj': page_obj})

def reset_schedule(request):
    # get the last added school year in the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # get the current active school year
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

    Schedule.objects.filter(school_year=selected_school_year).delete()
    # Log the action in AuditTrail
    AuditTrail.objects.create(
        user=request.user,
        action=f"Schedule for the titlle hearing has been reset to none",
        ip_address=request.META.get('REMOTE_ADDR')
    )

    # creating a notif
    Notif.objects.create(
        created_by=request.user,
        notif=f"Schedule for the titlle hearing has been reset to none"
    )
    return redirect('schedule_list')


@login_required
def update_group(request, id):
    group = get_object_or_404(GroupInfoTH, id=id)
    teachers = Faculty.objects.filter(is_active=True)

    if request.method == 'POST':
        # Update group with posted data
        group.section = request.POST['section']
        group.subject_teacher = get_object_or_404(Faculty, id=request.POST['subject_teacher'])
        group.member1 = request.POST['member1']
        group.member2 = request.POST.get('member2', '')  # Use get to allow empty strings
        group.member3 = request.POST.get('member3', '')
        group.save()
        
        # Log the action in AuditTrail
        AuditTrail.objects.create(
            user=request.user,
            action=f"Updated Group in Title Hearing Schedule: <br>{group.member1}<br>{group.member2}<br>{group.member3}",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return redirect('carousel_page')  # Redirect to group list after saving

    return render(request, 'admin/title_hearing/update_group.html', {
        'group': group,
        'teachers': teachers
    })


def delete_group(request, group_id):
    group = get_object_or_404(GroupInfoTH, id=group_id)
    
    # Log the action in AuditTrail before deleting the group
    full_name = request.user.get_full_name()
    if not full_name.strip():
        full_name = request.user.username
    AuditTrail.objects.create(
        user=request.user,
        action=f"""Deleted Group From Title Hearing Schedule:<br>
        Group {group.section} with members:<br>
              {group.member1}<br>
              {group.member2}<br>
              {group.member3}""",
        ip_address=request.META.get('REMOTE_ADDR')
    )
    group_name = f"{group.member1}<br>{group.member2}<br>{group.member3}"
    group_exists = Adviser.objects.filter(group_name=group_name).exists()
    if group_exists:
        Adviser.objects.filter(group_name=group_name).delete()
    group.delete()
    return redirect('carousel_page')







# the following function are for generating the pre oral scheddule together with uploading the group info of pre oral
# this check if there are already groups for the title hearing
def checker2(request):
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
    
    if not GroupInfoTH.objects.filter(school_year=selected_school_year).exists():
        print("no th group")
        messages.warning(request, 'No groups found. Please add groups first for title hearing to proceed with pre oral groups')
        empty = "True"
        message = "No groups found. Please add groups first for title hearing to proceed with pre oral groups"
        url = reverse('add_group')
        query_string = urlencode({'empty': empty, 'message': message})
        return redirect(f'{url}?{query_string}')
    else:
        print("no po group")
        if not GroupInfoPOD.objects.filter(school_year=selected_school_year).exists():
            messages.warning(request, 'No groups found. Please add groups first to generate schedule for pre oral defense.')
            empty = "True"
            message = "No groups found. Please add groups first to generate schedule for pre oral defense."
            url = reverse('add_groupPOD')
            query_string = urlencode({'empty': empty, 'message': message})
            return redirect(f'{url}?{query_string}')
        else:
            return redirect('schedule_listPOD')
 
def group_infoPOD(request):
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
    
    # Ensure there are school years available
    school_years = SchoolYear.objects.all().order_by('start_year')
    if school_years.count() == 0:
        SchoolYear.create_new_school_year()
        school_years = SchoolYear.objects.all().order_by('start_year')

    # Subquery to count graded groups for each GroupInfoPOD
    graded_groups = PreOral_Grade.objects.filter(project_title=OuterRef('title'), school_year=selected_school_year)
    graded_count = graded_groups.values('project_title').annotate(graded_count=Count('*')).values('graded_count')

    # Annotate each GroupInfoPOD with grading status
    groupsPOD = GroupInfoPOD.objects.filter(school_year=selected_school_year).annotate(
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

    # Paginate the groups, showing 10 groups per page
    paginator = Paginator(groupsPOD, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    advisers = Faculty.objects.all()

    return render(request, 'admin/pre_oral/group_infoPOD.html', {
        'page_obj': page_obj, 
        'advisers': advisers,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years
    })

@login_required
def add_groupPOD(request):
    # Check for the conflict query parameter
    empty_str = request.GET.get('empty')  # Should return True if 'conflict' param is 'True'
    message = request.GET.get('message')
    empty = empty_str.lower() == 'true' if empty_str else False #variable to hold a bolean value

    error_message = request.GET.get('error_message')
    print("error_message: ", error_message)
    
    # Get the last added school year in the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the current active school year
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

    # Check if the active school year is same as the last added school year
    if selected_school_year != last_school_year:
        return HttpResponse("Oops, you are no longer allowed to access this page.")

    if request.method == 'POST':
        if 'upload_file' in request.FILES:
            upload_file_form = UploadFileForm(request.POST, request.FILES)
            if upload_file_form.is_valid():
                file = request.FILES['upload_file']
                fs = FileSystemStorage()
                filename = fs.save(file.name, file)
                file_path = fs.path(filename)

                try:
                    process_excel_file_POD(file_path)
                    messages.success(request, 'File uploaded and processed successfully.')
                except Exception as e:
                    logger.error(f'Error processing file: {e}')
                    messages.error(request, f'Error processing file: {e}')

                AuditTrail.objects.create(
                    user=request.user,
                    action="Uploaded and processed file for group addition in Pre-Oral Defense",
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                return redirect(reverse('carousel_page') + '#preoral-details')
        else:
            form = GroupInfoPODForm(request.POST)
            mock_form = GroupInfoMDForm(request.POST)
            final_form = GroupInfoFDForm(request.POST)
            if form.is_valid():
                section = form.save(commit=False)
                section2 = mock_form.save(commit=False)
                section3 = final_form.save(commit=False)

                # Normalize names
                section.member1 = normalize_name_improvedPOD(section.member1) if section.member1 else section.member1
                section.member2 = normalize_name_improvedPOD(section.member2) if section.member2 else section.member2
                section.member3 = normalize_name_improvedPOD(section.member3) if section.member3 else section.member3


                # Get the selected capstone teacher from the form
                capstone_teacher = section.capstone_teacher
                print("capstone_teacher: ", capstone_teacher)
                
                # get the adviser from the form
                form_adviser = section.adviser
                print("form_adviser: ", form_adviser)

                if capstone_teacher == form_adviser:
                    error_message = "Cannot assign the same faculty as both subject teacher and adviser!"
                    base_url = reverse('add_groupPOD')
                    query_string = urlencode({'error_message': error_message})
                    url = f'{base_url}?{query_string}'
                    return redirect(url)
                else:
                    # Reset previous capstone teachers before setting the new one
                    # reset_previous_capstone_teachers()

                    # Set the `is_capstone_teacher` field to True for the selected faculty
                    if capstone_teacher:
                        capstone_teacher.is_capstone_teacher = True
                        capstone_teacher.save()

                    # Get the current active school year
                    active_school_year = SchoolYear.get_active_school_year()

                    # If no active school year exists, create a new one
                    if not active_school_year:
                        active_school_year = SchoolYear.create_new_school_year()

                    # Assign the active school year to both sections
                    section.school_year = active_school_year
                    section2.school_year = active_school_year
                    section3.school_year = active_school_year

                    # Save the GroupInfoPOD instance
                    section.save()

                    # Update the section value in GroupInfoMD
                    section_value_pod = section.section
                    if section_value_pod[-1].isalpha() and section_value_pod[:-1].isdigit():
                        # Extract year and increment it
                        year = int(section_value_pod[:-1])
                        letter = section_value_pod[-1]
                        updated_section_value = f"{year + 1}{letter}"
                    else:
                        # If the format is unexpected, you can handle it accordingly
                        updated_section_value = section_value_pod  # Fallback or custom logic

                    print('updated section: ', updated_section_value)
                    # Set the updated value to GroupInfoMD and GroupInfoFD instances
                    section2.section = updated_section_value
                    section3.section = updated_section_value

                    # Save the GroupInfoMD and GroupInfoFD instance
                    section2.save()
                    section3.save()

                    try:
                        # Try to find an existing Adviser record linked to the group
                        members = f"{section.member1}<br>{section.member2}<br>{section.member3}"
                        adviser_record = Adviser.objects.filter(group_name=members, school_year=selected_school_year)
                        print(members)

                        if adviser_record:
                            # If an existing adviser record is found, delete it
                            Adviser.objects.filter(group_name=members, school_year=selected_school_year).delete()
                            # Create a new Adviser record with the updated information
                            Adviser.objects.create(
                                faculty=section.adviser,
                                approved_title=section.title,
                                group_name=members,
                                school_year=selected_school_year,
                                accepted=True,
                                declined=False
                            )
                        else:
                            # If no adviser record exists for the current group adviser, create a new one
                            Adviser.objects.create(
                                faculty=section.adviser,
                                approved_title=section.title,
                                group_name=members,
                                school_year=selected_school_year,
                                accepted=True,
                                declined=False
                            )

                    except Exception as e:
                        logger.error(f"Error updating adviser record: {e}")

                    messages.success(request, 'Group added successfully.')
                    AuditTrail.objects.create(
                        user=request.user,
                        action=f"Added a New Group in Pre-Oral Defense",
                        ip_address=request.META.get('REMOTE_ADDR')
                    )
                    return redirect(reverse('carousel_page') + '#preoral-details')
    else:
        form = GroupInfoPODForm()
        upload_file_form = UploadFileForm()
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

    print("error_message: ", error_message)
    return render(request, 'admin/pre_oral/add_groupPOD.html', {
        'form': form, 
        'upload_file_form': upload_file_form,
        'school_years': school_years, 
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'empty': empty,
        'message': message,
        'error_message': error_message
    })

# # Helper function to normalize names (handles commas, extra spaces, and proper casing)
# def normalize_name_improvedPOD(name):
#     """
#     Normalize the name for better matching by:
#     - Removing extra spaces
#     - Handling both "Last, First" and "First Last" formats
#     - Converting to lowercase for case-insensitive comparison
#     - Removing special characters
#     """
#     # Remove leading and trailing whitespace
#     name = name.strip()
    
#     # Replace any sequences of whitespace with a single space
#     name = re.sub(r'\s+', ' ', name)
    
#     # Handle "Last, First" format
#     if ',' in name:
#         last, first = name.split(',', 1)
#         normalized_name = f"{first.strip()} {last.strip()}"
#     else:
#         # If it's already in "First Last" format, just use it
#         normalized_name = name

#     # Convert to lowercase for case-insensitive matching
#     # normalized_name = normalized_name.lower()
    
#     # Optionally, remove special characters (if needed)
#     normalized_name = re.sub(r'[^\w\s]', '', normalized_name)

#     return normalized_name

def normalize_name_improvedPOD(name):
    """
    Normalizes name to 'Lastname, Firstname, M.I.' format
    
    Handles various name formats more robustly:
    - Single names
    - First Last
    - First Middle Last
    - Last, First
    - Last, First Middle
    """
    # Convert to string and strip whitespace
    name = str(name).strip()
    
    # Replace multiple spaces with single space
    name = re.sub(r'\s+', ' ', name)
    
    # Handle "Last, First" format
    if ',' in name:
        last, first = name.split(',', 1)
        last = last.strip()
        first = first.strip()
    else:
        # Split name into parts
        parts = name.split()
        if len(parts) == 1:
            return parts[0]  # Single name
        
        # More robust last name extraction
        # Assume last name is the last part, but with some intelligence
        last = parts[-1]
        first_parts = parts[:-1]
        first = ' '.join(first_parts)
    
    # Extract middle initial (if exists)
    name_parts = first.split()
    mi = ''
    if len(name_parts) > 1:
        # Check the last part for potential middle initial
        potential_mi = name_parts[-1]
        # If it's a single letter or single letter followed by a period
        if len(potential_mi) == 1 or (len(potential_mi) == 2 and potential_mi[1] == '.'):
            mi = potential_mi if potential_mi.endswith('.') else potential_mi + '.'
            # Remove the middle initial from the first name
            first = ' '.join(name_parts[:-1])
    
    # Return normalized name 
    return f"{last}, {first} {mi}".rstrip(', ')


# Function to find matching faculty using normalized names and fuzzy logic
def find_matching_faculty(teacher_or_adviser_name):
    """
    Finds a matching faculty member in the database using fuzzy string matching.
    It compares the first and last names and returns the best match with a threshold.
    
    Can be used for Capstone Teacher or Adviser.
    """
    normalized_name = normalize_name_improvedPOD(teacher_or_adviser_name)
    potential_faculties = Faculty.objects.all()

    best_match = None
    best_score = 0

    for faculty in potential_faculties:
        faculty_normalized_name = normalize_name_improvedPOD(faculty.name)
        match_score = fuzz.ratio(normalized_name, faculty_normalized_name)

        if match_score > best_score:
            best_score = match_score
            best_match = faculty

    # Define a threshold for considering a match good enough
    if best_score >= 85:  # This threshold can be adjusted
        return best_match
    
    return None


# Helper function to reset current capstone teachers
def reset_previous_capstone_teachers():
    """
    Sets `is_capstone_teacher` to False for all Faculty members.
    This ensures that only one capstone teacher is active at a time.
    """
    Faculty.objects.filter(is_capstone_teacher=True).update(is_capstone_teacher=False)


# # Updated function to process the uploaded Excel file with row shuffling
# def process_excel_file_POD(file_path):
#     try:
#         # Read the Excel file
#         df = pd.read_excel(file_path)

#         # Validate the required columns
#         required_columns = ['Member 1', 'Member 2', 'Member 3', 'Approved Title', 'Capstone Teacher', 'Section', 'Adviser']
#         for col in required_columns:
#             if col not in df.columns:
#                 raise ValueError(f"Missing required column: {col}")

#         # Shuffle the rows in the DataFrame
#         df = df.sample(frac=1).reset_index(drop=True)

#         with transaction.atomic():  # Ensure atomic transaction
#             # Process each row
#             for _, row in df.iterrows():
#                 # Normalize and validate Capstone Teacher name
#                 capstone_teacher_name = row['Capstone Teacher']
#                 capstone_teacher = find_matching_faculty(capstone_teacher_name)
                
#                 if not capstone_teacher:
#                     logger.error(f"Capstone Teacher '{capstone_teacher_name}' not found or matched in the system.")
#                     continue

#                 # Reset previous capstone teachers
#                 reset_previous_capstone_teachers()

#                 # Set the current capstone teacher's field to True
#                 capstone_teacher.is_capstone_teacher = True
#                 capstone_teacher.save()

#                 # Normalize and validate Adviser name
#                 adviser_name = row['Adviser']
#                 adviser = find_matching_faculty(adviser_name)
#                 if not adviser:
#                     logger.error(f"Adviser '{adviser_name}' not found or matched in the system.")
#                     continue

#                 # Normalize member names
#                 member1 = normalize_name_improvedPOD(row['Member 1'])
#                 member2 = normalize_name_improvedPOD(row['Member 2'])
#                 member3 = normalize_name_improvedPOD(row['Member 3'])

#                 # Get the current active school year
#                 active_school_year = SchoolYear.get_active_school_year()

#                 # If no active school year exists, create a new one
#                 if not active_school_year:
#                     active_school_year = SchoolYear.create_new_school_year()

#                 # Create GroupInfoPOD record
#                 group = GroupInfoPOD.objects.create(
#                     member1=member1,
#                     member2=member2,
#                     member3=member3,
#                     title=row['Approved Title'],
#                     capstone_teacher=capstone_teacher,
#                     section=row['Section'],
#                     adviser=adviser,
#                     school_year=active_school_year
#                 )

#                 # Now create GroupInfoMD and GroupInfoFD with the updated section value
#                 section_value_pod = group.section
#                 if section_value_pod[-1].isalpha() and section_value_pod[:-1].isdigit():
#                     # Extract year and increment it
#                     year = int(section_value_pod[:-1])
#                     letter = section_value_pod[-1]
#                     updated_section_value = f"{year + 1}{letter}"
#                 else:
#                     updated_section_value = section_value_pod  # Fallback or custom logic

#                 # Create GroupInfoMD record
#                 group_md = GroupInfoMD.objects.create(
#                     member1=member1,
#                     member2=member2,
#                     member3=member3,
#                     title=group.title,
#                     capstone_teacher=capstone_teacher,
#                     section=updated_section_value,
#                     adviser=adviser,
#                     school_year=active_school_year
#                 )

#                 # Create GroupInfoFD record
#                 group_fd = GroupInfoFD.objects.create(
#                     member1=member1,
#                     member2=member2,
#                     member3=member3,
#                     title=group.title,
#                     capstone_teacher=capstone_teacher,
#                     section=updated_section_value,
#                     adviser=adviser,
#                     school_year=active_school_year
#                 )

#                 # Update Adviser records after group is added
#                 try:
#                     # Try to find an existing Adviser record linked to the group
#                     members = f"{member1}<br>{member2}<br>{member3}"
#                     adviser_record = Adviser.objects.filter(group_name=members, school_year=active_school_year)

#                     if adviser_record:
#                         # If an existing adviser record is found, delete it
#                         Adviser.objects.filter(group_name=members, school_year=active_school_year).delete()
#                         # Create a new Adviser record with the updated information
#                         Adviser.objects.create(
#                             faculty=group.adviser,
#                             approved_title=group.title,
#                             group_name=members,
#                             school_year=active_school_year
#                         )
#                     else:
#                         # If no adviser record exists for the current group adviser, create a new one
#                         Adviser.objects.create(
#                             faculty=group.adviser,
#                             approved_title=group.title,
#                             group_name=members,
#                             school_year=active_school_year
#                         )

#                 except Exception as e:
#                     logger.error(f"Error updating adviser record: {e}")

#     except Exception as e:
#         logger.error(f"Error processing file: {e}")
#         raise
def process_excel_file_POD(file_path):
    try:
        # Read the Excel file
        df = pd.read_excel(file_path)

        # Validate the required columns
        required_columns = ['Member 1', 'Member 2', 'Member 3', 'Approved Title', 'Capstone Teacher', 'Section', 'Adviser']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        # Shuffle the rows in the DataFrame
        df = df.sample(frac=1).reset_index(drop=True)

        # Track capstone teachers to set `is_capstone_teacher` for them all at once
        capstone_teachers_to_set = set()

        # Process each row in a transaction
        with transaction.atomic():
            for _, row in df.iterrows():
                # Normalize and validate Capstone Teacher name
                capstone_teacher_name = row['Capstone Teacher']
                capstone_teacher = find_matching_faculty(capstone_teacher_name)

                if not capstone_teacher:
                    logger.error(f"Capstone Teacher '{capstone_teacher_name}' not found or matched in the system.")
                    continue

                # Collect capstone teachers to set the flag later
                capstone_teachers_to_set.add(capstone_teacher)

                # Normalize and validate Adviser name
                adviser_name = row['Adviser']
                adviser = find_matching_faculty(adviser_name)
                if not adviser:
                    logger.error(f"Adviser '{adviser_name}' not found or matched in the system.")
                    continue

                # Normalize member names
                member1 = normalize_name_improvedPOD(row['Member 1'])
                member2 = normalize_name_improvedPOD(row['Member 2'])
                member3 = normalize_name_improvedPOD(row['Member 3'])

                # Get or create the current active school year
                active_school_year = SchoolYear.get_active_school_year() or SchoolYear.create_new_school_year()

                # Create GroupInfoPOD record
                group = GroupInfoPOD.objects.create(
                    member1=member1,
                    member2=member2,
                    member3=member3,
                    title=row['Approved Title'],
                    capstone_teacher=capstone_teacher,
                    section=row['Section'],
                    adviser=adviser,
                    school_year=active_school_year
                )

                # Derive the updated section value for MD and FD groups
                section_value_pod = group.section
                if section_value_pod[-1].isalpha() and section_value_pod[:-1].isdigit():
                    year = int(section_value_pod[:-1])
                    letter = section_value_pod[-1]
                    updated_section_value = f"{year + 1}{letter}"
                else:
                    updated_section_value = section_value_pod  # Fallback or custom logic

                # Create GroupInfoMD and GroupInfoFD records
                GroupInfoMD.objects.create(
                    member1=member1,
                    member2=member2,
                    member3=member3,
                    title=group.title,
                    capstone_teacher=capstone_teacher,
                    section=updated_section_value,
                    adviser=adviser,
                    school_year=active_school_year
                )

                GroupInfoFD.objects.create(
                    member1=member1,
                    member2=member2,
                    member3=member3,
                    title=group.title,
                    capstone_teacher=capstone_teacher,
                    section=updated_section_value,
                    adviser=adviser,
                    school_year=active_school_year
                )

                # Update Adviser records after group is added
                members = f"{member1}<br>{member2}<br>{member3}"
                Adviser.objects.filter(group_name=members, school_year=active_school_year).delete()
                Adviser.objects.create(
                    faculty=group.adviser,
                    approved_title=group.title,
                    group_name=members,
                    school_year=active_school_year,
                    accepted=True,
                    declined=False
                )

        # Reset previous capstone teachers and set all required ones to True
        reset_previous_capstone_teachers()
        for teacher in capstone_teachers_to_set:
            teacher.is_capstone_teacher = True
            teacher.save()

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise


# Schedule list for the pre-oral schedule
def schedule_listPOD(request):
    # get the last added school year in the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # get the current active school year
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

    last_used_date_str = request.GET.get('last_used_date')
    print("last_used_date_str: ", last_used_date_str)

    last_used_date = None
    if last_used_date_str:
        last_used_date = last_used_date_str
    else:
        # Fetch the latest schedule date
        last_schedule = SchedulePOD.objects.filter(school_year=selected_school_year).order_by('-date').first()
        last_used_date = last_schedule.date if last_schedule else None
    print("last_used_date: ", last_used_date)

    # Fetch the latest schedule date
    last_schedule_th = Schedule.objects.filter(school_year=selected_school_year).order_by('-day').first()
    last_used_date_th = last_schedule_th.date if last_schedule_th else None
    print("last_used_date_th: ", last_used_date_th)

    # Check for the conflict query parameter
    conflict_str = request.GET.get('conflict')  # Should return True if 'conflict' param is 'True'
    message = request.GET.get('message')
    conflict = conflict_str.lower() == 'true' if conflict_str else False #variable to hold a bolean value

    if request.method == 'POST':
        start_date_str = request.POST.get('start_date')
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                generate_schedulePOD(request, start_date=start_date)
                messages.success(request, 'Schedule generated successfully.')
                # Record the recommendation event in the audit trail
                AuditTrail.objects.create(
                    user=request.user,
                    action=f"Generate Schedule for Pre-Oral Defense starting date is {start_date.strftime('%B %d, %Y')}",
                    ip_address=request.META.get('REMOTE_ADDR')
                )

                # creating a notif
                Notif.objects.create(
                    created_by=request.user,
                    notif=f"Generate New Schedule for Pre-Oral Defense starting date is {start_date.strftime('%B %d, %Y')}",
                )
            except Exception as e:
                messages.error(request, f'Error generating schedule: {e}')
            
            return redirect('schedule_listPOD')

    schedulesPOD = SchedulePOD.objects.filter(school_year=selected_school_year).order_by('date')
    grouped_schedulesPOD = {}

    def convert_slot_to_sortablePOD(slot):
        if isinstance(slot, list):
            logger.error(f"Expected string for slot, got list: {slot}")
            raise TypeError(f"Expected string for slot, got list: {slot}")

        start_time = slot.split('-')[0].strip()
        period = start_time[-2:]  # AM or PM
        time_parts = start_time[:-2].strip().split(':')

        if len(time_parts) == 1:
            hour = int(time_parts[0])
            minute = 0
        else:
            hour, minute = map(int, time_parts)

        if period == 'PM' and hour != 12:
            hour += 12
        if period == 'AM' and hour == 12:
            hour = 0

        return hour * 60 + minute

    for schedule in schedulesPOD:
        day_room = (schedule.day, schedule.date, schedule.room)
        if day_room not in grouped_schedulesPOD:
            grouped_schedulesPOD[day_room] = []
        grouped_schedulesPOD[day_room].append(schedule)

    for day_room in grouped_schedulesPOD:
        try:
            # Check if all slots are strings before sorting
            for schedule in grouped_schedulesPOD[day_room]:
                if not isinstance(schedule.slot, str):
                    logger.error(f"Invalid slot type for schedule ID {schedule.id}: {schedule.slot}")
                    raise TypeError(f"Invalid slot type for schedule ID {schedule.id}: {schedule.slot}")

            grouped_schedulesPOD[day_room].sort(key=lambda x: convert_slot_to_sortablePOD(x.slot))
        except Exception as e:
            logger.error(f"Error sorting schedule for {day_room}: {e}")
            messages.error(request, f"Error sorting schedule for {day_room}: {e}")
    
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

    rooms = Room.objects.all().order_by("status")

    new_group = request.GET.get('new_group')
    print('new_group: ', new_group)

    new_schedule = SchedulePOD.objects.order_by('-created_at').first()

    return render(request, 'admin/pre_oral/schedule_listPOD.html', {
        'grouped_schedulesPOD': grouped_schedulesPOD,
        'school_years': school_years, 
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'conflict': conflict,
        'message': message,
        'last_used_date': last_used_date,
        'last_used_date_th': last_used_date_th,
        'rooms': rooms,
        'new_group': new_group,
        'new_schedule': new_schedule

        })


def reschedulePOD(request, schedulePOD_id):
    # Get the last added school year in the database
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the current active school year
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

    # Check if the active school year is the same as the last added school year
    if selected_school_year != last_school_year:
        return HttpResponse("Oops, you are no longer allowed to access this page.") 

    # Get the schedule object by ID
    schedule = get_object_or_404(SchedulePOD, id=schedulePOD_id)
    base_time_slots = ['8AM-9:30AM', '9:30AM-11AM', '12PM-01:30PM', '1:30PM-3PM', '3PM-4:30PM', '4:30PM-5PM', '5PM-6:30PM']
    rooms = Room.objects.all().order_by("status")

    # Adjust time slots based on whether the day is Monday or a weekend
    def get_valid_time_slots(current_date):
        weekday = current_date.weekday()
        if weekday == 0:  # Monday, skip first slot
            return base_time_slots[1:]
        elif weekday >= 5:  # Saturday or Sunday
            return []  # No scheduling on weekends
        return base_time_slots

    # Check if a faculty is already booked for the slot on the same day
    def is_faculty_available(faculty_list, date, slot):
        for faculty in faculty_list:
            if SchedulePOD.objects.filter(
                (Q(faculty1=faculty) | Q(faculty2=faculty) | Q(faculty3=faculty) | Q(adviser=faculty)),
                date=date.strftime('%B %d, %Y'),
                slot=slot,
                school_year=selected_school_year
            ).exists():
                return False  # Faculty is booked for that slot
        return True

    # Get the last schedule to ensure we reschedule after the last slot
    last_schedule = SchedulePOD.objects.filter(school_year=selected_school_year).order_by('-date').first()
    if not last_schedule:
        return JsonResponse({'success': False, 'message': 'No existing schedules found.'})

    last_date_str = last_schedule.date
    last_date = datetime.strptime(last_date_str, '%B %d, %Y')
    last_slot = last_schedule.slot
    last_day_str = last_schedule.day
    last_day_number = int(last_day_str.split()[1])

    next_date = datetime.strptime(schedule.date, '%B %d, %Y')
    next_day_number = int(schedule.day.split()[1])

    # Step 1: Find any available vacant slots that have no records and don't cause a conflict
    while next_date <= last_date:
        valid_time_slots = get_valid_time_slots(next_date)
        if not valid_time_slots:  # Skip weekends or invalid days
            next_date += timedelta(days=1)
            # next_day_number += 1
            continue

        # Try each time slot for each room in alternating order
        for slot in valid_time_slots:
            for room in rooms:
                faculties = [schedule.faculty1, schedule.faculty2, schedule.faculty3, schedule.adviser]
                if is_faculty_available(faculties, next_date, slot):
                    if not SchedulePOD.objects.filter(
                        date=next_date.strftime('%B %d, %Y'),
                        room=room,
                        slot=slot,
                        school_year=selected_school_year
                    ).exists():

                        # Query to check if there is a SchedulePOD with the given criteria
                        schedule_day = SchedulePOD.objects.filter(
                            date=next_date.strftime('%B %d, %Y'),
                            room=room,
                            school_year=selected_school_year
                        ).first() 

                        # Found a vacant slot
                        next_slot = slot
                        next_room = room

                        # Mark the existing schedule as rescheduled
                        schedule.has_been_rescheduled = True
                        schedule.save()
                        
                        print("next_day_number: ", next_day_number)
                        print("date: ", next_date.strftime('%B %d, %Y'))
                        print("slot: ", next_slot)

                        if schedule_day:
                            # Create the new schedule entry
                            new_schedule = SchedulePOD.objects.create(
                                group=schedule.group,
                                faculty1=schedule.faculty1,
                                faculty2=schedule.faculty2,
                                faculty3=schedule.faculty3,
                                title=schedule.title,
                                slot=next_slot,
                                date=next_date.strftime('%B %d, %Y'),
                                day=schedule_day.day,
                                room=next_room,
                                adviser=schedule.adviser,
                                capstone_teacher=schedule.capstone_teacher,
                                school_year=selected_school_year,
                                new_sched = True
                            )
                        else:
                            # Create the new schedule entry
                            new_schedule = SchedulePOD.objects.create(
                                group=schedule.group,
                                faculty1=schedule.faculty1,
                                faculty2=schedule.faculty2,
                                faculty3=schedule.faculty3,
                                title=schedule.title,
                                slot=next_slot,
                                date=next_date.strftime('%B %d, %Y'),
                                day=f"Day {next_day_number}",
                                room=next_room,
                                adviser=schedule.adviser,
                                capstone_teacher=schedule.capstone_teacher,
                                school_year=selected_school_year,
                                new_sched = True
                            )

                        # Log the action in AuditTrail
                        AuditTrail.objects.create(
                            user=request.user,
                            action=f"""Rescheduled Pre-Oral Defense Group
                            Group {schedule.group.section} with members:<br>
                            {schedule.group.member1}<br>
                            {schedule.group.member2}<br>
                            {schedule.group.member3}<br>
                            from {schedule.slot} on {schedule.date} ({schedule.day}) to {next_slot} on {next_date.strftime('%B %d, %Y')} (Day {next_day_number})""",
                            ip_address=request.META.get('REMOTE_ADDR')
                        )

                        # creating a notif
                        Notif.objects.create(
                            created_by=request.user,
                            notif=f"This Pre Oral Group: {schedule.group} has been rescheduled from {schedule.slot} on {schedule.date} ({schedule.day}) to {next_slot} on {next_date.strftime('%B %d, %Y')} (Day {next_day_number})"
                        )


                        url = reverse('schedule_listPOD')
                        new_slot=next_slot,
                        new_date=next_date.strftime('%B %d, %Y'),
                        new_day=f"Day {next_day_number}",
                        new_room=next_room,
                        new_group=schedule.group
                        print("new_groupr: ", new_group)
                        query_string = urlencode({'new_slot': new_slot, 'new_date': new_date, 'new_day': new_day, 'new_room': new_room, 'new_group': new_group})
                        return redirect(f'{url}?{query_string}')

        # Move to the next day if no available slot was found on the current date
        next_date += timedelta(days=1)
        next_day_number += 1

    # Step 2: Find slots after the last scheduled date, similar logic
    max_reschedule_date = last_date + timedelta(weeks=3)
    next_date = last_date
    next_day_number = last_day_number
    next_slot_index = (base_time_slots.index(last_slot) + 1) % len(base_time_slots)

    while next_date <= max_reschedule_date:
        valid_time_slots = get_valid_time_slots(next_date)  # Dynamic slot selection
        if not valid_time_slots:  # Skip weekends or days with no slots
            next_date += timedelta(days=1)
            # next_day_number += 1
            continue

        # Iterate over slots starting from next_slot_index
        for slot_index in range(next_slot_index, len(valid_time_slots)):
            next_slot = valid_time_slots[slot_index]  # Select slot

            for room in rooms:
                faculties = [schedule.faculty1, schedule.faculty2, schedule.faculty3, schedule.adviser]
                if is_faculty_available(faculties, next_date, next_slot):  # Faculty check
                    if not SchedulePOD.objects.filter(
                        date=next_date.strftime('%B %d, %Y'),
                        room=room,
                        slot=next_slot,
                        school_year=selected_school_year
                    ).exists():  # Check room availability

                        # Check for existing day label or assign new one
                        schedule_day = SchedulePOD.objects.filter(
                            date=next_date.strftime('%B %d, %Y'),
                            room=room,
                            school_year=selected_school_year
                        ).first() 

                        # Found a vacant slot
                        next_room = room

                        # Mark the existing schedule as rescheduled
                        schedule.has_been_rescheduled = True
                        schedule.save()

                        # Logging for debugging
                        print("next_day_number2:", next_day_number)
                        print("date2:", next_date.strftime('%B %d, %Y'))
                        print("slot:", next_slot)

                        if schedule_day:
                            # Create the new schedule entry
                            new_schedule = SchedulePOD.objects.create(
                                group=schedule.group,
                                faculty1=schedule.faculty1,
                                faculty2=schedule.faculty2,
                                faculty3=schedule.faculty3,
                                title=schedule.title,
                                slot=next_slot,
                                date=next_date.strftime('%B %d, %Y'),
                                day=schedule_day.day,
                                room=next_room,
                                adviser=schedule.adviser,
                                capstone_teacher=schedule.capstone_teacher,
                                school_year=selected_school_year,
                                new_sched = True
                            )
                        else:
                            # Create the new schedule entry
                            new_schedule = SchedulePOD.objects.create(
                                group=schedule.group,
                                faculty1=schedule.faculty1,
                                faculty2=schedule.faculty2,
                                faculty3=schedule.faculty3,
                                title=schedule.title,
                                slot=next_slot,
                                date=next_date.strftime('%B %d, %Y'),
                                day=f"Day {next_day_number}",
                                room=next_room,
                                adviser=schedule.adviser,
                                capstone_teacher=schedule.capstone_teacher,
                                school_year=selected_school_year,
                                new_sched = True
                            )

                        # Log the action in AuditTrail
                        AuditTrail.objects.create(
                            user=request.user,
                            action=f"""Rescheduled Pre-Oral Defense Group
                            Group {schedule.group.section} with members:<br>
                            {schedule.group.member1}<br>
                            {schedule.group.member2}<br>
                            {schedule.group.member3}<br>
                            from {schedule.slot} on {schedule.date} ({schedule.day}) to {next_slot} on {next_date.strftime('%B %d, %Y')} (Day {next_day_number})""",
                            ip_address=request.META.get('REMOTE_ADDR')
                        )

                        # creating a notif
                        Notif.objects.create(
                            created_by=request.user,
                            notif=f"This Pre Oral Group: {schedule.group} has been rescheduled from {schedule.slot} on {schedule.date} ({schedule.day}) to {next_slot} on {next_date.strftime('%B %d, %Y')} (Day {next_day_number})"
                        )

                        # return redirect('schedule_listPOD')
                        url = reverse('schedule_listPOD')
                        new_slot=next_slot,
                        new_date=next_date.strftime('%B %d, %Y'),
                        new_day=f"Day {next_day_number}",
                        new_room=next_room,
                        new_group=schedule.group
                        print("new_groupr: ", new_group)
                        query_string = urlencode({'new_slot': new_slot, 'new_date': new_date, 'new_day': new_day, 'new_room': new_room, 'new_group': new_group})
                        return redirect(f'{url}?{query_string}')

        # Move to the next day if no available slot was found on the current date
        next_date += timedelta(days=1)
        next_day_number += 1
        next_slot_index = 0  # Reset index for each new day


    return JsonResponse({'success': False, 'message': 'No available slots to reschedule within the 3-week limit.'})

def reassignPOD(request, schedule_id):
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
        new_date_str = request.POST.get('new_date')
        new_time_str = request.POST.get('new_time')
        new_lab_id = request.POST.get('new_lab')  # Fetch the room ID
        last_used_date_str = request.POST.get('last_used_date')  # Fetch the last used date

        if new_date_str and new_time_str and new_lab_id:
            try:
                new_date = datetime.strptime(new_date_str, '%Y-%m-%d')
                print("new_date: ", new_date)

                # Fetch the Room instance using the new_lab_id
                new_lab = get_object_or_404(Room, id=new_lab_id)

                # Get the earliest schedule date (the start date)
                earliest_schedule = SchedulePOD.objects.filter(school_year=selected_school_year).order_by('date').first()
                if not earliest_schedule:
                    messages.error(request, 'No schedules found for the current school year.')
                    return redirect('schedule_listPOD')

                earliest_date = datetime.strptime(earliest_schedule.date, '%B %d, %Y')
                print("earliest_date: ", earliest_date)

                # Ensure new date is not earlier than the earliest schedule
                if new_date < earliest_date:
                    conflict = "True"
                    message = "Cannot reschedule to a date earlier than the original schedule."
                    url = reverse('schedule_listPOD')
                    query_string = urlencode({'conflict': conflict, 'message': message, 'last_used_date': last_used_date_str})
                    return redirect(f'{url}?{query_string}')

                # Check if the new date is within one to two weeks from the earliest schedule date
                if not (earliest_date <= new_date <= earliest_date + timedelta(weeks=3)):
                    conflict = "True"
                    message = "Rescheduling is only allowed within one to two weeks from the original schedule."
                    url = reverse('schedule_listPOD')
                    query_string = urlencode({'conflict': conflict, 'message': message, 'last_used_date': last_used_date_str})
                    return redirect(f'{url}?{query_string}')

                # Check if the new schedule already exists
                if SchedulePOD.objects.filter(date=new_date.strftime('%B %d, %Y'), slot=new_time_str, room=new_lab, school_year=selected_school_year).exists():
                    conflict = "True"
                    message = "Schedule already exists for the selected date, time, and room. Please choose a different slot."
                    url = reverse('schedule_listPOD')
                    query_string = urlencode({'conflict': conflict, 'message': message, 'last_used_date': last_used_date_str})
                    return redirect(f'{url}?{query_string}')

                schedule = get_object_or_404(SchedulePOD, id=schedule_id)
                faculties = [schedule.faculty1, schedule.faculty2, schedule.faculty3]

                # Check if any faculty is double-booked for the new date and time
                for faculty in faculties:
                    if SchedulePOD.objects.filter(
                        date=new_date.strftime('%B %d, %Y'),
                        slot=new_time_str,
                        school_year=selected_school_year
                    ).filter(
                        (Q(faculty1=faculty) | Q(faculty2=faculty) | Q(faculty3=faculty))
                    ).exists():
                        conflict = "True"
                        message = f"Faculty {faculty.name} already has a schedule on {new_date.strftime('%B %d, %Y')} at {new_time_str}. Please choose a different slot or adjust the faculty assignment."
                        url = reverse('schedule_listPOD')
                        query_string = urlencode({'conflict': conflict, 'message': message, 'last_used_date': last_used_date_str})
                        return redirect(f'{url}?{query_string}')

                # Calculate day_count excluding weekends
                current_date = earliest_date
                day_count = 0
                while current_date <= new_date:
                    if current_date.weekday() < 5:  # Only count weekdays (Mon-Fri)
                        day_count += 1
                    current_date += timedelta(days=1)
                
                print("day count (excluding weekends): ", day_count)

                # Mark the existing schedule as rescheduled
                schedule.has_been_rescheduled = True
                schedule.save()

                # Create the new schedule entry with the updated information
                new_schedule = SchedulePOD.objects.create(
                    group=schedule.group,
                    faculty1=schedule.faculty1,
                    faculty2=schedule.faculty2,
                    faculty3=schedule.faculty3,
                    title=schedule.title,
                    slot=new_time_str,
                    date=new_date.strftime('%B %d, %Y'),
                    day=f"Day {day_count}",  # Use the calculated day count
                    room=new_lab,
                    adviser=schedule.adviser,
                    capstone_teacher=schedule.capstone_teacher,
                    school_year=selected_school_year,
                    new_sched = True
                )

                # Log the action in AuditTrail
                AuditTrail.objects.create(
                    user=request.user,
                    action=f"Rescheduled Pre-Oral Defense Group: {schedule.group} from {schedule.slot} on {schedule.date} ({schedule.day}) to {new_time_str} on {new_date.strftime('%B %d, %Y')} (Day {day_count})",
                    ip_address=request.META.get('REMOTE_ADDR')
                )

                # creating a notif
                Notif.objects.create(
                    created_by=request.user,
                    notif=f"This Pre Oral Group: {schedule.group} has been rescheduled from {schedule.slot} on {schedule.date} ({schedule.day}) to {new_time_str} on {new_date.strftime('%B %d, %Y')} (Day {day_count})"
                )


                messages.success(request, 'Schedule rescheduled successfully.')
                # Redirect to schedule_listPOD with last_used_date included
                url = reverse('schedule_listPOD')
                new_group=schedule.group
                query_string = urlencode({'last_used_date': last_used_date_str, 'new_group': new_group})
                return redirect(f'{url}?{query_string}')

            except Exception as e:
                messages.error(request, f'Error during rescheduling: {e}')
                # Include last_used_date in error redirect
                url = reverse('schedule_listPOD')
                query_string = urlencode({'last_used_date': last_used_date_str})
                return redirect(f'{url}?{query_string}')
        else:
            messages.error(request, 'Please provide a date, time, and room.')
            # Include last_used_date in the redirect
            url = reverse('schedule_listPOD')
            query_string = urlencode({'last_used_date': last_used_date_str})
            return redirect(f'{url}?{query_string}')
    else:
        messages.error(request, 'Invalid request method.')
        return redirect('schedule_listPOD')


# def faculty_tally_viewPOD(request):
#     school_years = SchoolYear.objects.all().order_by('start_year')
#     # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
#     # current_school_year = SchoolYear.get_active_school_year()
#     selected_school_year_id = request.session.get('selected_school_year_id')
#     # get the last school year added to the db
#     last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

#     # Get the selected school year from session or fallback to the active school year
#     selected_school_year = ''
#     if not selected_school_year_id:
#         selected_school_year = last_school_year
#         request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
#     else:
#         # Retrieve the selected school year based on the session
#         selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

#     # Initialize a dictionary to hold faculty assignments
#     faculty_tally = defaultdict(lambda: defaultdict(int))

#     # Get all schedules
#     schedules = SchedulePOD.objects.all()

#     # Count the number of groups each faculty is assigned as a panel member
#     for schedule in schedules:
#         # Extract the actual date from the string
#         date_str = schedule.date  # Assuming date is in 'Month Day, Year' format
#         date = datetime.strptime(date_str, '%B %d, %Y')  # Parse the date string
#         weekday = date.strftime('%A')  # Get the day name, e.g., "Monday"

#         # Count assignments for each faculty
#         faculty_tally[schedule.faculty1.id][weekday] += 1
#         faculty_tally[schedule.faculty2.id][weekday] += 1
#         faculty_tally[schedule.faculty3.id][weekday] += 1

#     # Prepare data for the template
#     faculty_summary = []
    
#     # To store the mapping of weekday to actual dates for this week
#     week_dates = {}
    
#     # Iterate through the schedules to create a mapping of weekday to actual dates
#     for schedule in schedules:
#         date_str = schedule.date
#         date = datetime.strptime(date_str, '%B %d, %Y')
#         weekday = date.strftime('%A')
#         if weekday not in week_dates:
#             week_dates[weekday] = date_str  # Store the first occurrence of the date for that weekday

#     # Get all active faculty members and store them in a list for sorting later
#     faculties = list(Faculty.objects.filter(is_active=True))

#     for faculty in faculties:
#         days = faculty_tally[faculty.id]
#         adviser_count = Adviser.objects.filter(faculty=faculty).count()  # Get the adviser count

#         row = {
#             'faculty_name': faculty.name,
#             'adviser_count': adviser_count,
#             'monday_count': days.get('Monday', 0),
#             'tuesday_count': days.get('Tuesday', 0),
#             'wednesday_count': days.get('Wednesday', 0),
#             'thursday_count': days.get('Thursday', 0),
#             'friday_count': days.get('Friday', 0),
#         }

#         # Calculate total assignments including adviser count
#         total = sum(row[day] for day in ['monday_count', 'tuesday_count', 'wednesday_count', 'thursday_count', 'friday_count']) #+ adviser_count
#         row['total'] = total
        
#         # Add actual dates for each weekday
#         row['monday_date'] = week_dates.get('Monday', '')
#         row['tuesday_date'] = week_dates.get('Tuesday', '')
#         row['wednesday_date'] = week_dates.get('Wednesday', '')
#         row['thursday_date'] = week_dates.get('Thursday', '')
#         row['friday_date'] = week_dates.get('Friday', '')

#         faculty_summary.append(row)

#     # Sort the faculty summary based on years of teaching and degree criteria
#     faculty_summary.sort(key=lambda x: (
#         not next((f for f in faculties if f.name == x['faculty_name']), None).has_master_degree,  # Ensure those with a master's degree come first
#         -next((f for f in faculties if f.name == x['faculty_name']), None).years_of_teaching,     # Sort by years of teaching in descending order
#         next((f for f in faculties if f.name == x['faculty_name']), None).highest_degree         # Sort by highest degree in ascending order (if needed)
#     ))

#     context = {
#         'faculty_summary': faculty_summary,
#         # 'current_school_year': current_school_year,
#         'selected_school_year': selected_school_year,
#         'last_school_year': last_school_year,
#         'school_years': school_years,
#     }

#     return render(request, 'admin/pre_oral/faculty_tally.html', context)

def faculty_tally_viewPOD(request):
    school_years = SchoolYear.objects.all().order_by('start_year')
    selected_school_year_id = request.session.get('selected_school_year_id')
    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the selected school year from session or fallback to the last school year
    selected_school_year = ''
    if not selected_school_year_id:
        selected_school_year = last_school_year
        request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    else:
        selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    # Initialize a dictionary to hold faculty assignments
    faculty_tally = defaultdict(lambda: defaultdict(int))
    capstone_teacher_count = defaultdict(int)

    # Get all schedules
    schedules = SchedulePOD.objects.all()

    # Count the number of groups each faculty is assigned as a panel member
    for schedule in schedules:
        # Extract the actual date from the string
        date_str = schedule.date  # Assuming date is in 'Month Day, Year' format
        date = datetime.strptime(date_str, '%B %d, %Y')  # Parse the date string
        weekday = date.strftime('%A')  # Get the day name, e.g., "Monday"

        # Count assignments for each faculty
        faculty_tally[schedule.faculty1.id][weekday] += 1
        faculty_tally[schedule.faculty2.id][weekday] += 1
        faculty_tally[schedule.faculty3.id][weekday] += 1

        # Count capstone teacher assignments
        capstone_teacher_count[schedule.capstone_teacher.id] += 1

    # Prepare data for the template
    faculty_summary = []
    week_dates = {}

    # Create a mapping of weekday to actual dates
    for schedule in schedules:
        date_str = schedule.date
        date = datetime.strptime(date_str, '%B %d, %Y')
        weekday = date.strftime('%A')
        if weekday not in week_dates:
            week_dates[weekday] = date_str  # Store the first occurrence of the date for that weekday

    # Get all active faculty members
    faculties = list(Faculty.objects.filter(is_active=True))

    for faculty in faculties:
        days = faculty_tally[faculty.id]
        adviser_count = Adviser.objects.filter(faculty=faculty, school_year=selected_school_year).count()  # Get the adviser count
        capstone_count = capstone_teacher_count[faculty.id]  # Get the capstone teacher count

        row = {
            'faculty_name': faculty.name,
            'adviser_count': adviser_count,
            'capstone_teacher_count': capstone_count,
            'monday_count': days.get('Monday', 0),
            'tuesday_count': days.get('Tuesday', 0),
            'wednesday_count': days.get('Wednesday', 0),
            'thursday_count': days.get('Thursday', 0),
            'friday_count': days.get('Friday', 0),
        }

        # Calculate total assignments including adviser and capstone teacher counts
        total = sum(row[day] for day in ['monday_count', 'tuesday_count', 'wednesday_count', 'thursday_count', 'friday_count']) #+ adviser_count + capstone_count
        row['total'] = total
        
        # Add actual dates for each weekday
        row['monday_date'] = week_dates.get('Monday', '')
        row['tuesday_date'] = week_dates.get('Tuesday', '')
        row['wednesday_date'] = week_dates.get('Wednesday', '')
        row['thursday_date'] = week_dates.get('Thursday', '')
        row['friday_date'] = week_dates.get('Friday', '')

        faculty_summary.append(row)

    # Sort the faculty summary based on years of teaching and degree criteria
    faculty_summary.sort(key=lambda x: (
        not next((f for f in faculties if f.name == x['faculty_name']), None).has_master_degree,  # Ensure those with a master's degree come first
        -next((f for f in faculties if f.name == x['faculty_name']), None).years_of_teaching,     # Sort by years of teaching in descending order
        next((f for f in faculties if f.name == x['faculty_name']), None).highest_degree         # Sort by highest degree in ascending order (if needed)
    ))

    context = {
        'faculty_summary': faculty_summary,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
    }

    return render(request, 'admin/pre_oral/faculty_tally.html', context)

def reset_schedulePOD(request):
    # get the last added school year in the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # get the current active school year
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

    SchedulePOD.objects.filter(school_year=selected_school_year).delete()
    # Log the action in AuditTrail
    AuditTrail.objects.create(
        user=request.user,
        action=f"Schedule for the Pre Oral Defense has been reset to none",
        ip_address=request.META.get('REMOTE_ADDR')
    )

    # creating a notif
    Notif.objects.create(
        created_by=request.user,
        notif=f"Schedule for the Pre Oral Defense has been reset to none"
    )
    return redirect('schedule_listPOD')


# function to view the preoral grade  of a specific group in the admin side
@login_required
def grade_view(request, title_id):
    # Fetch the CustomUser object associated with the logged-in user
    user_profile = get_object_or_404(CustomUser, id=request.user.id)

    # If the user is a superuser, use the user profile as the faculty member
    if request.user.is_superuser:
        faculty_member = user_profile  # Use user_profile if superuser
    else:
        # If not a superuser, fetch the Faculty object associated with the CustomUser
        faculty_member = get_object_or_404(Faculty, custom_user=user_profile)
    print("faculty_member: ", faculty_member)

    # Get all available school years
    school_years = SchoolYear.objects.all().order_by('start_year')
    if school_years.count() == 0:
        SchoolYear.create_new_school_year()
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
    
    temp = get_object_or_404(GroupInfoPOD, id=title_id)
    title = temp.title
    adviser = get_object_or_404(Adviser, approved_title=title)
    print("Adviser: ", adviser.faculty)
    adviser_id = adviser.approved_title
     
    groups = GroupInfoPOD.objects.filter(title=title, school_year=selected_school_year)
    
    adviser_id2=adviser.id
    print('adviser_id2', adviser_id2)
    verdicts = Verdict.objects.filter(school_year=selected_school_year).order_by('-percentage')
    print(verdicts)
    title = adviser.approved_title
    preoral_grade_record = PreOral_Grade.objects.filter(project_title=title, school_year=selected_school_year)
    recos = PreOral_Recos.objects.filter(project_title=title, school_year=selected_school_year)
    all_checkboxes = Checkbox.objects.filter(school_year=selected_school_year)
    for reco in recos:
        reco.recommendation = escape(reco.recommendation)

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
                reco.delete()
            else:
                reco.recommendation = recommendation
                # Save the recommendation record (updated)
                print("empyt also")
                reco.save()
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
        
        
        
        print(f"Redirecting with adviser_id: {adviser_id}")  # Debugging line
        return redirect('adviser_record_detail', adviser_id=adviser_id)
    
    # Fetch grades with the same title
    grades = PreOral_Grade.objects.filter(project_title=title, school_year=selected_school_year)
    groups = GroupInfoPOD.objects.filter(title=title, school_year=selected_school_year)
    criteria_list = PreOral_EvaluationSection.objects.filter(school_year=selected_school_year).annotate(total_criteria_percentage=Sum('criteria__percentage'))
    criteria_percentage = PreOral_Criteria.objects.filter(school_year=selected_school_year)
    total_points = sum(criteria.percentage for criteria in criteria_percentage)
    adviser_records = ''
    if not request.user.is_superuser:
        adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)
    
    if not grades.exists():
        member1 = groups.first().member1 if groups.exists() else None
        member2 = groups.first().member2 if groups.exists() else None
        member3 = groups.first().member3 if groups.exists() else None
        return render(request, 'faculty/pre_oral_grade/adviser_record_detailPOD.html', {
            'error': 'No records found for this title.',
            'title': title, 
            'member1': member1, 
            'member2': member2, 
            'member3': member3,
            'adviser': adviser,
            'recos': recos,
            'faculty_member': faculty_member,
            # 'current_school_year': current_school_year,
            'selected_school_year': selected_school_year,
            'last_school_year': last_school_year,
            'school_years': school_years,
            'adviser_records': adviser_records

        })

    # Initialize member variables
    member1_grade = grades.first().member1_grade if grades.exists() else None
    print("member1_grade: ", member1_grade)
    member2_grade = grades.first().member2_grade if grades.exists() else None
    print("member2_grade: ", member2_grade)
    member3_grade = grades.first().member3_grade if grades.exists() else None
    print("member3_grade: ", member3_grade)
    recommendation = grades.first().recommendation if grades.exists() else None
    total_grade1 = grades.aggregate(Sum('member1_grade'))['member1_grade__sum']
    total_grade2 = grades.aggregate(Sum('member2_grade'))['member2_grade__sum']
    total_grade3 = grades.aggregate(Sum('member3_grade'))['member3_grade__sum']

    #grade for the member1
    if total_grade1 is not None and grades.count() is not 0:
        print("total_grade1: ", total_grade1)
        average_grade1 = total_grade1 / 3
        print('the grade is no 0')
    else:
        average_grade1 = 0  # Handle the case where no grades exist
        print('the grade is 0')
    print('member grade1: ', average_grade1)

    #grade for the member2
    if total_grade2 is not None and grades.count() is not 0:
        print("total_grade2: ", total_grade2)
        average_grade2 = total_grade2 / 3
        print('the grade is no 0')
        
    else:
        average_grade2 = 0  # Handle the case where no grades exist
        print('the grade is 0')
    print('member grade2: ', average_grade2)

    #grade for the member3
    if total_grade3 is not None and grades.count() is not 0:
        print("total_grade3: ", total_grade3)
        average_grade3 = total_grade3 / 3
        print('the grade is no 0')
        
    else:
        average_grade3 = 0  # Handle the case where no grades exist
        print('the grade is 0')
    print('member grade3: ', average_grade3)

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
        'all_checkboxes': Checkbox.objects.all(),
        'preoral_grade_record': preoral_grade_record,
        'checkbox_entry': checkbox_entry,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
        'adviser_records': adviser_records
    }
    
    return render(request, 'faculty/pre_oral_grade/adviser_record_detailPOD.html', context)




def group_grades(request, group_id):
    group = get_object_or_404(GroupInfoPOD, id=group_id)
    members = [group.member1, group.member2, group.member3]
    
    # Collect faculty information for each member's schedule
    faculty_info = []
    for member in members:
        schedule = SchedulePOD.objects.filter(group=group).first()  # Assuming each group has one schedule
        faculty_info.append({
            'member': member,
            'faculty1': schedule.faculty1.name if schedule else 'N/A',
            'faculty2': schedule.faculty2.name if schedule else 'N/A',
            'faculty3': schedule.faculty3.name if schedule else 'N/A',
        })
    
    context = {
        'members': faculty_info,
        'section': group.section,
    }
    return render(request, 'admin/pre_oral/group_grades.html', context)


# update group in Pre-Oral Defense
@login_required
def update_groupPOD(request, group_id):
    group = get_object_or_404(GroupInfoPOD, id=group_id)
    members = f"{group.member1}<br>{group.member2}<br>{group.member3}"
    capstone_teachers = Faculty.objects.filter(is_active=True)
    advisers = Adviser.objects.all()
    previous_capstone_teacher = group.capstone_teacher  # Original capstone teacher
    print("previous_capstone_teacher: ", previous_capstone_teacher)
    
    
    if request.method == 'POST':
        form = GroupInfoPODEditForm(request.POST, instance=group)
        if form.is_valid():
            members = f"{group.member1}<br>{group.member2}<br>{group.member3}"
            print("members: ", members)
            new_capstone_teacher = group.capstone_teacher  # New capstone teacher from form
            print("new_capstone_teacher: ", new_capstone_teacher)

            new_adviser = group.adviser

            if new_capstone_teacher == new_adviser:
                error_message = "Cannot assign the same faculty as both subject teacher and adviser!"
                base_url = reverse('carousel_page')
                query_string = urlencode({'error_message': error_message})
                url = f'{base_url}?{query_string}#preoral-details'
                return redirect(url)

            else:
                if previous_capstone_teacher != new_capstone_teacher:
                    # Only update the `is_capstone_teacher` flag for the new teacher
                    if new_capstone_teacher:
                        new_capstone_teacher.is_capstone_teacher = True
                        new_capstone_teacher.save()

                # Update Adviser records after group is updated
                update_adviser_record(group, group_id)

                # update the mock group
                update_mock_record(group, group_id)
                form.save()
                
                # Log the action in AuditTrail
                full_name = request.user.get_full_name()
                if not full_name.strip():
                    full_name = request.user.username
                AuditTrail.objects.create(
                    user=request.user,
                    action=f"Updated Pre-Oral Defense Group:<br>Group {group.section} with Adviser: {group.adviser.name} <br>And members:<br>{group.member1}<br>{group.member2}<br>{group.member3}",
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                return redirect(reverse('carousel_page') + '#preoral-details')
    else:
        form = GroupInfoPODEditForm(instance=group)
    
    return render(request, 'admin/pre_oral/update_groupPOD.html', {'form': form, 'group': group, 'capstone_teachers': capstone_teachers, 'advisers': advisers})

def update_adviser_record(group, group_id):
    # Get the current active school year
    active_school_year = SchoolYear.get_active_school_year()

    groups = get_object_or_404(GroupInfoPOD, id=group_id)
    """
    Updates the Adviser record with the group's approved title and adviser information.
    """
    try:
        # Try to find an existing Adviser record linked to the group
        members = f"{groups.member1}<br>{groups.member2}<br>{groups.member3}"
        adviser_record = Adviser.objects.filter(group_name=members, school_year=active_school_year)
        print(members)
        print(group)
        print(groups)
        print(group.adviser)
        print(groups.adviser)
        

        if adviser_record:
            # If an existing adviser record is found, delete it
            Adviser.objects.filter(group_name=members, school_year=active_school_year).delete()
            # Create a new Adviser record with the updated information
            Adviser.objects.create(
                faculty=group.adviser,
                approved_title=group.title,
                group_name=f"{group.member1}<br>{group.member2}<br>{group.member3}",
                school_year=active_school_year
            )
        else:
            # If no adviser record exists for the current group adviser, create a new one
            Adviser.objects.create(
                faculty=group.adviser,
                approved_title=group.title,
                group_name=f"{group.member1}<br>{group.member2}<br>{group.member3}",
                school_year=active_school_year
            )

    except Exception as e:
        logger.error(f"Error updating adviser record: {e}")

def update_mock_record(group, group_id):
    # Get the current active school year
    active_school_year = SchoolYear.get_active_school_year()

    groups = get_object_or_404(GroupInfoPOD, id=group_id)
    """
    Updates the Adviser record with the group's approved title and adviser information.
    """
    member1=groups.member1
    member2=groups.member2
    member3=groups.member3
    print("member1: ", member1)
    try:
        mock_record = GroupInfoMD.objects.filter(member1=groups.member1, member2=groups.member2, member3=groups.member3, school_year=active_school_year)
        final_record = GroupInfoFD.objects.filter(member1=groups.member1, member2=groups.member2, member3=groups.member3, school_year=active_school_year)

        # Now create GroupInfoMD with the updated section value
        updated_section_value = ''
        section_value_pod = groups.section
        if section_value_pod[-1].isalpha() and section_value_pod[:-1].isdigit():
            # Extract year and increment it
            year = int(section_value_pod[:-1])
            letter = section_value_pod[-1]
            updated_section_value = f"{year + 1}{letter}"
        else:
            # If the format is unexpected, you can handle it accordingly
            updated_section_value = section_value_pod  # Fallback or custom logic

        if mock_record:
            # If an existing mock record is found, delete it
            GroupInfoMD.objects.filter(member1=groups.member1, member2=groups.member2, member3=groups.member3, school_year=active_school_year).delete()
            # Create a new Adviser record with the updated information
            GroupInfoMD.objects.create(
                    member1=group.member1,
                    member2=group.member2,
                    member3=group.member3,
                    title=group.title,
                    capstone_teacher=group.capstone_teacher,
                    section=updated_section_value,
                    adviser=group.adviser,
                    school_year=active_school_year
            )
        else:
            # If no mock record exists for the current group adviser, create a new one
            GroupInfoMD.objects.create(
                    member1=group.member1,
                    member2=group.member2,
                    member3=group.member3,
                    title=group.title,
                    capstone_teacher=group.capstone_teacher,
                    section=updated_section_value,
                    adviser=group.adviser,
                    school_year=active_school_year
            )




        if final_record:
            # If an existing mock record is found, delete it
            GroupInfoFD.objects.filter(member1=groups.member1, member2=groups.member2, member3=groups.member3, school_year=active_school_year).delete()
            # Create a new Adviser record with the updated information
            GroupInfoFD.objects.create(
                    member1=group.member1,
                    member2=group.member2,
                    member3=group.member3,
                    title=group.title,
                    capstone_teacher=group.capstone_teacher,
                    section=updated_section_value,
                    adviser=group.adviser,
                    school_year=active_school_year
            )
        else:
            # If no mock record exists for the current group adviser, create a new one
            GroupInfoFD.objects.create(
                    member1=group.member1,
                    member2=group.member2,
                    member3=group.member3,
                    title=group.title,
                    capstone_teacher=group.capstone_teacher,
                    section=updated_section_value,
                    adviser=group.adviser,
                    school_year=active_school_year
            )

    except Exception as e:
        logger.error(f"Error updating adviser record: {e}")


@login_required
def delete_groupPOD(request, id):
    # Get the current active school year
    active_school_year = SchoolYear.get_active_school_year()
    group = get_object_or_404(GroupInfoPOD, id=id)
    mgroup = GroupInfoMD.objects.filter(member1=group.member1, member2=group.member2, member3=group.member3, school_year=active_school_year).exists()
    if mgroup:
        GroupInfoMD.objects.filter(member1=group.member1, member2=group.member2, member3=group.member3, school_year=active_school_year).delete()
    
    fgroup = GroupInfoFD.objects.filter(member1=group.member1, member2=group.member2, member3=group.member3, school_year=active_school_year).exists()
    if fgroup:
        GroupInfoFD.objects.filter(member1=group.member1, member2=group.member2, member3=group.member3, school_year=active_school_year).delete()
    
    # group_name = f"{group.member1}, {group.member2}, {group.member3}"
    # group_exists = Adviser.objects.filter(group_name=group_name).exists()
    # if group_exists:
    #     Adviser.objects.filter(group_name=group_name).delete()
    
    group_name = f"{group.member1}<br>{group.member2}<br>{group.member3}"
    advisee_exists = Adviser.objects.filter(group_name=group_name, school_year=active_school_year).exists()
    if advisee_exists:
        Adviser.objects.filter(group_name=group_name, school_year=active_school_year).delete()
    
    # Delete related Grade records
    Grade.objects.filter(
        member1=group.member1,
        member2=group.member2,
        member3=group.member3,
        title=group.title
    ).delete()
    
    # Log the action in AuditTrail
    full_name = request.user.get_full_name()
    if not full_name.strip():
        full_name = request.user.username
    AuditTrail.objects.create(
        user=request.user,
        action=f"""Deleted Pre-Oral Defense Group:<br>
    Group {group.section} with title: {group.title} <br>And members:<br>
        {group.member1}<br>
        {group.member2}<br>
        {group.member3}""",
            ip_address=request.META.get('REMOTE_ADDR')
        )
    
    group.delete()
    
    # Get the current page number from the query parameters
    current_page = request.GET.get('page', 1)
    
    # Redirect back to the same page
    return redirect(reverse('carousel_page') + f'?page={current_page}#preoral-details')


# the following views are used in the mock defense
# update group in Pre-Oral Defense
def checker3(request):
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

    if not GroupInfoPOD.objects.filter(school_year=selected_school_year).exists():
        messages.warning(request, 'No groups found. Please add groups first to generate schedule for pre oral defense.')
        empty = "True"
        message = "No groups found. Please add groups first to generate schedule for pre oral, mock, and final defense."
        url = reverse('add_groupPOD')
        query_string = urlencode({'empty': empty, 'message': message})
        return redirect(f'{url}?{query_string}')
    else:
        return redirect('schedule_listMD')

def group_infoMD(request):
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
    
    # Ensure there are school years available
    school_years = SchoolYear.objects.all().order_by('start_year')
    if school_years.count() == 0:
        SchoolYear.create_new_school_year()
        school_years = SchoolYear.objects.all().order_by('start_year')

    # Subquery to count graded groups for each GroupInfomD
    mock_graded_groups = Mock_Grade.objects.filter(project_title=OuterRef('title'), school_year=selected_school_year)
    graded_count = mock_graded_groups.values('project_title').annotate(graded_count=Count('*')).values('graded_count')

    # Annotate each GroupInfoMD with grading status
    groupsMD = GroupInfoMD.objects.filter(school_year=selected_school_year).annotate(
        is_graded=Exists(mock_graded_groups),
        graded_count=Subquery(graded_count, output_field=IntegerField())
    ).annotate(
        is_fully_graded=Case(
            When(graded_count=3, then=1),  # Fully graded
            When(graded_count__lt=3, then=0),  # Incomplete
            default=0,
            output_field=IntegerField(),
        )
    ).order_by('-is_fully_graded', '-is_graded')

    print("Mock grade records: ", groupsMD)

    # Paginate the groups, showing 10 groups per page
    paginator = Paginator(groupsMD, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    advisers = Faculty.objects.all()

    return render(request, 'admin/mock/group_infoMD.html', {
        'page_obj': page_obj, 
        'advisers': advisers,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years
    })


@login_required
def update_groupMD(request, mgroup_id):
    mgroup = get_object_or_404(GroupInfoMD, id=mgroup_id)
    members = f"{mgroup.member1}<br>{mgroup.member2}<br>{mgroup.member3}"
    capstone_teachers = Faculty.objects.filter(is_active=True)
    advisers = Adviser.objects.all()
    previous_capstone_teacher = mgroup.capstone_teacher  # Original capstone teacher
    print("previous_capstone_teacher: ", previous_capstone_teacher)
    
    if request.method == 'POST':
        form = GroupInfoMDEditForm(request.POST, instance=mgroup)
        if form.is_valid():
            members = f"{mgroup.member1}<br>{mgroup.member2}<br>{mgroup.member3}"
            print("members: ", members)
            new_capstone_teacher = mgroup.capstone_teacher  # New capstone teacher from form
            print("new_capstone_teacher: ", new_capstone_teacher)

            new_adviser = mgroup.adviser

            if new_capstone_teacher == new_adviser:
                error_message = "Cannot assign the same faculty as both subject teacher and adviser!"
                base_url = reverse('carousel_page')
                query_string = urlencode({'error_message': error_message})
                url = f'{base_url}?{query_string}#preoral-details'
                return redirect(url)
            else:
                if previous_capstone_teacher != new_capstone_teacher:
                    # Only update the `is_capstone_teacher` flag for the new teacher
                    if new_capstone_teacher:
                        new_capstone_teacher.is_capstone_teacher = True
                        new_capstone_teacher.save()

                # Update Adviser records after group is updated
                update_final_record(mgroup, mgroup_id)
                form.save()
                
                # Log the action in AuditTrail
                full_name = request.user.get_full_name()
                if not full_name.strip():
                    full_name = request.user.username
                AuditTrail.objects.create(
                    user=request.user,
                    action=f"Updated Mock Defense Group:<br>Group {mgroup.section} with Adviser: {mgroup.adviser.name} <br>And members:<br>{mgroup.member1}<br>{mgroup.member2}<br>{mgroup.member3}",
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                return redirect(reverse('carousel_page') + '#preoral-details')
    else:
        form = GroupInfoMDEditForm(instance=mgroup)
    
    return render(request, 'admin/pre_oral/update_groupPOD.html', {'form': form, 'mgroup': mgroup, 'capstone_teachers': capstone_teachers, 'advisers': advisers})

def update_final_record(mgroup, mgroup_id):
    # Get the current active school year
    active_school_year = SchoolYear.get_active_school_year()

    groups = get_object_or_404(GroupInfoMD, id=mgroup_id)
    """
    Updates the Adviser record with the group's approved title and adviser information.
    """
    try:
        final_record = GroupInfoFD.objects.filter(member1=groups.member1, member2=groups.member2, member3=groups.member3, school_year=active_school_year)
        
        # Now create GroupInfoMD with the updated section value
        updated_section_value = ''
        section_value_pod = groups.section
        if section_value_pod[-1].isalpha() and section_value_pod[:-1].isdigit():
            # Extract year and increment it
            year = int(section_value_pod[:-1])
            letter = section_value_pod[-1]
            updated_section_value = f"{year + 1}{letter}"
        else:
            # If the format is unexpected, you can handle it accordingly
            updated_section_value = section_value_pod  # Fallback or custom logic

        if final_record:
            # If an existing mock record is found, delete it
            GroupInfoFD.objects.filter(member1=groups.member1, member2=groups.member2, member3=groups.member3, school_year=active_school_year).delete()
            # Create a new Adviser record with the updated information
            GroupInfoFD.objects.create(
                    member1=mgroup.member1,
                    member2=mgroup.member2,
                    member3=mgroup.member3,
                    title=mgroup.title,
                    capstone_teacher=mgroup.capstone_teacher,
                    section=updated_section_value,
                    adviser=mgroup.adviser,
                    school_year=active_school_year
            )
        else:
            # If no mock record exists for the current group adviser, create a new one
            GroupInfoFD.objects.create(
                    member1=mgroup.member1,
                    member2=mgroup.member2,
                    member3=mgroup.member3,
                    title=mgroup.title,
                    capstone_teacher=mgroup.capstone_teacher,
                    section=updated_section_value,
                    adviser=mgroup.adviser,
                    school_year=active_school_year
            )

    except Exception as e:
        logger.error(f"Error updating adviser record: {e}")


@login_required
def delete_groupMD(request, id):
    # Get the current active school year
    active_school_year = SchoolYear.get_active_school_year()
    mgroup = get_object_or_404(GroupInfoMD, id=id)
    
    fgroup = GroupInfoFD.objects.filter(member1=mgroup.member1, member2=mgroup.member2, member3=mgroup.member3, school_year=active_school_year).exists()
    if fgroup:
        GroupInfoFD.objects.filter(member1=mgroup.member1, member2=mgroup.member2, member3=mgroup.member3, school_year=active_school_year).delete()
    
    # Log the action in AuditTrail
    full_name = request.user.get_full_name()
    if not full_name.strip():
        full_name = request.user.username
    AuditTrail.objects.create(
        user=request.user,
        action=f"""Deleted Mock Defense Group:<br>
    Group {mgroup.section} with title: {mgroup.title} <br>And members:<br>
        {mgroup.member1}<br>
        {mgroup.member2}<br>
        {mgroup.member3}""",
            ip_address=request.META.get('REMOTE_ADDR')
        )
    
    mgroup.delete()
    
    # Get the current page number from the query parameters
    current_page = request.GET.get('page', 1)
    
    # Redirect back to the same page
    return redirect(reverse('carousel_page') + f'?page={current_page}#preoral-details')

def schedule_listMD(request):
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

    # Check for the conflict query parameter
    conflict_str = request.GET.get('conflict')
    message = request.GET.get('message')
    conflict = conflict_str.lower() == 'true' if conflict_str else False

    last_used_date_str = request.GET.get('last_used_date')
    print("last_used_date_str: ", last_used_date_str)

    last_used_date = None
    if last_used_date_str:
        last_used_date = last_used_date_str
    else:
        # Fetch the latest schedule date
        last_schedule = ScheduleMD.objects.filter(school_year=selected_school_year).order_by('-date').first()
        last_used_date = last_schedule.date if last_schedule else None
    print("last_used_date: ", last_used_date)

    # Fetch the latest schedule date
    last_schedulePOD = SchedulePOD.objects.filter(school_year=selected_school_year).order_by('-date').first()
    last_used_datePOD = last_schedulePOD.date if last_schedulePOD else None

    if request.method == 'POST':
        start_date_str = request.POST.get('start_date')
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                generate_scheduleMD(request, start_date=start_date)
                messages.success(request, 'Schedule generated successfully.')

                # Record the action in the audit trail
                AuditTrail.objects.create(
                    user=request.user,
                    action=f"Generated Schedule for Mock Defense starting from {start_date.strftime('%B %d, %Y')}",
                    ip_address=request.META.get('REMOTE_ADDR')
                )

                # creating a notif
                Notif.objects.create(
                    created_by=request.user,
                    notif=f"Generate New Schedule for Mock Defense starting date is {start_date.strftime('%B %d, %Y')}",
                )
            except Exception as e:
                messages.error(request, f'Error generating schedule: {e}')
            
            return redirect('schedule_listMD')

    schedulesMD = ScheduleMD.objects.filter(school_year=selected_school_year).order_by('date')
    grouped_schedulesMD = {}

    def convert_slot_to_sortableMD(slot):
        start_time = slot.split('-')[0].strip()
        period = start_time[-2:]  # AM or PM
        time_parts = start_time[:-2].strip().split(':')

        if len(time_parts) == 1:
            hour = int(time_parts[0])
            minute = 0
        else:
            hour, minute = map(int, time_parts)

        if period == 'PM' and hour != 12:
            hour += 12
        if period == 'AM' and hour == 12:
            hour = 0

        return hour * 60 + minute

    for schedule in schedulesMD:
        day_room = (schedule.day, schedule.date, schedule.room)
        if day_room not in grouped_schedulesMD:
            grouped_schedulesMD[day_room] = []
        grouped_schedulesMD[day_room].append(schedule)

    for day_room in grouped_schedulesMD:
        try:
            grouped_schedulesMD[day_room].sort(key=lambda x: convert_slot_to_sortableMD(x.slot))
        except Exception as e:
            logger.error(f"Error sorting schedule for {day_room}: {e}")
            messages.error(request, f"Error sorting schedule for {day_room}: {e}")
    
    school_years = SchoolYear.objects.all().order_by('start_year')
    if school_years.count() == 0:
        SchoolYear.create_new_school_year()
        school_years = SchoolYear.objects.all().order_by('start_year')

    rooms = Room.objects.all().order_by("status")

    new_group = request.GET.get('new_group')
    print('new_group: ', new_group)

    new_schedule = ScheduleMD.objects.order_by('-created_at').first()
    
    return render(request, 'admin/mock/schedule_listMD.html', {
        'grouped_schedulesMD': grouped_schedulesMD,
        'school_years': school_years, 
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'conflict': conflict,
        'message': message,
        'last_used_date': last_used_date,
        'last_used_datePOD': last_used_datePOD, 
        'rooms': rooms,
        'new_group': new_group,
        'new_schedule': new_schedule
    })

# def rescheduleMD(request, scheduleMD_id):
#     # Get the last added school year in the database
#     last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

#     # Get the current active school year
#     current_school_year = SchoolYear.get_active_school_year()

#     # Check if the active school year is the same as the last added school year
#     if current_school_year != last_school_year:
#         return HttpResponse("Oops, you are no longer allowed to access this page.") 

#     # Get the schedule object by ID
#     schedule = get_object_or_404(ScheduleMD, id=scheduleMD_id)
#     time_slots = ['8AM-9:30AM', '9:30AM-11AM', '12PM-01:30PM', '1:30PM-3PM', '3PM-4:30PM', '4:30PM-5PM', '5PM-6:30PM']
#     rooms = ["Cisco Lab", "Lab 2"]

#     # Get the last schedule to ensure we reschedule after the last slot
#     last_schedule = ScheduleMD.objects.filter(school_year=current_school_year).order_by('-created_at').first()
#     if not last_schedule:
#         return JsonResponse({'success': False, 'message': 'No existing schedules found.'})

#     last_date_str = last_schedule.date
#     last_date = datetime.strptime(last_date_str, '%B %d, %Y')
#     last_slot = last_schedule.slot
#     last_day_str = last_schedule.day
#     last_day_number = int(last_day_str.split()[1])  # Extract day number (e.g., "Day 2" -> 2)

#     # Step 1: Find any available vacant slots starting from the date of the schedule being rescheduled
#     next_date = datetime.strptime(schedule.date, '%B %d, %Y')
#     next_day_number = int(schedule.day.split()[1])  # Extract day number from the current schedule

#     while next_date <= last_date:  # Loop until we reach the last scheduled date
#         for room in rooms:  # Iterate over rooms first
#             for slot in time_slots:  # Then iterate over time slots
#                 # Check if there's no record for this date, room, and slot in the current school year
#                 if not ScheduleMD.objects.filter(
#                     date=next_date.strftime('%B %d, %Y'),
#                     room=room,
#                     slot=slot,
#                     school_year=current_school_year
#                 ).exists():
#                     # Found a completely vacant slot in one of the rooms
#                     next_slot = slot
#                     next_room = room

#                     # Mark the existing schedule as rescheduled
#                     schedule.has_been_rescheduled = True
#                     schedule.save()

#                     # Create the new schedule entry
#                     new_schedule = ScheduleMD.objects.create(
#                         group=schedule.group,
#                         faculty1=schedule.faculty1,
#                         faculty2=schedule.faculty2,
#                         faculty3=schedule.faculty3,
#                         title=schedule.title,
#                         slot=next_slot,
#                         date=next_date.strftime('%B %d, %Y'),
#                         day=f"Day {next_day_number}",
#                         room=next_room,
#                         adviser=schedule.adviser,
#                         capstone_teacher=schedule.capstone_teacher,
#                         school_year=current_school_year
#                     )

#                     # Log the action in AuditTrail
#                     AuditTrail.objects.create(
#                         user=request.user,
#                         action=f"""Rescheduled Mock Defense Group
#                         Group {schedule.group.section} with members:<br>
#                         {schedule.group.member1}<br>
#                         {schedule.group.member2}<br>
#                         {schedule.group.member3}<br>
#                         from {schedule.slot} on {schedule.date} ({schedule.day}) to {next_slot} on {next_date.strftime('%B %d, %Y')} (Day {next_day_number})""",
#                         ip_address=request.META.get('REMOTE_ADDR')
#                     )

#                     return redirect('schedule_listMD')

#         # Move to the next day if no available slot was found on the current date
#         next_date += timedelta(days=1)
#         next_day_number += 1

#     # Step 2: If no completely vacant slot is available for the current day, proceed with your previous logic
#     max_reschedule_date = last_date + timedelta(weeks=2)
#     next_date = last_date
#     next_slot_index = (time_slots.index(last_slot) + 1) % len(time_slots)
#     next_day_number = last_day_number

#     day_count = 0  # Counter to avoid infinite loops
#     while day_count < 1000:  # Arbitrary large number to prevent infinite loop
#         # Loop through all time slots starting from the next slot
#         for slot_index in range(next_slot_index, len(time_slots)):
#             next_slot = time_slots[slot_index]

#             # Check both rooms for the current slot
#             for room in rooms:
#                 if not ScheduleMD.objects.filter(date=next_date.strftime('%B %d, %Y'), room=room, slot=next_slot, school_year=current_school_year).exists():
#                     # Room and slot are available, reschedule to this slot and room
#                     next_room = room
#                     break
#             else:
#                 # If no room is available for the current slot, continue to the next slot
#                 continue
#             break  # Exit the loop once an available slot and room are found
#         else:
#             # If all slots are occupied on the current day, move to the next day
#             next_date += timedelta(days=1)
#             next_day_number += 1
#             next_slot_index = 0  # Reset slot index to check from the beginning of the day
#             day_count += 1
#             continue  # Start checking the new day with all slots

#         # Break out of the loop if a valid slot and room are found
#         if next_date <= max_reschedule_date:
#             break

#     # Ensure we are rescheduling within the valid time range (1-2 weeks)
#     if next_date > max_reschedule_date:
#         return JsonResponse({'success': False, 'message': 'No available slots to reschedule within the 2-week limit.'})

#     # Mark the existing schedule as rescheduled
#     schedule.has_been_rescheduled = True
#     schedule.save()

#     # Create the new schedule entry
#     new_schedule = ScheduleMD.objects.create(
#         group=schedule.group,
#         faculty1=schedule.faculty1,
#         faculty2=schedule.faculty2,
#         faculty3=schedule.faculty3,
#         title=schedule.title,
#         slot=next_slot,
#         date=next_date.strftime('%B %d, %Y'),
#         day=f"Day {next_day_number}",
#         room=next_room,
#         adviser=schedule.adviser,
#         capstone_teacher=schedule.capstone_teacher,
#         school_year=current_school_year
#     )

#     # Log the action in AuditTrail
#     AuditTrail.objects.create(
#         user=request.user,
#         action=f"""Rescheduled Mock Defense Group
#         Group {schedule.group.section} with members:<br>
#         {schedule.group.member1}<br>
#         {schedule.group.member2}<br>
#         {schedule.group.member3}<br>
#         from {schedule.slot} on {schedule.date} ({schedule.day}) to {next_slot} on {next_date.strftime('%B %d, %Y')} (Day {next_day_number})""",
#         ip_address=request.META.get('REMOTE_ADDR')
#     )
#     return redirect('schedule_listMD')

def rescheduleMD(request, scheduleMD_id):
    # Get the last added school year in the database
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the current active school year
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

    # Check if the active school year is the same as the last added school year
    if selected_school_year != last_school_year:
        return HttpResponse("Oops, you are no longer allowed to access this page.") 

    # Get the schedule object by ID
    schedule = get_object_or_404(ScheduleMD, id=scheduleMD_id)
    base_time_slots = ['8AM-9:30AM', '9:30AM-11AM', '12PM-01:30PM', '1:30PM-3PM', '3PM-4:30PM', '4:30PM-5PM', '5PM-6:30PM']
    rooms = Room.objects.all().order_by("status")

    # Adjust time slots based on whether the day is Monday or a weekend
    def get_valid_time_slots(current_date):
        weekday = current_date.weekday()
        if weekday == 0:  # Monday, skip first slot
            return base_time_slots[1:]
        elif weekday >= 5:  # Saturday or Sunday
            return []  # No scheduling on weekends
        return base_time_slots

    # Check if a faculty is already booked for the slot on the same day
    def is_faculty_available(faculty_list, date, slot):
        for faculty in faculty_list:
            if ScheduleMD.objects.filter(
                (Q(faculty1=faculty) | Q(faculty2=faculty) | Q(faculty3=faculty) | Q(adviser=faculty)),
                date=date.strftime('%B %d, %Y'),
                slot=slot,
                school_year=selected_school_year
            ).exists():
                return False  # Faculty is booked for that slot
        return True

    # Get the last schedule to ensure we reschedule after the last slot
    last_schedule = ScheduleMD.objects.filter(school_year=selected_school_year).order_by('-date').first()
    if not last_schedule:
        return JsonResponse({'success': False, 'message': 'No existing schedules found.'})

    last_date_str = last_schedule.date
    last_date = datetime.strptime(last_date_str, '%B %d, %Y')
    last_slot = last_schedule.slot
    last_day_str = last_schedule.day
    last_day_number = int(last_day_str.split()[1])

    next_date = datetime.strptime(schedule.date, '%B %d, %Y')
    next_day_number = int(schedule.day.split()[1])

    # Step 1: Find any available vacant slots that have no records and don't cause a conflict
    while next_date <= last_date:
        valid_time_slots = get_valid_time_slots(next_date)
        if not valid_time_slots:  # Skip weekends or invalid days
            next_date += timedelta(days=1)
            # next_day_number += 1
            continue

        # Try each time slot for each room in alternating order
        for slot in valid_time_slots:
            for room in rooms:
                faculties = [schedule.faculty1, schedule.faculty2, schedule.faculty3, schedule.adviser]
                if is_faculty_available(faculties, next_date, slot):
                    if not ScheduleMD.objects.filter(
                        date=next_date.strftime('%B %d, %Y'),
                        room=room,
                        slot=slot,
                        school_year=selected_school_year
                    ).exists():
                        # Found a vacant slot
                        next_slot = slot
                        next_room = room

                        # Query to check if there is a SchedulePOD with the given criteria
                        schedule_day = ScheduleMD.objects.filter(
                            date=next_date.strftime('%B %d, %Y'),
                            room=room,
                            school_year=selected_school_year
                        ).first() 

                        # Mark the existing schedule as rescheduled
                        schedule.has_been_rescheduled = True
                        schedule.save()

                        if schedule_day:
                            # Create the new schedule entry
                            new_schedule = ScheduleMD.objects.create(
                                group=schedule.group,
                                faculty1=schedule.faculty1,
                                faculty2=schedule.faculty2,
                                faculty3=schedule.faculty3,
                                title=schedule.title,
                                slot=next_slot,
                                date=next_date.strftime('%B %d, %Y'),
                                day=schedule_day.day,
                                room=next_room,
                                adviser=schedule.adviser,
                                capstone_teacher=schedule.capstone_teacher,
                                school_year=selected_school_year,
                                new_sched = True
                            )
                        else:
                            # Create the new schedule entry
                            new_schedule = ScheduleMD.objects.create(
                                group=schedule.group,
                                faculty1=schedule.faculty1,
                                faculty2=schedule.faculty2,
                                faculty3=schedule.faculty3,
                                title=schedule.title,
                                slot=next_slot,
                                date=next_date.strftime('%B %d, %Y'),
                                day=f"Day {next_day_number}",
                                room=next_room,
                                adviser=schedule.adviser,
                                capstone_teacher=schedule.capstone_teacher,
                                school_year=selected_school_year,
                                new_sched = True
                            )

                        # Log the action in AuditTrail
                        AuditTrail.objects.create(
                            user=request.user,
                            action=f"""Rescheduled Mock Defense Group
                            Group {schedule.group.section} with members:<br>
                            {schedule.group.member1}<br>
                            {schedule.group.member2}<br>
                            {schedule.group.member3}<br>
                            from {schedule.slot} on {schedule.date} ({schedule.day}) to {next_slot} on {next_date.strftime('%B %d, %Y')} (Day {next_day_number})""",
                            ip_address=request.META.get('REMOTE_ADDR')
                        )

                        # creating a notif
                        Notif.objects.create(
                            created_by=request.user,
                            notif=f"This Mock Group: {schedule.group} has been rescheduled from {schedule.slot} on {schedule.date} ({schedule.day}) to {next_slot} on {next_date.strftime('%B %d, %Y')} (Day {next_day_number})"
                        )

                        # return redirect('schedule_listMD')
                        url = reverse('schedule_listMD')
                        new_slot=next_slot,
                        new_date=next_date.strftime('%B %d, %Y'),
                        new_day=f"Day {next_day_number}",
                        new_room=next_room,
                        new_group=schedule.group
                        print("new_groupr: ", new_group)
                        query_string = urlencode({'new_slot': new_slot, 'new_date': new_date, 'new_day': new_day, 'new_room': new_room, 'new_group': new_group})
                        return redirect(f'{url}?{query_string}')

        # Move to the next day if no available slot was found on the current date
        next_date += timedelta(days=1)
        next_day_number += 1

    # Step 2: Find slots after the last scheduled date, similar logic
    max_reschedule_date = last_date + timedelta(weeks=3)
    next_date = last_date
    next_day_number = last_day_number
    next_slot_index = (base_time_slots.index(last_slot) + 1) % len(base_time_slots)

    while next_date <= max_reschedule_date:
        valid_time_slots = get_valid_time_slots(next_date)  # Dynamic slot selection
        if not valid_time_slots:  # Skip weekends or days with no slots
            next_date += timedelta(days=1)
            # next_day_number += 1
            continue

        # Iterate over slots starting from next_slot_index
        for slot_index in range(next_slot_index, len(valid_time_slots)):
            next_slot = valid_time_slots[slot_index]  # Select slot

            for room in rooms:
                faculties = [schedule.faculty1, schedule.faculty2, schedule.faculty3, schedule.adviser]
                if is_faculty_available(faculties, next_date, next_slot):  # Faculty check
                    if not ScheduleMD.objects.filter(
                        date=next_date.strftime('%B %d, %Y'),
                        room=room,
                        slot=next_slot,
                        school_year=selected_school_year
                    ).exists():  # Check room availability

                        # Check for existing day label or assign new one
                        schedule_day = ScheduleMD.objects.filter(
                            date=next_date.strftime('%B %d, %Y'),
                            room=room,
                            school_year=selected_school_year
                        ).first() 

                        # Mark the existing schedule as rescheduled
                        schedule.has_been_rescheduled = True
                        schedule.save()

                        # Logging for debugging
                        print("next_day_number2:", next_day_number)
                        print("date2:", next_date.strftime('%B %d, %Y'))
                        print("slot:", next_slot)

                        next_room = room

                        if schedule_day:
                            # Create the new schedule entry
                            new_schedule = ScheduleMD.objects.create(
                                group=schedule.group,
                                faculty1=schedule.faculty1,
                                faculty2=schedule.faculty2,
                                faculty3=schedule.faculty3,
                                title=schedule.title,
                                slot=next_slot,
                                date=next_date.strftime('%B %d, %Y'),
                                day=schedule_day.day,
                                room=next_room,
                                adviser=schedule.adviser,
                                capstone_teacher=schedule.capstone_teacher,
                                school_year=selected_school_year,
                                new_sched = True
                            )
                        else:
                            # Create the new schedule entry
                            new_schedule = ScheduleMD.objects.create(
                                group=schedule.group,
                                faculty1=schedule.faculty1,
                                faculty2=schedule.faculty2,
                                faculty3=schedule.faculty3,
                                title=schedule.title,
                                slot=next_slot,
                                date=next_date.strftime('%B %d, %Y'),
                                day=f"Day {next_day_number}",
                                room=next_room,
                                adviser=schedule.adviser,
                                capstone_teacher=schedule.capstone_teacher,
                                school_year=selected_school_year,
                                new_sched = True
                            )

                        # Log the action in AuditTrail
                        AuditTrail.objects.create(
                            user=request.user,
                            action=f"""Rescheduled Mock Defense Group
                            Group {schedule.group.section} with members:<br>
                            {schedule.group.member1}<br>
                            {schedule.group.member2}<br>
                            {schedule.group.member3}<br>
                            from {schedule.slot} on {schedule.date} ({schedule.day}) to {next_slot} on {next_date.strftime('%B %d, %Y')} (Day {next_day_number})""",
                            ip_address=request.META.get('REMOTE_ADDR')
                        )

                        # creating a notif
                        Notif.objects.create(
                            created_by=request.user,
                            notif=f"This Mock Group: {schedule.group} has been rescheduled from {schedule.slot} on {schedule.date} ({schedule.day}) to {next_slot} on {next_date.strftime('%B %d, %Y')} (Day {next_day_number})"
                        )

                        # return redirect('schedule_listMD')
                        url = reverse('schedule_listMD')
                        new_slot=next_slot,
                        new_date=next_date.strftime('%B %d, %Y'),
                        new_day=f"Day {next_day_number}",
                        new_room=next_room,
                        new_group=schedule.group
                        print("new_groupr: ", new_group)
                        query_string = urlencode({'new_slot': new_slot, 'new_date': new_date, 'new_day': new_day, 'new_room': new_room, 'new_group': new_group})
                        return redirect(f'{url}?{query_string}')

        # Move to the next day if no available slot was found on the current date
        next_date += timedelta(days=1)
        next_day_number += 1
        next_slot_index = 0  # Reset index for each new day

    return JsonResponse({'success': False, 'message': 'No available slots to reschedule within the 3-week limit.'})


# def reassignMD(request, schedule_id):
#     schedule = get_object_or_404(ScheduleMD, id=schedule_id)

#     # get the current active school year
#     current_school_year = SchoolYear.get_active_school_year()
#     if request.method == 'POST':
#         new_date_str = request.POST.get('new_date')
#         new_time_str = request.POST.get('new_time')
#         new_lab = request.POST.get('new_lab')
#         if new_date_str and new_time_str and new_lab:
#             try:
#                 new_date = datetime.strptime(new_date_str, '%Y-%m-%d')

#                 # Get the earliest schedule date
#                 earliest_schedule = ScheduleMD.objects.filter(school_year=current_school_year).order_by('date').first()
#                 if earliest_schedule:
#                     earliest_date = datetime.strptime(earliest_schedule.date, '%B %d, %Y')
#                     if new_date < earliest_date:
#                         conflict = "True"
#                         message = "Cannot reschedule to a date earlier than the original schedule."
#                         url = reverse('schedule_listMD')
#                         query_string = urlencode({'conflict': conflict, 'message': message})
#                         return redirect(f'{url}?{query_string}')

#                     # Check if the new date is within one to two weeks from the earliest schedule date
#                     if not (earliest_date <= new_date <= earliest_date + timedelta(weeks=2)):
#                         conflict = "True"
#                         message = "Rescheduling is only allowed within one to two weeks from the original schedule."
#                         url = reverse('schedule_listMD')
#                         query_string = urlencode({'conflict': conflict, 'message': message})
#                         return redirect(f'{url}?{query_string}')

#                 # Check if the new schedule already exists
#                 if ScheduleMD.objects.filter(date=new_date.strftime('%B %d, %Y'), slot=new_time_str, room=new_lab, school_year=current_school_year).exists():
#                     conflict = "True"
#                     message = "Schedule already exists for the selected date, time, and room. Please choose a different slot."
#                     url = reverse('schedule_listMD')
#                     query_string = urlencode({'conflict': conflict, 'message': message})
#                     return redirect(f'{url}?{query_string}')

#                 # Mark the existing schedule as rescheduled
#                 schedule.has_been_rescheduled = True
#                 schedule.save()

#                 # Create the new schedule entry with the updated information
#                 new_schedule = ScheduleMD.objects.create(
#                     group=schedule.group,
#                     faculty1=schedule.faculty1,
#                     faculty2=schedule.faculty2,
#                     faculty3=schedule.faculty3,
#                     title=schedule.title,
#                     slot=new_time_str,
#                     date=new_date.strftime('%B %d, %Y'),
#                     day=f"Day {schedule.day.split()[1]}",  # Keep the same day number
#                     room=new_lab,
#                     adviser=schedule.adviser,
#                     capstone_teacher=schedule.capstone_teacher,
#                     school_year=current_school_year
#                 )

#                 # Log the action in AuditTrail
#                 AuditTrail.objects.create(
#                     user=request.user,
#                     action=f"Rescheduled Mock Defense Group: {schedule.group} from {schedule.slot} on {schedule.date} ({schedule.day}) to {new_time_str} on {new_date.strftime('%B %d, %Y')} (Day {schedule.day.split()[1]})",
#                     ip_address=request.META.get('REMOTE_ADDR')
#                 )

#                 messages.success(request, 'Schedule rescheduled successfully.')
#                 return redirect('schedule_listMD')
#             except Exception as e:
#                 messages.error(request, f'Error during rescheduling: {e}')
#                 return redirect('schedule_listMD')
#         else:
#             messages.error(request, 'Please provide a date, time, and room.')
#             return redirect('schedule_listMD')
#     else:
#         messages.error(request, 'Invalid request method.')
#         return redirect('schedule_listMD')

#     return render(request, 'reassign_md.html', {'schedule': schedule})

def reassignMD(request, schedule_id):
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
        new_date_str = request.POST.get('new_date')
        new_time_str = request.POST.get('new_time')
        new_lab_id = request.POST.get('new_lab')  # Fetch the room ID
        last_used_date_str = request.POST.get('last_used_date')  # Fetch the last used date

        if new_date_str and new_time_str and new_lab_id:
            try:
                new_date = datetime.strptime(new_date_str, '%Y-%m-%d')

                # Fetch the Room instance using the new_lab_id
                new_lab = get_object_or_404(Room, id=new_lab_id)

                # Get the earliest schedule date (the start date)
                earliest_schedule = ScheduleMD.objects.filter(school_year=selected_school_year).order_by('date').first()
                if not earliest_schedule:
                    messages.error(request, 'No schedules found for the current school year.')
                    return redirect('schedule_listMD')

                earliest_date = datetime.strptime(earliest_schedule.date, '%B %d, %Y')

                # Ensure new date is not earlier than the earliest schedule
                if new_date < earliest_date:
                    conflict = "True"
                    message = "Cannot reschedule to a date earlier than the original schedule."
                    url = reverse('schedule_listMD')
                    query_string = urlencode({'conflict': conflict, 'message': message, 'last_used_date': last_used_date_str})
                    return redirect(f'{url}?{query_string}')

                # Check if the new date is within one to two weeks from the earliest schedule date
                if not (earliest_date <= new_date <= earliest_date + timedelta(weeks=3)):
                    conflict = "True"
                    message = "Rescheduling is only allowed within one to two weeks from the original schedule."
                    url = reverse('schedule_listMD')
                    query_string = urlencode({'conflict': conflict, 'message': message, 'last_used_date': last_used_date_str})
                    return redirect(f'{url}?{query_string}')

                # Check if the new schedule already exists
                if ScheduleMD.objects.filter(date=new_date.strftime('%B %d, %Y'), slot=new_time_str, room=new_lab, school_year=selected_school_year).exists():
                    conflict = "True"
                    message = "Schedule already exists for the selected date, time, and room. Please choose a different slot."
                    url = reverse('schedule_listMD')
                    query_string = urlencode({'conflict': conflict, 'message': message, 'last_used_date': last_used_date_str})
                    return redirect(f'{url}?{query_string}')

                schedule = get_object_or_404(ScheduleMD, id=schedule_id)
                faculties = [schedule.faculty1, schedule.faculty2, schedule.faculty3]

                # Check if any faculty is double-booked for the new date and time
                for faculty in faculties:
                    if ScheduleMD.objects.filter(
                        date=new_date.strftime('%B %d, %Y'),
                        slot=new_time_str,
                        school_year=selected_school_year
                    ).filter(
                        (Q(faculty1=faculty) | Q(faculty2=faculty) | Q(faculty3=faculty))
                    ).exists():
                        conflict = "True"
                        message = f"Faculty {faculty.name} already has a schedule on {new_date.strftime('%B %d, %Y')} at {new_time_str}. Please choose a different slot or adjust the faculty assignment."
                        url = reverse('schedule_listMD')
                        query_string = urlencode({'conflict': conflict, 'message': message, 'last_used_date': last_used_date_str})
                        return redirect(f'{url}?{query_string}')

                # Calculate day_count excluding weekends
                current_date = earliest_date
                day_count = 0
                while current_date <= new_date:
                    if current_date.weekday() < 5:  # Only count weekdays (Mon-Fri)
                        day_count += 1
                    current_date += timedelta(days=1)
                
                print("day count (excluding weekends): ", day_count)
                
                # Mark the existing schedule as rescheduled
                schedule.has_been_rescheduled = True
                schedule.save()

                # Create the new schedule entry with the updated information
                new_schedule = ScheduleMD.objects.create(
                    group=schedule.group,
                    faculty1=schedule.faculty1,
                    faculty2=schedule.faculty2,
                    faculty3=schedule.faculty3,
                    title=schedule.title,
                    slot=new_time_str,
                    date=new_date.strftime('%B %d, %Y'),
                    day=f"Day {day_count}",  # Use the calculated day count
                    room=new_lab,
                    adviser=schedule.adviser,
                    capstone_teacher=schedule.capstone_teacher,
                    school_year=selected_school_year,
                    new_sched = True
                )

                # Log the action in AuditTrail
                AuditTrail.objects.create(
                    user=request.user,
                    action=f"Rescheduled Mock Defense Group: {schedule.group} from {schedule.slot} on {schedule.date} ({schedule.day}) to {new_time_str} on {new_date.strftime('%B %d, %Y')} (Day {day_count})",
                    ip_address=request.META.get('REMOTE_ADDR')
                )

                # creating a notif
                Notif.objects.create(
                    created_by=request.user,
                    notif=f"This Mock Group: {schedule.group} has been rescheduled from {schedule.slot} on {schedule.date} ({schedule.day}) to {new_time_str} on {new_date.strftime('%B %d, %Y')} (Day {day_count})"
                )


                messages.success(request, 'Schedule rescheduled successfully.')
                # Redirect to schedule_listPOD with last_used_date included
                url = reverse('schedule_listMD')
                new_group = schedule.group
                query_string = urlencode({'last_used_date': last_used_date_str, 'new_group': new_group})
                return redirect(f'{url}?{query_string}')
                

            except Exception as e:
                messages.error(request, f'Error during rescheduling: {e}')
                # Include last_used_date in error redirect
                url = reverse('schedule_listMD')
                query_string = urlencode({'last_used_date': last_used_date_str})
                return redirect(f'{url}?{query_string}')
        else:
            messages.error(request, 'Please provide a date, time, and room.')
            # Include last_used_date in the redirect
            url = reverse('schedule_listMD')
            query_string = urlencode({'last_used_date': last_used_date_str})
            return redirect(f'{url}?{query_string}')
    else:
        messages.error(request, 'Invalid request method.')
        return redirect('schedule_listMD')


def faculty_tally_viewMD(request):
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

    # Initialize a dictionary to hold faculty assignments
    faculty_tally = defaultdict(lambda: defaultdict(int))

    # Get all schedules
    schedules = ScheduleMD.objects.filter(school_year=selected_school_year)

    # Count the number of groups each faculty is assigned as a panel member
    for schedule in schedules:
        # Extract the actual date from the string
        date_str = schedule.date  # Assuming date is in 'Month Day, Year' format
        date = datetime.strptime(date_str, '%B %d, %Y')  # Parse the date string
        weekday = date.strftime('%A')  # Get the day name, e.g., "Monday"

        # Count assignments for each faculty
        faculty_tally[schedule.faculty1.id][weekday] += 1
        faculty_tally[schedule.faculty2.id][weekday] += 1
        faculty_tally[schedule.faculty3.id][weekday] += 1

    # Prepare data for the template
    faculty_summary = []
    
    # To store the mapping of weekday to actual dates for this week
    week_dates = {}
    
    # Iterate through the schedules to create a mapping of weekday to actual dates
    for schedule in schedules:
        date_str = schedule.date
        date = datetime.strptime(date_str, '%B %d, %Y')
        weekday = date.strftime('%A')
        if weekday not in week_dates:
            week_dates[weekday] = date_str  # Store the first occurrence of the date for that weekday

    # Get all active faculty members and store them in a list for sorting later
    faculties = list(Faculty.objects.filter(is_active=True))

    for faculty in faculties:
        days = faculty_tally[faculty.id]
        adviser_count = Adviser.objects.filter(faculty=faculty).count()  # Get the adviser count

        row = {
            'faculty_name': faculty.name,
            'adviser_count': adviser_count,
            'monday_count': days.get('Monday', 0),
            'tuesday_count': days.get('Tuesday', 0),
            'wednesday_count': days.get('Wednesday', 0),
            'thursday_count': days.get('Thursday', 0),
            'friday_count': days.get('Friday', 0),
        }

        # Calculate total assignments including adviser count
        total = sum(row[day] for day in ['monday_count', 'tuesday_count', 'wednesday_count', 'thursday_count', 'friday_count']) #+ adviser_count
        row['total'] = total
        
        # Add actual dates for each weekday
        row['monday_date'] = week_dates.get('Monday', '')
        row['tuesday_date'] = week_dates.get('Tuesday', '')
        row['wednesday_date'] = week_dates.get('Wednesday', '')
        row['thursday_date'] = week_dates.get('Thursday', '')
        row['friday_date'] = week_dates.get('Friday', '')

        faculty_summary.append(row)

    # Sort the faculty summary based on years of teaching and degree criteria
    faculty_summary.sort(key=lambda x: (
        not next((f for f in faculties if f.name == x['faculty_name']), None).has_master_degree,  # Ensure those with a master's degree come first
        -next((f for f in faculties if f.name == x['faculty_name']), None).years_of_teaching,     # Sort by years of teaching in descending order
        next((f for f in faculties if f.name == x['faculty_name']), None).highest_degree         # Sort by highest degree in ascending order (if needed)
    ))

    context = {
        'faculty_summary': faculty_summary,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
    }

    return render(request, 'admin/mock/faculty_tally.html', context)

def reset_scheduleMD(request):
    # get the last added school year in the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # get the current active school year
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

    ScheduleMD.objects.filter(school_year=selected_school_year).delete()
    # Log the action in AuditTrail
    AuditTrail.objects.create(
        user=request.user,
        action=f"Schedule for the Mock Defense has been reset to none",
        ip_address=request.META.get('REMOTE_ADDR')
    )

    # creating a notif
    Notif.objects.create(
        created_by=request.user,
        notif=f"Schedule for the Mock defense has been reset to none"
    )
    return redirect('schedule_listMD')

# function to view the preoral grade  of a specific group in the admin side
@login_required
def mock_grade_view(request, title_id):
    # Fetch the CustomUser object associated with the logged-in user
    user_profile = get_object_or_404(CustomUser, id=request.user.id)

    # If the user is a superuser, use the user profile as the faculty member
    if request.user.is_superuser:
        faculty_member = user_profile  # Use user_profile if superuser
    else:
        # If not a superuser, fetch the Faculty object associated with the CustomUser
        faculty_member = get_object_or_404(Faculty, custom_user=user_profile)

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

    

    temp = get_object_or_404(GroupInfoMD, id=title_id)
    title = temp.title
    adviser = get_object_or_404(Adviser, approved_title=title)
    adviser_id = adviser.approved_title
     
    # Fetch grades with the same title
    groups = GroupInfoMD.objects.filter(title=title, school_year=selected_school_year)
    
    adviser_id2=adviser.id
    print('adviser_id2', adviser_id2)
    verdicts = Mock_Verdict.objects.all().order_by('-percentage')
    print(verdicts)
    title = adviser.approved_title
    mock_grade_record = Mock_Grade.objects.filter(project_title=title, school_year=selected_school_year)
    recos = Mock_Recos.objects.filter(project_title=title, school_year=selected_school_year)
    all_checkboxes = Mock_Checkbox.objects.filter(school_year=selected_school_year)
    for reco in recos:
        reco.recommendation = escape(reco.recommendation)

    # Handle form submission
    if request.method == "POST":
        recommendation = request.POST.get("recommendation")
        print("recosss: ", recommendation)
        
        # Try to find an existing PreOral_Recos record with the same title
        reco = Mock_Recos.objects.filter(project_title=title, school_year=selected_school_year).first()
        
        if reco:
            # If recommendation record exists, update the recommendation
            reco.recommendation = recommendation
            if recommendation == "":
                print("Empty reco")
                reco.recommendation = recommendation
                reco.delete()
            else:
                reco.recommendation = recommendation
                # Save the recommendation record (updated)
                print("empyt also")
                reco.save()
        else:
            # If no recommendation record exists, create a new one
            if recommendation == "":
                print("Empty reco")
            else:
                reco = Mock_Recos(
                    project_title=title,  # Assuming `title` is defined elsewhere in the view
                    recommendation=recommendation,
                    school_year=selected_school_year
                )
                # Save the recommendation record (new)
                reco.save()
        
        
        
        print(f"Redirecting with adviser_id: {adviser_id}")  # Debugging line
        return redirect('adviser_record_detail', adviser_id=adviser_id)
    
    # Fetch grades with the same title
    grades = Mock_Grade.objects.filter(project_title=title, school_year=selected_school_year)
    groups = GroupInfoMD.objects.filter(title=title, school_year=selected_school_year)
    criteria_list = Mock_EvaluationSection.objects.filter(school_year=selected_school_year).annotate(total_criteria_percentage=Sum('mcriteria__percentage'))
    criteria_percentage = Mock_Criteria.objects.filter(school_year=selected_school_year)
    total_points = sum(criteria.percentage for criteria in criteria_percentage)
    adviser_records = ''
    if not request.user.is_superuser:
        adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)
    
    if not grades.exists():
        member1 = groups.first().member1 if groups.exists() else None
        member2 = groups.first().member2 if groups.exists() else None
        member3 = groups.first().member3 if groups.exists() else None
        return render(request, 'faculty/mock_grade/adviser_record_detailMD.html', {
            'error': 'No records found for this title',
            'title': title, 
            'member1': member1, 
            'member2': member2, 
            'member3': member3,
            'adviser': adviser,
            'recos': recos,
            'faculty_member': faculty_member,
            # 'current_school_year': current_school_year,
            'selected_school_year': selected_school_year,
            'last_school_year': last_school_year,
            'school_years': school_years,
            'adviser_records': adviser_records
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
    if total_grade1 is not None and grades.count() is not 0:
        average_grade1 = total_grade1 / 3
        print('the grade is no 0')
        
    else:
        average_grade1 = 0  # Handle the case where no grades exist
        print('the grade is 0')
    print('member grade1', average_grade1)

    #grade for the member2
    if total_grade2 is not None and grades.count() is not 0:
        average_grade2 = total_grade2 / 3
        print('the grade is no 0')
        
    else:
        average_grade2 = 0  # Handle the case where no grades exist
        print('the grade is 0')
    print('member grade3', average_grade2)

    #grade for the member3
    if total_grade3 is not None and grades.count() is not 0:
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
    # Decode the checkbox_data from the Mock_Grade instance
    for checkbox_entry in mock_grade_record:
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
        'all_checkboxes': Mock_Checkbox.objects.all(),
        'mock_grade_record': mock_grade_record,
        'checkbox_entry': checkbox_entry,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
        'adviser_records': adviser_records
    }
    
    return render(request, 'faculty/mock_grade/adviser_record_detailMD.html', context)



# the following views are used in the final defense
# update group in Pre-Oral Defense
def checker4(request):
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

    if not GroupInfoPOD.objects.filter(school_year=selected_school_year).exists():
        messages.warning(request, 'No groups found. Please add groups first to generate schedule for pre oral defense.')
        empty = "True"
        message = "No groups found. Please add groups first to generate schedule for pre oral, mock, and final defense."
        url = reverse('add_groupPOD')
        query_string = urlencode({'empty': empty, 'message': message})
        return redirect(f'{url}?{query_string}')
    else:
        return redirect('schedule_listFD')

def group_infoFD(request):
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
    
    # Ensure there are school years available
    school_years = SchoolYear.objects.all().order_by('start_year')
    if school_years.count() == 0:
        SchoolYear.create_new_school_year()
        school_years = SchoolYear.objects.all().order_by('start_year')

    # Subquery to count graded groups for each GroupInfomD
    final_graded_groups = Final_Grade.objects.filter(project_title=OuterRef('title'), school_year=selected_school_year)
    graded_count = final_graded_groups.values('project_title').annotate(graded_count=Count('*')).values('graded_count')

    # Annotate each GroupInfoMD with grading status
    groupsFD = GroupInfoFD.objects.filter(school_year=selected_school_year).annotate(
        is_graded=Exists(final_graded_groups),
        graded_count=Subquery(graded_count, output_field=IntegerField())
    ).annotate(
        is_fully_graded=Case(
            When(graded_count=3, then=1),  # Fully graded
            When(graded_count__lt=3, then=0),  # Incomplete
            default=0,
            output_field=IntegerField(),
        )
    ).order_by('-is_fully_graded', '-is_graded')

    print("Final grade records: ", groupsFD)

    # Paginate the groups, showing 10 groups per page
    paginator = Paginator(groupsFD, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    advisers = Faculty.objects.all()

    return render(request, 'admin/final/group_infoFD.html', {
        'page_obj': page_obj, 
        'advisers': advisers,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years
    })


@login_required
def update_groupFD(request, fgroup_id):
    fgroup = get_object_or_404(GroupInfoFD, id=fgroup_id)
    members = f"{fgroup.member1}<br>{fgroup.member2}<br>{fgroup.member3}"
    capstone_teachers = Faculty.objects.filter(is_active=True)
    advisers = Adviser.objects.all()
    previous_capstone_teacher = fgroup.capstone_teacher  # Original capstone teacher
    print("previous_capstone_teacher: ", previous_capstone_teacher)
    
    if request.method == 'POST':
        form = GroupInfoFDEditForm(request.POST, instance=fgroup)
        if form.is_valid():
            members = f"{fgroup.member1}<br>{fgroup.member2}<br>{fgroup.member3}"
            print("members: ", members)
            new_capstone_teacher = fgroup.capstone_teacher  # New capstone teacher from form
            print("new_capstone_teacher: ", new_capstone_teacher)

            new_adviser = fgroup.adviser

            if new_capstone_teacher == new_adviser:
                error_message = "Cannot assign the same faculty as both subject teacher and adviser!"
                base_url = reverse('carousel_page')
                query_string = urlencode({'error_message': error_message})
                url = f'{base_url}?{query_string}#preoral-details'
                return redirect(url)
            else:
                if previous_capstone_teacher != new_capstone_teacher:
                    # Only update the `is_capstone_teacher` flag for the new teacher
                    if new_capstone_teacher:
                        new_capstone_teacher.is_capstone_teacher = True
                        new_capstone_teacher.save()
                form.save()
                
                # Log the action in AuditTrail
                full_name = request.user.get_full_name()
                if not full_name.strip():
                    full_name = request.user.username
                AuditTrail.objects.create(
                    user=request.user,
                    action=f"Updated Final Defense Group:<br>Group {fgroup.section} with Adviser: {fgroup.adviser.name} <br>And members:<br>{fgroup.member1}<br>{fgroup.member2}<br>{fgroup.member3}",
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                return redirect(reverse('carousel_page') + '#preoral-details')
    else:
        form = GroupInfoFDEditForm(instance=fgroup)
    
    return render(request, 'admin/pre_oral/update_groupPOD.html', {'form': form, 'fgroup': fgroup, 'capstone_teachers': capstone_teachers, 'advisers': advisers})

@login_required
def delete_groupFD(request, id):
    # Get the current active school year
    active_school_year = SchoolYear.get_active_school_year()
    fgroup = get_object_or_404(GroupInfoFD, id=id)
    
    
    # Log the action in AuditTrail
    full_name = request.user.get_full_name()
    if not full_name.strip():
        full_name = request.user.username
    AuditTrail.objects.create(
        user=request.user,
        action=f"""Deleted Final Defense Group:<br>
    Group {fgroup.section} with title: {fgroup.title} <br>And members:<br>
        {fgroup.member1}<br>
        {fgroup.member2}<br>
        {fgroup.member3}""",
            ip_address=request.META.get('REMOTE_ADDR')
        )
    
    fgroup.delete()
    
    # Get the current page number from the query parameters
    current_page = request.GET.get('page', 1)
    
    # Redirect back to the same page
    return redirect(reverse('carousel_page') + f'?page={current_page}#preoral-details')

def schedule_listFD(request):
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

    # Check for the conflict query parameter
    conflict_str = request.GET.get('conflict')
    message = request.GET.get('message')
    conflict = conflict_str.lower() == 'true' if conflict_str else False

    last_used_date_str = request.GET.get('last_used_date')
    print("last_used_date_str: ", last_used_date_str)

    last_used_date = None
    if last_used_date_str:
        last_used_date = last_used_date_str
    else:
        # Fetch the latest schedule date
        last_schedule = ScheduleFD.objects.filter(school_year=selected_school_year).order_by('-date').first()
        last_used_date = last_schedule.date if last_schedule else None
    print("last_used_date: ", last_used_date)

    # Fetch the latest schedule date from ScheduleMD
    last_scheduleMD = ScheduleMD.objects.filter(school_year=selected_school_year).order_by('-date').first()
    last_used_dateMD = last_scheduleMD.date if last_scheduleMD else None

    if request.method == 'POST':
        start_date_str = request.POST.get('start_date')
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                generate_scheduleFD(request, start_date=start_date)
                messages.success(request, 'Schedule generated successfully.')

                # Record the action in the audit trail
                AuditTrail.objects.create(
                    user=request.user,
                    action=f"Generated Schedule for Final Defense starting from {start_date.strftime('%B %d, %Y')}",
                    ip_address=request.META.get('REMOTE_ADDR')
                )

                # creating a notif
                Notif.objects.create(
                    created_by=request.user,
                    notif=f"Generate New Schedule for Final Defense starting date is {start_date.strftime('%B %d, %Y')}",
                )
            except Exception as e:
                messages.error(request, f'Error generating schedule: {e}')
            
            return redirect('schedule_listFD')

    schedulesFD = ScheduleFD.objects.filter(school_year=selected_school_year).order_by('date')
    grouped_schedulesFD = {}

    def convert_slot_to_sortableFD(slot):
        start_time = slot.split('-')[0].strip()
        period = start_time[-2:]  # AM or PM
        time_parts = start_time[:-2].strip().split(':')

        if len(time_parts) == 1:
            hour = int(time_parts[0])
            minute = 0
        else:
            hour, minute = map(int, time_parts)

        if period == 'PM' and hour != 12:
            hour += 12
        if period == 'AM' and hour == 12:
            hour = 0

        return hour * 60 + minute

    for schedule in schedulesFD:
        day_room = (schedule.day, schedule.date, schedule.room)
        if day_room not in grouped_schedulesFD:
            grouped_schedulesFD[day_room] = []
        grouped_schedulesFD[day_room].append(schedule)

    for day_room in grouped_schedulesFD:
        try:
            grouped_schedulesFD[day_room].sort(key=lambda x: convert_slot_to_sortableFD(x.slot))
        except Exception as e:
            logger.error(f"Error sorting schedule for {day_room}: {e}")
            messages.error(request, f"Error sorting schedule for {day_room}: {e}")
    
    school_years = SchoolYear.objects.all().order_by('start_year')
    if school_years.count() == 0:
        SchoolYear.create_new_school_year()
        school_years = SchoolYear.objects.all().order_by('start_year')
    
    rooms = Room.objects.all().order_by("status")

    new_group = request.GET.get('new_group')
    print('new_group: ', new_group)

    new_schedule = ScheduleFD.objects.order_by('-created_at').first()

    return render(request, 'admin/final/schedule_listFD.html', {
        'grouped_schedulesFD': grouped_schedulesFD,
        'school_years': school_years, 
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'conflict': conflict,
        'message': message,
        'last_used_date': last_used_date,
        'last_used_dateMD': last_used_dateMD,
        'rooms': rooms,
        'new_group': new_group,
        'new_schedule': new_schedule
    })

# def rescheduleFD(request, scheduleFD_id):
#     # Get the last added school year in the database
#     last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

#     # Get the current active school year
#     current_school_year = SchoolYear.get_active_school_year()

#     # Check if the active school year is the same as the last added school year
#     if current_school_year != last_school_year:
#         return HttpResponse("Oops, you are no longer allowed to access this page.") 

#     # Get the schedule object by ID
#     schedule = get_object_or_404(ScheduleFD, id=scheduleFD_id)
#     time_slots = ['8AM-9:30AM', '9:30AM-11AM', '12PM-01:30PM', '1:30PM-3PM', '3PM-4:30PM', '4:30PM-5PM', '5PM-6:30PM']
#     rooms = ["Cisco Lab", "Lab 2"]

#     # Get the last schedule to ensure we reschedule after the last slot
#     last_schedule = ScheduleFD.objects.filter(school_year=current_school_year).order_by('-created_at').first()
#     if not last_schedule:
#         return JsonResponse({'success': False, 'message': 'No existing schedules found.'})

#     last_date_str = last_schedule.date
#     last_date = datetime.strptime(last_date_str, '%B %d, %Y')
#     last_slot = last_schedule.slot
#     last_day_str = last_schedule.day
#     last_day_number = int(last_day_str.split()[1])  # Extract day number (e.g., "Day 2" -> 2)

#     # Step 1: Find any available vacant slots starting from the date of the schedule being rescheduled
#     next_date = datetime.strptime(schedule.date, '%B %d, %Y')
#     next_day_number = int(schedule.day.split()[1])  # Extract day number from the current schedule

#     while next_date <= last_date:  # Loop until we reach the last scheduled date
#         for room in rooms:  # Iterate over rooms first
#             for slot in time_slots:  # Then iterate over time slots
#                 # Check if there's no record for this date, room, and slot in the current school year
#                 if not ScheduleFD.objects.filter(
#                     date=next_date.strftime('%B %d, %Y'),
#                     room=room,
#                     slot=slot,
#                     school_year=current_school_year
#                 ).exists():
#                     # Found a completely vacant slot in one of the rooms
#                     next_slot = slot
#                     next_room = room

#                     # Mark the existing schedule as rescheduled
#                     schedule.has_been_rescheduled = True
#                     schedule.save()

#                     # Create the new schedule entry
#                     new_schedule = ScheduleFD.objects.create(
#                         group=schedule.group,
#                         faculty1=schedule.faculty1,
#                         faculty2=schedule.faculty2,
#                         faculty3=schedule.faculty3,
#                         title=schedule.title,
#                         slot=next_slot,
#                         date=next_date.strftime('%B %d, %Y'),
#                         day=f"Day {next_day_number}",
#                         room=next_room,
#                         adviser=schedule.adviser,
#                         capstone_teacher=schedule.capstone_teacher,
#                         school_year=current_school_year
#                     )

#                     # Log the action in AuditTrail
#                     AuditTrail.objects.create(
#                         user=request.user,
#                         action=f"""Rescheduled Final Defense Group
#                         Group {schedule.group.section} with members:<br>
#                         {schedule.group.member1}<br>
#                         {schedule.group.member2}<br>
#                         {schedule.group.member3}<br>
#                         from {schedule.slot} on {schedule.date} ({schedule.day}) to {next_slot} on {next_date.strftime('%B %d, %Y')} (Day {next_day_number})""",
#                         ip_address=request.META.get('REMOTE_ADDR')
#                     )

#                     return redirect('schedule_listFD')

#         # Move to the next day if no available slot was found on the current date
#         next_date += timedelta(days=1)
#         next_day_number += 1

#     # Step 2: If no completely vacant slot is available for the current day, proceed with your previous logic
#     max_reschedule_date = last_date + timedelta(weeks=2)
#     next_date = last_date
#     next_slot_index = (time_slots.index(last_slot) + 1) % len(time_slots)
#     next_day_number = last_day_number

#     day_count = 0  # Counter to avoid infinite loops
#     while day_count < 1000:  # Arbitrary large number to prevent infinite loop
#         # Loop through all time slots starting from the next slot
#         for slot_index in range(next_slot_index, len(time_slots)):
#             next_slot = time_slots[slot_index]

#             # Check both rooms for the current slot
#             for room in rooms:
#                 if not ScheduleFD.objects.filter(date=next_date.strftime('%B %d, %Y'), room=room, slot=next_slot, school_year=current_school_year).exists():
#                     # Room and slot are available, reschedule to this slot and room
#                     next_room = room
#                     break
#             else:
#                 # If no room is available for the current slot, continue to the next slot
#                 continue
#             break  # Exit the loop once an available slot and room are found
#         else:
#             # If all slots are occupied on the current day, move to the next day
#             next_date += timedelta(days=1)
#             next_day_number += 1
#             next_slot_index = 0  # Reset slot index to check from the beginning of the day
#             day_count += 1
#             continue  # Start checking the new day with all slots

#         # Break out of the loop if a valid slot and room are found
#         if next_date <= max_reschedule_date:
#             break

#     # Ensure we are rescheduling within the valid time range (1-2 weeks)
#     if next_date > max_reschedule_date:
#         return JsonResponse({'success': False, 'message': 'No available slots to reschedule within the 2-week limit.'})

#     # Mark the existing schedule as rescheduled
#     schedule.has_been_rescheduled = True
#     schedule.save()

#     # Create the new schedule entry
#     new_schedule = ScheduleFD.objects.create(
#         group=schedule.group,
#         faculty1=schedule.faculty1,
#         faculty2=schedule.faculty2,
#         faculty3=schedule.faculty3,
#         title=schedule.title,
#         slot=next_slot,
#         date=next_date.strftime('%B %d, %Y'),
#         day=f"Day {next_day_number}",
#         room=next_room,
#         adviser=schedule.adviser,
#         capstone_teacher=schedule.capstone_teacher,
#         school_year=current_school_year
#     )

#     # Log the action in AuditTrail
#     AuditTrail.objects.create(
#         user=request.user,
#         action=f"""Rescheduled Final Defense Group
#         Group {schedule.group.section} with members:<br>
#         {schedule.group.member1}<br>
#         {schedule.group.member2}<br>
#         {schedule.group.member3}<br>
#         from {schedule.slot} on {schedule.date} ({schedule.day}) to {next_slot} on {next_date.strftime('%B %d, %Y')} (Day {next_day_number})""",
#         ip_address=request.META.get('REMOTE_ADDR')
#     )
#     return redirect('schedule_listFD')

def rescheduleFD(request, scheduleFD_id):
    # Get the last added school year in the database
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # Get the current active school year
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

    # Check if the active school year is the same as the last added school year
    if selected_school_year != last_school_year:
        return HttpResponse("Oops, you are no longer allowed to access this page.") 

    # Get the schedule object by ID
    schedule = get_object_or_404(ScheduleFD, id=scheduleFD_id)
    base_time_slots = ['8AM-9:30AM', '9:30AM-11AM', '12PM-01:30PM', '1:30PM-3PM', '3PM-4:30PM', '4:30PM-5PM', '5PM-6:30PM']
    rooms = Room.objects.all().order_by("status")

    # Adjust time slots based on whether the day is Monday or a weekend
    def get_valid_time_slots(current_date):
        weekday = current_date.weekday()
        if weekday == 0:  # Monday, skip first slot
            return base_time_slots[1:]
        elif weekday >= 5:  # Saturday or Sunday
            return []  # No scheduling on weekends
        return base_time_slots

    # Check if a faculty is already booked for the slot on the same day
    def is_faculty_available(faculty_list, date, slot):
        for faculty in faculty_list:
            if ScheduleFD.objects.filter(
                (Q(faculty1=faculty) | Q(faculty2=faculty) | Q(faculty3=faculty) | Q(adviser=faculty)),
                date=date.strftime('%B %d, %Y'),
                slot=slot,
                school_year=selected_school_year
            ).exists():
                return False  # Faculty is booked for that slot
        return True

    # Get the last schedule to ensure we reschedule after the last slot
    last_schedule = ScheduleFD.objects.filter(school_year=selected_school_year).order_by('-date').first()
    if not last_schedule:
        return JsonResponse({'success': False, 'message': 'No existing schedules found.'})

    last_date_str = last_schedule.date
    last_date = datetime.strptime(last_date_str, '%B %d, %Y')
    last_slot = last_schedule.slot
    last_day_str = last_schedule.day
    last_day_number = int(last_day_str.split()[1])

    next_date = datetime.strptime(schedule.date, '%B %d, %Y')
    next_day_number = int(schedule.day.split()[1])

    # Step 1: Find any available vacant slots that have no records and don't cause a conflict
    while next_date <= last_date:
        valid_time_slots = get_valid_time_slots(next_date)
        if not valid_time_slots:  # Skip weekends or invalid days
            next_date += timedelta(days=1)
            # next_day_number += 1
            continue

        # Try each time slot for each room in alternating order
        for slot in valid_time_slots:
            for room in rooms:
                faculties = [schedule.faculty1, schedule.faculty2, schedule.faculty3, schedule.adviser]
                if is_faculty_available(faculties, next_date, slot):
                    if not ScheduleFD.objects.filter(
                        date=next_date.strftime('%B %d, %Y'),
                        room=room,
                        slot=slot,
                        school_year=selected_school_year
                    ).exists():
                        # Found a vacant slot
                        next_slot = slot
                        next_room = room

                        # Query to check if there is a SchedulePOD with the given criteria
                        schedule_day = ScheduleFD.objects.filter(
                            date=next_date.strftime('%B %d, %Y'),
                            room=room,
                            school_year=selected_school_year
                        ).first() 

                        # Mark the existing schedule as rescheduled
                        schedule.has_been_rescheduled = True
                        schedule.save()

                        if schedule_day:
                            # Create the new schedule entry
                            new_schedule = ScheduleFD.objects.create(
                                group=schedule.group,
                                faculty1=schedule.faculty1,
                                faculty2=schedule.faculty2,
                                faculty3=schedule.faculty3,
                                title=schedule.title,
                                slot=next_slot,
                                date=next_date.strftime('%B %d, %Y'),
                                day=schedule_day.day,
                                room=next_room,
                                adviser=schedule.adviser,
                                capstone_teacher=schedule.capstone_teacher,
                                school_year=selected_school_year,
                                new_sched = True
                            )
                        else:
                            # Create the new schedule entry
                            new_schedule = ScheduleFD.objects.create(
                                group=schedule.group,
                                faculty1=schedule.faculty1,
                                faculty2=schedule.faculty2,
                                faculty3=schedule.faculty3,
                                title=schedule.title,
                                slot=next_slot,
                                date=next_date.strftime('%B %d, %Y'),
                                day=f"Day {next_day_number}",
                                room=next_room,
                                adviser=schedule.adviser,
                                capstone_teacher=schedule.capstone_teacher,
                                school_year=selected_school_year,
                                new_sched = True
                            )

                        # Log the action in AuditTrail
                        AuditTrail.objects.create(
                            user=request.user,
                            action=f"""Rescheduled Final Defense Group
                            Group {schedule.group.section} with members:<br>
                            {schedule.group.member1}<br>
                            {schedule.group.member2}<br>
                            {schedule.group.member3}<br>
                            from {schedule.slot} on {schedule.date} ({schedule.day}) to {next_slot} on {next_date.strftime('%B %d, %Y')} (Day {next_day_number})""",
                            ip_address=request.META.get('REMOTE_ADDR')
                        )

                        # creating a notif
                        Notif.objects.create(
                            created_by=request.user,
                            notif=f"This Group for the final defense: {schedule.group} has been rescheduled from {schedule.slot} on {schedule.date} ({schedule.day}) to {next_slot} on {next_date.strftime('%B %d, %Y')} (Day {next_day_number})"
                        )

                        # return redirect('schedule_listFD')
                        url = reverse('schedule_listFD')
                        new_slot=next_slot,
                        new_date=next_date.strftime('%B %d, %Y'),
                        new_day=f"Day {next_day_number}",
                        new_room=next_room,
                        new_group=schedule.group
                        print("new_groupr: ", new_group)
                        query_string = urlencode({'new_slot': new_slot, 'new_date': new_date, 'new_day': new_day, 'new_room': new_room, 'new_group': new_group})
                        return redirect(f'{url}?{query_string}')

        # Move to the next day if no available slot was found on the current date
        next_date += timedelta(days=1)
        next_day_number += 1

    # Step 2: Find slots after the last scheduled date, similar logic
    max_reschedule_date = last_date + timedelta(weeks=3)
    next_date = last_date
    next_day_number = last_day_number
    next_slot_index = (base_time_slots.index(last_slot) + 1) % len(base_time_slots)

    while next_date <= max_reschedule_date:
        valid_time_slots = get_valid_time_slots(next_date)  # Dynamic slot selection
        if not valid_time_slots:  # Skip weekends or days with no slots
            next_date += timedelta(days=1)
            # next_day_number += 1
            continue

        # Iterate over slots starting from next_slot_index
        for slot_index in range(next_slot_index, len(valid_time_slots)):
            next_slot = valid_time_slots[slot_index]  # Select slot

            for room in rooms:
                faculties = [schedule.faculty1, schedule.faculty2, schedule.faculty3, schedule.adviser]
                if is_faculty_available(faculties, next_date, next_slot):  # Faculty check
                    if not ScheduleFD.objects.filter(
                        date=next_date.strftime('%B %d, %Y'),
                        room=room,
                        slot=next_slot,
                        school_year=selected_school_year
                    ).exists():  # Check room availability

                        # Check for existing day label or assign new one
                        schedule_day = ScheduleFD.objects.filter(
                            date=next_date.strftime('%B %d, %Y'),
                            room=room,
                            school_year=selected_school_year
                        ).first() 

                        # Mark the existing schedule as rescheduled
                        schedule.has_been_rescheduled = True
                        schedule.save()

                        
                        next_room = room

                        # Logging for debugging
                        print("next_day_number2:", next_day_number)
                        print("date2:", next_date.strftime('%B %d, %Y'))
                        print("slot:", next_slot)

                        if schedule_day:
                            # Create the new schedule entry
                            new_schedule = ScheduleFD.objects.create(
                                group=schedule.group,
                                faculty1=schedule.faculty1,
                                faculty2=schedule.faculty2,
                                faculty3=schedule.faculty3,
                                title=schedule.title,
                                slot=next_slot,
                                date=next_date.strftime('%B %d, %Y'),
                                day=schedule_day.day,
                                room=next_room,
                                adviser=schedule.adviser,
                                capstone_teacher=schedule.capstone_teacher,
                                school_year=selected_school_year,
                                new_sched = True
                            )
                        else:
                            # Create the new schedule entry
                            new_schedule = ScheduleFD.objects.create(
                                group=schedule.group,
                                faculty1=schedule.faculty1,
                                faculty2=schedule.faculty2,
                                faculty3=schedule.faculty3,
                                title=schedule.title,
                                slot=next_slot,
                                date=next_date.strftime('%B %d, %Y'),
                                day=f"Day {next_day_number}",
                                room=next_room,
                                adviser=schedule.adviser,
                                capstone_teacher=schedule.capstone_teacher,
                                school_year=selected_school_year,
                                new_sched = True
                            )

                        # Log the action in AuditTrail
                        AuditTrail.objects.create(
                            user=request.user,
                            action=f"""Rescheduled Final Defense Group
                            Group {schedule.group.section} with members:<br>
                            {schedule.group.member1}<br>
                            {schedule.group.member2}<br>
                            {schedule.group.member3}<br>
                            from {schedule.slot} on {schedule.date} ({schedule.day}) to {next_slot} on {next_date.strftime('%B %d, %Y')} (Day {next_day_number})""",
                            ip_address=request.META.get('REMOTE_ADDR')
                        )

                        # creating a notif
                        Notif.objects.create(
                            created_by=request.user,
                            notif=f"This Group for the final defense: {schedule.group} has been rescheduled from {schedule.slot} on {schedule.date} ({schedule.day}) to {next_slot} on {next_date.strftime('%B %d, %Y')} (Day {next_day_number})"
                        )

                        # return redirect('schedule_listFD')
                        url = reverse('schedule_listFD')
                        new_slot=next_slot,
                        new_date=next_date.strftime('%B %d, %Y'),
                        new_day=f"Day {next_day_number}",
                        new_room=next_room,
                        new_group=schedule.group
                        print("new_groupr: ", new_group)
                        query_string = urlencode({'new_slot': new_slot, 'new_date': new_date, 'new_day': new_day, 'new_room': new_room, 'new_group': new_group})
                        return redirect(f'{url}?{query_string}')

        # Move to the next day if no available slot was found on the current date
        next_date += timedelta(days=1)
        next_day_number += 1
        next_slot_index = 0  # Reset index for each new day

    return JsonResponse({'success': False, 'message': 'No available slots to reschedule within the 3-week limit.'})


# def reassignFD(request, schedule_id):
#     schedule = get_object_or_404(ScheduleFD, id=schedule_id)

#     # get the current active school year
#     current_school_year = SchoolYear.get_active_school_year()
#     if request.method == 'POST':
#         new_date_str = request.POST.get('new_date')
#         new_time_str = request.POST.get('new_time')
#         new_lab = request.POST.get('new_lab')
#         if new_date_str and new_time_str and new_lab:
#             try:
#                 new_date = datetime.strptime(new_date_str, '%Y-%m-%d')

#                 # Get the earliest schedule date
#                 earliest_schedule = ScheduleFD.objects.filter(school_year=current_school_year).order_by('date').first()
#                 if earliest_schedule:
#                     earliest_date = datetime.strptime(earliest_schedule.date, '%B %d, %Y')
#                     if new_date < earliest_date:
#                         conflict = "True"
#                         message = "Cannot reschedule to a date earlier than the original schedule."
#                         url = reverse('schedule_listFD')
#                         query_string = urlencode({'conflict': conflict, 'message': message})
#                         return redirect(f'{url}?{query_string}')

#                     # Check if the new date is within one to two weeks from the earliest schedule date
#                     if not (earliest_date <= new_date <= earliest_date + timedelta(weeks=2)):
#                         conflict = "True"
#                         message = "Rescheduling is only allowed within one to two weeks from the original schedule."
#                         url = reverse('schedule_listFD')
#                         query_string = urlencode({'conflict': conflict, 'message': message})
#                         return redirect(f'{url}?{query_string}')

#                 # Check if the new schedule already exists
#                 if ScheduleFD.objects.filter(date=new_date.strftime('%B %d, %Y'), slot=new_time_str, room=new_lab, school_year=current_school_year).exists():
#                     conflict = "True"
#                     message = "Schedule already exists for the selected date, time, and room. Please choose a different slot."
#                     url = reverse('schedule_listFD')
#                     query_string = urlencode({'conflict': conflict, 'message': message})
#                     return redirect(f'{url}?{query_string}')

#                 # Mark the existing schedule as rescheduled
#                 schedule.has_been_rescheduled = True
#                 schedule.save()

#                 # Create the new schedule entry with the updated information
#                 new_schedule = ScheduleFD.objects.create(
#                     group=schedule.group,
#                     faculty1=schedule.faculty1,
#                     faculty2=schedule.faculty2,
#                     faculty3=schedule.faculty3,
#                     title=schedule.title,
#                     slot=new_time_str,
#                     date=new_date.strftime('%B %d, %Y'),
#                     day=f"Day {schedule.day.split()[1]}",  # Keep the same day number
#                     room=new_lab,
#                     adviser=schedule.adviser,
#                     capstone_teacher=schedule.capstone_teacher,
#                     school_year=current_school_year
#                 )

#                 # Log the action in AuditTrail
#                 AuditTrail.objects.create(
#                     user=request.user,
#                     action=f"Rescheduled Final Defense Group: {schedule.group} from {schedule.slot} on {schedule.date} ({schedule.day}) to {new_time_str} on {new_date.strftime('%B %d, %Y')} (Day {schedule.day.split()[1]})",
#                     ip_address=request.META.get('REMOTE_ADDR')
#                 )

#                 messages.success(request, 'Schedule rescheduled successfully.')
#                 return redirect('schedule_listFD')
#             except Exception as e:
#                 messages.error(request, f'Error during rescheduling: {e}')
#                 return redirect('schedule_listFD')
#         else:
#             messages.error(request, 'Please provide a date, time, and room.')
#             return redirect('schedule_listFD')
#     else:
#         messages.error(request, 'Invalid request method.')
#         return redirect('schedule_listFD')

#     return render(request, 'reassign_fd.html', {'schedule': schedule})

def reassignFD(request, schedule_id):
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
        new_date_str = request.POST.get('new_date')
        new_time_str = request.POST.get('new_time')
        new_lab_id = request.POST.get('new_lab')  # Fetch the room ID
        last_used_date_str = request.POST.get('last_used_date')  # Fetch the last used date

        if new_date_str and new_time_str and new_lab_id:
            try:
                new_date = datetime.strptime(new_date_str, '%Y-%m-%d')

                # Fetch the Room instance using the new_lab_id
                new_lab = get_object_or_404(Room, id=new_lab_id)

                # Get the earliest schedule date (the start date)
                earliest_schedule = ScheduleFD.objects.filter(school_year=selected_school_year).order_by('date').first()
                if not earliest_schedule:
                    messages.error(request, 'No schedules found for the current school year.')
                    return redirect('schedule_listFD')

                earliest_date = datetime.strptime(earliest_schedule.date, '%B %d, %Y')

                # Ensure new date is not earlier than the earliest schedule
                if new_date < earliest_date:
                    conflict = "True"
                    message = "Cannot reschedule to a date earlier than the original schedule."
                    url = reverse('schedule_listFD')
                    query_string = urlencode({'conflict': conflict, 'message': message, 'last_used_date': last_used_date_str})
                    return redirect(f'{url}?{query_string}')

                # Check if the new date is within one to two weeks from the earliest schedule date
                if not (earliest_date <= new_date <= earliest_date + timedelta(weeks=3)):
                    conflict = "True"
                    message = "Rescheduling is only allowed within one to three weeks from the original schedule."
                    url = reverse('schedule_listFD')
                    query_string = urlencode({'conflict': conflict, 'message': message, 'last_used_date': last_used_date_str})
                    return redirect(f'{url}?{query_string}')

                # Check if the new schedule already exists
                if ScheduleFD.objects.filter(date=new_date.strftime('%B %d, %Y'), slot=new_time_str, room=new_lab, school_year=selected_school_year).exists():
                    conflict = "True"
                    message = "Schedule already exists for the selected date, time, and room. Please choose a different slot."
                    url = reverse('schedule_listFD')
                    query_string = urlencode({'conflict': conflict, 'message': message, 'last_used_date': last_used_date_str})
                    return redirect(f'{url}?{query_string}')

                schedule = get_object_or_404(ScheduleFD, id=schedule_id)
                faculties = [schedule.faculty1, schedule.faculty2, schedule.faculty3]

                # Check if any faculty is double-booked for the new date and time
                for faculty in faculties:
                    if ScheduleFD.objects.filter(
                        date=new_date.strftime('%B %d, %Y'),
                        slot=new_time_str,
                        school_year=selected_school_year
                    ).filter(
                        (Q(faculty1=faculty) | Q(faculty2=faculty) | Q(faculty3=faculty))
                    ).exists():
                        conflict = "True"
                        message = f"Faculty {faculty.name} already has a schedule on {new_date.strftime('%B %d, %Y')} at {new_time_str}. Please choose a different slot or adjust the faculty assignment."
                        url = reverse('schedule_listFD')
                        query_string = urlencode({'conflict': conflict, 'message': message, 'last_used_date': last_used_date_str})
                        return redirect(f'{url}?{query_string}')

                # Calculate day_count excluding weekends
                current_date = earliest_date
                day_count = 0
                while current_date <= new_date:
                    if current_date.weekday() < 5:  # Only count weekdays (Mon-Fri)
                        day_count += 1
                    current_date += timedelta(days=1)
                
                print("day count (excluding weekends): ", day_count)
                
                # Mark the existing schedule as rescheduled
                schedule.has_been_rescheduled = True
                schedule.save()

                # Create the new schedule entry with the updated information
                new_schedule = ScheduleFD.objects.create(
                    group=schedule.group,
                    faculty1=schedule.faculty1,
                    faculty2=schedule.faculty2,
                    faculty3=schedule.faculty3,
                    title=schedule.title,
                    slot=new_time_str,
                    date=new_date.strftime('%B %d, %Y'),
                    day=f"Day {day_count}",  # Use the calculated day count
                    room=new_lab,
                    adviser=schedule.adviser,
                    capstone_teacher=schedule.capstone_teacher,
                    school_year=selected_school_year,
                    new_sched = True
                )

                # Log the action in AuditTrail
                AuditTrail.objects.create(
                    user=request.user,
                    action=f"Rescheduled Final Defense Group: {schedule.group} from {schedule.slot} on {schedule.date} ({schedule.day}) to {new_time_str} on {new_date.strftime('%B %d, %Y')} (Day {day_count})",
                    ip_address=request.META.get('REMOTE_ADDR')
                )

                # creating a notif
                Notif.objects.create(
                    created_by=request.user,
                    notif=f"This Group for the final defense: {schedule.group} has been rescheduled from {schedule.slot} on {schedule.date} ({schedule.day}) to {new_time_str} on {new_date.strftime('%B %d, %Y')} (Day {day_count})"
                )


                messages.success(request, 'Schedule rescheduled successfully.')
                # Redirect to schedule_listPOD with last_used_date included
                url = reverse('schedule_listFD')
                new_group=schedule.group
                query_string = urlencode({'last_used_date': last_used_date_str, 'new_group': new_group})
                return redirect(f'{url}?{query_string}')

            except Exception as e:
                messages.error(request, f'Error during rescheduling: {e}')
                # Include last_used_date in error redirect
                url = reverse('schedule_listFD')
                query_string = urlencode({'last_used_date': last_used_date_str})
                return redirect(f'{url}?{query_string}')
        else:
            messages.error(request, 'Please provide a date, time, and room.')
            # Include last_used_date in the redirect
            url = reverse('schedule_listFD')
            query_string = urlencode({'last_used_date': last_used_date_str})
            return redirect(f'{url}?{query_string}')
    else:
        messages.error(request, 'Invalid request method.')
        return redirect('schedule_listFD')

def faculty_tally_viewFD(request):
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
    # Initialize a dictionary to hold faculty assignments
    faculty_tally = defaultdict(lambda: defaultdict(int))

    # Get all schedules
    schedules = ScheduleFD.objects.filter(school_year=selected_school_year)

    # Count the number of groups each faculty is assigned as a panel member
    for schedule in schedules:
        # Extract the actual date from the string
        date_str = schedule.date  # Assuming date is in 'Month Day, Year' format
        date = datetime.strptime(date_str, '%B %d, %Y')  # Parse the date string
        weekday = date.strftime('%A')  # Get the day name, e.g., "Monday"

        # Count assignments for each faculty
        faculty_tally[schedule.faculty1.id][weekday] += 1
        faculty_tally[schedule.faculty2.id][weekday] += 1
        faculty_tally[schedule.faculty3.id][weekday] += 1

    # Prepare data for the template
    faculty_summary = []
    
    # To store the mapping of weekday to actual dates for this week
    week_dates = {}
    
    # Iterate through the schedules to create a mapping of weekday to actual dates
    for schedule in schedules:
        date_str = schedule.date
        date = datetime.strptime(date_str, '%B %d, %Y')
        weekday = date.strftime('%A')
        if weekday not in week_dates:
            week_dates[weekday] = date_str  # Store the first occurrence of the date for that weekday

    # Get all active faculty members and store them in a list for sorting later
    faculties = list(Faculty.objects.filter(is_active=True))

    for faculty in faculties:
        days = faculty_tally[faculty.id]
        adviser_count = Adviser.objects.filter(faculty=faculty).count()  # Get the adviser count

        row = {
            'faculty_name': faculty.name,
            'adviser_count': adviser_count,
            'monday_count': days.get('Monday', 0),
            'tuesday_count': days.get('Tuesday', 0),
            'wednesday_count': days.get('Wednesday', 0),
            'thursday_count': days.get('Thursday', 0),
            'friday_count': days.get('Friday', 0),
        }

        # Calculate total assignments including adviser count
        total = sum(row[day] for day in ['monday_count', 'tuesday_count', 'wednesday_count', 'thursday_count', 'friday_count']) #+ adviser_count
        row['total'] = total
        
        # Add actual dates for each weekday
        row['monday_date'] = week_dates.get('Monday', '')
        row['tuesday_date'] = week_dates.get('Tuesday', '')
        row['wednesday_date'] = week_dates.get('Wednesday', '')
        row['thursday_date'] = week_dates.get('Thursday', '')
        row['friday_date'] = week_dates.get('Friday', '')

        faculty_summary.append(row)

    # Sort the faculty summary based on years of teaching and degree criteria
    faculty_summary.sort(key=lambda x: (
        not next((f for f in faculties if f.name == x['faculty_name']), None).has_master_degree,  # Ensure those with a master's degree come first
        -next((f for f in faculties if f.name == x['faculty_name']), None).years_of_teaching,     # Sort by years of teaching in descending order
        next((f for f in faculties if f.name == x['faculty_name']), None).highest_degree         # Sort by highest degree in ascending order (if needed)
    ))

    context = {
        'faculty_summary': faculty_summary,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
    }

    return render(request, 'admin/final/faculty_tally.html', context)

def reset_scheduleFD(request):
    # get the last added school year in the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # get the current active school year
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

    ScheduleFD.objects.filter(school_year=selected_school_year).delete()
    # Log the action in AuditTrail
    AuditTrail.objects.create(
        user=request.user,
        action=f"Schedule for the Final Defense has been reset to none",
        ip_address=request.META.get('REMOTE_ADDR')
    )

    # creating a notif
    Notif.objects.create(
        created_by=request.user,
        notif=f"Schedule for the Final Defense has been reset to none"
    )
    return redirect('schedule_listFD')


# function to view the preoral grade  of a specific group in the admin side
@login_required
def final_grade_view(request, title_id):
    # Fetch the CustomUser object associated with the logged-in user
    user_profile = get_object_or_404(CustomUser, id=request.user.id)

    # If the user is a superuser, use the user profile as the faculty member
    if request.user.is_superuser:
        faculty_member = user_profile  # Use user_profile if superuser
    else:
        # If not a superuser, fetch the Faculty object associated with the CustomUser
        faculty_member = get_object_or_404(Faculty, custom_user=user_profile)

    # Get all available school years
    school_years = SchoolYear.objects.all().order_by('start_year')
    if school_years.count() == 0:
        SchoolYear.create_new_school_year()
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

    temp = get_object_or_404(GroupInfoFD, id=title_id)
    title = temp.title
    adviser = get_object_or_404(Adviser, approved_title=title, school_year=selected_school_year)
    adviser_id = adviser.approved_title
     
    # Fetch grades with the same title
    groups = GroupInfoFD.objects.filter(title=title, school_year=selected_school_year)
    
    adviser_id2=adviser.id
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
        
        # Try to find an existing PreOral_Recos record with the same title
        reco = Final_Recos.objects.filter(project_title=title, school_year=selected_school_year).first()
        
        if reco:
            # If recommendation record exists, update the recommendation
            reco.recommendation = recommendation
            if recommendation == "":
                print("Empty reco")
                reco.recommendation = recommendation
                reco.delete()
            else:
                reco.recommendation = recommendation
                # Save the recommendation record (updated)
                print("empyt also")
                reco.save()
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
        
        
        
        print(f"Redirecting with adviser_id: {adviser_id}")  # Debugging line
        return redirect('adviser_record_detail', adviser_id=adviser_id)
    
    # Fetch grades with the same title
    grades = Final_Grade.objects.filter(project_title=title, school_year=selected_school_year)
    groups = GroupInfoFD.objects.filter(title=title, school_year=selected_school_year)
    criteria_list = Final_EvaluationSection.objects.filter(school_year=selected_school_year).annotate(total_criteria_percentage=Sum('fcriteria__percentage'))
    criteria_percentage = Final_Criteria.objects.filter(school_year=selected_school_year)
    total_points = sum(criteria.percentage for criteria in criteria_percentage)
    adviser_records = ''
    if not request.user.is_superuser:
        adviser_records = Adviser.objects.filter(faculty=faculty_member, school_year=selected_school_year, accepted=True)
    
    if not grades.exists():
        member1 = groups.first().member1 if groups.exists() else None
        member2 = groups.first().member2 if groups.exists() else None
        member3 = groups.first().member3 if groups.exists() else None
        return render(request, 'faculty/final_grade/adviser_record_detailFD.html', {
            'error': 'No records found for this title',
            'title': title, 
            'member1': member1, 
            'member2': member2, 
            'member3': member3,
            'adviser': adviser,
            'recos': recos,
            'faculty_member': faculty_member,
            # 'current_school_year': current_school_year,
            'selected_school_year': selected_school_year,
            'last_school_year': last_school_year,
            'school_years': school_years,
            'adviser_records': adviser_records
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
    if total_grade1 is not None and grades.count() is not 0:
        average_grade1 = total_grade1 / 3
        print('the grade is no 0')
        
    else:
        average_grade1 = 0  # Handle the case where no grades exist
        print('the grade is 0')
    print('member grade1', average_grade1)

    #grade for the member2
    if total_grade2 is not None and grades.count() is not 0:
        average_grade2 = total_grade2 / 3
        print('the grade is no 0')
        
    else:
        average_grade2 = 0  # Handle the case where no grades exist
        print('the grade is 0')
    print('member grade3', average_grade2)

    #grade for the member3
    if total_grade3 is not None and grades.count() is not 0:
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
        'all_checkboxes': Final_Checkbox.objects.all(),
        'final_grade_record': final_grade_record,
        'checkbox_entry': checkbox_entry,
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'school_years': school_years,
        'adviser_records': adviser_records
    }
    
    return render(request, 'faculty/final_grade/adviser_record_detailFD.html', context)


def carousel_view(request):
    # current_school_year = SchoolYear.get_active_school_year()selected_school_year_id = request.session.get('selected_school_year_id')
    # get the last school year added to the db
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

    group_info_list = GroupInfoTH.objects.filter(school_year=selected_school_year).order_by('-created_at')
    group_infoPOD = GroupInfoPOD.objects.filter(school_year=selected_school_year).order_by('-created_at')
    group_infoMD = GroupInfoMD.objects.filter(school_year=selected_school_year).order_by('-created_at')
    group_infoFD = GroupInfoFD.objects.filter(school_year=selected_school_year).order_by('-created_at')

    teachers = Faculty.objects.filter(is_active=True)
    
    schedules = Schedule.objects.filter(school_year=selected_school_year)  
    schedules_pod = SchedulePOD.objects.filter(school_year=selected_school_year)
    schedules_md = ScheduleMD.objects.filter(school_year=selected_school_year)
    schedules_fd = ScheduleFD.objects.filter(school_year=selected_school_year)

    paginator_group_info_list = Paginator(group_info_list, 20)
    paginator_group_infoPOD = Paginator(group_infoPOD, 20)
    paginator_group_infoMD = Paginator(group_infoMD, 20)
    paginator_group_infoFD = Paginator(group_infoFD, 20)

    page_number_group_info_list = request.GET.get('page_group_info_list', 1)
    page_number_group_infoPOD = request.GET.get('page_group_infoPOD', 1)
    page_number_group_infoMD = request.GET.get('page_group_infoMD', 1)
    page_number_group_infoFD = request.GET.get('page_group_infoFD', 1)

    page_group_info_list = paginator_group_info_list.get_page(page_number_group_info_list)
    page_group_infoPOD = paginator_group_infoPOD.get_page(page_number_group_infoPOD)
    page_group_infoMD = paginator_group_infoMD.get_page(page_number_group_infoMD)
    page_group_infoFD = paginator_group_infoFD.get_page(page_number_group_infoFD)

    forms = {group.id: GroupInfoPODEditForm(instance=group) for group in group_infoPOD}
    md_forms = {mgroup.id: GroupInfoMDEditForm(instance=mgroup) for mgroup in group_infoMD}
    fd_forms = {fgroup.id: GroupInfoFDEditForm(instance=fgroup) for fgroup in group_infoFD}

    # Create a dictionary to map thgroups to their schedules
    group_schedules = {schedule.group.id: schedule for schedule in schedules}

    # Create a dictionary to map podgroups to their schedules
    group_schedules_pod = {schedule.group.id: schedule for schedule in schedules_pod}

    # Create a dictionary to map mdgroups to their schedules
    group_schedules_md = {schedule.group.id: schedule for schedule in schedules_md}

    # Create a dictionary to map fdgroups to their schedules
    group_schedules_fd = {schedule.group.id: schedule for schedule in schedules_fd}

    last_school_year = SchoolYear.objects.all().order_by('-end_year').first()
    current_school_year = SchoolYear.get_active_school_year()
    # Get all available school years
    school_years = SchoolYear.objects.all().order_by('start_year')
    if school_years.count() == 0:
        SchoolYear.create_new_school_year()
        school_years = SchoolYear.objects.all().order_by('start_year')
    
    error_message = request.GET.get('error_message')
    print("error_message: ",error_message)

    context = {
        'group_info_list': page_group_info_list,
        'group_infoPOD': page_group_infoPOD,
        'group_infoMD': page_group_infoMD,
        'group_infoFD': page_group_infoFD,
        'forms': forms,
        'md_forms': md_forms,
        'fd_forms': fd_forms,
        'teachers': teachers,
        'group_schedules': group_schedules,
        'group_schedules_pod': group_schedules_pod,
        'group_schedules_md': group_schedules_md,
        'group_schedules_fd': group_schedules_fd,
        'school_years': school_years, 
        # 'current_school_year': current_school_year,
        'selected_school_year': selected_school_year,
        'last_school_year': last_school_year,
        'error_message': error_message
    }
    return render(request, 'carousel.html', context)


