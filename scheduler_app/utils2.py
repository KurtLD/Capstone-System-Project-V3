import logging
import random
from collections import defaultdict, deque
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from .models import GroupInfoPOD, Faculty, SchedulePOD, Schedule, Room
from datetime import datetime, timedelta
from users.models import SchoolYear
import re

# Set up logging
logger = logging.getLogger(__name__)

# def normalize_members(members):
#     """Normalize member names for comparison."""
#     return sorted([member.strip().lower() for member in members if member])

def normalize_members(members):
    """
    Normalize member names for comparison.
    Ensures consistent formatting and removes trailing initials like 'A.'.
    """
    def clean_name(name):
        # Remove trailing initials (e.g., 'A.' or 'B.') using regex
        name = re.sub(r'\s+[A-Z]\.$', '', name.strip())
        return name.lower()

    return sorted([clean_name(member) for member in members if member])

def remove_faculties(excluded_faculty1, excluded_faculty2, members_pod, faculty_bookings, day, slot, faculty_loads):
    """
    Selectively replaces conflicting faculties while retaining the original order as much as possible.
    Ensures the final panel includes a validated lead faculty, fills up with available faculties
    to reach three members, and integrates load balancing during selection.
    """
    current_school_year = SchoolYear.get_active_school_year()
    schedules = Schedule.objects.filter(school_year=current_school_year, has_been_rescheduled=False)
    prev_panel = []

    # Convert excluded_faculty1 and excluded_faculty2 to sets of IDs
    excluded_faculty1_ids = {fac.id if hasattr(fac, 'id') else fac for fac in excluded_faculty1}
    excluded_faculty2_ids = {fac.id if hasattr(fac, 'id') else fac for fac in excluded_faculty2}
    all_excluded_ids = excluded_faculty1_ids | excluded_faculty2_ids

    # Step 1: Identify the previous panel for the given members pod
    for schedule in schedules:
        members_schedule = schedule.get_members()
        pod_normalized = set(normalize_members(members_pod))
        schedule_normalized = set(normalize_members(members_schedule))

        if pod_normalized & schedule_normalized:  # Check if any record exists in both sets
            prev_panel.extend(schedule.get_faculties_by_members())
            # print("Match found:")
            # print("prev_panel:", prev_panel)
            # print("members_schedule:", members_schedule)
            # print("members_pod:", members_pod)
            break
        # else:
        #     print("No match found:")
        #     print("prev_panel:", prev_panel)
        #     print("members_schedule:", members_schedule)
        #     print("members_pod:", members_pod)

    # Step 2: Replace conflicting faculties while retaining original order
    new_panel = []
    for faculty in prev_panel:
        faculty_id = faculty.id if hasattr(faculty, 'id') else faculty
        if faculty_id in all_excluded_ids:
            # Replace conflicting faculty
            available_faculties = Faculty.objects.filter(is_active=True).exclude(
                id__in=all_excluded_ids | {f.id if hasattr(f, 'id') else f for f in new_panel}
            )
            sorted_faculties = sorted(available_faculties, key=lambda f: faculty_loads[f.id])
            replacement = next(iter(sorted_faculties), None)
            new_panel.append(replacement if replacement else None)
        else:
            # Retain non-conflicting faculty
            new_panel.append(faculty)

    # Step 3: Fill up gaps to ensure three members in the panel
    if len(new_panel) < 3:
        available_faculties = Faculty.objects.filter(is_active=True).exclude(
            id__in=all_excluded_ids | {f.id if hasattr(f, 'id') else f for f in new_panel}
        )
        sorted_faculties = sorted(available_faculties, key=lambda f: faculty_loads[f.id])

        for faculty in sorted_faculties:
            if len(new_panel) < 3:
                new_panel.append(faculty)
            else:
                break

    # Ensure no gaps remain in the panel by replacing `None` with additional faculties if needed
    new_panel = [f for f in new_panel if f]  # Remove any `None` entries
    while len(new_panel) < 3:
        available_faculty = Faculty.objects.filter(is_active=True).exclude(
            id__in={f.id if hasattr(f, 'id') else f for f in new_panel}
        ).first()
        if available_faculty:
            new_panel.append(available_faculty)
        else:
            break

    # Step 4: Validate and finalize the panel with lead faculty criteria while retaining order
    final_panel = validate_lead_faculty(new_panel[:3])  # Ensure exactly three members and validate the lead faculty

    return final_panel



def validate_lead_faculty(panel):
    """Ensure the lead faculty (first in list) has a master’s degree, highest years of teaching, or highest degree.
       Retain original order when criteria are equal."""
    if not panel:
        return panel

    # Create a mapping for highest degree to a numeric scale
    degree_order = {
        "Doctor of Philosophy (PhD)": 5,
        "Doctor of Education (EdD)": 5,
        "Specialist Degree (EdS)": 4,
        "Professional Doctorates": 4,
        "Master's": 3,
        "Bachelor's": 2,
        "None": 0  # Assuming "None" if no degree is provided
    }

    # Save the original order for fallback sorting
    indexed_panel = [(i, f) for i, f in enumerate(panel)]

    # Sort with fallback to original order
    indexed_panel.sort(key=lambda x: (
        not x[1].has_master_degree,  # Faculty with master's degree should come first
        -x[1].years_of_teaching,    # Faculty with highest teaching years next
        -degree_order.get(x[1].highest_degree, 0),  # Convert degree string to numeric value, default to 0 if not found
        x[0]                        # Retain original order in case of ties
    ))

    # Extract the sorted faculty members
    sorted_panel = [item[1] for item in indexed_panel]
    return sorted_panel


def generate_schedulePOD(request, start_date):
    try:
        logger.info("Starting schedule generation...")

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

        # Clear existing schedules
        SchedulePOD.objects.filter(school_year=selected_school_year).delete()
        logger.debug("Existing schedules cleared.")

        groups = list(GroupInfoPOD.objects.filter(school_year=selected_school_year))
        random.shuffle(groups)
        logger.debug(f"Fetched {len(groups)} groups for scheduling.")
        
        faculties = list(Faculty.objects.filter(is_active=True))
        logger.debug(f"Loaded {len(faculties)} active faculties.")

        # Initialize assignment tracking
        faculty_loads = defaultdict(int)  # Track total assignments per faculty
        daily_loads = defaultdict(lambda: defaultdict(int))  # Track daily loads to balance within each day
        time_slots = ['8AM-9:30AM', '9:30AM-11AM', '12PM-01:30PM', '1:30PM-3PM', '3PM-4:30PM', '4:30PM-5PM', '5PM-6:30PM']
        rooms = Room.objects.all().order_by("status")

        assignments = []
        faculty_bookings = defaultdict(lambda: defaultdict(set))  # faculty_id -> day -> slot
        conflict_groups = deque(groups)

        day_offset = 0
        actual_day_counter = 0  # Track actual scheduling days

        while conflict_groups:
            # Calculate the current date
            current_date = start_date + timedelta(days=day_offset)

            # Skip weekends
            if current_date.weekday() in (5, 6):  # Skip Saturday and Sunday
                day_offset += 1
                continue

            # Adjust for Monday's first time slot skip
            slots_to_schedule = time_slots if current_date.weekday() != 0 else time_slots[1:]

            assigned_today = False

            for slot in slots_to_schedule:
                for room in rooms:
                    for _ in range(len(conflict_groups)):
                        group = conflict_groups.popleft()
                        excluded_faculty1 = {group.capstone_teacher}
                        excluded_faculty2 = {group.adviser}
                        members_pod = group.get_members()

                        assigned_faculty = remove_faculties(
                            excluded_faculty1, excluded_faculty2, members_pod, 
                            faculty_bookings, current_date.strftime('%B %d, %Y'), slot, faculty_loads
                        )

                        print("assigned_faculty: ", assigned_faculty)

                        # Ensure at least one faculty has a master's degree
                        if not any(faculty.has_master_degree for faculty in assigned_faculty):
                            logger.warning(f"Group {group} cannot be assigned due to lack of master's degree.")
                            conflict_groups.append(group)
                            continue

                        # Check for double booking conflicts
                        if any(slot in faculty_bookings[faculty.id][current_date.strftime('%B %d, %Y')] for faculty in assigned_faculty) or \
                            slot in faculty_bookings[group.adviser.id][current_date.strftime('%B %d, %Y')] or \
                            slot in faculty_bookings[group.capstone_teacher.id][current_date.strftime('%B %d, %Y')]:
                            conflict_groups.append(group)
                            continue

                        # Assign the group if no conflicts
                        for faculty in assigned_faculty:
                            faculty_bookings[faculty.id][current_date.strftime('%B %d, %Y')].add(slot)
                            faculty_loads[faculty.id] += 1  # Track total assignments
                            daily_loads[current_date][faculty.id] += 1  # Track daily assignments
                        faculty_bookings[group.adviser.id][current_date.strftime('%B %d, %Y')].add(slot)
                        faculty_bookings[group.capstone_teacher.id][current_date.strftime('%B %d, %Y')].add(slot)

                        assignments.append({
                            'group': group,
                            'title': group.title,
                            'faculties': assigned_faculty,
                            'slot': slot,
                            'date': current_date.strftime('%B %d, %Y'),
                            'room': room,
                            'day_label': f"Day {actual_day_counter + 1}"  # Track actual day
                        })

                        logger.debug(f"Assignment created for group {group}: {assignments[-1]}")
                        assigned_today = True
                        break  # Move to the next room after successful assignment

                if len(assignments) >= len(groups):
                    break  # Break outer loop if all groups are assigned

            # Only increment the actual day counter if there were assignments
            if assigned_today:
                actual_day_counter += 1

            # If still conflict groups exist, we need to move to the next day
            if conflict_groups:
                day_offset += 1
            else:
                break  # Break if all groups are successfully scheduled

        # Save assignments to the database in a transaction
        with transaction.atomic():
            logger.info("Starting transaction to save schedules.")
            SchedulePOD.objects.bulk_create([
                SchedulePOD(
                    group=assignment['group'],
                    title=assignment['title'],
                    faculty1=assignment['faculties'][0],
                    faculty2=assignment['faculties'][1],
                    faculty3=assignment['faculties'][2],
                    slot=assignment['slot'],
                    date=assignment['date'],
                    room=assignment['room'],
                    adviser=assignment['group'].adviser,
                    capstone_teacher=assignment['group'].capstone_teacher,
                    day=assignment['day_label'],
                    school_year=selected_school_year
                )
                for assignment in assignments
            ])
            logger.info("Transaction completed successfully.")
            print("Scheduling completed successfully.")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        print(f"An error occurred: {e}")

def get_faculty_assignmentsPOD():
    """Retrieve a summary of faculty assignments, sorted by teaching experience."""
    faculty_assignments = {faculty.id: 0 for faculty in Faculty.objects.all()}

    current_school_year = SchoolYear.get_active_school_year()
    # selected_school_year_id = request.session.get('selected_school_year_id')
    # # get the last school year added to the db
    # last_school_year = SchoolYear.objects.all().order_by('-end_year').first()

    # # Get the selected school year from session or fallback to the active school year
    # selected_school_year = ''
    # if not selected_school_year_id:
    #     selected_school_year = last_school_year
    #     request.session['selected_school_year_id'] = selected_school_year.id  # Set in session
    # else:
    #     # Retrieve the selected school year based on the session
    #     selected_school_year = SchoolYear.objects.get(id=selected_school_year_id)

    schedules = SchedulePOD.objects.filter(school_year=current_school_year)

    for schedule in schedules:
        for faculty_id in [schedule.faculty1.id, schedule.faculty2.id, schedule.faculty3.id]:
            faculty_assignments[faculty_id] += 1

    faculty_list = []
    for faculty in Faculty.objects.all():
        faculty_list.append({
            'faculty_id': faculty.id,
            'name': faculty.name,
            'years': faculty.years_of_teaching,
            'assignments': faculty_assignments.get(faculty.id, 0)
        })

    faculty_list.sort(key=lambda x: x['years'], reverse=True)

    return faculty_list


